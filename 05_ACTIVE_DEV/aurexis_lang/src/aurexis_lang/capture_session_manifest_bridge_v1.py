"""
Aurexis Core — Capture Session Manifest Bridge V1

Deterministic manifest surface for observed capture sessions.
Tracks session identity, capture set membership, evidence tier,
timestamps, device metadata, and source file references.

What this proves:
  A bounded capture session can be described by a deterministic
  manifest that links capture files, their ingest results, device
  metadata, and evidence tier entries into a single auditable record.
  The manifest is both human-readable (to_summary) and machine-readable
  (to_dict / to_json). The manifest hash is deterministic.

What this does NOT prove:
  - That actual capture files exist on disk
  - Full media management or DAM capability
  - Full Aurexis Core completion

Design:
  - CaptureFileRecord: frozen record for one ingested file.
  - CaptureSessionManifest: mutable session collecting file records.
  - finalize() freezes the session and computes manifest hash.
  - SessionManifestVerdict: VALID / EMPTY / INCOMPLETE / ERROR.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import hashlib
import json
import time


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

SESSION_MANIFEST_VERSION = "V1.0"
SESSION_MANIFEST_FROZEN = True


# ════════════════════════════════════════════════════════════
# CAPTURE FILE RECORD
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CaptureFileRecord:
    """
    Record of one capture file admitted into a session.

    file_ref: opaque file reference (path or URI)
    file_ext: file extension including dot
    file_size_bytes: file size
    width_px: image width
    height_px: image height
    ingest_case_name: which IngestCase matched
    evidence_tier: evidence tier entry value
    capture_device: device identifier
    capture_timestamp: ISO-8601 or epoch timestamp string
    metadata: additional metadata dict (frozen after creation)
    """
    file_ref: str
    file_ext: str
    file_size_bytes: int
    width_px: int
    height_px: int
    ingest_case_name: str
    evidence_tier: str = "real-capture"
    capture_device: str = ""
    capture_timestamp: str = ""
    metadata: Tuple[Tuple[str, str], ...] = ()

    def metadata_dict(self) -> Dict[str, str]:
        return dict(self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_ref": self.file_ref,
            "file_ext": self.file_ext,
            "file_size_bytes": self.file_size_bytes,
            "resolution": f"{self.width_px}x{self.height_px}",
            "ingest_case_name": self.ingest_case_name,
            "evidence_tier": self.evidence_tier,
            "capture_device": self.capture_device,
            "capture_timestamp": self.capture_timestamp,
            "metadata": self.metadata_dict(),
        }


# ════════════════════════════════════════════════════════════
# SESSION MANIFEST VERDICT
# ════════════════════════════════════════════════════════════

class SessionManifestVerdict(str, Enum):
    """Result of validating or finalizing a session manifest."""
    VALID = "VALID"
    EMPTY = "EMPTY"
    INCOMPLETE = "INCOMPLETE"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# SESSION SUMMARY
# ════════════════════════════════════════════════════════════

@dataclass
class SessionSummary:
    """Aggregate statistics for a capture session."""
    verdict: SessionManifestVerdict = SessionManifestVerdict.ERROR
    session_id: str = ""
    file_count: int = 0
    total_bytes: int = 0
    unique_devices: int = 0
    device_list: List[str] = field(default_factory=list)
    ingest_case_breakdown: Dict[str, int] = field(default_factory=dict)
    evidence_tier: str = ""
    manifest_hash: str = ""
    finalized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "session_id": self.session_id,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "unique_devices": self.unique_devices,
            "device_list": self.device_list,
            "ingest_case_breakdown": self.ingest_case_breakdown,
            "evidence_tier": self.evidence_tier,
            "manifest_hash": self.manifest_hash,
            "finalized": self.finalized,
        }


# ════════════════════════════════════════════════════════════
# CAPTURE SESSION MANIFEST
# ════════════════════════════════════════════════════════════

class CaptureSessionManifest:
    """
    Mutable manifest for a capture session. Call finalize() to freeze.

    session_id: unique identifier for this session
    description: human-readable description
    created_at: creation timestamp
    """

    def __init__(
        self,
        session_id: str,
        description: str = "",
        created_at: str = "",
    ):
        self.session_id = session_id
        self.description = description
        self.created_at = created_at or str(int(time.time()))
        self._records: List[CaptureFileRecord] = []
        self._finalized = False
        self._manifest_hash = ""

    @property
    def finalized(self) -> bool:
        return self._finalized

    @property
    def manifest_hash(self) -> str:
        return self._manifest_hash

    @property
    def file_count(self) -> int:
        return len(self._records)

    @property
    def records(self) -> Tuple[CaptureFileRecord, ...]:
        return tuple(self._records)

    def add_record(self, record: CaptureFileRecord) -> bool:
        """Add a file record. Returns False if already finalized."""
        if self._finalized:
            return False
        self._records.append(record)
        return True

    def finalize(self) -> SessionSummary:
        """
        Freeze the manifest and compute a deterministic hash.
        Returns a SessionSummary with the finalized state.
        """
        summary = SessionSummary(session_id=self.session_id)

        if not self._records:
            summary.verdict = SessionManifestVerdict.EMPTY
            self._finalized = True
            return summary

        # Compute hash
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        self._manifest_hash = hashlib.sha256(data.encode()).hexdigest()
        self._finalized = True

        # Compute summary
        summary.file_count = len(self._records)
        summary.total_bytes = sum(r.file_size_bytes for r in self._records)
        devices = sorted(set(r.capture_device for r in self._records if r.capture_device))
        summary.unique_devices = len(devices)
        summary.device_list = devices
        summary.evidence_tier = "real-capture"
        summary.manifest_hash = self._manifest_hash
        summary.finalized = True
        summary.verdict = SessionManifestVerdict.VALID

        # Case breakdown
        breakdown: Dict[str, int] = {}
        for r in self._records:
            breakdown[r.ingest_case_name] = breakdown.get(r.ingest_case_name, 0) + 1
        summary.ingest_case_breakdown = breakdown

        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": SESSION_MANIFEST_VERSION,
            "session_id": self.session_id,
            "description": self.description,
            "created_at": self.created_at,
            "finalized": self._finalized,
            "manifest_hash": self._manifest_hash,
            "file_count": len(self._records),
            "records": [r.to_dict() for r in self._records],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_summary_text(self) -> str:
        """Human-readable summary of the session."""
        lines = [
            f"Capture Session: {self.session_id}",
            f"Description: {self.description}",
            f"Created: {self.created_at}",
            f"Finalized: {self._finalized}",
            f"Files: {len(self._records)}",
        ]
        if self._manifest_hash:
            lines.append(f"Manifest Hash: {self._manifest_hash}")
        if self._records:
            total_bytes = sum(r.file_size_bytes for r in self._records)
            lines.append(f"Total Size: {total_bytes} bytes")
            devices = sorted(set(r.capture_device for r in self._records if r.capture_device))
            if devices:
                lines.append(f"Devices: {', '.join(devices)}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# CONVENIENCE: CREATE RECORD FROM INGEST RESULT
# ════════════════════════════════════════════════════════════

def record_from_ingest(
    file_ref: str,
    file_ext: str,
    file_size: int,
    width: int,
    height: int,
    ingest_case_name: str,
    evidence_tier: str,
    metadata: Dict[str, Any],
) -> CaptureFileRecord:
    """Create a CaptureFileRecord from ingest validation outputs."""
    meta_tuples = tuple(sorted((str(k), str(v)) for k, v in metadata.items()))
    return CaptureFileRecord(
        file_ref=file_ref,
        file_ext=file_ext,
        file_size_bytes=file_size,
        width_px=width,
        height_px=height,
        ingest_case_name=ingest_case_name,
        evidence_tier=evidence_tier,
        capture_device=str(metadata.get("capture_device", "")),
        capture_timestamp=str(metadata.get("capture_timestamp", "")),
        metadata=meta_tuples,
    )


def make_empty_summary(session_id: str = "") -> SessionSummary:
    """Create an empty summary for testing/error paths."""
    return SessionSummary(
        verdict=SessionManifestVerdict.EMPTY,
        session_id=session_id,
    )


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_RECORD_FIELDS = 10  # fields in CaptureFileRecord
EXPECTED_SUMMARY_FIELDS = 11  # fields in SessionSummary
EXPECTED_VERDICT_COUNT = 4  # VALID, EMPTY, INCOMPLETE, ERROR
