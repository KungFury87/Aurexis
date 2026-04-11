"""
Standalone test runner for Visual Parse Rules V1 — no pytest dependency.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

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
passed = 0
failed = 0
errors = []


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        errors.append(f"{name}: {msg}")
        print(f"  FAIL  {name} — {msg}")


# ═══════ SPEC CHECKS ═══════
print("\n=== Parse Rules Spec ===")
check("parse_rules_version", PARSE_RULES_VERSION == "V1.0")
check("parse_rules_frozen", PARSE_RULES_FROZEN is True)
check("rule_count", len(V1_PARSE_RULES) == 2)
check("rule_order", V1_PARSE_RULES[0].priority < V1_PARSE_RULES[1].priority,
      f"priorities: {[r.priority for r in V1_PARSE_RULES]}")
check("fixture_count", len(all_parse_fixtures()) == PARSE_FIXTURE_COUNTS["total"])

# ═══════ FIXTURE 1: Empty frame ═══════
print("\n=== Empty Frame ===")
fx = EmptyFrameFixture.get()
prog = parse_frame_to_program(fx["frame"])
check("empty_root_kind", prog.kind == fx["expected_root_kind"])
check("empty_child_count", len(prog.children) == fx["expected_child_count"])
check("empty_confidence", abs(prog.confidence - fx["expected_confidence"]) < FLOAT_TOL)
check("empty_status", prog.execution_status == fx["expected_execution_status"])
check("empty_statements", prog.value["total_statements"] == fx["expected_total_statements"])

# ═══════ FIXTURE 2: Single binding ═══════
print("\n=== Single Binding ===")
fx = SingleBindingFixture.get()
prog = parse_frame_to_program(fx["frame"])
check("bind_root_kind", prog.kind == fx["expected_root_kind"])
check("bind_child_count", len(prog.children) == fx["expected_child_count"])
check("bind_confidence", abs(prog.confidence - fx["expected_confidence"]) < FLOAT_TOL)
check("bind_status", prog.execution_status == fx["expected_execution_status"])
check("bind_statements", prog.value["total_statements"] == fx["expected_total_statements"])

# Check the child
expected = fx["expected_children"][0]
child = prog.children[0]
check("bind_child_kind", child.kind == expected["kind"])
check("bind_child_target", child.value["target"] == expected["target"],
      f"got {child.value.get('target')}")
check("bind_child_conf", abs(child.confidence - expected["confidence"]) < FLOAT_TOL)
check("bind_child_status", child.execution_status == expected["execution_status"])
check("bind_child_children", len(child.children) == expected["child_count"])
check("bind_grandchild_kind", child.children[0].kind == expected["child_kind"])
check("bind_grandchild_prim", child.children[0].value["primitive_kind"] == expected["child_primitive_kind"])

# ═══════ FIXTURE 3a: Single relation (adjacent) ═══════
print("\n=== Single Relation — Adjacent TRUE ===")
fx = SingleRelationFixture.adjacent_true()
prog = parse_frame_to_program(fx["frame"])
check("adj_root_kind", prog.kind == fx["expected_root_kind"])
check("adj_child_count", len(prog.children) == fx["expected_child_count"])
check("adj_confidence", abs(prog.confidence - fx["expected_confidence"]) < FLOAT_TOL)
check("adj_status", prog.execution_status == fx["expected_execution_status"])

expected = fx["expected_children"][0]
child = prog.children[0]
check("adj_child_kind", child.kind == expected["kind"])
check("adj_child_op", child.value["operation"] == expected["operation"],
      f"got {child.value.get('operation')}")
check("adj_child_result", child.value["result"] == expected["result"],
      f"got {child.value.get('result')}")
check("adj_child_measured", abs(child.value["measured_value"] - expected["measured_value"]) < FLOAT_TOL)
check("adj_child_conf", abs(child.confidence - expected["confidence"]) < FLOAT_TOL)
check("adj_child_children", len(child.children) == expected["child_count"])

# ═══════ FIXTURE 3b: Single relation (contains) ═══════
print("\n=== Single Relation — Contains TRUE ===")
fx = SingleRelationFixture.contains_true()
prog = parse_frame_to_program(fx["frame"])
expected = fx["expected_children"][0]
child = prog.children[0]
check("cnt_child_kind", child.kind == expected["kind"])
check("cnt_child_op", child.value["operation"] == expected["operation"])
check("cnt_child_result", child.value["result"] == expected["result"])
check("cnt_child_measured", abs(child.value["measured_value"] - expected["measured_value"]) < FLOAT_TOL)

# ═══════ FIXTURE 4: Mixed bindings + relations ═══════
print("\n=== Mixed Bindings + Relations ===")
fx = MixedFixture.get()
prog = parse_frame_to_program(fx["frame"])
check("mixed_root_kind", prog.kind == fx["expected_root_kind"])
check("mixed_child_count", len(prog.children) == fx["expected_child_count"],
      f"got {len(prog.children)}")
check("mixed_statements", prog.value["total_statements"] == fx["expected_total_statements"])

assignments = [c for c in prog.children if c.kind == ProgramNodeKind.BINDING_STMT]
relations = [c for c in prog.children if c.kind == ProgramNodeKind.RELATION_EXPR]
check("mixed_assignment_count", len(assignments) == fx["expected_assignment_count"],
      f"got {len(assignments)}")
check("mixed_relation_count", len(relations) == fx["expected_relation_count"],
      f"got {len(relations)}")

# Verify assignment targets are sorted
targets = [a.value["target"] for a in assignments]
check("mixed_targets_sorted", targets == sorted(targets), f"got {targets}")

# ═══════ FIXTURE 5: Heuristic propagation ═══════
print("\n=== Heuristic Input Propagation ===")
fx = HeuristicFixture.get()
prog = parse_frame_to_program(fx["frame"])
check("heur_root_status", prog.execution_status == fx["expected_execution_status"],
      f"got {prog.execution_status.name}")
check("heur_root_conf", abs(prog.confidence - fx["expected_confidence"]) < FLOAT_TOL,
      f"got {prog.confidence}")
check("heur_child_status",
      prog.children[0].execution_status == ExecutionStatus.HEURISTIC_INPUT)

# ═══════ FIXTURE 6: Multi-relation ═══════
print("\n=== Multi Relation ===")
fx = MultiRelationFixture.get()
prog = parse_frame_to_program(fx["frame"])
check("multi_child_count", len(prog.children) == fx["expected_child_count"])
check("multi_statements", prog.value["total_statements"] == fx["expected_total_statements"])

results = [c.value["result"] for c in prog.children]
operations = [c.value["operation"] for c in prog.children]
check("multi_results", results == fx["expected_relation_results"],
      f"got {results}")
check("multi_operations", operations == fx["expected_relation_operations"],
      f"got {operations}")

# ═══════ FIXTURE 7: AST/IR bridge ═══════
print("\n=== AST/IR Bridge ===")
fx = BridgeFixture.get()
prog = parse_frame_to_program(fx["frame"])

ast_dict = program_node_to_ast_dict(prog)
check("bridge_ast_root", ast_dict["node_type"] == fx["expected_ast_root_type"])
check("bridge_ast_child", ast_dict["children"][0]["node_type"] == fx["expected_ast_child_type"],
      f"got {ast_dict['children'][0]['node_type']}" if ast_dict["children"] else "no children")

ir_dict = program_node_to_ir_dict(prog)
check("bridge_ir_root", ir_dict["op"] == fx["expected_ir_root_op"])
check("bridge_ir_child", ir_dict["children"][0]["op"] == fx["expected_ir_child_op"],
      f"got {ir_dict['children'][0]['op']}" if ir_dict["children"] else "no children")

# Verify metadata propagation
check("bridge_ir_metadata", ir_dict["metadata"]["grammar_version"] == GRAMMAR_VERSION)
check("bridge_ir_parse_version", ir_dict["metadata"]["parse_rules_version"] == PARSE_RULES_VERSION)

# ═══════ FIXTURE 8: Determinism proof ═══════
print("\n=== Determinism Proof ===")
fx = DeterminismFixture.get()
programs = [parse_frame_to_program(fx["frame"]) for _ in range(fx["repeat_count"])]

# All programs must have identical to_dict output
dicts = [p.to_dict() for p in programs]
all_same = all(d == dicts[0] for d in dicts)
check("determinism_all_same", all_same,
      f"Not all {fx['repeat_count']} parses produced identical output")

# Specific checks on the first parse
first = programs[0]
check("det_child_count", len(first.children) == 4,
      f"expected 4 (2 bindings + 2 relations), got {len(first.children)}")
check("det_confidence", first.confidence == 1.0)
check("det_status", first.execution_status == ExecutionStatus.DETERMINISTIC)

# ═══════ SERIALIZATION ROUNDTRIP ═══════
print("\n=== Serialization ===")
fx = MixedFixture.get()
prog = parse_frame_to_program(fx["frame"])
d = prog.to_dict()
check("ser_kind", d["kind"] == "Program")
check("ser_children_count", len(d["children"]) == 3)
check("ser_grammar", d["grammar_version"] == GRAMMAR_VERSION)
check("ser_status", d["execution_status"] == "DETERMINISTIC")

# Check each child serialized correctly
for child_dict in d["children"]:
    check(f"ser_child_{child_dict['kind']}_has_value", "value" in child_dict)
    check(f"ser_child_{child_dict['kind']}_has_children", "children" in child_dict)

# ═══════ SUMMARY ═══════
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
if errors:
    print("\nFAILURES:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("\nALL TESTS PASSED ✓")
    sys.exit(0)
