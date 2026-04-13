"""
Aurexis Core — Calibration Recommendation Bridge V1

Converts bounded evidence deltas into explicit calibration and mutation
recommendations. Recommendations are ADVISORY and SUBORDINATE to the
deterministic truth layer — they never automatically mutate frozen law.

What this proves:
  Given a DeltaSurface from evidence delta analysis, the recommendation
  engine produces a bounded set of actionable advisory candidates:
  threshold adjustment, extractor profile, capture guidance. Each
  recommendation is tagged with a kind, priority, rationale, and
  suggested action — but none auto-execute.

What this does NOT prove:
  - Automatic self-improvement
  - Automatic law mutation
  - Full real-world robustness
  - Full Aurexis Core completion

Design:
  - RecommendationKind: THRESHOLD_ADJUSTMENT, EXTRACTOR_PROFILE,
    CAPTURE_GUIDANCE, CONTRACT_REVIEW, SIGNATURE_REVIEW.
  - RecommendationPriority: LOW, MEDIUM, HIGH, CRITICAL.
  - CalibrationRecommendation: one advisory record.
  - RecommendationSurface: full set of recommendations from one analysis.
  - generate_recommendations(): DeltaSurface → RecommendationSurface.
  - All recommendations are advisory. None auto-execute.

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

RECOMMENDATION_VERSION = "V1.0"
RECOMMENDATION_FROZEN = True


# ════════════════════════════════════════════════════════════
# RECOMMENDATION KIND
# ════════════════════════════════════════════════════════════

class RecommendationKind(str, Enum):
    """What kind of calibration action is recommended."""
    THRESHOLD_ADJUSTMENT = "THRESHOLD_ADJUSTMENT"
    EXTRACTOR_PROFILE = "EXTRACTOR_PROFILE"
    CAPTURE_GUIDANCE = "CAPTURE_GUIDANCE"
    CONTRACT_REVIEW = "CONTRACT_REVIEW"
    SIGNATURE_REVIEW = "SIGNATURE_REVIEW"


# ════════════════════════════════════════════════════════════
# RECOMMENDATION PRIORITY
# ════════════════════════════════════════════════════════════

class RecommendationPriority(str, Enum):
    """Priority level for a recommendation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ════════════════════════════════════════════════════════════
# CALIBRATION RECOMMENDATION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalibrationRecommendation:
    """
    One advisory calibration recommendation.

    kind: what kind of action
    priority: how urgent
    rationale: why this recommendation exists
    suggested_action: human-readable description of what to do
    metric_name: which metric triggered this (if applicable)
    metric_value: the value that triggered this
    threshold_current: current threshold (if applicable)
    threshold_suggested: suggested threshold (if applicable)
    advisory: always True — recommendations never auto-execute
    """
    kind: RecommendationKind
    priority: RecommendationPriority
    rationale: str
    suggested_action: str
    metric_name: str = ""
    metric_value: float = 0.0
    threshold_current: float = 0.0
    threshold_suggested: float = 0.0
    advisory: bool = True  # ALWAYS True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "priority": self.priority.value,
            "rationale": self.rationale,
            "suggested_action": self.suggested_action,
            "metric_name": self.metric_name,
            "metric_value": round(self.metric_value, 6),
            "threshold_current": round(self.threshold_current, 6),
            "threshold_suggested": round(self.threshold_suggested, 6),
            "advisory": self.advisory,
        }


# ════════════════════════════════════════════════════════════
# RECOMMENDATION SURFACE VERDICT
# ════════════════════════════════════════════════════════════

class RecommendationVerdict(str, Enum):
    """Overall verdict for the recommendation surface."""
    NO_ACTION_NEEDED = "NO_ACTION_NEEDED"
    ADVISORY_ISSUED = "ADVISORY_ISSUED"
    CRITICAL_ADVISORY = "CRITICAL_ADVISORY"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# RECOMMENDATION SURFACE
# ════════════════════════════════════════════════════════════

@dataclass
class RecommendationSurface:
    """Full set of recommendations from one delta analysis."""
    verdict: RecommendationVerdict = RecommendationVerdict.ERROR
    recommendations: List[CalibrationRecommendation] = field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    surface_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "total_count": self.total_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "surface_hash": self.surface_hash,
            "recommendations": [r.to_dict() for r in self.recommendations],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def to_summary_text(self) -> str:
        lines = [
            f"Recommendation Surface: {self.verdict.value}",
            f"Total: {self.total_count} (Critical={self.critical_count}, "
            f"High={self.high_count}, Medium={self.medium_count}, Low={self.low_count})",
        ]
        for r in self.recommendations:
            lines.append(f"  [{r.priority.value}] {r.kind.value}: {r.suggested_action}")
        return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# GENERATE RECOMMENDATIONS
# ════════════════════════════════════════════════════════════

def generate_recommendations(
    delta_surface: Any,
    confidence_tolerance: float = 0.05,
    position_tolerance: float = 5.0,
) -> RecommendationSurface:
    """
    Convert a DeltaSurface into advisory CalibrationRecommendations.

    This function inspects the delta surface and generates bounded,
    actionable recommendations. All recommendations are advisory.

    Parameters:
        delta_surface: a DeltaSurface from evidence_delta_analysis_bridge_v1
        confidence_tolerance: threshold for confidence-based recommendations
        position_tolerance: threshold for position-based recommendations

    Returns a RecommendationSurface.
    """
    surface = RecommendationSurface()
    recs: List[CalibrationRecommendation] = []

    # Access delta surface attributes
    try:
        missing_count = getattr(delta_surface, 'missing_primitive_count', 0)
        extra_count = getattr(delta_surface, 'extra_primitive_count', 0)
        max_conf_delta = getattr(delta_surface, 'max_confidence_delta', 0.0)
        max_pos_delta = getattr(delta_surface, 'max_position_delta', 0.0)
        changed_contracts = getattr(delta_surface, 'changed_contract_count', 0)
        changed_sigs = getattr(delta_surface, 'changed_signature_count', 0)
        primitive_deltas = getattr(delta_surface, 'primitive_deltas', [])
        verdict_val = getattr(delta_surface, 'verdict', None)
    except Exception:
        surface.verdict = RecommendationVerdict.ERROR
        return surface

    # Rule 1: Missing primitives → capture guidance
    if missing_count > 0:
        priority = (RecommendationPriority.CRITICAL if missing_count > 3
                    else RecommendationPriority.HIGH)
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.CAPTURE_GUIDANCE,
            priority=priority,
            rationale=f"{missing_count} expected primitive(s) not found in observed capture",
            suggested_action=(
                "Re-capture with better lighting, closer distance, or higher resolution. "
                "Ensure the full artifact is visible and well-lit."
            ),
            metric_name="missing_primitive_count",
            metric_value=float(missing_count),
        ))

    # Rule 2: Extra primitives → extractor profile review
    if extra_count > 0:
        priority = (RecommendationPriority.HIGH if extra_count > 3
                    else RecommendationPriority.MEDIUM)
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.EXTRACTOR_PROFILE,
            priority=priority,
            rationale=f"{extra_count} unexpected primitive(s) found in observed capture",
            suggested_action=(
                "Review extractor sensitivity. Extra primitives may indicate noise, "
                "reflections, or background elements being misidentified."
            ),
            metric_name="extra_primitive_count",
            metric_value=float(extra_count),
        ))

    # Rule 3: Confidence degradation → threshold adjustment
    if max_conf_delta > confidence_tolerance:
        priority = (RecommendationPriority.HIGH if max_conf_delta > 0.15
                    else RecommendationPriority.MEDIUM)
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.THRESHOLD_ADJUSTMENT,
            priority=priority,
            rationale=f"Max confidence delta {max_conf_delta:.4f} exceeds tolerance {confidence_tolerance:.4f}",
            suggested_action=(
                "Consider widening confidence tolerance for this capture condition, "
                "or investigate hardware calibration profile for the capture device."
            ),
            metric_name="max_confidence_delta",
            metric_value=max_conf_delta,
            threshold_current=confidence_tolerance,
            threshold_suggested=round(max_conf_delta * 1.2, 4),
        ))

    # Rule 4: Position drift → capture guidance
    if max_pos_delta > position_tolerance:
        priority = (RecommendationPriority.HIGH if max_pos_delta > position_tolerance * 3
                    else RecommendationPriority.MEDIUM)
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.CAPTURE_GUIDANCE,
            priority=priority,
            rationale=f"Max position delta {max_pos_delta:.2f}px exceeds tolerance {position_tolerance:.2f}px",
            suggested_action=(
                "Capture may have perspective distortion or alignment issues. "
                "Re-capture with the camera perpendicular to the artifact surface."
            ),
            metric_name="max_position_delta",
            metric_value=max_pos_delta,
            threshold_current=position_tolerance,
            threshold_suggested=round(max_pos_delta * 1.2, 2),
        ))

    # Rule 5: Contract failures → contract review
    if changed_contracts > 0:
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.CONTRACT_REVIEW,
            priority=RecommendationPriority.HIGH,
            rationale=f"{changed_contracts} contract(s) changed verdict between expected and observed",
            suggested_action=(
                "Review which contracts failed under observed conditions. "
                "Contract failures indicate structural capture issues, not just noise."
            ),
            metric_name="changed_contract_count",
            metric_value=float(changed_contracts),
        ))

    # Rule 6: Signature mismatches → signature review
    if changed_sigs > 0:
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.SIGNATURE_REVIEW,
            priority=RecommendationPriority.MEDIUM,
            rationale=f"{changed_sigs} signature(s) changed match status",
            suggested_action=(
                "Review signature matching thresholds. Signature changes may "
                "indicate the artifact identity is ambiguous under these capture conditions."
            ),
            metric_name="changed_signature_count",
            metric_value=float(changed_sigs),
        ))

    # Rule 7: Per-primitive confidence degradation patterns
    degraded_prims = [
        d for d in primitive_deltas
        if hasattr(d, 'confidence_delta') and d.confidence_delta < -confidence_tolerance
    ]
    if len(degraded_prims) > 2:
        recs.append(CalibrationRecommendation(
            kind=RecommendationKind.THRESHOLD_ADJUSTMENT,
            priority=RecommendationPriority.MEDIUM,
            rationale=f"{len(degraded_prims)} primitives show confidence degradation beyond tolerance",
            suggested_action=(
                "Multiple primitives lost confidence. Consider adjusting the "
                "hardware calibration profile or improving capture conditions."
            ),
            metric_name="degraded_primitive_count",
            metric_value=float(len(degraded_prims)),
        ))

    # Finalize
    surface.recommendations = recs
    surface.total_count = len(recs)
    surface.critical_count = sum(1 for r in recs if r.priority == RecommendationPriority.CRITICAL)
    surface.high_count = sum(1 for r in recs if r.priority == RecommendationPriority.HIGH)
    surface.medium_count = sum(1 for r in recs if r.priority == RecommendationPriority.MEDIUM)
    surface.low_count = sum(1 for r in recs if r.priority == RecommendationPriority.LOW)

    # Compute hash
    hash_data = json.dumps(surface.to_dict(), sort_keys=True, separators=(",", ":"))
    surface.surface_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    # Determine verdict
    if not recs:
        surface.verdict = RecommendationVerdict.NO_ACTION_NEEDED
    elif surface.critical_count > 0:
        surface.verdict = RecommendationVerdict.CRITICAL_ADVISORY
    else:
        surface.verdict = RecommendationVerdict.ADVISORY_ISSUED

    # Recompute hash with verdict set
    hash_data = json.dumps(surface.to_dict(), sort_keys=True, separators=(",", ":"))
    surface.surface_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    return surface


def make_empty_surface() -> RecommendationSurface:
    """Create an empty recommendation surface for testing."""
    return RecommendationSurface(
        verdict=RecommendationVerdict.NO_ACTION_NEEDED,
        total_count=0,
    )


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_KIND_COUNT = 5  # THRESHOLD_ADJUSTMENT, EXTRACTOR_PROFILE, CAPTURE_GUIDANCE, CONTRACT_REVIEW, SIGNATURE_REVIEW
EXPECTED_PRIORITY_COUNT = 4  # LOW, MEDIUM, HIGH, CRITICAL
EXPECTED_VERDICT_COUNT = 4  # NO_ACTION_NEEDED, ADVISORY_ISSUED, CRITICAL_ADVISORY, ERROR
RECOMMENDATION_RULES_COUNT = 7  # number of recommendation rules in generate_recommendations
