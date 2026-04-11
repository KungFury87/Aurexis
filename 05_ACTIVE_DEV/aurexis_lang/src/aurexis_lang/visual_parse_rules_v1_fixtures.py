"""
Aurexis Core — Visual Parse Rules V1 Canonical Fixtures (FROZEN)

These fixtures define deterministic parse inputs (GrammarFrames) with
exact expected program tree outputs. Every fixture has one correct
parse result under V1 rules.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from typing import List, Dict, Any

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarLaw, V1_LAW, BoundingBox, VisualPrimitive, Binding,
    Relation, GrammarFrame, GRAMMAR_VERSION,
)
from aurexis_lang.visual_executor_v1 import (
    evaluate_adjacent, evaluate_contains, evaluate_bind, execute_frame,
)
from aurexis_lang.visual_parse_rules_v1 import ProgramNodeKind


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def _prim(kind: PrimitiveKind, x: float, y: float, w: float, h: float,
          conf: float = 1.0) -> VisualPrimitive:
    return VisualPrimitive(
        kind=kind,
        bbox=BoundingBox(x=x, y=y, width=w, height=h),
        source_confidence=conf,
    )


def _frame_with_bindings_and_relations(
    frame_index: int,
    primitives: List[VisualPrimitive],
    bindings: Dict[str, VisualPrimitive],
    ops: List[Dict],
) -> GrammarFrame:
    """Build a frame using the executor for relations."""
    return execute_frame(frame_index, primitives, bindings=bindings, operations=ops)


# ════════════════════════════════════════════════════════════
# FIXTURE 1: Empty frame → empty program
# ════════════════════════════════════════════════════════════

class EmptyFrameFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        frame = GrammarFrame(frame_index=0)
        return {
            "name": "empty_frame",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 0,
            "expected_confidence": 0.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
            "expected_total_statements": 0,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 2: Single binding → one Assignment
# ════════════════════════════════════════════════════════════

class SingleBindingFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        p = _prim(PrimitiveKind.REGION, 10, 10, 80, 80, conf=1.0)
        frame = execute_frame(0, [p], bindings={"green_patch": p}, operations=[])

        return {
            "name": "single_binding",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 1,
            "expected_confidence": 1.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
            "expected_total_statements": 1,
            "expected_children": [
                {
                    "kind": ProgramNodeKind.BINDING_STMT,
                    "target": "green_patch",
                    "confidence": 1.0,
                    "execution_status": ExecutionStatus.DETERMINISTIC,
                    "child_count": 1,
                    "child_kind": ProgramNodeKind.PRIMITIVE_REF,
                    "child_primitive_kind": "REGION",
                },
            ],
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 3: Single relation → one BinaryExpression
# ════════════════════════════════════════════════════════════

class SingleRelationFixture:

    @staticmethod
    def adjacent_true() -> Dict[str, Any]:
        """Two touching regions → ADJACENT TRUE → one BinaryExpression."""
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
        ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
        frame = execute_frame(0, [a, b], operations=ops)

        return {
            "name": "single_relation_adjacent_true",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 1,
            "expected_confidence": 1.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
            "expected_total_statements": 1,
            "expected_children": [
                {
                    "kind": ProgramNodeKind.RELATION_EXPR,
                    "operation": "ADJACENT",
                    "result": "TRUE",
                    "measured_value": 0.0,
                    "confidence": 1.0,
                    "execution_status": ExecutionStatus.DETERMINISTIC,
                    "child_count": 2,
                },
            ],
        }

    @staticmethod
    def contains_true() -> Dict[str, Any]:
        """Outer contains inner → CONTAINS TRUE → one BinaryExpression."""
        outer = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
        inner = _prim(PrimitiveKind.REGION, 50, 50, 50, 50)
        ops = [{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}]
        frame = execute_frame(0, [outer, inner], operations=ops)

        return {
            "name": "single_relation_contains_true",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 1,
            "expected_confidence": 1.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
            "expected_total_statements": 1,
            "expected_children": [
                {
                    "kind": ProgramNodeKind.RELATION_EXPR,
                    "operation": "CONTAINS",
                    "result": "TRUE",
                    "measured_value": 50.0,
                    "confidence": 1.0,
                    "execution_status": ExecutionStatus.DETERMINISTIC,
                    "child_count": 2,
                },
            ],
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 4: Mixed bindings + relations
# ════════════════════════════════════════════════════════════

class MixedFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        """
        Three primitives: two regions and a point.
        Two bindings: "box_a", "box_b"
        One relation: ADJACENT(box_a, box_b) → TRUE (10px gap)

        Expected program:
          Program (3 children)
            Assignment: box_a = REGION ref
            Assignment: box_b = REGION ref
            BinaryExpression: ADJACENT(box_a, box_b) → TRUE
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 110, 0, 100, 100)
        pt = _prim(PrimitiveKind.POINT, 50, 50, 5, 5)
        ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
        frame = execute_frame(0, [a, b, pt],
                              bindings={"box_a": a, "box_b": b},
                              operations=ops)

        return {
            "name": "mixed_bindings_and_relations",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 3,  # 2 assignments + 1 expression
            "expected_confidence": 1.0,
            "expected_execution_status": ExecutionStatus.DETERMINISTIC,
            "expected_total_statements": 3,
            "expected_assignment_count": 2,
            "expected_relation_count": 1,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 5: Heuristic input propagation
# ════════════════════════════════════════════════════════════

class HeuristicFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        """
        One primitive with confidence < 1.0.
        The binding and any relations should have HEURISTIC_INPUT status.
        Root program should also be HEURISTIC_INPUT.
        """
        p = _prim(PrimitiveKind.REGION, 10, 10, 80, 80, conf=0.65)
        frame = execute_frame(0, [p], bindings={"uncertain_region": p}, operations=[])

        return {
            "name": "heuristic_input_propagation",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 1,
            "expected_confidence": 0.65,
            "expected_execution_status": ExecutionStatus.HEURISTIC_INPUT,
            "expected_total_statements": 1,
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 6: Multiple relations same frame
# ════════════════════════════════════════════════════════════

class MultiRelationFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        """
        Three regions in a row:
          R1: (0,0)-(100,100)
          R2: (110,0)-(210,100) — 10px from R1
          R3: (300,0)-(400,100) — 90px from R2

        Three relations:
          ADJACENT(R1, R2) → TRUE (10px)
          ADJACENT(R1, R3) → FALSE (200px)
          CONTAINS(R1, R2) → FALSE
        """
        r1 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        r2 = _prim(PrimitiveKind.REGION, 110, 0, 100, 100)
        r3 = _prim(PrimitiveKind.REGION, 300, 0, 100, 100)
        ops = [
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 2},
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1},
        ]
        frame = execute_frame(0, [r1, r2, r3], operations=ops)

        return {
            "name": "multi_relation",
            "frame": frame,
            "expected_root_kind": ProgramNodeKind.PROGRAM,
            "expected_child_count": 3,
            "expected_total_statements": 3,
            "expected_relation_results": ["TRUE", "FALSE", "FALSE"],
            "expected_relation_operations": ["ADJACENT", "ADJACENT", "CONTAINS"],
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 7: AST/IR bridge output
# ════════════════════════════════════════════════════════════

class BridgeFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        """
        Simple binding parsed to program, then converted to AST and IR dicts.
        Verifies the bridge functions produce correct structure.
        """
        p = _prim(PrimitiveKind.REGION, 0, 0, 50, 50, conf=0.9)
        frame = execute_frame(0, [p], bindings={"my_region": p}, operations=[])

        return {
            "name": "ast_ir_bridge",
            "frame": frame,
            "expected_ast_root_type": "Program",
            "expected_ast_child_type": "Assignment",
            "expected_ir_root_op": "program",
            "expected_ir_child_op": "assign",
        }


# ════════════════════════════════════════════════════════════
# FIXTURE 8: Determinism proof — same frame, multiple parses
# ════════════════════════════════════════════════════════════

class DeterminismFixture:

    @staticmethod
    def get() -> Dict[str, Any]:
        """
        A frame with 2 bindings and 2 relations.
        Parse 10 times → must produce identical program trees.
        """
        a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
        b = _prim(PrimitiveKind.REGION, 120, 0, 100, 100)
        ops = [
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1},
        ]
        frame = execute_frame(0, [a, b],
                              bindings={"left": a, "right": b},
                              operations=ops)

        return {
            "name": "determinism_proof",
            "frame": frame,
            "repeat_count": 10,
        }


# ════════════════════════════════════════════════════════════
# MASTER FIXTURE REGISTRY
# ════════════════════════════════════════════════════════════

def all_parse_fixtures() -> List[Dict[str, Any]]:
    return [
        EmptyFrameFixture.get(),
        SingleBindingFixture.get(),
        SingleRelationFixture.adjacent_true(),
        SingleRelationFixture.contains_true(),
        MixedFixture.get(),
        HeuristicFixture.get(),
        MultiRelationFixture.get(),
        BridgeFixture.get(),
        DeterminismFixture.get(),
    ]


PARSE_FIXTURE_COUNTS = {
    "total": 9,
}
