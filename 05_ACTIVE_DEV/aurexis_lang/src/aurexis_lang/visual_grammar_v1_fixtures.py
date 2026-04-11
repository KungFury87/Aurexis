"""
Aurexis Core — Visual Grammar V1 Canonical Fixtures (FROZEN)

These fixtures define deterministic test inputs with exact expected outputs.
Every fixture has one correct answer under V1 law. No ambiguity, no heuristic.

If a fixture result changes, the grammar is broken — not the fixture.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from typing import List, Dict, Any

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarLaw, V1_LAW, BoundingBox, VisualPrimitive, Binding,
    Relation, GrammarFrame, GRAMMAR_VERSION,
)


# ════════════════════════════════════════════════════════════
# HELPER — build primitives compactly
# ════════════════════════════════════════════════════════════

def _prim(kind: PrimitiveKind, x: float, y: float, w: float, h: float,
          conf: float = 1.0, attrs: Dict[str, Any] | None = None) -> VisualPrimitive:
    return VisualPrimitive(
        kind=kind,
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
        source_confidence=conf,
        attributes=attrs or {},
    )


# ════════════════════════════════════════════════════════════
# FIXTURE SET 1 — ADJACENT operation
# ════════════════════════════════════════════════════════════

class AdjacentFixtures:
    """
    ADJACENT law: two primitives are adjacent if the minimum Euclidean
    distance between their bounding box edges <= 30.0 px.
    """

    @staticmethod
    def touching_regions() -> Dict[str, Any]:
        """Two regions sharing an edge → distance = 0.0 → ADJACENT TRUE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
        return {
            "name": "touching_regions",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 0.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def overlapping_regions() -> Dict[str, Any]:
        """Two overlapping regions → distance = 0.0 → ADJACENT TRUE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 50, 50, 100, 100)
        return {
            "name": "overlapping_regions",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 0.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def nearby_within_threshold() -> Dict[str, Any]:
        """
        Two regions with a 20px horizontal gap → distance = 20.0 → ADJACENT TRUE.
        A: (0,0)-(100,100), B: (120,0)-(220,100)
        Edge distance: 120 - 100 = 20px horizontal, 0 vertical → sqrt(20²+0²) = 20.0
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 120, 0, 100, 100)
        return {
            "name": "nearby_within_threshold",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 20.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def exactly_at_threshold() -> Dict[str, Any]:
        """
        Two regions with exactly 30px gap → distance = 30.0 → ADJACENT TRUE.
        A: (0,0)-(100,100), B: (130,0)-(230,100)
        Edge distance: 130 - 100 = 30px → exactly at threshold.
        Law: distance <= 30.0 → TRUE.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 130, 0, 100, 100)
        return {
            "name": "exactly_at_threshold",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 30.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def just_beyond_threshold() -> Dict[str, Any]:
        """
        Two regions with 31px gap → distance = 31.0 → ADJACENT FALSE.
        A: (0,0)-(100,100), B: (131,0)-(231,100)
        Edge distance: 131 - 100 = 31px → exceeds threshold.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 131, 0, 100, 100)
        return {
            "name": "just_beyond_threshold",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": 31.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def far_apart() -> Dict[str, Any]:
        """
        Two regions separated by 200px → ADJACENT FALSE.
        A: (0,0)-(50,50), B: (250,0)-(300,50)
        Edge distance: 250 - 50 = 200px → far beyond threshold.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 50, 50)
        b = _prim(PrimitiveKind.REGION, 250, 0, 50, 50)
        return {
            "name": "far_apart",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": 200.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def diagonal_within_threshold() -> Dict[str, Any]:
        """
        Two regions separated diagonally.
        A: (0,0)-(100,100), B: (120,120)-(220,220)
        dx = max(0, max(0-220, 120-100)) = max(0, 20) = 20
        dy = max(0, max(0-220, 120-100)) = max(0, 20) = 20
        distance = sqrt(20² + 20²) = sqrt(800) ≈ 28.284
        28.284 <= 30.0 → ADJACENT TRUE.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 120, 120, 100, 100)
        import math
        expected_dist = math.sqrt(20**2 + 20**2)  # 28.284271247...
        return {
            "name": "diagonal_within_threshold",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": expected_dist,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def diagonal_beyond_threshold() -> Dict[str, Any]:
        """
        Two regions separated diagonally beyond threshold.
        A: (0,0)-(100,100), B: (125,125)-(225,225)
        dx = 25, dy = 25
        distance = sqrt(25² + 25²) = sqrt(1250) ≈ 35.355
        35.355 > 30.0 → ADJACENT FALSE.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 125, 125, 100, 100)
        import math
        expected_dist = math.sqrt(25**2 + 25**2)  # 35.355339059...
        return {
            "name": "diagonal_beyond_threshold",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": expected_dist,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def mixed_primitive_types() -> Dict[str, Any]:
        """
        A REGION and a POINT that are adjacent.
        REGION: (0,0)-(100,100), POINT: (110,50)-(115,55)
        dx = 110 - 100 = 10, dy = 0 (overlapping vertically)
        distance = 10.0 → ADJACENT TRUE.
        Primitive types don't affect ADJACENT evaluation — pure geometry.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.POINT, 110, 50, 5, 5)
        return {
            "name": "mixed_primitive_types",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 10.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def heuristic_input_flagged() -> Dict[str, Any]:
        """
        Same geometry as touching_regions, but one primitive has
        source_confidence < 1.0, indicating heuristic CV input.
        Result is still TRUE (geometry doesn't change), but
        execution_status is HEURISTIC_INPUT.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100, conf=0.65)
        b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100, conf=1.0)
        return {
            "name": "heuristic_input_flagged",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.ADJACENT,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 0.0,
            "expected_law_threshold": 30.0,
            "expected_execution_status": ExecutionStatus.HEURISTIC_INPUT,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE SET 2 — CONTAINS operation
# ════════════════════════════════════════════════════════════

class ContainsFixtures:
    """
    CONTAINS law: primitive A contains primitive B if B's bounding box
    is fully within A's bounding box with margin >= 0.0 px on all sides.
    """

    @staticmethod
    def fully_contained() -> Dict[str, Any]:
        """B is well inside A → CONTAINS TRUE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
        b = _prim(PrimitiveKind.REGION, 50, 50, 50, 50)
        # Minimum margin: min(50-0, 50-0, 200-100, 200-100) = min(50,50,100,100) = 50
        return {
            "name": "fully_contained",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 50.0,  # min margin on all sides
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def exact_containment() -> Dict[str, Any]:
        """B exactly fills A → margin = 0 → CONTAINS TRUE (margin >= 0.0)."""
        a = _prim(PrimitiveKind.REGION, 10, 10, 100, 100)
        b = _prim(PrimitiveKind.REGION, 10, 10, 100, 100)
        return {
            "name": "exact_containment",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 0.0,
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def partial_overlap_not_contained() -> Dict[str, Any]:
        """B extends outside A on the right → CONTAINS FALSE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 50, 25, 100, 50)
        # B goes from (50,25) to (150,75) — B.x2=150 > A.x2=100
        # Margin on right: 100 - 150 = -50 (negative = outside)
        return {
            "name": "partial_overlap_not_contained",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": -50.0,
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def completely_outside() -> Dict[str, Any]:
        """B is completely outside A → CONTAINS FALSE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 200, 200, 50, 50)
        # B is at (200,200)-(250,250), A is at (0,0)-(100,100)
        # Margin: min(200-0, 200-0, 100-250, 100-250) = min(200, 200, -150, -150) = -150
        return {
            "name": "completely_outside",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": -150.0,
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def region_contains_point() -> Dict[str, Any]:
        """A region contains a small point primitive → CONTAINS TRUE."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
        b = _prim(PrimitiveKind.POINT, 95, 95, 5, 5)
        # B at (95,95)-(100,100), A at (0,0)-(200,200)
        # Margins: left=95, top=95, right=200-100=100, bottom=200-100=100
        # Min margin = 95
        return {
            "name": "region_contains_point",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.TRUE,
            "expected_measured_value": 95.0,
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }

    @staticmethod
    def containment_not_symmetric() -> Dict[str, Any]:
        """
        A contains B does NOT mean B contains A.
        Small primitive A cannot contain larger primitive B.
        """
        a = _prim(PrimitiveKind.REGION, 50, 50, 50, 50)  # (50,50)-(100,100)
        b = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)  # (0,0)-(200,200)
        # A.contains(B): margins: left=0-50=-50, top=0-50=-50,
        # right=100-200=-100, bottom=100-200=-100 → min = -100
        return {
            "name": "containment_not_symmetric",
            "operand_a": a,
            "operand_b": b,
            "operation": OperationKind.CONTAINS,
            "expected_result": RelationResult.FALSE,
            "expected_measured_value": -100.0,
            "expected_law_threshold": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE SET 3 — BIND operation
# ════════════════════════════════════════════════════════════

class BindFixtures:
    """
    BIND law: assigns a name to a primitive. Always succeeds for valid
    primitives. Produces a Binding, not a Relation.
    """

    @staticmethod
    def bind_region() -> Dict[str, Any]:
        """Bind a name to a valid region primitive."""
        p = _prim(PrimitiveKind.REGION, 10, 10, 80, 80)
        return {
            "name": "bind_region",
            "primitive": p,
            "bind_name": "green_patch",
            "expected_binding_name": "green_patch",
            "expected_primitive_kind": PrimitiveKind.REGION,
        }

    @staticmethod
    def bind_point() -> Dict[str, Any]:
        """Bind a name to a valid point primitive."""
        p = _prim(PrimitiveKind.POINT, 50, 50, 3, 3)
        return {
            "name": "bind_point",
            "primitive": p,
            "bind_name": "corner_a",
            "expected_binding_name": "corner_a",
            "expected_primitive_kind": PrimitiveKind.POINT,
        }

    @staticmethod
    def bind_edge() -> Dict[str, Any]:
        """Bind a name to a valid edge primitive."""
        p = _prim(PrimitiveKind.EDGE, 0, 50, 200, 3,
                   attrs={"orientation_deg": 0.0, "length_px": 200})
        return {
            "name": "bind_edge",
            "primitive": p,
            "bind_name": "horizon_line",
            "expected_binding_name": "horizon_line",
            "expected_primitive_kind": PrimitiveKind.EDGE,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE SET 4 — VALIDITY checks (error cases)
# ════════════════════════════════════════════════════════════

class ValidityFixtures:
    """
    Validity law: primitive must have bbox area >= 4.0 px² and
    width > 0 and height > 0 to be valid under V1 law.
    """

    @staticmethod
    def valid_minimum() -> Dict[str, Any]:
        """Exactly at minimum area: 2x2 = 4.0 px² → valid."""
        p = _prim(PrimitiveKind.POINT, 0, 0, 2, 2)
        return {
            "name": "valid_minimum",
            "primitive": p,
            "expected_valid": True,
        }

    @staticmethod
    def below_minimum_area() -> Dict[str, Any]:
        """Below minimum area: 1x3 = 3.0 px² → invalid."""
        p = _prim(PrimitiveKind.POINT, 0, 0, 1, 3)
        return {
            "name": "below_minimum_area",
            "primitive": p,
            "expected_valid": False,
        }

    @staticmethod
    def zero_width() -> Dict[str, Any]:
        """Zero width → invalid regardless of area formula."""
        p = _prim(PrimitiveKind.EDGE, 10, 10, 0, 100)
        return {
            "name": "zero_width",
            "primitive": p,
            "expected_valid": False,
        }

    @staticmethod
    def zero_height() -> Dict[str, Any]:
        """Zero height → invalid."""
        p = _prim(PrimitiveKind.EDGE, 10, 10, 100, 0)
        return {
            "name": "zero_height",
            "primitive": p,
            "expected_valid": False,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE SET 5 — FRAME-LEVEL fixtures
# ════════════════════════════════════════════════════════════

class FrameFixtures:
    """
    Frame-level fixtures that test the full grammar frame pipeline:
    multiple primitives → bindings → multiple relation evaluations.
    """

    @staticmethod
    def three_region_frame() -> Dict[str, Any]:
        """
        Three regions in a row:
          R1: (0,0)-(100,100)
          R2: (110,0)-(210,100)   — 10px gap from R1
          R3: (300,0)-(400,100)   — 90px gap from R2

        Expected relations:
          R1 ADJACENT R2 → TRUE  (distance = 10.0)
          R1 ADJACENT R3 → FALSE (distance = 200.0)
          R2 ADJACENT R3 → FALSE (distance = 90.0)
          R1 CONTAINS R2 → FALSE
          R1 CONTAINS R3 → FALSE
        """
        r1 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100,
                    attrs={"dominant_color": "red"})
        r2 = _prim(PrimitiveKind.REGION, 110, 0, 100, 100,
                    attrs={"dominant_color": "green"})
        r3 = _prim(PrimitiveKind.REGION, 300, 0, 100, 100,
                    attrs={"dominant_color": "blue"})
        return {
            "name": "three_region_frame",
            "primitives": [r1, r2, r3],
            "bindings": {"red_region": r1, "green_region": r2, "blue_region": r3},
            "expected_relations": [
                {
                    "operation": OperationKind.ADJACENT,
                    "a_index": 0, "b_index": 1,
                    "expected_result": RelationResult.TRUE,
                    "expected_measured_value": 10.0,
                },
                {
                    "operation": OperationKind.ADJACENT,
                    "a_index": 0, "b_index": 2,
                    "expected_result": RelationResult.FALSE,
                    "expected_measured_value": 200.0,
                },
                {
                    "operation": OperationKind.ADJACENT,
                    "a_index": 1, "b_index": 2,
                    "expected_result": RelationResult.FALSE,
                    "expected_measured_value": 90.0,
                },
            ],
        }

    @staticmethod
    def nested_containment_frame() -> Dict[str, Any]:
        """
        Nested containment:
          Outer: (0,0)-(300,300)
          Inner: (50,50)-(200,200)
          Point: (100,100)-(105,105)

        Expected:
          Outer CONTAINS Inner → TRUE  (min margin = 50)
          Outer CONTAINS Point → TRUE  (min margin = 100)
          Inner CONTAINS Point → TRUE  (min margin = 50)
          Inner CONTAINS Outer → FALSE (smaller can't contain larger)
        """
        outer = _prim(PrimitiveKind.REGION, 0, 0, 300, 300,
                       attrs={"dominant_color": "white"})
        inner = _prim(PrimitiveKind.REGION, 50, 50, 150, 150,
                       attrs={"dominant_color": "gray"})
        point = _prim(PrimitiveKind.POINT, 100, 100, 5, 5)
        return {
            "name": "nested_containment_frame",
            "primitives": [outer, inner, point],
            "bindings": {"outer": outer, "inner": inner, "keypoint": point},
            "expected_relations": [
                {
                    "operation": OperationKind.CONTAINS,
                    "a_index": 0, "b_index": 1,
                    "expected_result": RelationResult.TRUE,
                    "expected_measured_value": 50.0,
                },
                {
                    "operation": OperationKind.CONTAINS,
                    "a_index": 0, "b_index": 2,
                    "expected_result": RelationResult.TRUE,
                    "expected_measured_value": 100.0,
                },
                {
                    "operation": OperationKind.CONTAINS,
                    "a_index": 1, "b_index": 2,
                    "expected_result": RelationResult.TRUE,
                    "expected_measured_value": 50.0,
                },
                {
                    "operation": OperationKind.CONTAINS,
                    "a_index": 1, "b_index": 0,
                    "expected_result": RelationResult.FALSE,
                    "expected_measured_value": -100.0,
                },
            ],
        }

    @staticmethod
    def max_primitives_exceeded() -> Dict[str, Any]:
        """
        Generate 205 primitives (exceeding max_primitives_per_frame = 200).
        Executor must drop the 5 smallest-area primitives.
        Returns the primitives and the expected count after filtering.
        """
        prims = []
        for i in range(205):
            # First 200 have area 100 (10x10), last 5 have area 4 (2x2)
            if i < 200:
                prims.append(_prim(PrimitiveKind.REGION, i * 12, 0, 10, 10))
            else:
                prims.append(_prim(PrimitiveKind.REGION, i * 12, 0, 2, 2))
        return {
            "name": "max_primitives_exceeded",
            "primitives": prims,
            "expected_kept_count": 200,
            "expected_dropped_count": 5,
        }


# ════════════════════════════════════════════════════════════
# MASTER FIXTURE REGISTRY — for iteration by tests/executor
# ════════════════════════════════════════════════════════════

def all_adjacent_fixtures() -> List[Dict[str, Any]]:
    return [
        AdjacentFixtures.touching_regions(),
        AdjacentFixtures.overlapping_regions(),
        AdjacentFixtures.nearby_within_threshold(),
        AdjacentFixtures.exactly_at_threshold(),
        AdjacentFixtures.just_beyond_threshold(),
        AdjacentFixtures.far_apart(),
        AdjacentFixtures.diagonal_within_threshold(),
        AdjacentFixtures.diagonal_beyond_threshold(),
        AdjacentFixtures.mixed_primitive_types(),
        AdjacentFixtures.heuristic_input_flagged(),
    ]


def all_contains_fixtures() -> List[Dict[str, Any]]:
    return [
        ContainsFixtures.fully_contained(),
        ContainsFixtures.exact_containment(),
        ContainsFixtures.partial_overlap_not_contained(),
        ContainsFixtures.completely_outside(),
        ContainsFixtures.region_contains_point(),
        ContainsFixtures.containment_not_symmetric(),
    ]


def all_bind_fixtures() -> List[Dict[str, Any]]:
    return [
        BindFixtures.bind_region(),
        BindFixtures.bind_point(),
        BindFixtures.bind_edge(),
    ]


def all_validity_fixtures() -> List[Dict[str, Any]]:
    return [
        ValidityFixtures.valid_minimum(),
        ValidityFixtures.below_minimum_area(),
        ValidityFixtures.zero_width(),
        ValidityFixtures.zero_height(),
    ]


def all_frame_fixtures() -> List[Dict[str, Any]]:
    return [
        FrameFixtures.three_region_frame(),
        FrameFixtures.nested_containment_frame(),
        FrameFixtures.max_primitives_exceeded(),
    ]


# ════════════════════════════════════════════════════════════
# FIXTURE COUNTS — for gate verification
# ════════════════════════════════════════════════════════════

FIXTURE_COUNTS = {
    "adjacent": 10,
    "contains": 6,
    "bind": 3,
    "validity": 4,
    "frame": 3,
    "total": 26,
}
