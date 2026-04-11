"""
Aurexis Core — Temporal Law V1 (FROZEN)

Formal rules for consistency across frames over time.
Replaces the heuristic multi_frame_consistency.py which used
magic thresholds (50px spatial tolerance, 0.2 confidence tolerance).

V1 temporal law defines:
  1. Temporal consistency: a binding that existed in frame N should
     appear in frame N+1 within a spatial tolerance under law
  2. Verdict stability: if a program PASSes for K consecutive frames,
     it is TEMPORALLY_CONFIRMED
  3. Binding persistence: bindings track across frames by spatial proximity
  4. Assertion drift: how much an assertion's measured value can change
     between frames before it's flagged

This is NOT a video processing module. It operates on frame-level
ExecutionResults produced by the V1 program executor, and evaluates
temporal relationships between them.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math

from aurexis_lang.visual_grammar_v1 import (
    ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import (
    ProgramVerdict, ExecutionResult,
)


# ════════════════════════════════════════════════════════════
# TEMPORAL LAW — frozen thresholds
# ════════════════════════════════════════════════════════════

TEMPORAL_VERSION = "V1.0"
TEMPORAL_FROZEN = True


@dataclass(frozen=True)
class TemporalLaw:
    """
    Frozen temporal consistency thresholds.

    These replace the magic numbers in multi_frame_consistency.py:
    - Old: spatial_tolerance = 50px (magic), confidence_tolerance = 0.2 (magic)
    - New: law-derived, explicit, frozen
    """
    # A binding is "the same" across frames if its bbox center
    # moved less than this distance
    binding_persistence_radius_px: float = 40.0

    # A program verdict is "confirmed" after this many consecutive
    # identical verdicts
    confirmation_window: int = 3

    # Maximum measured_value drift between consecutive frames for
    # an assertion before it's flagged as "drifting"
    assertion_drift_max_px: float = 15.0

    # Maximum confidence change between frames before flagging
    confidence_drift_max: float = 0.25

    # Minimum frames required for any temporal analysis
    min_frames: int = 2


V1_TEMPORAL = TemporalLaw()


# ════════════════════════════════════════════════════════════
# TEMPORAL VERDICT
# ════════════════════════════════════════════════════════════

class TemporalVerdict(str, Enum):
    """Temporal consistency verdict across multiple frames."""
    CONFIRMED = "CONFIRMED"       # Same verdict for confirmation_window frames
    CONSISTENT = "CONSISTENT"     # Same verdict, but not enough frames yet
    DRIFTING = "DRIFTING"         # Verdict same, but values shifting significantly
    FLIPPED = "FLIPPED"           # Verdict changed between frames
    INSUFFICIENT = "INSUFFICIENT" # Not enough frames to evaluate


# ════════════════════════════════════════════════════════════
# BINDING TRACKING — persistence across frames
# ════════════════════════════════════════════════════════════

@dataclass
class TrackedBinding:
    """A binding tracked across multiple frames."""
    name: str
    frames_seen: int = 0
    last_bbox: Optional[Dict[str, float]] = None
    total_drift_px: float = 0.0
    max_drift_px: float = 0.0
    lost: bool = False  # True if binding disappeared


def track_bindings(
    results: List[ExecutionResult],
    law: TemporalLaw = V1_TEMPORAL,
) -> Dict[str, TrackedBinding]:
    """
    Track bindings across a sequence of execution results.

    For each binding name, compute:
    - How many frames it appeared in
    - Total drift (sum of center movements)
    - Max single-frame drift
    - Whether it was lost (disappeared from a frame)
    """
    tracked: Dict[str, TrackedBinding] = {}

    for result in results:
        seen_this_frame = set()

        for name, binding_data in result.bindings.items():
            seen_this_frame.add(name)
            bbox = binding_data.get("bbox", {})
            cx = bbox.get("x", 0) + bbox.get("width", 0) / 2.0
            cy = bbox.get("y", 0) + bbox.get("height", 0) / 2.0
            current_center = {"cx": cx, "cy": cy}

            if name not in tracked:
                tracked[name] = TrackedBinding(
                    name=name,
                    frames_seen=1,
                    last_bbox=current_center,
                )
            else:
                tb = tracked[name]
                tb.frames_seen += 1

                if tb.last_bbox:
                    dx = current_center["cx"] - tb.last_bbox["cx"]
                    dy = current_center["cy"] - tb.last_bbox["cy"]
                    drift = math.sqrt(dx * dx + dy * dy)
                    tb.total_drift_px += drift
                    tb.max_drift_px = max(tb.max_drift_px, drift)

                tb.last_bbox = current_center

        # Check for lost bindings
        for name, tb in tracked.items():
            if name not in seen_this_frame and not tb.lost:
                tb.lost = True

    return tracked


# ════════════════════════════════════════════════════════════
# ASSERTION DRIFT — value changes between frames
# ════════════════════════════════════════════════════════════

@dataclass
class AssertionDrift:
    """Drift analysis for one assertion across frames."""
    operation: str
    index: int
    values: List[float] = field(default_factory=list)
    max_drift: float = 0.0
    mean_drift: float = 0.0
    drifting: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "index": self.index,
            "frames_tracked": len(self.values),
            "max_drift": round(self.max_drift, 3),
            "mean_drift": round(self.mean_drift, 3),
            "drifting": self.drifting,
        }


def analyze_assertion_drift(
    results: List[ExecutionResult],
    law: TemporalLaw = V1_TEMPORAL,
) -> List[AssertionDrift]:
    """
    Track assertion measured_values across frames and detect drift.
    """
    if len(results) < 2:
        return []

    # Track by assertion index (position in the assertions list)
    max_assertions = max(len(r.assertions) for r in results) if results else 0
    drifts = []

    for idx in range(max_assertions):
        values = []
        operation = "?"

        for result in results:
            if idx < len(result.assertions):
                assertion = result.assertions[idx]
                values.append(assertion.get("measured_value", 0.0))
                operation = assertion.get("operation", "?")

        if len(values) < 2:
            continue

        # Compute frame-to-frame drifts
        frame_drifts = [abs(values[i+1] - values[i]) for i in range(len(values)-1)]
        max_d = max(frame_drifts) if frame_drifts else 0.0
        mean_d = sum(frame_drifts) / len(frame_drifts) if frame_drifts else 0.0

        ad = AssertionDrift(
            operation=operation,
            index=idx,
            values=values,
            max_drift=max_d,
            mean_drift=mean_d,
            drifting=max_d > law.assertion_drift_max_px,
        )
        drifts.append(ad)

    return drifts


# ════════════════════════════════════════════════════════════
# TEMPORAL PROOF — complete analysis across frames
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalProof:
    """Complete temporal consistency analysis."""
    verdict: TemporalVerdict = TemporalVerdict.INSUFFICIENT
    frame_count: int = 0
    verdicts: List[str] = field(default_factory=list)
    consecutive_same: int = 0
    binding_tracking: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    assertion_drifts: List[Dict[str, Any]] = field(default_factory=list)
    lost_bindings: List[str] = field(default_factory=list)
    drifting_assertions: List[int] = field(default_factory=list)
    temporal_version: str = TEMPORAL_VERSION
    grammar_version: str = GRAMMAR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "frame_count": self.frame_count,
            "verdicts": self.verdicts,
            "consecutive_same": self.consecutive_same,
            "binding_tracking": self.binding_tracking,
            "assertion_drifts": self.assertion_drifts,
            "lost_bindings": self.lost_bindings,
            "drifting_assertions": self.drifting_assertions,
            "temporal_version": self.temporal_version,
            "grammar_version": self.grammar_version,
        }


# ════════════════════════════════════════════════════════════
# TEMPORAL PROVER — the main entry point
# ════════════════════════════════════════════════════════════

def prove_temporal_consistency(
    results: List[ExecutionResult],
    law: TemporalLaw = V1_TEMPORAL,
) -> TemporalProof:
    """
    Prove (or disprove) temporal consistency across a sequence of
    execution results from consecutive frames.

    Returns a TemporalProof with complete analysis.
    """
    proof = TemporalProof(
        frame_count=len(results),
    )

    if len(results) < law.min_frames:
        proof.verdict = TemporalVerdict.INSUFFICIENT
        return proof

    # Collect verdicts
    proof.verdicts = [r.verdict.value for r in results]

    # Count consecutive same verdicts from the end
    consecutive = 1
    for i in range(len(proof.verdicts) - 1, 0, -1):
        if proof.verdicts[i] == proof.verdicts[i - 1]:
            consecutive += 1
        else:
            break
    proof.consecutive_same = consecutive

    # Check for verdict flips
    has_flip = any(
        proof.verdicts[i] != proof.verdicts[i + 1]
        for i in range(len(proof.verdicts) - 1)
    )

    # Track bindings
    tracked = track_bindings(results, law)
    proof.binding_tracking = {
        name: {
            "frames_seen": tb.frames_seen,
            "total_drift_px": round(tb.total_drift_px, 3),
            "max_drift_px": round(tb.max_drift_px, 3),
            "lost": tb.lost,
        }
        for name, tb in tracked.items()
    }
    proof.lost_bindings = [name for name, tb in tracked.items() if tb.lost]

    # Analyze assertion drift
    drifts = analyze_assertion_drift(results, law)
    proof.assertion_drifts = [d.to_dict() for d in drifts]
    proof.drifting_assertions = [d.index for d in drifts if d.drifting]

    # Compute verdict
    if has_flip:
        proof.verdict = TemporalVerdict.FLIPPED
    elif proof.drifting_assertions or proof.lost_bindings:
        proof.verdict = TemporalVerdict.DRIFTING
    elif consecutive >= law.confirmation_window:
        proof.verdict = TemporalVerdict.CONFIRMED
    else:
        proof.verdict = TemporalVerdict.CONSISTENT

    return proof
