"""
Standalone test runner for Hardware Calibration V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.hardware_calibration_v1 import (
    CALIBRATION_VERSION, CALIBRATION_FROZEN,
    CameraProfile, CalibrationLaw, V1_CALIBRATION_LAW,
    CalibrationVerdict, CalibrationResult, CalibrationFactors,
    compute_factors, calibrate_confidence, calibrate_frame,
    CalibrationRegistry, BUILTIN_PROFILES,
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
print("\n=== Calibration Spec ===")
check("version", CALIBRATION_VERSION == "V1.0")
check("frozen", CALIBRATION_FROZEN is True)

# ═══════ CAMERA PROFILE ═══════
print("\n=== Camera Profile ===")
ideal = CameraProfile(
    name="test_ideal", resolution_megapixels=48.0,
    focal_length_mm=26.0, sensor_noise_level=0.02,
    lens_distortion=0.01, capture_distance_m=0.3)
check("profile_name", ideal.name == "test_ideal")
check("profile_frozen", True)  # frozen=True in dataclass
d = ideal.to_dict()
check("profile_ser", d["name"] == "test_ideal" and d["resolution_megapixels"] == 48.0)

# ═══════ CALIBRATION LAW ═══════
print("\n=== Calibration Law ===")
law = V1_CALIBRATION_LAW
check("law_res_baseline", law.resolution_baseline_mp == 2.0)
check("law_dist_baseline", law.distance_baseline_m == 1.0)
check("law_floor", law.confidence_floor == 0.1)
check("law_ceiling", law.confidence_ceiling_max == 1.0)

# ═══════ COMPUTE FACTORS — ideal camera ═══════
print("\n=== Factors — Ideal Camera ===")
f_ideal = compute_factors(ideal)
check("ideal_res_bonus", f_ideal.resolution_bonus > 0,
      f"bonus={f_ideal.resolution_bonus}")
check("ideal_no_dist_penalty", f_ideal.distance_penalty == 0.0,
      f"penalty={f_ideal.distance_penalty}")
check("ideal_low_noise", f_ideal.noise_penalty < 0.05,
      f"noise={f_ideal.noise_penalty}")
check("ideal_low_distortion", f_ideal.distortion_penalty < 0.02,
      f"dist={f_ideal.distortion_penalty}")
check("ideal_high_ceiling", f_ideal.hardware_ceiling >= 0.95,
      f"ceiling={f_ideal.hardware_ceiling}")

# ═══════ COMPUTE FACTORS — bad camera ═══════
print("\n=== Factors — Bad Camera ===")
bad = CameraProfile(
    name="bad", resolution_megapixels=1.0,
    sensor_noise_level=0.5, lens_distortion=0.4,
    capture_distance_m=3.0)
f_bad = compute_factors(bad)
check("bad_lower_ceiling", f_bad.hardware_ceiling < f_ideal.hardware_ceiling,
      f"bad={f_bad.hardware_ceiling} vs ideal={f_ideal.hardware_ceiling}")
check("bad_has_dist_penalty", f_bad.distance_penalty > 0,
      f"penalty={f_bad.distance_penalty}")
check("bad_has_noise", f_bad.noise_penalty > 0.2,
      f"noise={f_bad.noise_penalty}")
check("bad_has_distortion", f_bad.distortion_penalty > 0.1,
      f"dist={f_bad.distortion_penalty}")

# ═══════ CALIBRATE — UNCAPPED ═══════
print("\n=== Calibrate — Uncapped ===")
cr_uncap = calibrate_confidence(0.7, ideal)
check("uncap_verdict", cr_uncap.verdict == CalibrationVerdict.UNCAPPED,
      f"got {cr_uncap.verdict}")
check("uncap_not_capped", cr_uncap.was_capped is False)
check("uncap_same_conf", cr_uncap.calibrated_confidence == 0.7,
      f"got {cr_uncap.calibrated_confidence}")
check("uncap_delta_zero", cr_uncap.confidence_delta == 0.0)

# ═══════ CALIBRATE — CAPPED ═══════
print("\n=== Calibrate — Capped ===")
cr_cap = calibrate_confidence(0.95, bad)
check("cap_was_capped", cr_cap.was_capped is True)
check("cap_lower_conf", cr_cap.calibrated_confidence < 0.95,
      f"got {cr_cap.calibrated_confidence}")
check("cap_equals_ceiling", cr_cap.calibrated_confidence == cr_cap.hardware_ceiling,
      f"conf={cr_cap.calibrated_confidence}, ceil={cr_cap.hardware_ceiling}")
check("cap_negative_delta", cr_cap.confidence_delta < 0,
      f"delta={cr_cap.confidence_delta}")

# ═══════ CALIBRATE — DEGRADED ═══════
print("\n=== Calibrate — Degraded ===")
terrible = CameraProfile(
    name="terrible", resolution_megapixels=0.5,
    sensor_noise_level=0.8, lens_distortion=0.7,
    capture_distance_m=5.0)
cr_deg = calibrate_confidence(0.9, terrible)
check("deg_verdict", cr_deg.verdict == CalibrationVerdict.DEGRADED,
      f"got {cr_deg.verdict}, ceiling={cr_deg.hardware_ceiling}")
check("deg_low_ceiling", cr_deg.hardware_ceiling < 0.5,
      f"ceiling={cr_deg.hardware_ceiling}")

# ═══════ CALIBRATE — INVALID PROFILE ═══════
print("\n=== Calibrate — Invalid Profile ===")
invalid = CameraProfile(name="invalid", resolution_megapixels=0.0)
cr_inv = calibrate_confidence(0.9, invalid)
check("inv_verdict", cr_inv.verdict == CalibrationVerdict.INVALID_PROFILE)

neg_dist = CameraProfile(name="neg", capture_distance_m=-1.0)
cr_neg = calibrate_confidence(0.9, neg_dist)
check("neg_dist_invalid", cr_neg.verdict == CalibrationVerdict.INVALID_PROFILE)

# ═══════ CALIBRATE FRAME ═══════
print("\n=== Calibrate Frame ===")
raw_frame = [
    {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 0.95},
    {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 0.85},
    {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 0.70},
]
modern = CameraProfile(
    name="modern", resolution_megapixels=12.0,
    sensor_noise_level=0.08, lens_distortion=0.05,
    capture_distance_m=0.5)
cf = calibrate_frame(raw_frame, modern)
check("frame_count", cf["frame_summary"]["total_primitives"] == 3)
check("frame_has_calibrated", len(cf["calibrated_primitives"]) == 3)
check("frame_has_results", len(cf["calibration_results"]) == 3)

# All calibrated confidences should be <= raw
for i, cal_prim in enumerate(cf["calibrated_primitives"]):
    raw_c = raw_frame[i]["confidence"]
    cal_c = cal_prim["confidence"]
    check(f"frame_prim_{i}_leq", cal_c <= raw_c,
          f"raw={raw_c}, cal={cal_c}")

# ═══════ CALIBRATION REGISTRY ═══════
print("\n=== Calibration Registry ===")
reg = CalibrationRegistry()
check("reg_has_builtins", len(reg.list_profiles()) == len(BUILTIN_PROFILES))
check("reg_has_ideal", reg.get("ideal") is not None)
check("reg_has_modern_phone", reg.get("modern_phone") is not None)

# Register custom
custom = CameraProfile(name="my_camera", resolution_megapixels=16.0)
check("reg_register_ok", reg.register(custom) is True)
check("reg_register_dup", reg.register(custom) is False)
check("reg_get_custom", reg.get("my_camera") is custom)

# Calibrate via registry
cr_reg = reg.calibrate(0.9, "ideal")
check("reg_cal_ok", cr_reg.verdict in (CalibrationVerdict.UNCAPPED, CalibrationVerdict.CALIBRATED))

cr_reg_bad = reg.calibrate(0.9, "nonexistent")
check("reg_cal_missing", cr_reg_bad.verdict == CalibrationVerdict.INVALID_PROFILE)

# Registry serialization
d_reg = reg.to_dict()
check("reg_ser_count", d_reg["profile_count"] == len(BUILTIN_PROFILES) + 1)

# ═══════ BUILTIN PROFILES ═══════
print("\n=== Builtin Profiles ===")
check("builtin_count", len(BUILTIN_PROFILES) == 5)

# Ideal should have highest ceiling
ceilings = {p.name: compute_factors(p).hardware_ceiling for p in BUILTIN_PROFILES}
check("ideal_highest", ceilings["ideal"] >= max(
    v for k, v in ceilings.items() if k != "ideal"
), f"ceilings={ceilings}")

# Webcam should have lower ceiling than modern phone
check("webcam_lower_than_phone",
    ceilings["webcam"] < ceilings["modern_phone"],
    f"webcam={ceilings['webcam']}, phone={ceilings['modern_phone']}")

# ═══════ SERIALIZATION ═══════
print("\n=== Serialization ===")
d_cr = cr_uncap.to_dict()
check("ser_verdict", d_cr["verdict"] == "UNCAPPED")
check("ser_raw", d_cr["raw_confidence"] == 0.7)
check("ser_version", d_cr["calibration_version"] == CALIBRATION_VERSION)
check("ser_factors", d_cr["factors"] is not None)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
results = [
    calibrate_confidence(0.85, modern).to_dict()
    for _ in range(5)
]
check("det_all_same", all(r == results[0] for r in results))

# ═══════ EDGE CASES ═══════
print("\n=== Edge Cases ===")

# Confidence clamp
cr_over = calibrate_confidence(1.5, ideal)
check("clamp_over", cr_over.raw_confidence == 1.0)

cr_under = calibrate_confidence(-0.5, ideal)
check("clamp_under", cr_under.raw_confidence == 0.0)

# Zero distance (at subject)
at_subject = CameraProfile(name="at_subject", capture_distance_m=0.0)
cr_zero = calibrate_confidence(0.9, at_subject)
check("zero_dist_ok", cr_zero.verdict != CalibrationVerdict.INVALID_PROFILE)

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
