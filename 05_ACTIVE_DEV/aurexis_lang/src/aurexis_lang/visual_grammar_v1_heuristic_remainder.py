"""
Aurexis Core — Visual Grammar V1 Heuristic Remainder Declaration

This file explicitly documents what is deterministic (governed by V1 law)
and what remains heuristic (not governed by V1 law) at the M1 milestone.

This is a governance requirement, not a code module.
It is executable only in the sense that it can be imported and inspected.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class HeuristicItem:
    """One component that remains heuristic (not law-governed) in V1."""
    component: str
    module: str
    description: str
    why_heuristic: str
    path_to_law: str


@dataclass(frozen=True)
class DeterministicItem:
    """One component that is fully deterministic (law-governed) in V1."""
    component: str
    module: str
    description: str


# ════════════════════════════════════════════════════════════
# DETERMINISTIC — governed by V1 law
# ════════════════════════════════════════════════════════════

V1_DETERMINISTIC: List[DeterministicItem] = [
    DeterministicItem(
        component="ADJACENT operation",
        module="visual_executor_v1.py",
        description="Evaluates spatial proximity between two primitives. "
                    "Pure Euclidean distance on bounding box edges vs frozen threshold (30.0 px).",
    ),
    DeterministicItem(
        component="CONTAINS operation",
        module="visual_executor_v1.py",
        description="Evaluates bounding box containment with minimum margin check. "
                    "Pure geometry, frozen threshold (0.0 px margin).",
    ),
    DeterministicItem(
        component="BIND operation",
        module="visual_executor_v1.py",
        description="Name assignment to a primitive. Always succeeds for valid primitives.",
    ),
    DeterministicItem(
        component="Primitive validity check",
        module="visual_grammar_v1.py",
        description="Minimum area (4.0 px²) and positive dimension checks. Frozen law.",
    ),
    DeterministicItem(
        component="Primitive count cap",
        module="visual_executor_v1.py",
        description="Max 200 primitives per frame, smallest-area dropped first. Frozen law.",
    ),
    DeterministicItem(
        component="Relation result",
        module="visual_grammar_v1.py",
        description="TRUE/FALSE/ERROR enum. Result is always determined by geometry, "
                    "never by confidence or heuristic input.",
    ),
    DeterministicItem(
        component="Execution status tracking",
        module="visual_executor_v1.py",
        description="Marks whether inputs came from heuristic CV (HEURISTIC_INPUT) "
                    "or deterministic sources (DETERMINISTIC). The tracking itself is deterministic.",
    ),
    DeterministicItem(
        component="Grammar law thresholds",
        module="visual_grammar_v1.py",
        description="Frozen dataclass (GrammarLaw). Cannot be mutated at runtime.",
    ),
    DeterministicItem(
        component="Kind classification",
        module="visual_parser_v1.py",
        description="CV label → PrimitiveKind mapping. Deterministic lookup table, "
                    "unknown labels default to REGION.",
    ),
    DeterministicItem(
        component="Parser structural conversion",
        module="visual_parser_v1.py",
        description="Raw CV dict → VisualPrimitive. Same input dict always produces "
                    "same primitive. No heuristic decisions in parsing.",
    ),
    DeterministicItem(
        component="Serialization roundtrip",
        module="visual_parser_v1.py",
        description="primitive_to_dict → parse_primitive reproduces equivalent primitive. "
                    "Deterministic and lossless for structural fields.",
    ),
]


# ════════════════════════════════════════════════════════════
# HEURISTIC — not governed by V1 law (temporary scaffolding)
# ════════════════════════════════════════════════════════════

V1_HEURISTIC_REMAINDER: List[HeuristicItem] = [
    HeuristicItem(
        component="CV primitive extraction",
        module="cv_primitive_extractor.py, enhanced_cv_extractor.py, etc.",
        description="Extraction of bounding boxes and type labels from raw images. "
                    "Uses edge detection, color segmentation, ORB features, etc.",
        why_heuristic="Fundamentally depends on image content, lighting, noise. "
                      "No deterministic law can guarantee extraction quality.",
        path_to_law="Future: tighter extraction contracts, calibrated confidence, "
                    "or hardware-assisted sensing may reduce heuristic dependency. "
                    "V1 accepts heuristic input but tracks it explicitly.",
    ),
    HeuristicItem(
        component="source_confidence values",
        module="All CV extractors",
        description="Confidence scores (0.0-1.0) attached to extracted primitives. "
                    "Based on edge density, contrast, color uniformity, etc.",
        why_heuristic="Confidence is a heuristic estimate of extraction quality. "
                      "It is not a deterministic measurement.",
        path_to_law="V1 uses confidence only for execution status tracking "
                    "(DETERMINISTIC vs HEURISTIC_INPUT). It never affects the "
                    "TRUE/FALSE result of any operation.",
    ),
    HeuristicItem(
        component="IR optimizer (0.7 confidence threshold)",
        module="ir_optimizer.py",
        description="6-pass evidence-aware optimizer uses 0.7 confidence threshold "
                    "for EXECUTABLE promotion decisions.",
        why_heuristic="The 0.7 threshold is a magic number, not derived from V1 law.",
        path_to_law="Future: V1 executor's deterministic promotion path should "
                    "replace or supplement the IR optimizer's heuristic threshold.",
    ),
    HeuristicItem(
        component="Multi-frame consistency",
        module="multi_frame_consistency.py",
        description="Cross-frame validation uses spatial tolerance (50px) and "
                    "confidence tolerance (0.2).",
        why_heuristic="Tolerance values are provisional, not derived from V1 law.",
        path_to_law="Future V2+ may define law-governed temporal consistency rules.",
    ),
    HeuristicItem(
        component="Perception inference ambiguity",
        module="perception_inference.py",
        description="Ambiguity detection uses delta threshold (0.12) for ranking.",
        why_heuristic="Threshold is heuristic, based on empirical observation.",
        path_to_law="Not on V1 path. May be addressed in future perception law.",
    ),
    HeuristicItem(
        component="Learned candidate model",
        module="learned_candidate_model.py",
        description="Feature vector scoring into confidence tiers.",
        why_heuristic="Scoring function is heuristic by design — it's a model.",
        path_to_law="Remains heuristic. V1 law doesn't govern ML scoring.",
    ),
]


# ════════════════════════════════════════════════════════════
# SUMMARY — for gate verification
# ════════════════════════════════════════════════════════════

V1_REMAINDER_SUMMARY = {
    "deterministic_count": len(V1_DETERMINISTIC),
    "heuristic_count": len(V1_HEURISTIC_REMAINDER),
    "v1_law_components": [d.component for d in V1_DETERMINISTIC],
    "heuristic_components": [h.component for h in V1_HEURISTIC_REMAINDER],
    "boundary": (
        "V1 law governs all operation evaluation (ADJACENT, CONTAINS, BIND), "
        "primitive validity, frame filtering, and structural parsing. "
        "V1 law does NOT govern CV extraction, confidence scoring, "
        "IR optimization thresholds, or cross-frame consistency. "
        "The boundary is explicit and frozen."
    ),
}
