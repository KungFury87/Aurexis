"""
Aurexis Core — Visual Parse Rules V1 Deterministic Test Suite (pytest format)

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarFrame, GRAMMAR_VERSION,
)
from aurexis_lang.visual_parse_rules_v1 import (
    ProgramNodeKind, ProgramNode, parse_frame_to_program,
    program_node_to_ast_dict, program_node_to_ir_dict,
    PARSE_RULES_VERSION, PARSE_RULES_FROZEN, V1_PARSE_RULES,
)
from aurexis_lang.visual_parse_rules_v1_fixtures import (
    EmptyFrameFixture, SingleBindingFixture, SingleRelationFixture,
    MixedFixture, HeuristicFixture, MultiRelationFixture,
    BridgeFixture, DeterminismFixture,
    all_parse_fixtures, PARSE_FIXTURE_COUNTS,
)

FLOAT_TOL = 1e-9


class TestParseRulesSpec:
    def test_version(self):
        assert PARSE_RULES_VERSION == "V1.0"

    def test_frozen(self):
        assert PARSE_RULES_FROZEN is True

    def test_rule_count(self):
        assert len(V1_PARSE_RULES) == 2

    def test_fixture_count(self):
        assert len(all_parse_fixtures()) == PARSE_FIXTURE_COUNTS["total"]


class TestEmptyFrame:
    def test_parse(self):
        fx = EmptyFrameFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        assert prog.kind == ProgramNodeKind.PROGRAM
        assert len(prog.children) == 0
        assert prog.confidence == 0.0
        assert prog.execution_status == ExecutionStatus.DETERMINISTIC


class TestSingleBinding:
    def test_parse(self):
        fx = SingleBindingFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        assert len(prog.children) == 1
        child = prog.children[0]
        assert child.kind == ProgramNodeKind.BINDING_STMT
        assert child.value["target"] == "green_patch"
        assert child.children[0].kind == ProgramNodeKind.PRIMITIVE_REF


class TestSingleRelation:
    def test_adjacent(self):
        fx = SingleRelationFixture.adjacent_true()
        prog = parse_frame_to_program(fx["frame"])
        child = prog.children[0]
        assert child.kind == ProgramNodeKind.RELATION_EXPR
        assert child.value["operation"] == "ADJACENT"
        assert child.value["result"] == "TRUE"

    def test_contains(self):
        fx = SingleRelationFixture.contains_true()
        prog = parse_frame_to_program(fx["frame"])
        child = prog.children[0]
        assert child.value["operation"] == "CONTAINS"
        assert child.value["result"] == "TRUE"


class TestMixed:
    def test_parse(self):
        fx = MixedFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        assert len(prog.children) == 3
        assignments = [c for c in prog.children if c.kind == ProgramNodeKind.BINDING_STMT]
        relations = [c for c in prog.children if c.kind == ProgramNodeKind.RELATION_EXPR]
        assert len(assignments) == 2
        assert len(relations) == 1


class TestHeuristic:
    def test_propagation(self):
        fx = HeuristicFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        assert prog.execution_status == ExecutionStatus.HEURISTIC_INPUT
        assert abs(prog.confidence - 0.65) < FLOAT_TOL


class TestDeterminism:
    def test_repeated_parse(self):
        fx = DeterminismFixture.get()
        dicts = [parse_frame_to_program(fx["frame"]).to_dict() for _ in range(10)]
        assert all(d == dicts[0] for d in dicts)


class TestBridge:
    def test_ast(self):
        fx = BridgeFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        ast = program_node_to_ast_dict(prog)
        assert ast["node_type"] == "Program"
        assert ast["children"][0]["node_type"] == "Assignment"

    def test_ir(self):
        fx = BridgeFixture.get()
        prog = parse_frame_to_program(fx["frame"])
        ir = program_node_to_ir_dict(prog)
        assert ir["op"] == "program"
        assert ir["children"][0]["op"] == "assign"
        assert ir["metadata"]["grammar_version"] == GRAMMAR_VERSION
