"""
Aurexis Core — Intake-to-Delta Replay Harness V1

Deterministic harness that runs the full observed-evidence pipeline:
  preflight → ingest → session manifest → delta analysis → calibration recommendation
using AUTHORED fixture packs only.

What this proves:
  The complete intake-to-delta pipeline can be exercised end-to-end
  without user-supplied real captures. Each authored fixture produces
  a deterministic replay result with explicit verdicts at every stage.

What this does NOT prove:
  - Real-world camera robustness
  - Actual real-capture processing
  - Automatic self-improvement
  - Full Aurexis Core completion

Evidence tier: AUTHORED only. Never REAL_CAPTURE.

Design:
  - ReplayStageResult: result from one pipeline stage
  - ReplayResult: full pipeline result for one fixture
  - run_replay(): runs one fixture through the full pipeline
  - run_all_replays(): runs all fixtures in a pack
  - ReplaySummary: aggregate results across all fixtures

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import json


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

REPLAY_HARNESS_VERSION = "V1.0"
REPLAY_HARNESS_FROZEN = True


# ════════════════════════════════════════════════════════════
# REPLAY STAGE
# ════════════════════════════════════════════════════════════

class ReplayStage(str, Enum):
    """Pipeline stages in the replay harness."""
    PREFLIGHT = "PREFLIGHT"
    INGEST = "INGEST"
    MANIFEST = "MANIFEST"
    DELTA = "DELTA"
    RECOMMENDATION = "RECOMMENDATION"


# ════════════════════════════════════════════════════════════
# REPLAY STAGE RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class ReplayStageResult:
    """Result from one stage of the replay pipeline."""
    stage: ReplayStage = ReplayStage.PREFLIGHT
    verdict: str = ""
    passed: bool = False
    detail: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "verdict": self.verdict,
            "passed": self.passed,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# REPLAY RESULT
# ════════════════════════════════════════════════════════════

class ReplayVerdict(str, Enum):
    """Overall verdict for one fixture's replay."""
    ALL_STAGES_PASSED = "ALL_STAGES_PASSED"
    EXPECTED_REJECTION = "EXPECTED_REJECTION"
    UNEXPECTED_FAILURE = "UNEXPECTED_FAILURE"
    STAGE_MISMATCH = "STAGE_MISMATCH"
    ERROR = "ERROR"


@dataclass
class ReplayResult:
    """Full pipeline replay result for one fixture."""
    fixture_name: str = ""
    evidence_tier: str = "authored"
    verdict: ReplayVerdict = ReplayVerdict.ERROR
    stages: List[ReplayStageResult] = field(default_factory=list)
    stages_completed: int = 0
    stages_total: int = 5
    preflight_verdict_match: bool = False
    ingest_verdict_match: bool = False
    delta_verdict_match: bool = False
    replay_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixture_name": self.fixture_name,
            "evidence_tier": self.evidence_tier,
            "verdict": self.verdict.value,
            "stages_completed": self.stages_completed,
            "stages_total": self.stages_total,
            "preflight_verdict_match": self.preflight_verdict_match,
            "ingest_verdict_match": self.ingest_verdict_match,
            "delta_verdict_match": self.delta_verdict_match,
            "replay_hash": self.replay_hash,
            "stages": [s.to_dict() for s in self.stages],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ════════════════════════════════════════════════════════════
# REPLAY SUMMARY
# ════════════════════════════════════════════════════════════

@dataclass
class ReplaySummary:
    """Aggregate results across all fixtures in a pack."""
    version: str = REPLAY_HARNESS_VERSION
    evidence_tier: str = "authored"
    total_fixtures: int = 0
    passed_count: int = 0
    failed_count: int = 0
    expected_rejection_count: int = 0
    results: List[ReplayResult] = field(default_factory=list)
    summary_hash: str = ""

    def all_passed(self) -> bool:
        return self.failed_count == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "evidence_tier": self.evidence_tier,
            "total_fixtures": self.total_fixtures,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "expected_rejection_count": self.expected_rejection_count,
            "all_passed": self.all_passed(),
            "summary_hash": self.summary_hash,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_summary_text(self) -> str:
        lines = [
            f"Replay Summary ({self.version}): {self.total_fixtures} fixtures",
            f"  Passed: {self.passed_count}  Failed: {self.failed_count}  "
            f"Expected rejections: {self.expected_rejection_count}",
            f"  Evidence tier: {self.evidence_tier}",
            f"  All passed: {self.all_passed()}",
        ]
        for r in self.results:
            lines.append(f"  [{r.verdict.value}] {r.fixture_name}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# RUN REPLAY — one fixture through the full pipeline
# ════════════════════════════════════════════════════════════

def run_replay(fixture) -> ReplayResult:
    """
    Run one authored fixture through the full observed-evidence pipeline.

    Pipeline stages:
      1. PREFLIGHT — run_preflight() on the session manifest
      2. INGEST    — validate_capture_file() for each file (if preflight passed)
      3. MANIFEST  — build CaptureSessionManifest (if ingest passed)
      4. DELTA     — analyze_deltas() against reference output (if manifest built)
      5. RECOMMENDATION — generate_recommendations() from delta surface

    Returns a ReplayResult with verdicts at each stage.
    """
    from aurexis_lang.real_capture_intake_preflight_bridge_v1 import (
        run_preflight, PreflightVerdict,
    )
    from aurexis_lang.real_capture_ingest_profile_bridge_v1 import (
        validate_capture_file, IngestVerdict,
    )
    from aurexis_lang.capture_session_manifest_bridge_v1 import (
        CaptureSessionManifest, CaptureFileRecord, SessionManifestVerdict,
    )
    from aurexis_lang.evidence_delta_analysis_bridge_v1 import (
        analyze_deltas, SubstrateOutput, PrimitiveRecord,
        ContractOutcome, SignatureOutcome, DeltaVerdict,
    )
    from aurexis_lang.calibration_recommendation_bridge_v1 import (
        generate_recommendations, RecommendationVerdict,
    )
    from aurexis_lang.authored_capture_fixtures_v1 import (
        REFERENCE_PHONE_JPEG_PRIMITIVES, REFERENCE_PHONE_JPEG_CONTRACTS,
        REFERENCE_PHONE_JPEG_SIGNATURES, REFERENCE_SCANNER_TIFF_PRIMITIVES,
        REFERENCE_SCANNER_TIFF_CONTRACTS, REFERENCE_SCANNER_TIFF_SIGNATURES,
    )

    result = ReplayResult(
        fixture_name=fixture.name,
        evidence_tier=fixture.evidence_tier,
    )

    manifest = fixture.session_manifest

    # ── Stage 1: PREFLIGHT ──
    try:
        preflight_result = run_preflight(manifest)
        pf_verdict_str = preflight_result.verdict.value
        pf_passed = preflight_result.verdict == PreflightVerdict.CLEARED

        result.stages.append(ReplayStageResult(
            stage=ReplayStage.PREFLIGHT,
            verdict=pf_verdict_str,
            passed=pf_passed,
            detail=f"checks={preflight_result.total_checks}, passed={preflight_result.passed_checks}",
            data={"preflight_result": preflight_result.to_dict()},
        ))
        result.stages_completed = 1

        # Check preflight verdict matches expected
        result.preflight_verdict_match = (pf_verdict_str == fixture.expected_preflight_verdict)

    except Exception as e:
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.PREFLIGHT,
            verdict="ERROR",
            passed=False,
            detail=str(e),
        ))
        result.verdict = ReplayVerdict.ERROR
        _finalize_hash(result)
        return result

    # If preflight rejected and that was expected, this is a successful expected rejection
    if not pf_passed:
        if fixture.expected_preflight_verdict in ("REJECTED", "WARNING", "ERROR"):
            result.verdict = ReplayVerdict.EXPECTED_REJECTION
        else:
            result.verdict = ReplayVerdict.STAGE_MISMATCH
        _finalize_hash(result)
        return result

    # ── Stage 2: INGEST ──
    files = manifest.get("files", [])
    ingest_verdicts = []
    try:
        for f in files:
            ext = f.get("file_ext", f.get("extension", ""))
            size = f.get("file_size_bytes", f.get("size_bytes", 0))
            w = f.get("width_px", 0)
            h = f.get("height_px", 0)
            metadata = {
                "capture_device": f.get("capture_device", ""),
                "capture_timestamp": f.get("capture_timestamp", ""),
                "adequate_lighting": manifest.get("conditions", {}).get("adequate_lighting", False),
                "stable_orientation": True,
                "subject_in_frame": manifest.get("conditions", {}).get("subject_in_frame", False),
                "flat_placement": True,
                "scan_dpi": f.get("scan_dpi", 300),
            }
            ingest_result = validate_capture_file(ext, size, w, h, metadata)
            ingest_verdicts.append(ingest_result.verdict.value)

        all_accepted = all(v == "ACCEPTED" for v in ingest_verdicts)
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.INGEST,
            verdict="ALL_ACCEPTED" if all_accepted else "SOME_REJECTED",
            passed=all_accepted,
            detail=f"files={len(files)}, verdicts={ingest_verdicts}",
        ))
        result.stages_completed = 2

        # Check ingest verdicts match expected
        if fixture.expected_ingest_verdicts:
            result.ingest_verdict_match = (
                tuple(ingest_verdicts) == tuple(fixture.expected_ingest_verdicts)
            )

    except Exception as e:
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.INGEST,
            verdict="ERROR",
            passed=False,
            detail=str(e),
        ))
        result.verdict = ReplayVerdict.ERROR
        _finalize_hash(result)
        return result

    if not all_accepted:
        result.verdict = ReplayVerdict.UNEXPECTED_FAILURE
        _finalize_hash(result)
        return result

    # ── Stage 3: MANIFEST ──
    try:
        session = CaptureSessionManifest(
            session_id=manifest.get("session_id", ""),
            description=manifest.get("description", ""),
            created_at=manifest.get("created_at", ""),
        )
        for i, f in enumerate(files):
            record = CaptureFileRecord(
                file_ref=f.get("file_ref", f.get("filename", "")),
                file_ext=f.get("file_ext", f.get("extension", "")),
                file_size_bytes=f.get("file_size_bytes", f.get("size_bytes", 0)),
                width_px=f.get("width_px", 0),
                height_px=f.get("height_px", 0),
                ingest_case_name=ingest_verdicts[i] if i < len(ingest_verdicts) else "",
                evidence_tier="authored",
                capture_device=f.get("capture_device", ""),
                capture_timestamp=f.get("capture_timestamp", ""),
            )
            session.add_record(record)

        summary = session.finalize()
        manifest_valid = summary.verdict == SessionManifestVerdict.VALID

        result.stages.append(ReplayStageResult(
            stage=ReplayStage.MANIFEST,
            verdict=summary.verdict.value,
            passed=manifest_valid,
            detail=f"files={summary.file_count}, hash={summary.manifest_hash[:16]}...",
            data={"manifest_hash": summary.manifest_hash},
        ))
        result.stages_completed = 3

    except Exception as e:
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.MANIFEST,
            verdict="ERROR",
            passed=False,
            detail=str(e),
        ))
        result.verdict = ReplayVerdict.ERROR
        _finalize_hash(result)
        return result

    if not manifest_valid:
        result.verdict = ReplayVerdict.UNEXPECTED_FAILURE
        _finalize_hash(result)
        return result

    # ── Stage 4: DELTA ──
    try:
        # Select reference based on fixture
        ref_prims, ref_contracts, ref_sigs = _select_reference(fixture.name)

        expected_output = SubstrateOutput(
            label="expected",
            primitives=tuple(
                PrimitiveRecord(
                    name=p["name"], kind=p["kind"],
                    confidence=p["confidence"], x=p["x"], y=p["y"],
                ) for p in ref_prims
            ),
            contracts=tuple(
                ContractOutcome(
                    contract_name=c["contract_name"],
                    passed=c["passed"], detail=c["detail"],
                ) for c in ref_contracts
            ),
            signatures=tuple(
                SignatureOutcome(
                    signature_name=s["signature_name"],
                    matched=s["matched"], similarity=s["similarity"],
                ) for s in ref_sigs
            ),
        )

        # For IDENTICAL verdict, observed = expected
        # For WITHIN_TOLERANCE, add small perturbation
        if fixture.expected_delta_verdict == "IDENTICAL":
            observed_output = expected_output
        elif fixture.expected_delta_verdict == "WITHIN_TOLERANCE":
            observed_prims = tuple(
                PrimitiveRecord(
                    name=p.name, kind=p.kind,
                    confidence=p.confidence + 0.01,
                    x=p.x + 1.0, y=p.y + 1.0,
                ) for p in expected_output.primitives
            )
            observed_output = SubstrateOutput(
                label="observed",
                primitives=observed_prims,
                contracts=expected_output.contracts,
                signatures=expected_output.signatures,
            )
        else:
            observed_output = expected_output

        delta_surface = analyze_deltas(expected_output, observed_output)
        delta_verdict_str = delta_surface.verdict.value

        result.stages.append(ReplayStageResult(
            stage=ReplayStage.DELTA,
            verdict=delta_verdict_str,
            passed=True,
            detail=f"missing={delta_surface.missing_primitive_count}, extra={delta_surface.extra_primitive_count}",
            data={"delta_hash": delta_surface.analysis_hash},
        ))
        result.stages_completed = 4

        result.delta_verdict_match = (delta_verdict_str == fixture.expected_delta_verdict)

    except Exception as e:
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.DELTA,
            verdict="ERROR",
            passed=False,
            detail=str(e),
        ))
        result.verdict = ReplayVerdict.ERROR
        _finalize_hash(result)
        return result

    # ── Stage 5: RECOMMENDATION ──
    try:
        rec_surface = generate_recommendations(delta_surface)
        rec_verdict_str = rec_surface.verdict.value

        result.stages.append(ReplayStageResult(
            stage=ReplayStage.RECOMMENDATION,
            verdict=rec_verdict_str,
            passed=True,
            detail=f"total={rec_surface.total_count}, critical={rec_surface.critical_count}",
        ))
        result.stages_completed = 5

    except Exception as e:
        result.stages.append(ReplayStageResult(
            stage=ReplayStage.RECOMMENDATION,
            verdict="ERROR",
            passed=False,
            detail=str(e),
        ))
        result.verdict = ReplayVerdict.ERROR
        _finalize_hash(result)
        return result

    # All stages completed — determine overall verdict
    if (result.preflight_verdict_match and
        result.ingest_verdict_match and
        result.delta_verdict_match):
        result.verdict = ReplayVerdict.ALL_STAGES_PASSED
    else:
        result.verdict = ReplayVerdict.STAGE_MISMATCH

    _finalize_hash(result)
    return result


def _select_reference(fixture_name: str):
    """Select reference substrate output based on fixture name."""
    from aurexis_lang.authored_capture_fixtures_v1 import (
        REFERENCE_PHONE_JPEG_PRIMITIVES, REFERENCE_PHONE_JPEG_CONTRACTS,
        REFERENCE_PHONE_JPEG_SIGNATURES, REFERENCE_SCANNER_TIFF_PRIMITIVES,
        REFERENCE_SCANNER_TIFF_CONTRACTS, REFERENCE_SCANNER_TIFF_SIGNATURES,
    )
    if "scanner" in fixture_name or "tiff" in fixture_name:
        return (REFERENCE_SCANNER_TIFF_PRIMITIVES,
                REFERENCE_SCANNER_TIFF_CONTRACTS,
                REFERENCE_SCANNER_TIFF_SIGNATURES)
    else:
        return (REFERENCE_PHONE_JPEG_PRIMITIVES,
                REFERENCE_PHONE_JPEG_CONTRACTS,
                REFERENCE_PHONE_JPEG_SIGNATURES)


def _finalize_hash(result: ReplayResult):
    """Compute deterministic hash for replay result."""
    data = json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))
    result.replay_hash = hashlib.sha256(data.encode()).hexdigest()


# ════════════════════════════════════════════════════════════
# RUN ALL REPLAYS
# ════════════════════════════════════════════════════════════

def run_all_replays(fixture_pack=None) -> ReplaySummary:
    """
    Run all fixtures in a pack through the full pipeline.

    Parameters:
        fixture_pack: an AuthoredFixturePack (default: V1_FIXTURE_PACK)

    Returns a ReplaySummary with aggregate results.
    """
    if fixture_pack is None:
        from aurexis_lang.authored_capture_fixtures_v1 import V1_FIXTURE_PACK
        fixture_pack = V1_FIXTURE_PACK

    summary = ReplaySummary(
        version=REPLAY_HARNESS_VERSION,
        evidence_tier=fixture_pack.evidence_tier,
        total_fixtures=len(fixture_pack.fixtures),
    )

    for fixture in fixture_pack.fixtures:
        replay_result = run_replay(fixture)
        summary.results.append(replay_result)

        if replay_result.verdict == ReplayVerdict.ALL_STAGES_PASSED:
            summary.passed_count += 1
        elif replay_result.verdict == ReplayVerdict.EXPECTED_REJECTION:
            summary.passed_count += 1
            summary.expected_rejection_count += 1
        else:
            summary.failed_count += 1

    # Compute summary hash
    data = json.dumps(summary.to_dict(), sort_keys=True, separators=(",", ":"))
    summary.summary_hash = hashlib.sha256(data.encode()).hexdigest()

    return summary


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_STAGE_COUNT = 5
EXPECTED_REPLAY_VERDICT_COUNT = 5
EXPECTED_SUMMARY_FIELDS = 8
