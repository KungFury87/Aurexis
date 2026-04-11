"""
Standalone test runner for Composition V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
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
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import (
    parse_frame_to_program, ProgramNodeKind, ProgramNode,
)
from aurexis_lang.visual_program_executor_v1 import execute_program, ProgramVerdict
from aurexis_lang.type_system_v1 import type_check_program, TypeCheckVerdict
from aurexis_lang.composition_v1 import (
    COMPOSITION_VERSION, COMPOSITION_FROZEN,
    ProgramModule, CompositionErrorKind, CompositionVerdict,
    CompositionResult, CompositionError,
    compose, ProgramLibrary,
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


def _make_frame(primitives, bindings=None, operations=None):
    """Build a GrammarFrame via execute_frame."""
    binding_map = None
    if bindings:
        binding_map = {name: primitives[idx] for name, idx in bindings.items()}
    return execute_frame(0, primitives, bindings=binding_map, operations=operations)


def _make_module(name, primitives, bindings=None, operations=None):
    """Build a ProgramModule from primitives."""
    frame = _make_frame(primitives, bindings, operations)
    program = parse_frame_to_program(frame)
    return ProgramModule(name=name, program=program)


# ═══════ SPEC ═══════
print("\n=== Composition Spec ===")
check("version", COMPOSITION_VERSION == "V1.0")
check("frozen", COMPOSITION_FROZEN is True)

# ═══════ PROGRAM MODULE BASICS ═══════
print("\n=== ProgramModule Basics ===")

# Module with two regions and an ADJACENT relation
a = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
b = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
mod_adj = _make_module("adjacent_mod", [a, b],
    bindings={"left": 0, "right": 1},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])

check("module_name", mod_adj.name == "adjacent_mod")
check("module_well_typed", mod_adj.is_well_typed)
check("module_exports_auto", "left" in mod_adj.exports and "right" in mod_adj.exports,
      f"exports={mod_adj.exports}")
check("module_version", mod_adj.module_version == COMPOSITION_VERSION)

# Module to_dict
d = mod_adj.to_dict()
check("module_dict_name", d["name"] == "adjacent_mod")
check("module_dict_well_typed", d["is_well_typed"] is True)
check("module_dict_version", d["module_version"] == COMPOSITION_VERSION)

# ═══════ PROGRAM MODULE — ill-typed ═══════
print("\n=== ProgramModule Ill-Typed ===")

# Create a module with CONTAINS(small, big) — should be ill-typed
small = _prim(PrimitiveKind.POINT, 50, 50, 5, 5)
big = _prim(PrimitiveKind.REGION, 0, 0, 200, 200)
mod_ill = _make_module("ill_mod", [small, big],
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}])

check("ill_module_not_well_typed", not mod_ill.is_well_typed,
      f"expected ill-typed, got well_typed={mod_ill.is_well_typed}")

# ═══════ COMPOSE — SUCCESS (shared bindings) ═══════
print("\n=== Compose Success — Shared Bindings ===")

# Module A: left, center
c1 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
c2 = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
mod_a = _make_module("mod_a", [c1, c2],
    bindings={"left": 0, "center": 1},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])

# Module B: center, right (center is shared)
c3 = _prim(PrimitiveKind.REGION, 100, 0, 100, 100)
c4 = _prim(PrimitiveKind.REGION, 200, 0, 100, 100)
mod_b = _make_module("mod_b", [c3, c4],
    bindings={"center": 0, "right": 1},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}])

cr = compose(mod_a, mod_b)
check("compose_success", cr.verdict == CompositionVerdict.SUCCESS,
      f"got {cr.verdict}, errors={[e.message for e in cr.errors]}")
check("compose_shared", "center" in cr.shared_bindings,
      f"shared={cr.shared_bindings}")
check("compose_sources", cr.source_modules == ["mod_a", "mod_b"])
check("compose_module_name", cr.composed_module is not None and
      cr.composed_module.name == "mod_a+mod_b")
check("compose_module_well_typed", cr.composed_module is not None and
      cr.composed_module.is_well_typed)

# ═══════ COMPOSE — SUCCESS (no shared bindings, require_shared=False) ═══════
print("\n=== Compose Success — No Shared Bindings ===")

c5 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
mod_x = _make_module("mod_x", [c5], bindings={"alpha": 0})

c6 = _prim(PrimitiveKind.REGION, 200, 0, 100, 100)
mod_y = _make_module("mod_y", [c6], bindings={"beta": 0})

cr2 = compose(mod_x, mod_y, require_shared=False)
check("compose_no_shared_ok", cr2.verdict == CompositionVerdict.SUCCESS,
      f"got {cr2.verdict}, errors={[e.message for e in cr2.errors]}")
check("compose_no_shared_empty", len(cr2.shared_bindings) == 0)

# ═══════ COMPOSE — FAIL (require_shared but none exist) ═══════
print("\n=== Compose Fail — Require Shared ===")

cr3 = compose(mod_x, mod_y, require_shared=True)
check("compose_require_shared_fail", cr3.verdict == CompositionVerdict.FAILED)
check("compose_require_shared_error", any(
    e.kind == CompositionErrorKind.NO_SHARED_BINDINGS for e in cr3.errors
))

# ═══════ COMPOSE — FAIL (ill-typed module) ═══════
print("\n=== Compose Fail — Ill-Typed Module ===")

cr4 = compose(mod_ill, mod_a)
check("compose_ill_typed_fail", cr4.verdict == CompositionVerdict.FAILED)
check("compose_ill_typed_error", any(
    e.kind == CompositionErrorKind.ILL_TYPED_MODULE for e in cr4.errors
))

# ═══════ COMPOSE — FAIL (binding kind mismatch) ═══════
print("\n=== Compose Fail — Binding Kind Mismatch ===")

# Module with "shared" bound to a REGION
r1 = _prim(PrimitiveKind.REGION, 0, 0, 100, 100)
mod_region = _make_module("mod_region", [r1], bindings={"shared": 0})

# Module with "shared" bound to an EDGE
e1 = _prim(PrimitiveKind.EDGE, 0, 0, 200, 5)
mod_edge = _make_module("mod_edge", [e1], bindings={"shared": 0})

cr5 = compose(mod_region, mod_edge)
check("compose_kind_mismatch_fail", cr5.verdict == CompositionVerdict.FAILED,
      f"got {cr5.verdict}, errors={[e.message for e in cr5.errors]}")
check("compose_kind_mismatch_error", any(
    e.kind == CompositionErrorKind.BINDING_KIND_MISMATCH for e in cr5.errors
), f"errors={[e.kind for e in cr5.errors]}")

# ═══════ COMPOSITION RESULT SERIALIZATION ═══════
print("\n=== CompositionResult Serialization ===")

d_cr = cr.to_dict()
check("cr_ser_verdict", d_cr["verdict"] == "SUCCESS")
check("cr_ser_shared", "center" in d_cr["shared_bindings"])
check("cr_ser_sources", d_cr["source_modules"] == ["mod_a", "mod_b"])
check("cr_ser_version", d_cr["composition_version"] == COMPOSITION_VERSION)

d_cr3 = cr3.to_dict()
check("cr_ser_fail_verdict", d_cr3["verdict"] == "FAILED")
check("cr_ser_fail_errors", d_cr3["error_count"] > 0)

# ═══════ PROGRAM LIBRARY ═══════
print("\n=== ProgramLibrary ===")

lib = ProgramLibrary()
check("lib_empty", len(lib.list_modules()) == 0)

check("lib_register_a", lib.register(mod_a) is True)
check("lib_register_b", lib.register(mod_b) is True)
check("lib_register_dup", lib.register(mod_a) is False)  # Already registered

check("lib_list", lib.list_modules() == ["mod_a", "mod_b"])
check("lib_get_a", lib.get("mod_a") is mod_a)
check("lib_get_none", lib.get("nonexistent") is None)

# Compose by name
cr_lib = lib.compose_by_name("mod_a", "mod_b")
check("lib_compose_success", cr_lib.verdict == CompositionVerdict.SUCCESS)
check("lib_compose_registered", "mod_a+mod_b" in lib.list_modules())

# Compose by name — missing module
cr_missing = lib.compose_by_name("mod_a", "ghost")
check("lib_compose_missing_fail", cr_missing.verdict == CompositionVerdict.FAILED)

# Library serialization
d_lib = lib.to_dict()
check("lib_ser_count", d_lib["module_count"] == 3)  # mod_a, mod_b, mod_a+mod_b

# ═══════ COMPOSED MODULE EXECUTION ═══════
print("\n=== Composed Module Execution ===")

if cr.composed_program is not None:
    exec_result = execute_program(cr.composed_program)
    check("composed_exec_verdict", exec_result.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL),
          f"got {exec_result.verdict}")
    check("composed_exec_has_trace", len(exec_result.trace) > 0)
else:
    check("composed_program_exists", False, "composed_program is None")

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")

results = []
for _ in range(5):
    cr_det = compose(mod_a, mod_b)
    results.append(cr_det.to_dict())

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
