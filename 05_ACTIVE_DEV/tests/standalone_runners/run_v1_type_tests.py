"""
Standalone test runner for Type System V1.
"""
import sys, os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, ExecutionStatus,
    BoundingBox, VisualPrimitive, GrammarFrame, Relation, Binding, V1_LAW,
)
from aurexis_lang.visual_executor_v1 import execute_frame, evaluate_adjacent, evaluate_contains
from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program, ProgramNodeKind, ProgramNode
from aurexis_lang.visual_program_executor_v1 import ProgramVerdict
from aurexis_lang.type_system_v1 import (
    TYPE_SYSTEM_VERSION, TYPE_SYSTEM_FROZEN,
    TypeErrorKind, TypeCheckVerdict,
    type_check_frame, type_check_program, safe_execute_image_as_program,
    check_primitive_valid, check_contains_type, check_self_relation,
    check_binding_name,
)

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
    return VisualPrimitive(kind=kind, bbox=BoundingBox(x, y, w, h), source_confidence=conf)

# ═══════ SPEC ═══════
print("\n=== Type System Spec ===")
check("version", TYPE_SYSTEM_VERSION == "V1.0")
check("frozen", TYPE_SYSTEM_FROZEN is True)

# ═══════ PRIMITIVE VALIDITY ═══════
print("\n=== Primitive Validity ===")
valid_prim = _prim(PrimitiveKind.REGION, 0, 0, 10, 10)
check("valid_prim_ok", check_primitive_valid(valid_prim, 0) is None)

invalid_prim = _prim(PrimitiveKind.POINT, 0, 0, 1, 1)  # area=1 < 4
err = check_primitive_valid(invalid_prim, 0)
check("invalid_prim_caught", err is not None)
check("invalid_prim_kind", err.kind == TypeErrorKind.INVALID_PRIMITIVE)

zero_w = _prim(PrimitiveKind.EDGE, 0, 0, 0, 10)
check("zero_width_caught", check_primitive_valid(zero_w, 0) is not None)

# ═══════ CONTAINS AREA RULE ═══════
print("\n=== Contains Area Rule ===")
big = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
small = _prim(PrimitiveKind.POINT, 50, 50, 5, 5)

check("contains_big_small_ok", check_contains_type(big, small, 0, 1) is None)
err_cs = check_contains_type(small, big, 0, 1)
check("contains_small_big_error", err_cs is not None)
check("contains_error_kind", err_cs.kind == TypeErrorKind.CONTAINS_AREA_VIOLATION)

# Equal areas: OK (a can contain something its own size)
equal_a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
equal_b = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
check("contains_equal_ok", check_contains_type(equal_a, equal_b, 0, 1) is None)

# ═══════ SELF RELATION ═══════
print("\n=== Self Relation ===")
check("self_adj_error", check_self_relation(0, 0, OperationKind.ADJACENT) is not None)
check("self_cnt_error", check_self_relation(1, 1, OperationKind.CONTAINS) is not None)
check("diff_ok", check_self_relation(0, 1, OperationKind.ADJACENT) is None)

# ═══════ BINDING NAME ═══════
print("\n=== Binding Name ===")
check("name_ok", check_binding_name("my_region") is None)
check("name_empty", check_binding_name("") is not None)
check("name_space", check_binding_name("   ") is not None)

# ═══════ FRAME TYPE CHECK — well-typed ═══════
print("\n=== Frame Type Check — Well Typed ===")
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
frame = execute_frame(0, [a, b],
    bindings={"left": a, "right": b},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])
tc = type_check_frame(frame)
check("frame_well_typed", tc.verdict == TypeCheckVerdict.WELL_TYPED)
check("frame_no_errors", len(tc.errors) == 0)
check("frame_prims_checked", tc.primitives_checked == 2)
check("frame_ops_checked", tc.operations_checked == 1)
check("frame_binds_checked", tc.bindings_checked == 2)

# ═══════ FRAME TYPE CHECK — empty ═══════
print("\n=== Frame Type Check — Empty ===")
empty_frame = GrammarFrame(frame_index=0)
tc_empty = type_check_frame(empty_frame)
check("frame_empty", tc_empty.verdict == TypeCheckVerdict.EMPTY)

# ═══════ FRAME TYPE CHECK — ill-typed CONTAINS ═══════
print("\n=== Frame Type Check — Ill-Typed Contains ===")
small_p = _prim(PrimitiveKind.POINT, 50, 50, 5, 5)
big_p = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
# Force CONTAINS(small, big) — type error
frame_bad = execute_frame(0, [small_p, big_p],
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}])
tc_bad = type_check_frame(frame_bad)
check("frame_ill_typed", tc_bad.verdict == TypeCheckVerdict.ILL_TYPED)
check("frame_contains_error", any(
    e.kind == TypeErrorKind.CONTAINS_AREA_VIOLATION for e in tc_bad.errors
))

# ═══════ PROGRAM TYPE CHECK — well-typed ═══════
print("\n=== Program Type Check — Well Typed ===")
prog = parse_frame_to_program(frame)  # from the well-typed frame above
tc_prog = type_check_program(prog)
check("prog_well_typed", tc_prog.verdict == TypeCheckVerdict.WELL_TYPED)

# ═══════ PROGRAM TYPE CHECK — empty ═══════
print("\n=== Program Type Check — Empty ===")
empty_prog = ProgramNode(kind=ProgramNodeKind.PROGRAM)
tc_ep = type_check_program(empty_prog)
check("prog_empty", tc_ep.verdict == TypeCheckVerdict.EMPTY)

# ═══════ SAFE EXECUTE — well-typed ═══════
print("\n=== Safe Execute — Well Typed ===")
safe = safe_execute_image_as_program(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
     {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
    bindings={"a": 0, "b": 1},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("safe_executed", safe["executed"] is True)
check("safe_well_typed", safe["type_check"]["is_well_typed"] is True)
check("safe_verdict", safe["execution"]["verdict"] == "PASS")

# ═══════ SAFE EXECUTE — ill-typed ═══════
print("\n=== Safe Execute — Ill Typed ===")
safe_bad = safe_execute_image_as_program(
    [{"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
     {"type": "region", "bbox": [0, 0, 200, 200], "confidence": 1.0}],
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}],
)
check("safe_bad_not_executed", safe_bad["executed"] is False)
check("safe_bad_ill_typed", safe_bad["type_check"]["is_well_typed"] is False)
check("safe_bad_no_execution", safe_bad["execution"] is None)

# ═══════ SERIALIZATION ═══════
print("\n=== Serialization ===")
d = tc.to_dict()
check("ser_verdict", d["verdict"] == "WELL_TYPED")
check("ser_well_typed", d["is_well_typed"] is True)
check("ser_error_count", d["error_count"] == 0)
check("ser_version", d["type_system_version"] == TYPE_SYSTEM_VERSION)

d_bad = tc_bad.to_dict()
check("ser_bad_verdict", d_bad["verdict"] == "ILL_TYPED")
check("ser_bad_errors", d_bad["error_count"] > 0)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
results = [
    safe_execute_image_as_program(
        [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
         {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
        operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
    )
    for _ in range(5)
]
check("det_all_same", all(r == results[0] for r in results))

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
