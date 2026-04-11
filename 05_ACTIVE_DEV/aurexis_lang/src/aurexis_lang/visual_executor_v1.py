"""
Aurexis Core — Visual Executor V1 (DETERMINISTIC)

Evaluates ADJACENT, CONTAINS, and BIND operations under frozen V1 law.
Every evaluation is pure geometry. No heuristics, no confidence tuning,
no magic numbers. The law thresholds come from GrammarLaw and nowhere else.

The executor tracks whether its inputs came from heuristic CV extraction
(source_confidence < 1.0) and marks the execution status accordingly,
but the *result* (TRUE/FALSE) is always determined by geometry alone.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarLaw, V1_LAW, BoundingBox, VisualPrimitive, Binding,
    Relation, GrammarFrame, GRAMMAR_VERSION,
)


# ════════════════════════════════════════════════════════════
# EXECUTION STATUS RESOLUTION
# ════════════════════════════════════════════════════════════

def _resolve_execution_status(a: VisualPrimitive, b: VisualPrimitive) -> ExecutionStatus:
    """
    If both operands have source_confidence == 1.0, the evaluation
    is fully DETERMINISTIC. Otherwise, it's HEURISTIC_INPUT — the
    geometry is still law-governed, but the inputs came from
    heuristic CV extraction.
    """
    if a.source_confidence >= 1.0 and b.source_confidence >= 1.0:
        return ExecutionStatus.DETERMINISTIC
    return ExecutionStatus.HEURISTIC_INPUT


# ════════════════════════════════════════════════════════════
# ADJACENT EVALUATOR
# ════════════════════════════════════════════════════════════

def evaluate_adjacent(
    a: VisualPrimitive,
    b: VisualPrimitive,
    law: GrammarLaw = V1_LAW,
) -> Relation:
    """
    Evaluate ADJACENT(a, b) under V1 law.

    Returns TRUE if the minimum Euclidean distance between the
    bounding box edges of a and b is <= adjacent_max_distance_px.
    Returns FALSE otherwise.

    The result is symmetric: ADJACENT(a, b) == ADJACENT(b, a).
    """
    distance = a.bbox.edge_distance(b.bbox)
    threshold = law.adjacent_max_distance_px

    if distance <= threshold:
        result = RelationResult.TRUE
    else:
        result = RelationResult.FALSE

    return Relation(
        operation=OperationKind.ADJACENT,
        operand_a=a,
        operand_b=b,
        result=result,
        execution_status=_resolve_execution_status(a, b),
        measured_value=distance,
        law_threshold=threshold,
    )


# ════════════════════════════════════════════════════════════
# CONTAINS EVALUATOR
# ════════════════════════════════════════════════════════════

def _min_containment_margin(outer: BoundingBox, inner: BoundingBox) -> float:
    """
    Compute the minimum margin on all four sides.
    Positive = inner is within outer by that amount.
    Negative = inner extends outside outer by that amount.
    """
    margin_left = inner.x - outer.x
    margin_top = inner.y - outer.y
    margin_right = outer.x2 - inner.x2
    margin_bottom = outer.y2 - inner.y2
    return min(margin_left, margin_top, margin_right, margin_bottom)


def evaluate_contains(
    a: VisualPrimitive,
    b: VisualPrimitive,
    law: GrammarLaw = V1_LAW,
) -> Relation:
    """
    Evaluate CONTAINS(a, b) under V1 law.

    Returns TRUE if b's bounding box is fully within a's bounding box
    with minimum margin >= contains_min_margin_px on all sides.

    NOT symmetric: CONTAINS(a, b) != CONTAINS(b, a) in general.
    """
    min_margin = _min_containment_margin(a.bbox, b.bbox)
    threshold = law.contains_min_margin_px

    if min_margin >= threshold:
        result = RelationResult.TRUE
    else:
        result = RelationResult.FALSE

    return Relation(
        operation=OperationKind.CONTAINS,
        operand_a=a,
        operand_b=b,
        result=result,
        execution_status=_resolve_execution_status(a, b),
        measured_value=min_margin,
        law_threshold=threshold,
    )


# ════════════════════════════════════════════════════════════
# BIND EVALUATOR
# ════════════════════════════════════════════════════════════

def evaluate_bind(
    name: str,
    primitive: VisualPrimitive,
    frame_index: int = 0,
) -> Binding:
    """
    Evaluate BIND(name, primitive).

    Creates a named reference to a primitive. Always succeeds for
    valid primitives. Returns a Binding object (not a Relation,
    since BIND produces a name assignment, not a boolean result).
    """
    return Binding(
        name=name,
        primitive=primitive,
        frame_index=frame_index,
    )


# ════════════════════════════════════════════════════════════
# PRIMITIVE FILTERING — enforce max_primitives_per_frame
# ════════════════════════════════════════════════════════════

def filter_primitives(
    primitives: List[VisualPrimitive],
    law: GrammarLaw = V1_LAW,
) -> Tuple[List[VisualPrimitive], List[VisualPrimitive]]:
    """
    Filter primitives through V1 law:
    1. Remove invalid primitives (area < min_primitive_area_px2 or zero dimension).
    2. If remaining count exceeds max_primitives_per_frame, drop the
       smallest-area primitives first.

    Returns (kept, dropped) tuple.
    """
    # Step 1: validity filter
    valid = [p for p in primitives if p.is_valid(law)]
    invalid = [p for p in primitives if not p.is_valid(law)]

    # Step 2: count cap — sort by area descending, keep top N
    if len(valid) <= law.max_primitives_per_frame:
        return valid, invalid

    sorted_by_area = sorted(valid, key=lambda p: p.bbox.area, reverse=True)
    kept = sorted_by_area[:law.max_primitives_per_frame]
    dropped = sorted_by_area[law.max_primitives_per_frame:] + invalid
    return kept, dropped


# ════════════════════════════════════════════════════════════
# FRAME EXECUTOR — full frame evaluation
# ════════════════════════════════════════════════════════════

def execute_frame(
    frame_index: int,
    primitives: List[VisualPrimitive],
    bindings: Optional[Dict[str, VisualPrimitive]] = None,
    operations: Optional[List[Dict]] = None,
    law: GrammarLaw = V1_LAW,
) -> GrammarFrame:
    """
    Execute a full frame through the V1 grammar.

    Parameters:
        frame_index: Sequential frame identifier.
        primitives: Raw primitives from CV extraction.
        bindings: Optional dict of {name: primitive} for BIND operations.
        operations: Optional list of operations to evaluate.
            Each operation is a dict with:
                {"op": OperationKind, "a_index": int, "b_index": int}
            If None, evaluates all pairwise ADJACENT and CONTAINS.
        law: The grammar law to apply (defaults to V1_LAW).

    Returns:
        A GrammarFrame containing filtered primitives, bindings,
        and all evaluated relations.
    """
    frame = GrammarFrame(frame_index=frame_index)

    # Step 1: filter primitives
    kept, _dropped = filter_primitives(primitives, law)
    frame.primitives = kept

    # Step 2: process bindings
    if bindings:
        for name, prim in bindings.items():
            if prim.is_valid(law) and prim in kept:
                binding = evaluate_bind(name, prim, frame_index)
                frame.bindings[name] = binding

    # Step 3: evaluate operations
    if operations is not None:
        # Explicit operation list
        for op_spec in operations:
            op_kind = op_spec["op"]
            a_idx = op_spec["a_index"]
            b_idx = op_spec["b_index"]

            if a_idx >= len(kept) or b_idx >= len(kept):
                continue

            a = kept[a_idx]
            b = kept[b_idx]

            if op_kind == OperationKind.ADJACENT:
                rel = evaluate_adjacent(a, b, law)
            elif op_kind == OperationKind.CONTAINS:
                rel = evaluate_contains(a, b, law)
            else:
                continue

            frame.relations.append(rel)
    else:
        # Default: all pairwise ADJACENT and CONTAINS
        for i in range(len(kept)):
            for j in range(i + 1, len(kept)):
                frame.relations.append(evaluate_adjacent(kept[i], kept[j], law))
                frame.relations.append(evaluate_contains(kept[i], kept[j], law))
                frame.relations.append(evaluate_contains(kept[j], kept[i], law))

    return frame
