#!/usr/bin/env python3
"""
Standalone test runner for Composed Recovery Bridge V1.
No external dependencies — pure Python 3.

Proves that a frozen bounded composition of localization, orientation
normalization, perspective normalization, and capture tolerance works
as an integrated end-to-end recovery path for V1 artifacts.

This is a narrow integrated recovery proof, not general invariance
or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

# ── Path setup ─────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'aurexis_lang', 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurexis_lang.composed_recovery_bridge_v1 import (
    COMPOSED_VERSION, COMPOSED_FROZEN, V1_COMPOSED_PROFILE,
    ComposedProfile, ComposedHostSpec, DegradationSpec, NO_DEGRADATION,
    ComposedVerdict, ComposedResult,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
    FROZEN_DISTORTIONS,
    generate_composed_host_image, detect_composed_transform,
    composed_recovery, build_composed_host_spec,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
)
from aurexis_lang.orientation_normalization_bridge_v1 import SUPPORTED_ANGLES
from aurexis_lang.perspective_normalization_bridge_v1 import (
    FROZEN_DISTORTIONS as PERSPECTIVE_DISTORTIONS,
)


passed = 0
failed = 0


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


# ════════════════════════════════════════════════════════════
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

print("=== Module Constants ===")
check(COMPOSED_VERSION == "V1.0", "version")
check(COMPOSED_FROZEN is True, "frozen")
check(isinstance(V1_COMPOSED_PROFILE, ComposedProfile), "profile_type")
check(V1_COMPOSED_PROFILE.host_width == 800, "host_width")
check(V1_COMPOSED_PROFILE.host_height == 800, "host_height")
check(V1_COMPOSED_PROFILE.supported_angles == (0, 90, 180, 270), "supported_angles")
check(V1_COMPOSED_PROFILE.max_corner_offset_px == 30, "max_corner_offset")
check(len(IN_BOUNDS_CASES) == 10, "in_bounds_count")
check(len(OUT_OF_BOUNDS_CASES) == 4, "oob_count")


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Host Image Generation ===")

spec = build_composed_host_spec(IN_BOUNDS_CASES[0])
host_png = generate_composed_host_image(spec)
check(host_png[:4] == b'\x89PNG', "host_png_valid")
check(len(host_png) > 100, "host_png_size")

# Deterministic
host_png_2 = generate_composed_host_image(spec)
check(host_png == host_png_2, "host_deterministic")

# Different cases produce different hosts
spec2 = build_composed_host_spec(IN_BOUNDS_CASES[7])
host_png_diff = generate_composed_host_image(spec2)
check(host_png != host_png_diff, "diff_cases_diff_hosts")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — adjacent_pair fixture
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (adjacent_pair) ===")

for i, case in enumerate(IN_BOUNDS_CASES):
    spec = build_composed_host_spec(case, artifact_spec=fixture_adjacent_pair())
    result = composed_recovery(spec)
    check(
        result.verdict == ComposedVerdict.RECOVERED,
        f"inbound_{i}_{case['label']}"
    )


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — containment fixture
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (containment) ===")

# Test a selection of cases with containment fixture
containment_cases = [0, 4, 7, 9]  # identity, rot+dist, full comp 1, full comp 3
for i in containment_cases:
    case = IN_BOUNDS_CASES[i]
    spec = build_composed_host_spec(case, artifact_spec=fixture_containment())
    result = composed_recovery(spec)
    check(
        result.verdict == ComposedVerdict.RECOVERED,
        f"inbound_cont_{case['label']}"
    )


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — three_regions fixture
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (three_regions) ===")

three_region_cases = [0, 7, 8]  # identity, full comp 1, full comp 2
for i in three_region_cases:
    case = IN_BOUNDS_CASES[i]
    spec = build_composed_host_spec(case, artifact_spec=fixture_three_regions())
    result = composed_recovery(spec)
    check(
        result.verdict == ComposedVerdict.RECOVERED,
        f"inbound_three_{case['label']}"
    )


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds Cases ===")

for i, case in enumerate(OUT_OF_BOUNDS_CASES):
    spec = build_composed_host_spec(case)
    result = composed_recovery(spec)
    check(
        result.verdict != ComposedVerdict.RECOVERED,
        f"oob_{i}_{case['label']}"
    )
    check(
        result.verdict in (
            ComposedVerdict.NOT_FOUND,
            ComposedVerdict.TRANSFORM_UNKNOWN,
            ComposedVerdict.PARSE_FAILED,
        ),
        f"oob_{i}_honest_failure"
    )


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

# Full composition case run twice must produce identical results
case = IN_BOUNDS_CASES[7]  # full_composition_90_hkey_deg
spec = build_composed_host_spec(case)
r1 = composed_recovery(spec)
r2 = composed_recovery(spec)
check(r1.verdict == r2.verdict, "determinism_verdict")
check(r1.detected_angle == r2.detected_angle, "determinism_angle")
check(r1.detected_distortion == r2.detected_distortion, "determinism_distortion")
check(r1.parsed_primitives == r2.parsed_primitives, "determinism_prims")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

spec = build_composed_host_spec(IN_BOUNDS_CASES[0])
result = composed_recovery(spec)
d = result.to_dict()
check(d["verdict"] == "RECOVERED", "ser_verdict")
check(d["detected_angle"] is not None, "ser_angle")
check(d["detected_distortion"] is not None, "ser_distortion")
check(d["parsed_primitives"] == d["expected_primitives"], "ser_prim_match")
check(d["version"] == "V1.0", "ser_version")


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

# All in-bounds cases are within the frozen profile bounds
p = V1_COMPOSED_PROFILE
for i, case in enumerate(IN_BOUNDS_CASES):
    ox = case["offset_x"]
    oy = case["offset_y"]
    scale = case.get("embed_scale", 1.0)
    angle = case.get("rotation_angle", 0)
    within = (
        p.min_offset_x <= ox <= p.max_offset_x and
        p.min_offset_y <= oy <= p.max_offset_y and
        p.min_embed_scale <= scale <= p.max_embed_scale and
        angle in p.supported_angles
    )
    check(within, f"profile_bounds_ib_{i}")

# Degradation bounds
for i, case in enumerate(IN_BOUNDS_CASES):
    deg = case.get("degradation", NO_DEGRADATION)
    within_deg = (
        abs(deg.brightness_shift) <= p.max_brightness_shift and
        abs(deg.contrast_factor - 1.0) <= p.max_contrast_deviation + 0.001 and
        deg.noise_amplitude <= p.max_noise_amplitude
    )
    check(within_deg, f"degradation_bounds_ib_{i}")


# ════════════════════════════════════════════════════════════
# COMPOSED TRANSFORM COVERAGE
# ════════════════════════════════════════════════════════════

print("\n=== Composed Transform Coverage ===")

# Check that at least some cases exercise each individual transform
has_rotation = any(c.get("rotation_angle", 0) != 0 for c in IN_BOUNDS_CASES)
has_distortion = any(c.get("distortion", "identity") != "identity" for c in IN_BOUNDS_CASES)
has_degradation = any(c.get("degradation", NO_DEGRADATION) != NO_DEGRADATION for c in IN_BOUNDS_CASES)
has_scale = any(c.get("embed_scale", 1.0) != 1.0 for c in IN_BOUNDS_CASES)
has_full = any(
    c.get("rotation_angle", 0) != 0 and
    c.get("distortion", "identity") != "identity" and
    c.get("degradation", NO_DEGRADATION) != NO_DEGRADATION
    for c in IN_BOUNDS_CASES
)

check(has_rotation, "coverage_rotation")
check(has_distortion, "coverage_distortion")
check(has_degradation, "coverage_degradation")
check(has_scale, "coverage_scale")
check(has_full, "coverage_full_composition")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Composed Recovery Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
