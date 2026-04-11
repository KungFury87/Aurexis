"""
Standalone test runner for Self-Hosting V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, ExecutionStatus, V1_LAW, GRAMMAR_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import ProgramVerdict, execute_program
from aurexis_lang.type_system_v1 import type_check_program, TypeCheckVerdict
from aurexis_lang.composition_v1 import compose, CompositionVerdict, ProgramLibrary
from aurexis_lang.self_hosting_v1 import (
    SELF_HOSTING_VERSION, SELF_HOSTING_FROZEN,
    MetaProgram, SelfHostingVerdict, SelfHostingProof,
    build_primitive_meta, build_operation_meta, build_law_meta,
    prove_self_hosting, SelfDescriptionRegistry,
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


# ═══════ SPEC ═══════
print("\n=== Self-Hosting Spec ===")
check("version", SELF_HOSTING_VERSION == "V1.0")
check("frozen", SELF_HOSTING_FROZEN is True)

# ═══════ PRIMITIVE META-PROGRAMS ═══════
print("\n=== Primitive Meta-Programs ===")
for kind in PrimitiveKind:
    mp = build_primitive_meta(kind)
    check(f"meta_{kind.name}_valid", mp.is_valid,
          f"module well_typed={mp.module.is_well_typed}")
    check(f"meta_{kind.name}_describes", mp.describes == kind.name)
    check(f"meta_{kind.name}_has_props", len(mp.properties) > 0)

    # Execute the meta-program
    result = execute_program(mp.module.program)
    check(f"meta_{kind.name}_executes",
          result.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL),
          f"verdict={result.verdict}")

# ═══════ OPERATION META-PROGRAMS ═══════
print("\n=== Operation Meta-Programs ===")
for op in OperationKind:
    mp = build_operation_meta(op)
    check(f"meta_{op.name}_valid", mp.is_valid,
          f"module well_typed={mp.module.is_well_typed}")
    check(f"meta_{op.name}_describes", mp.describes == op.name)

    result = execute_program(mp.module.program)
    # EMPTY is valid for BIND (no assertions, only a naming operation)
    check(f"meta_{op.name}_executes",
          result.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL, ProgramVerdict.EMPTY),
          f"verdict={result.verdict}")

# ═══════ LAW META-PROGRAM ═══════
print("\n=== Law Meta-Program ===")
law_mp = build_law_meta()
check("meta_law_valid", law_mp.is_valid)
check("meta_law_describes", law_mp.describes == "V1_LAW")
check("meta_law_has_thresholds",
      "adjacent_max_distance_px" in law_mp.properties)
check("meta_law_adj_threshold",
      law_mp.properties["adjacent_max_distance_px"] == V1_LAW.adjacent_max_distance_px)

result = execute_program(law_mp.module.program)
check("meta_law_executes",
      result.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL),
      f"verdict={result.verdict}")

# ═══════ META-PROGRAM SERIALIZATION ═══════
print("\n=== MetaProgram Serialization ===")
d = law_mp.to_dict()
check("ser_describes", d["describes"] == "V1_LAW")
check("ser_valid", d["is_valid"] is True)
check("ser_version", d["self_hosting_version"] == SELF_HOSTING_VERSION)
check("ser_exports", len(d["exports"]) > 0)

# ═══════ COMPOSITION OF META-PROGRAMS ═══════
print("\n=== Composition of Meta-Programs ===")
mp_region = build_primitive_meta(PrimitiveKind.REGION)
mp_adj = build_operation_meta(OperationKind.ADJACENT)
cr = compose(mp_region.module, mp_adj.module, require_shared=False)
check("meta_compose_success", cr.verdict == CompositionVerdict.SUCCESS,
      f"verdict={cr.verdict}, errors={[e.message for e in cr.errors]}")

# Compose law with a primitive
cr2 = compose(law_mp.module, mp_region.module, require_shared=False)
check("meta_compose_law_prim", cr2.verdict == CompositionVerdict.SUCCESS,
      f"verdict={cr2.verdict}")

# ═══════ FULL SELF-HOSTING PROOF ═══════
print("\n=== Full Self-Hosting Proof ===")
proof = prove_self_hosting()
check("proof_verdict", proof.verdict == SelfHostingVerdict.SELF_HOSTED,
      f"got {proof.verdict}, errors={proof.errors}")
check("proof_all_valid", proof.valid_count == proof.total_count,
      f"valid={proof.valid_count}/{proof.total_count}")
check("proof_execution", proof.execution_succeeded)
check("proof_composition", proof.composition_succeeded)

# Expected count: 3 primitives + 3 operations + 1 law = 7
check("proof_total_count", proof.total_count == 7,
      f"got {proof.total_count}")

# Serialization
d_proof = proof.to_dict()
check("proof_ser_verdict", d_proof["verdict"] == "SELF_HOSTED")
check("proof_ser_count", d_proof["total_count"] == 7)

# ═══════ SELF-DESCRIPTION REGISTRY ═══════
print("\n=== SelfDescriptionRegistry ===")
reg = SelfDescriptionRegistry()
proof2 = reg.bootstrap()
check("reg_self_hosted", reg.is_self_hosted)
check("reg_descriptions", len(reg.list_descriptions()) == 7,
      f"got {reg.list_descriptions()}")
check("reg_get_region", reg.get_meta("REGION") is not None)
check("reg_get_adjacent", reg.get_meta("ADJACENT") is not None)
check("reg_get_law", reg.get_meta("V1_LAW") is not None)

d_reg = reg.to_dict()
check("reg_ser_hosted", d_reg["is_self_hosted"] is True)
check("reg_ser_descriptions", len(d_reg["descriptions"]) == 7)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
results = [prove_self_hosting().to_dict() for _ in range(5)]
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
