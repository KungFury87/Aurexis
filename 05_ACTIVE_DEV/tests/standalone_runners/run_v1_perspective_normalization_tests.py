#!/usr/bin/env python3
"""
Standalone test runner for Perspective Normalization Bridge V1.
No external dependencies (no pytest). Pure Python 3.

Tests that canonical V1 artifacts subjected to bounded keystone/perspective
distortions can be localized, perspective-normalized, and bridged to the
V1 substrate deterministically.

This is a narrow keystone recovery proof, not general perspective
invariance or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "aurexis_lang", "src")
sys.path.insert(0, SRC)

from aurexis_lang.perspective_normalization_bridge_v1 import (
    PERSPECTIVE_VERSION, PERSPECTIVE_FROZEN,
    V1_PERSPECTIVE_PROFILE, PerspectiveProfile,
    FROZEN_DISTORTIONS, KeystoneDistortion,
    IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD,
    VERTICAL_KEYSTONE_MILD, CORNER_PULL_INWARD,
    HORIZONTAL_KEYSTONE_REVERSE, VERTICAL_KEYSTONE_REVERSE,
    MILD_TRAPEZOID,
    warp_forward, warp_inverse,
    PerspectiveHostSpec, generate_perspective_host_image,
    detect_and_normalize_perspective,
    PerspectiveVerdict, PerspectiveResult,
    perspective_and_bridge,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
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
check("version", PERSPECTIVE_VERSION == "V1.0")
check("frozen", PERSPECTIVE_FROZEN is True)
check("profile_type", isinstance(V1_PERSPECTIVE_PROFILE, PerspectiveProfile))
check("max_corner_offset", V1_PERSPECTIVE_PROFILE.max_corner_offset_px == 30)
check("host_size", V1_PERSPECTIVE_PROFILE.host_width == 800)
check("frozen_distortions_count", len(FROZEN_DISTORTIONS) == 7)
check("in_bounds_count", len(IN_BOUNDS_CASES) == 8)
check("oob_count", len(OUT_OF_BOUNDS_CASES) == 4)
check("identity_in_frozen", IDENTITY_DISTORTION in FROZEN_DISTORTIONS)


# ════════════════════════════════════════════════════════════
# WARP FUNCTIONS
# ════════════════════════════════════════════════════════════

print("\n=== Warp Functions ===")

spec_adj = fixture_adjacent_pair()
rgb = _render_to_raw_rgb(spec_adj)
w, h = CANVAS_WIDTH, CANVAS_HEIGHT

# Identity warp should be exact identity
id_buf, id_w, id_h = warp_forward(rgb, w, h, IDENTITY_DISTORTION)
check("identity_dims", id_w == w and id_h == h)
diff = sum(abs(a - b) for a, b in zip(rgb, id_buf))
check("identity_exact", diff == 0)

# Forward + inverse roundtrip should be near-identity
fwd, fw, fh = warp_forward(rgb, w, h, HORIZONTAL_KEYSTONE_MILD)
check("fwd_dims", fw == w and fh == h)
inv, iw, ih = warp_inverse(fwd, fw, fh, HORIZONTAL_KEYSTONE_MILD)
check("inv_dims", iw == w and ih == h)
avg_diff = sum(abs(a - b) for a, b in zip(rgb, inv)) / len(rgb)
check("roundtrip_close", avg_diff < 2.0)  # Average < 2 per byte

# Different distortions produce different outputs
fwd2, _, _ = warp_forward(rgb, w, h, VERTICAL_KEYSTONE_MILD)
check("diff_distortions_differ", fwd != fwd2)

# Determinism
fwd3, _, _ = warp_forward(rgb, w, h, HORIZONTAL_KEYSTONE_MILD)
check("warp_deterministic", fwd == fwd3)


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Distorted Host Image Generation ===")

host_spec = PerspectiveHostSpec(
    artifact_spec=spec_adj, distortion=HORIZONTAL_KEYSTONE_MILD,
    offset_x=200, offset_y=200,
    host_background=(220, 220, 220),
)
host_png = generate_perspective_host_image(host_spec)
check("host_png_valid", host_png[:4] == b'\x89PNG')
check("host_png_size", len(host_png) > 1000)

# Determinism
host_png2 = generate_perspective_host_image(host_spec)
check("host_deterministic", host_png == host_png2)

# Different distortions produce different host images
host_id = generate_perspective_host_image(PerspectiveHostSpec(
    artifact_spec=spec_adj, distortion=IDENTITY_DISTORTION,
    offset_x=200, offset_y=200))
host_hk = generate_perspective_host_image(PerspectiveHostSpec(
    artifact_spec=spec_adj, distortion=HORIZONTAL_KEYSTONE_MILD,
    offset_x=200, offset_y=200))
check("diff_distortions_diff_hosts", host_id != host_hk)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CASES — adjacent_pair
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (adjacent_pair) ===")

for i, case in enumerate(IN_BOUNDS_CASES):
    host = PerspectiveHostSpec(
        artifact_spec=spec_adj,
        distortion=case["distortion"],
        offset_x=case["offset_x"],
        offset_y=case["offset_y"],
        host_background=case["host_background"],
    )
    result = perspective_and_bridge(host)
    check(f"inbound_{i}_{case['distortion'].name}",
          result.verdict == PerspectiveVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — containment fixture
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (containment) ===")

spec_cont = fixture_containment()
for distortion in [IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD,
                   VERTICAL_KEYSTONE_MILD, CORNER_PULL_INWARD]:
    host = PerspectiveHostSpec(
        artifact_spec=spec_cont, distortion=distortion,
        offset_x=200, offset_y=200,
    )
    result = perspective_and_bridge(host)
    check(f"inbound_cont_{distortion.name}",
          result.verdict == PerspectiveVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — three_regions fixture
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Cases (three_regions) ===")

spec_three = fixture_three_regions()
for distortion in [IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD, MILD_TRAPEZOID]:
    host = PerspectiveHostSpec(
        artifact_spec=spec_three, distortion=distortion,
        offset_x=200, offset_y=200,
    )
    result = perspective_and_bridge(host)
    check(f"inbound_three_{distortion.name}",
          result.verdict == PerspectiveVerdict.NORMALIZED)


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds Cases ===")

for i, case in enumerate(OUT_OF_BOUNDS_CASES):
    host = PerspectiveHostSpec(
        artifact_spec=spec_adj,
        distortion=case["distortion"],
        offset_x=case["offset_x"],
        offset_y=case["offset_y"],
        host_background=case["host_background"],
    )
    result = perspective_and_bridge(host)
    check(f"oob_{i}_{case['distortion'].name}",
          result.verdict != PerspectiveVerdict.NORMALIZED)
    check(f"oob_{i}_honest",
          result.verdict.value in (
              "NOT_FOUND", "PERSPECTIVE_UNKNOWN", "PARSE_FAILED", "BRIDGE_FAILED"))


# ════════════════════════════════════════════════════════════
# DETERMINISM — repeated runs identical
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

host_det = PerspectiveHostSpec(
    artifact_spec=spec_adj,
    distortion=HORIZONTAL_KEYSTONE_MILD,
    offset_x=150, offset_y=150,
    host_background=(240, 240, 230),
)
r1 = perspective_and_bridge(host_det)
r2 = perspective_and_bridge(host_det)
check("determinism_verdict", r1.verdict == r2.verdict)
check("determinism_distortion", r1.detected_distortion == r2.detected_distortion)
check("determinism_prims", r1.parsed_primitives == r2.parsed_primitives)


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

result = perspective_and_bridge(PerspectiveHostSpec(
    artifact_spec=spec_adj,
    distortion=CORNER_PULL_INWARD,
    offset_x=200, offset_y=200,
))
d = result.to_dict()
check("ser_verdict", d["verdict"] == "NORMALIZED")
check("ser_distortion", d["detected_distortion"] is not None)
check("ser_parsed_prims", d["parsed_primitives"] == 2)
check("ser_expected_prims", d["expected_primitives"] == 2)
check("ser_version", d["profile_version"] == "V1.0")


# ════════════════════════════════════════════════════════════
# KEYSTONE PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

# All frozen distortions have offsets within max_corner_offset_px
max_off = V1_PERSPECTIVE_PROFILE.max_corner_offset_px
all_within = True
for dist in FROZEN_DISTORTIONS:
    for corner in [dist.tl, dist.tr, dist.bl, dist.br]:
        if abs(corner[0]) > max_off or abs(corner[1]) > max_off:
            all_within = False
            break
check("all_frozen_within_bounds", all_within)

# Each distortion has a unique name
names = [d.name for d in FROZEN_DISTORTIONS]
check("unique_names", len(names) == len(set(names)))


# ════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
total = passed + failed
print(f"Perspective Normalization Bridge V1: {passed}/{total} passed, {failed} failed")
if failed:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
