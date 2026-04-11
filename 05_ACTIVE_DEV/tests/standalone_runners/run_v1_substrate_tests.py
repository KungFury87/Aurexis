"""
Standalone test runner for Substrate V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import PrimitiveKind, OperationKind, V1_LAW
from aurexis_lang.hardware_calibration_v1 import CameraProfile
from aurexis_lang.substrate_v1 import (
    SUBSTRATE_VERSION, SUBSTRATE_FROZEN,
    SUBSYSTEM_VERSIONS, SUBSYSTEM_FROZEN,
    SubstrateVerdict, ProcessingResult, SubstrateProof,
    process_image, verify_substrate, SubstrateV1,
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
print("\n=== Substrate Spec ===")
check("version", SUBSTRATE_VERSION == "V1.0")
check("frozen", SUBSTRATE_FROZEN is True)
check("all_versions_v1", all(v == "V1.0" for v in SUBSYSTEM_VERSIONS.values()),
      f"versions={SUBSYSTEM_VERSIONS}")
check("all_frozen", all(SUBSYSTEM_FROZEN.values()),
      f"frozen={SUBSYSTEM_FROZEN}")
check("subsystem_count", len(SUBSYSTEM_VERSIONS) == 9,
      f"got {len(SUBSYSTEM_VERSIONS)}")

# ═══════ PROCESS IMAGE — basic ═══════
print("\n=== Process Image — Basic ===")
pr = process_image(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
     {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("proc_type_check", pr.type_check_verdict == "WELL_TYPED")
check("proc_execution", pr.execution_verdict == "PASS")
check("proc_not_calibrated", pr.calibrated is False)
check("proc_prims", pr.primitives_parsed == 2)

# ═══════ PROCESS IMAGE — with calibration ═══════
print("\n=== Process Image — Calibrated ===")
camera = CameraProfile(name="test_cam", resolution_megapixels=12.0)
pr_cal = process_image(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 0.95},
     {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 0.90}],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
    camera_profile=camera,
)
check("proc_cal_calibrated", pr_cal.calibrated is True)
check("proc_cal_verdict", pr_cal.calibration_verdict == "CALIBRATED")
check("proc_cal_executed", pr_cal.execution_verdict in ("PASS", "PARTIAL"),
      f"got {pr_cal.execution_verdict}")

# ═══════ PROCESS IMAGE — ill-typed ═══════
print("\n=== Process Image — Ill-Typed ===")
pr_bad = process_image(
    [{"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
     {"type": "region", "bbox": [0, 0, 200, 200], "confidence": 1.0}],
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}],
)
check("proc_bad_ill_typed", pr_bad.type_check_verdict == "ILL_TYPED")
check("proc_bad_skipped", pr_bad.execution_verdict == "SKIPPED")

# ═══════ PROCESS IMAGE — with bindings ═══════
print("\n=== Process Image — With Bindings ===")
pr_bind = process_image(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
     {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
    bindings={"left": 0, "right": 1},
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("proc_bind_pass", pr_bind.execution_verdict == "PASS")

# ═══════ PROCESSING RESULT SERIALIZATION ═══════
print("\n=== ProcessingResult Serialization ===")
d_pr = pr.to_dict()
check("pr_ser_version", d_pr["substrate_version"] == SUBSTRATE_VERSION)
check("pr_ser_type_check", d_pr["type_check_verdict"] == "WELL_TYPED")

# ═══════ VERIFY SUBSTRATE ═══════
print("\n=== Verify Substrate ===")
sp = verify_substrate()
check("verify_complete", sp.verdict == SubstrateVerdict.COMPLETE,
      f"got {sp.verdict}, passed={sp.subsystems_passed}/{sp.subsystems_total}, errors={sp.errors}")
check("verify_all_frozen", sp.all_frozen)
check("verify_all_v1", sp.all_versions_v1)
check("verify_type_system", sp.type_system_works)
check("verify_execution", sp.execution_works)
check("verify_stability", sp.stability_works)
check("verify_temporal", sp.temporal_works)
check("verify_composition", sp.composition_works)
check("verify_calibration", sp.calibration_works)
check("verify_self_hosting", sp.self_hosting_works)
check("verify_count", sp.subsystems_passed == 9,
      f"got {sp.subsystems_passed}")

# ═══════ SUBSTRATE PROOF SERIALIZATION ═══════
print("\n=== SubstrateProof Serialization ===")
d_sp = sp.to_dict()
check("sp_ser_verdict", d_sp["verdict"] == "COMPLETE")
check("sp_ser_passed", d_sp["subsystems_passed"] == 9)
check("sp_ser_version", d_sp["substrate_version"] == SUBSTRATE_VERSION)

# ═══════ SUBSTRATE V1 CLASS ═══════
print("\n=== SubstrateV1 Class ===")
sub = SubstrateV1()
check("sub_not_complete", not sub.is_complete)  # Before verify

sp2 = sub.verify()
check("sub_complete", sub.is_complete,
      f"verdict={sp2.verdict}, errors={sp2.errors}")
check("sub_self_hosted", sub.self_description.is_self_hosted)

# Process through substrate instance
pr_sub = sub.process(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
     {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("sub_process_pass", pr_sub.execution_verdict == "PASS")

# Serialization
d_sub = sub.to_dict()
check("sub_ser_complete", d_sub["is_complete"] is True)
check("sub_ser_hosted", d_sub["self_hosted"] is True)
check("sub_ser_version", d_sub["substrate_version"] == SUBSTRATE_VERSION)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
results = [
    process_image(
        [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
         {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0}],
        operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
    ).to_dict()
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
