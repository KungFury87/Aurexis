#!/usr/bin/env python3
"""
Standalone test runner for Orientation Normalization Bridge V1.
No external dependencies (no pytest). Pure Python 3.

Tests that canonical V1 artifacts embedded in host images with bounded
orientation variation (0, 90, 180, 270 degrees) can be localized,
orientation-normalized back to canonical form, and decoded through the
existing raster bridge into the V1 substrate.

This is a narrow orientation recovery proof, not general rotation
invariance or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "aurexis_lang", "src")
sys.path.insert(0, SRC)

from aurexis_lang.orientation_normalization_bridge_v1 import (
    ORIENTATION_VERSION, ORIENTATION_FROZEN, SUPPORTED_ANGLES,
    V1_ORIENTATION_PROFILE, OrientationProfile,
    rotate_image, rotate_90_cw, rotate_180, rotate_270_cw, rotate_png,
    RotatedHostSpec, generate_rotated_host_image,
    detect_orientation, normalize_orientation,
    OrientationVerdict, OrientationResult,
    orient_and_bridge,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
    _color_signature_matches,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_containment, fixture_three_regions,
    CANVAS_WIDTH, CANVAS_HEIGHT,
    _render_to_raw_rgb, _encode_png, _decode_png_to_rgb,
)

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


# ════════════════════════════════════════════════════════════
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

print("=== Module Constants ===")
check("version", ORIENTATION_VERSION == "V1.0")
check("frozen", ORIENTATION_FROZEN is True)
check("profile_type", isinstance(V1_ORIENTATION_PROFILE, OrientationProfile))
check("supported_angles", SUPPORTED_ANGLES == (0, 90, 180, 270))
check("detection_method", V1_ORIENTATION_PROFILE.detection_method == "exhaustive_trial")
check("host_size", V1_ORIENTATION_PROFILE.host_width == 800)
check("min_scale", V1_ORIENTATION_PROFILE.min_embed_scale == 0.80)
check("max_scale", V1_ORIENTATION_PROFILE.max_embed_scale == 1.20)
check("in_bounds_count", len(IN_BOUNDS_CASES) == 8)
check("oob_count", len(OUT_OF_BOUNDS_CASES) == 4)


# ════════════════════════════════════════════════════════════
# ROTATION FUNCTIONS
# ════════════════════════════════════════════════════════════

print("\n=== Rotation Functions ===")

spec_adj = fixture_adjacent_pair()
rgb = _render_to_raw_rgb(spec_adj)
w, h = CANVAS_WIDTH, CANVAS_HEIGHT

# 4x90 = identity
r1, w1, h1 = rotate_image(rgb, w, h, 90)
r2, w2, h2 = rotate_image(r1, w1, h1, 90)
r3, w3, h3 = rotate_image(r2, w2, h2, 90)
r4, w4, h4 = rotate_image(r3, w3, h3, 90)
check("4x90_identity_dims", w4 == w and h4 == h)
check("4x90_identity_data", r4 == rgb)

# 90+270 = identity
r90, w90, h90 = rotate_image(rgb, w, h, 90)
rback, wb, hb = rotate_image(r90, w90, h90, 270)
check("90_270_identity_dims", wb == w and hb == h)
check("90_270_identity_data", rback == rgb)

# 180+180 = identity
r180, w180, h180 = rotate_image(rgb, w, h, 180)
rback2, wb2, hb2 = rotate_image(r180, w180, h180, 180)
check("180_180_identity_dims", wb2 == w and hb2 == h)
check("180_180_identity_data", rback2 == rgb)

# 0 degrees = copy
r0, w0, h0 = rotate_image(rgb, w, h, 0)
check("0_deg_copy_dims", w0 == w and h0 == h)
check("0_deg_copy_data", r0 == rgb)

# 90 produces different data (non-symmetric artifact)
check("90_differs_from_0", r90 != rgb)

# 180 produces different data
check("180_differs_from_0", r180 != rgb)

# Unsupported angle raises
try:
    rotate_image(rgb, w, h, 45)
    check("45_raises", False)
except ValueError:
    check("45_raises", True)


# ════════════════════════════════════════════════════════════
# rotate_png roundtrip
# ════════════════════════════════════════════════════════════

print("\n=== rotate_png ===")
from aurexis_lang.raster_law_bridge_v1 import render_artifact
png_orig = render_artifact(spec_adj)
png_90 = rotate_png(png_orig, 90)
png_back = rotate_png(png_90, 270)
# PNG bytes may differ due to encode, compare decoded pixels
_, _, buf_orig = _decode_png_to_rgb(png_orig)
_, _, buf_back = _decode_png_to_rgb(png_back)
check("rotate_png_roundtrip", buf_orig == buf_back)


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Rotated Host Image Generation ===")

host_spec = RotatedHostSpec(
    artifact_spec=spec_adj, rotation_angle=90,
    offset_x=200, offset_y=200,
    host_background=(220, 220, 220),
)
host_png = generate_rotated_host_image(host_spec)
check("host_png_valid", host_png[:4] == b'\x89PNG')
check("host_png_size", len(host_png) > 1000)

# Determinism
host_png2 = generate_rotated_host_image(host_spec)
check("host_deterministic", host_png == host_png2)

# Different rotations produce different host images
host_0 = generate_rotated_host_image(RotatedHostSpec(
    artifact_spec=spec_adj, rotation_angle=0, offset_x=200, offset_y=200))
host_90 = generate_rotated_host_image(RotatedHostSpec(
    artifact_spec=spec_adj, rotation_angle=90, offset_x=200, offset_y=200))
check("diff_rotations_diff_hosts", host_0 != host_90)


# ════════════════════════════════════════════════════════════
# ORIENTATION DETECTION
# ════════════════════════════════════════════════════════════

print("\n=== Orientation Detection ===")

from aurexis_lang.artifact_localization_bridge_v1 import (
    localize_artifact, extract_and_normalize,
)
from aurexis_lang.capture_tolerance_bridge_v1 import V1_TOLERANCE_PROFILE

for angle in [0, 90, 180, 270]:
    host = RotatedHostSpec(
        artifact_spec=spec_adj, rotation_angle=angle,
        offset_x=200, offset_y=200,
    )
    hpng = generate_rotated_host_image(host)
    bbox = localize_artifact(hpng)
    extracted = extract_and_normalize(hpng, bbox)
    detected = detect_orientation(extracted, spec_adj)
    check(f"detect_{angle}_deg", detected == angle)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — adjacent_pair
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (adjacent_pair) ===")

for i, case in enumerate(IN_BOUNDS_CASES):
    host = RotatedHostSpec(
        artifact_spec=spec_adj,
        rotation_angle=case["angle"],
        offset_x=case["offset_x"],
        offset_y=case["offset_y"],
        embed_scale=case["embed_scale"],
        host_background=case["host_background"],
    )
    result = orient_and_bridge(host)
    check(f"inbound_{i}_adj_angle{case['angle']}", result.verdict == OrientationVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — single fixture per rotation with containment
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (containment) ===")

spec_cont = fixture_containment()
for angle in [0, 90, 180, 270]:
    host = RotatedHostSpec(
        artifact_spec=spec_cont, rotation_angle=angle,
        offset_x=200, offset_y=200,
    )
    result = orient_and_bridge(host)
    check(f"inbound_cont_angle{angle}", result.verdict == OrientationVerdict.NORMALIZED)
    check(f"inbound_cont_angle{angle}_detected", result.detected_angle == angle)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — three_regions
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (three_regions) ===")

spec_three = fixture_three_regions()
for angle in [0, 90, 180, 270]:
    host = RotatedHostSpec(
        artifact_spec=spec_three, rotation_angle=angle,
        offset_x=200, offset_y=200,
    )
    result = orient_and_bridge(host)
    check(f"inbound_three_angle{angle}", result.verdict == OrientationVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — single_region (symmetric — any detection valid)
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (single_region, symmetric) ===")

spec_single = fixture_single_region()
for angle in [0, 90, 180, 270]:
    host = RotatedHostSpec(
        artifact_spec=spec_single, rotation_angle=angle,
        offset_x=200, offset_y=200,
    )
    result = orient_and_bridge(host)
    check(f"inbound_single_angle{angle}", result.verdict == OrientationVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds Cases ===")

for i, case in enumerate(OUT_OF_BOUNDS_CASES):
    host = RotatedHostSpec(
        artifact_spec=spec_adj,
        rotation_angle=case["angle"],
        offset_x=case["offset_x"],
        offset_y=case["offset_y"],
        embed_scale=case["embed_scale"],
        host_background=case["host_background"],
    )
    result = orient_and_bridge(host)
    check(f"oob_{i}", result.verdict != OrientationVerdict.NORMALIZED)
    check(f"oob_{i}_honest_verdict", result.verdict.value in (
        "NOT_FOUND", "ORIENTATION_UNKNOWN", "PARSE_FAILED", "BRIDGE_FAILED"))


# ════════════════════════════════════════════════════════════
# DETERMINISM — repeated runs identical
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

host_det = RotatedHostSpec(
    artifact_spec=spec_adj, rotation_angle=90,
    offset_x=150, offset_y=150,
    host_background=(240, 240, 230),
)
r1 = orient_and_bridge(host_det)
r2 = orient_and_bridge(host_det)
check("determinism_verdict", r1.verdict == r2.verdict)
check("determinism_angle", r1.detected_angle == r2.detected_angle)
check("determinism_prims", r1.parsed_primitives == r2.parsed_primitives)


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

result = orient_and_bridge(RotatedHostSpec(
    artifact_spec=spec_adj, rotation_angle=180,
    offset_x=200, offset_y=200,
))
d = result.to_dict()
check("ser_verdict", d["verdict"] == "NORMALIZED")
check("ser_detected_angle", d["detected_angle"] == 180)
check("ser_parsed_prims", d["parsed_primitives"] == 2)
check("ser_expected_prims", d["expected_primitives"] == 2)
check("ser_version", d["profile_version"] == "V1.0")


# ════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
total = passed + failed
print(f"Orientation Normalization Bridge V1: {passed}/{total} passed, {failed} failed")
if failed:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
