"""
Standalone test runner for Visual Program Executor V1.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    BoundingBox, VisualPrimitive, GrammarFrame, GRAMMAR_VERSION,
)
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import (
    ProgramNodeKind, parse_frame_to_program, PARSE_RULES_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import (
    execute_program, execute_image_as_program,
    ProgramVerdict, StepKind, ExecutionResult, EXECUTOR_VERSION,
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


def _prim(kind, x, y, w, h, conf=1.0):
    return VisualPrimitive(kind=kind, bbox=BoundingBox(x, y, w, h),
                           source_confidence=conf)


# ═══════ SPEC ═══════
print("\n=== Executor Spec ===")
check("executor_version", EXECUTOR_VERSION == "V1.0")

# ═══════ EMPTY PROGRAM ═══════
print("\n=== Empty Program ===")
frame = GrammarFrame(frame_index=0)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("empty_verdict", result.verdict == ProgramVerdict.EMPTY)
check("empty_bindings", result.total_bindings == 0)
check("empty_assertions", result.total_assertions == 0)
check("empty_status", result.execution_status == ExecutionStatus.DETERMINISTIC)
check("empty_not_proof", result.is_proof is False)  # No assertions

# ═══════ SINGLE BINDING ═══════
print("\n=== Single Binding ===")
p = _prim(PrimitiveKind.REGION, 10, 10, 80, 80)
frame = execute_frame(0, [p], bindings={"patch": p}, operations=[])
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("bind_verdict", result.verdict == ProgramVerdict.EMPTY)  # No assertions
check("bind_count", result.total_bindings == 1)
check("bind_name", "patch" in result.bindings)
check("bind_kind", result.bindings["patch"]["primitive_kind"] == "REGION")

# ═══════ ALL TRUE → PASS ═══════
print("\n=== All True → PASS ===")
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
frame = execute_frame(0, [a, b], operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("pass_verdict", result.verdict == ProgramVerdict.PASS)
check("pass_true", result.true_assertions == 1)
check("pass_false", result.false_assertions == 0)
check("pass_status", result.execution_status == ExecutionStatus.DETERMINISTIC)
check("pass_is_proof", result.is_proof is True)

# ═══════ ONE FALSE → FAIL ═══════
print("\n=== One False → FAIL ===")
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
b = _prim(PrimitiveKind.REGION, 200, 0, 100, 100)  # 100px gap > 30px threshold
ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
frame = execute_frame(0, [a, b], operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("fail_verdict", result.verdict == ProgramVerdict.FAIL)
check("fail_false", result.false_assertions == 1)
check("fail_not_proof", result.is_proof is False)

# ═══════ HEURISTIC → PARTIAL ═══════
print("\n=== Heuristic → PARTIAL ===")
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100, conf=0.7)
b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
frame = execute_frame(0, [a, b], operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("partial_verdict", result.verdict == ProgramVerdict.PARTIAL)
check("partial_true", result.true_assertions == 1)
check("partial_status", result.execution_status == ExecutionStatus.HEURISTIC_INPUT)
check("partial_not_proof", result.is_proof is False)  # heuristic = not proof

# ═══════ MIXED TRUE/FALSE → FAIL ═══════
print("\n=== Mixed True/False → FAIL ===")
r1 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
r2 = _prim(PrimitiveKind.REGION, 110, 0, 100, 100)   # 10px → adjacent TRUE
r3 = _prim(PrimitiveKind.REGION, 300, 0, 100, 100)    # 190px → adjacent FALSE
ops = [
    {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
    {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 2},
]
frame = execute_frame(0, [r1, r2, r3], operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("mixed_verdict", result.verdict == ProgramVerdict.FAIL)
check("mixed_true", result.true_assertions == 1)
check("mixed_false", result.false_assertions == 1)

# ═══════ CONTAINS TRUE → PASS ═══════
print("\n=== Contains TRUE → PASS ===")
outer = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
inner = _prim(PrimitiveKind.POINT, 50, 50, 5, 5)
ops = [{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}]
frame = execute_frame(0, [outer, inner], operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("contains_verdict", result.verdict == ProgramVerdict.PASS)
check("contains_is_proof", result.is_proof is True)

# ═══════ BINDINGS + RELATIONS ═══════
print("\n=== Bindings + Relations ===")
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
ops = [{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}]
frame = execute_frame(0, [a, b], bindings={"left": a, "right": b}, operations=ops)
prog = parse_frame_to_program(frame)
result = execute_program(prog)
check("combo_verdict", result.verdict == ProgramVerdict.PASS)
check("combo_bindings", result.total_bindings == 2)
check("combo_assertions", result.total_assertions == 1)
check("combo_left", "left" in result.bindings)
check("combo_right", "right" in result.bindings)

# ═══════ EXECUTION TRACE ═══════
print("\n=== Execution Trace ===")
check("trace_start", result.trace[0].kind == StepKind.PROGRAM_START)
check("trace_end", result.trace[-1].kind == StepKind.PROGRAM_END)
bind_steps = [s for s in result.trace if s.kind == StepKind.BIND]
assert_steps = [s for s in result.trace if s.kind in (StepKind.ASSERT_TRUE, StepKind.ASSERT_FALSE)]
check("trace_binds", len(bind_steps) == 2)
check("trace_asserts", len(assert_steps) == 1)
check("trace_indices", all(s.step_index >= 0 for s in result.trace))
check("trace_monotonic", all(
    result.trace[i].step_index < result.trace[i+1].step_index
    for i in range(len(result.trace)-1)
))

# ═══════ SERIALIZATION ═══════
print("\n=== Serialization ===")
d = result.to_dict()
check("ser_verdict", d["verdict"] == "PASS")
check("ser_grammar", d["grammar_version"] == GRAMMAR_VERSION)
check("ser_parse", d["parse_rules_version"] == PARSE_RULES_VERSION)
check("ser_executor", d["executor_version"] == EXECUTOR_VERSION)
check("ser_trace_count", len(d["trace"]) == len(result.trace))
check("ser_bindings", len(d["bindings"]) == 2)
check("ser_assertions", len(d["assertions"]) == 1)

# ═══════ END-TO-END: execute_image_as_program ═══════
print("\n=== End-to-End: execute_image_as_program ===")
raw = [
    {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
    {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
    {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
]
e2e = execute_image_as_program(
    raw,
    bindings={"patch_a": 0, "patch_b": 1},
    operations=[
        {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
        {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 2},
    ],
    frame_index=42,
)
check("e2e_verdict", e2e.verdict == ProgramVerdict.PASS)
check("e2e_frame", e2e.frame_index == 42)
check("e2e_bindings", e2e.total_bindings == 2)
check("e2e_assertions", e2e.total_assertions == 2)
check("e2e_all_true", e2e.true_assertions == 2)
check("e2e_is_proof", e2e.is_proof is True)
check("e2e_status", e2e.execution_status == ExecutionStatus.DETERMINISTIC)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
results = [
    execute_image_as_program(
        raw,
        bindings={"patch_a": 0, "patch_b": 1},
        operations=[
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 2},
        ],
    )
    for _ in range(10)
]
dicts = [r.to_dict() for r in results]
check("det_all_same", all(d == dicts[0] for d in dicts))

# ═══════ IMAGE-AS-PROGRAM PROOF ═══════
print("\n=== Image-as-Program Proof ===")
# This is the canonical proof: raw CV data → deterministic execution
proof_raw = [
    {"type": "region", "bbox": [10, 10, 120, 80], "confidence": 1.0,
     "dominant_color": "green"},
    {"type": "region", "bbox": [140, 10, 120, 80], "confidence": 1.0,
     "dominant_color": "blue"},
    {"type": "region", "bbox": [0, 0, 300, 100], "confidence": 1.0,
     "dominant_color": "white"},
]
proof = execute_image_as_program(
    proof_raw,
    bindings={"green_box": 0, "blue_box": 1, "background": 2},
    operations=[
        {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
        {"op": OperationKind.CONTAINS, "a_index": 2, "b_index": 0},
        {"op": OperationKind.CONTAINS, "a_index": 2, "b_index": 1},
    ],
)
check("proof_verdict", proof.verdict == ProgramVerdict.PASS)
check("proof_is_proof", proof.is_proof is True)
check("proof_bindings", proof.total_bindings == 3)
check("proof_assertions", proof.total_assertions == 3)
check("proof_all_true", proof.true_assertions == 3)
check("proof_trace_has_steps", len(proof.trace) >= 8)  # start + 3 binds + 3 asserts + end

# Verify the proof semantics: green_box adjacent to blue_box,
# background contains both
adj_assert = proof.assertions[0]
check("proof_adj_op", adj_assert["operation"] == "ADJACENT")
check("proof_adj_true", adj_assert["result"] == "TRUE")
check("proof_adj_measured", adj_assert["measured_value"] == 10.0)  # 140-130=10px gap

cnt1 = proof.assertions[1]
check("proof_cnt1_op", cnt1["operation"] == "CONTAINS")
check("proof_cnt1_true", cnt1["result"] == "TRUE")

cnt2 = proof.assertions[2]
check("proof_cnt2_op", cnt2["operation"] == "CONTAINS")
check("proof_cnt2_true", cnt2["result"] == "TRUE")

# This result proves: the image (3 regions) was treated as source code.
# The program says: "green_box is adjacent to blue_box, and background
# contains both." The executor evaluated this deterministically and
# returned PASS with a complete trace.

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
    print("\n  IMAGE-AS-PROGRAM PROOF: A photograph can be treated as source code.")
    print("  Raw CV data → V1 primitives → grammar evaluation → parse rules →")
    print("  program tree → deterministic execution → PASS verdict with trace.")
    sys.exit(0)
