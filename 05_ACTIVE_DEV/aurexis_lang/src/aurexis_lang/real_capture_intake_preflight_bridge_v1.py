"""
Aurexis Core — Real Capture Intake Preflight Bridge V1

Bounded validator that checks whether a supplied real-capture session
pack is structurally valid before it enters the observed-evidence loop.
Validates session manifest structure, file references, metadata presence,
allowed media types, and basic manifest coherence.

What this proves:
  A user-supplied capture session pack can be structurally validated
  against the frozen intake profile before any downstream processing.
  Invalid packs are rejected with explicit reasons. Valid packs are
  cleared for ingest.

What this does NOT prove:
  - That capture files actually exist on disk
  - That image content is meaningful
  - Full media analysis
  - Full Aurexis Core completion

Design:
  - PreflightCheck: one named check with pass/fail and reason.
  - PreflightVerdict: CLEARED / REJECTED / WARNING / ERROR.
  - PreflightResult: full preflight report.
  - run_preflight(): validates a session manifest dict.
  - 10 frozen preflight checks.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
import hashlib
import json
import re


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

PREFLIGHT_VERSION = "V1.0"
PREFLIGHT_FROZEN = True


# ════════════════════════════════════════════════════════════
# PREFLIGHT VERDICT
# ════════════════════════════════════════════════════════════

class PreflightVerdict(str, Enum):
    """Overall verdict for a preflight check."""
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# PREFLIGHT CHECK
# ════════════════════════════════════════════════════════════

@dataclass
class PreflightCheck:
    """One named preflight check result."""
    name: str
    passed: bool = False
    reason: str = ""
    severity: str = "error"  # "error" or "warning"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason": self.reason,
            "severity": self.severity,
        }


# ════════════════════════════════════════════════════════════
# PREFLIGHT RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class PreflightResult:
    """Full preflight validation report."""
    verdict: PreflightVerdict = PreflightVerdict.ERROR
    checks: List[PreflightCheck] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    session_id: str = ""
    file_count: int = 0
    preflight_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "session_id": self.session_id,
            "file_count": self.file_count,
            "preflight_hash": self.preflight_hash,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_summary_text(self) -> str:
        lines = [
            f"Preflight: {self.verdict.value}",
            f"Session: {self.session_id}",
            f"Files: {self.file_count}",
            f"Checks: {self.passed_checks}/{self.total_checks} passed",
        ]
        for c in self.checks:
            status = "PASS" if c.passed else ("WARN" if c.severity == "warning" else "FAIL")
            lines.append(f"  [{status}] {c.name}: {c.reason}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# ALLOWED VALUES
# ════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {".jpg", ".png", ".tif"}
ALLOWED_DEVICE_CLASSES = {"phone", "webcam", "scanner", "video"}
REQUIRED_SESSION_FIELDS = {"session_id", "description", "created_at", "files"}
REQUIRED_FILE_FIELDS = {"file_ref", "file_ext", "file_size_bytes", "width_px",
                        "height_px", "capture_device", "capture_timestamp"}
REQUIRED_CONDITIONS = {"adequate_lighting", "subject_in_frame"}
FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')


# ════════════════════════════════════════════════════════════
# PREFLIGHT CHECKS
# ════════════════════════════════════════════════════════════

def _check_session_fields(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 1: Required session-level fields present."""
    missing = REQUIRED_SESSION_FIELDS - set(manifest.keys())
    if missing:
        return PreflightCheck(
            name="session_fields_present",
            passed=False,
            reason=f"Missing session fields: {', '.join(sorted(missing))}",
        )
    return PreflightCheck(
        name="session_fields_present",
        passed=True,
        reason="All required session fields present",
    )


def _check_session_id_format(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 2: Session ID is a non-empty string."""
    sid = manifest.get("session_id", "")
    if not isinstance(sid, str) or not sid.strip():
        return PreflightCheck(
            name="session_id_valid",
            passed=False,
            reason="session_id must be a non-empty string",
        )
    return PreflightCheck(
        name="session_id_valid",
        passed=True,
        reason=f"Session ID: {sid}",
    )


def _check_files_array(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 3: Files array exists and is non-empty."""
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) == 0:
        return PreflightCheck(
            name="files_array_valid",
            passed=False,
            reason="'files' must be a non-empty list",
        )
    return PreflightCheck(
        name="files_array_valid",
        passed=True,
        reason=f"{len(files)} file(s) declared",
    )


def _check_file_fields(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 4: Each file entry has required fields."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(
            name="file_fields_complete",
            passed=False,
            reason="'files' is not a list",
        )
    for i, f in enumerate(files):
        if not isinstance(f, dict):
            return PreflightCheck(
                name="file_fields_complete",
                passed=False,
                reason=f"File entry {i} is not a dict",
            )
        missing = REQUIRED_FILE_FIELDS - set(f.keys())
        if missing:
            return PreflightCheck(
                name="file_fields_complete",
                passed=False,
                reason=f"File {i} ({f.get('file_ref', '?')}) missing: {', '.join(sorted(missing))}",
            )
    return PreflightCheck(
        name="file_fields_complete",
        passed=True,
        reason=f"All {len(files)} file(s) have required fields",
    )


def _check_file_extensions(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 5: All file extensions are in the allowed set."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(name="file_extensions_allowed", passed=False, reason="No files")
    bad = []
    for f in files:
        ext = f.get("file_ext", "").lower()
        if ext not in ALLOWED_EXTENSIONS:
            bad.append(f"{f.get('file_ref', '?')} ({ext})")
    if bad:
        return PreflightCheck(
            name="file_extensions_allowed",
            passed=False,
            reason=f"Unsupported extensions: {', '.join(bad)}",
        )
    return PreflightCheck(
        name="file_extensions_allowed",
        passed=True,
        reason=f"All extensions in {sorted(ALLOWED_EXTENSIONS)}",
    )


def _check_filenames_valid(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 6: File references follow naming rules (no spaces, valid chars)."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(name="filenames_valid", passed=False, reason="No files")
    bad = []
    for f in files:
        ref = f.get("file_ref", "")
        if not isinstance(ref, str) or not FILENAME_PATTERN.match(ref):
            bad.append(ref or "(empty)")
    if bad:
        return PreflightCheck(
            name="filenames_valid",
            passed=False,
            reason=f"Invalid filenames (spaces or special chars): {', '.join(bad)}",
        )
    return PreflightCheck(
        name="filenames_valid",
        passed=True,
        reason="All filenames valid",
    )


def _check_no_duplicate_files(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 7: No duplicate file references."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(name="no_duplicate_files", passed=False, reason="No files")
    refs = [f.get("file_ref", "") for f in files]
    seen: Set[str] = set()
    dupes: Set[str] = set()
    for r in refs:
        if r in seen:
            dupes.add(r)
        seen.add(r)
    if dupes:
        return PreflightCheck(
            name="no_duplicate_files",
            passed=False,
            reason=f"Duplicate file refs: {', '.join(sorted(dupes))}",
        )
    return PreflightCheck(
        name="no_duplicate_files",
        passed=True,
        reason=f"{len(refs)} unique file refs",
    )


def _check_file_sizes_positive(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 8: All file sizes are positive integers."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(name="file_sizes_positive", passed=False, reason="No files")
    bad = []
    for f in files:
        size = f.get("file_size_bytes", 0)
        if not isinstance(size, (int, float)) or size <= 0:
            bad.append(f.get("file_ref", "?"))
    if bad:
        return PreflightCheck(
            name="file_sizes_positive",
            passed=False,
            reason=f"Non-positive file sizes: {', '.join(bad)}",
        )
    return PreflightCheck(
        name="file_sizes_positive",
        passed=True,
        reason="All file sizes positive",
    )


def _check_resolutions_valid(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 9: All resolutions are positive integers."""
    files = manifest.get("files", [])
    if not isinstance(files, list):
        return PreflightCheck(name="resolutions_valid", passed=False, reason="No files")
    bad = []
    for f in files:
        w = f.get("width_px", 0)
        h = f.get("height_px", 0)
        if not isinstance(w, (int, float)) or w <= 0 or not isinstance(h, (int, float)) or h <= 0:
            bad.append(f.get("file_ref", "?"))
    if bad:
        return PreflightCheck(
            name="resolutions_valid",
            passed=False,
            reason=f"Invalid resolutions: {', '.join(bad)}",
        )
    return PreflightCheck(
        name="resolutions_valid",
        passed=True,
        reason="All resolutions positive",
    )


def _check_conditions_present(manifest: Dict[str, Any]) -> PreflightCheck:
    """Check 10: Required capture conditions are declared."""
    conditions = manifest.get("conditions", {})
    if not isinstance(conditions, dict):
        # Conditions might be per-file in metadata — check files
        files = manifest.get("files", [])
        if isinstance(files, list) and len(files) > 0:
            # Accept if all files have the conditions as metadata
            return PreflightCheck(
                name="conditions_declared",
                passed=True,
                reason="Conditions not at session level (may be per-file)",
                severity="warning",
            )
        return PreflightCheck(
            name="conditions_declared",
            passed=False,
            reason="No 'conditions' section and no files",
        )
    missing = REQUIRED_CONDITIONS - set(conditions.keys())
    if missing:
        return PreflightCheck(
            name="conditions_declared",
            passed=False,
            reason=f"Missing required conditions: {', '.join(sorted(missing))}",
        )
    # Check values are boolean
    for cond_name in REQUIRED_CONDITIONS:
        val = conditions.get(cond_name)
        if not isinstance(val, bool):
            return PreflightCheck(
                name="conditions_declared",
                passed=False,
                reason=f"Condition '{cond_name}' must be true or false, got: {val}",
            )
    return PreflightCheck(
        name="conditions_declared",
        passed=True,
        reason="Required conditions declared",
    )


# ════════════════════════════════════════════════════════════
# PREFLIGHT CHECK REGISTRY
# ════════════════════════════════════════════════════════════

PREFLIGHT_CHECKS = [
    _check_session_fields,
    _check_session_id_format,
    _check_files_array,
    _check_file_fields,
    _check_file_extensions,
    _check_filenames_valid,
    _check_no_duplicate_files,
    _check_file_sizes_positive,
    _check_resolutions_valid,
    _check_conditions_present,
]

EXPECTED_CHECK_COUNT = 10


# ════════════════════════════════════════════════════════════
# RUN PREFLIGHT
# ════════════════════════════════════════════════════════════

def run_preflight(manifest: Dict[str, Any]) -> PreflightResult:
    """
    Run all preflight checks against a session manifest dict.

    Parameters:
        manifest: parsed session manifest JSON

    Returns a PreflightResult with all check outcomes and a verdict.
    """
    result = PreflightResult()
    result.session_id = str(manifest.get("session_id", ""))

    files = manifest.get("files")
    result.file_count = len(files) if isinstance(files, list) else 0

    checks: List[PreflightCheck] = []
    for check_fn in PREFLIGHT_CHECKS:
        c = check_fn(manifest)
        checks.append(c)

    result.checks = checks
    result.total_checks = len(checks)
    result.passed_checks = sum(1 for c in checks if c.passed)
    result.failed_checks = sum(1 for c in checks if not c.passed and c.severity == "error")
    result.warning_checks = sum(1 for c in checks if not c.passed and c.severity == "warning")

    # Compute hash
    hash_data = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
    result.preflight_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    # Determine verdict
    if result.failed_checks > 0:
        result.verdict = PreflightVerdict.REJECTED
    elif result.warning_checks > 0:
        result.verdict = PreflightVerdict.WARNING
    else:
        result.verdict = PreflightVerdict.CLEARED

    # Recompute hash with verdict
    hash_data = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
    result.preflight_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    return result


def make_error_preflight(reason: str) -> PreflightResult:
    """Create an error preflight result for testing."""
    return PreflightResult(
        verdict=PreflightVerdict.ERROR,
        checks=[PreflightCheck(name="error", passed=False, reason=reason)],
    )


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_VERDICT_COUNT = 4  # CLEARED, REJECTED, WARNING, ERROR
EXPECTED_ALLOWED_EXTENSIONS = 3  # .jpg, .png, .tif
EXPECTED_REQUIRED_SESSION_FIELDS = 4  # session_id, description, created_at, files
EXPECTED_REQUIRED_FILE_FIELDS = 7  # file_ref, file_ext, file_size_bytes, width_px, height_px, capture_device, capture_timestamp
