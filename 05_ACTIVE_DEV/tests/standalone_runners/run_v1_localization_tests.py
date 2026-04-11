#!/usr/bin/env python3
"""
Standalone test runner for Artifact Localization Bridge V1.
No external dependencies (no pytest). Pure Python 3.

Tests that canonical V1 artifacts embedded in larger host images can be
localized, extracted, normalized, and bridged into the V1 substrate.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "aurexis_lang", "src")
sys.path.insert(0, SRC)

from aurexis_lang.artifact_localization_bridge_v1 import (
    LOCALIZATION_VERSION, LOCALIZATION_FROZEN,
    V1_LOCALIZATION_PROFILE, LocalizationProfile,
    ALLOWED_HOST_BACKGROUNDS,
    LocalizationVerdict, LocalizationResult,
    HostImageSpec, generate_host_image,
    localize_artifact, extract_and_normalize,
    localize_and_bridge,
    IN_BOUNDS_PLACEMENTS, OUT_OF_BOUNDS_PLACEMENTS,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_containment, fixture_three_regions,
    CANVAS_WIDTH, CANVAS_HEIGHT,
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
check("version", LOCALIZATION_VERSION == "V1.0")
check("frozen", LOCALIZATION_FROZEN is True)
check("profile_type", isinstance(V1_LOCALIZATION_PROFILE, LocalizationProfile))
check("host_size", V1_LOCALIZATION_PROFILE.host_width == 800)
check("min_scale", V1_LOCALIZATION_PROFILE.min_embed_scale == 0.80)
check("max_scale", V1_LOCALIZATION_PROFILE.max_embed_scale == 1.20)
check("bg_count", len(ALLOWED_HOST_BACKGROUNDS) == 5)
check("min_pixels", V1_LOCALIZATION_PROFILE.min_artifact_pixels == 200)


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Host Image Generation ===")

spec_adj = fixture_adjacent_pair()
hs = HostImageSpec(artifact_spec=spec_adj, offset_x=200, offset_y=200,
                   host_background=(220, 220, 220))
host_png = generate_host_image(hs)
check("host_png_valid", host_png[:4] == b'\x89PNG')
check("host_png_size", len(host_png) > 1000)

# Determinism
host_png2 = generate_host_image(hs)
check("host_deterministic", host_png == host_png2)


# ════════════════════════════════════════════════════════════
# LOCALIZATION — bbox detection
# ════════════════════════════════════════════════════════════

print("\n=== Localization Detection ===")

bbox = localize_artifact(host_png)
check("bbox_found", bbox is not None)
check("bbox_is_tuple", isinstance(bbox, tuple) and len(bbox) == 4)
if bbox:
    bx, by, bw, bh = bbox
    # adjacent_pair: prims at (50,150,100,100) and (150,150,100,100)
    # Host offset (200,200) → host coords x:250-350, y:350-450
    # With padding, bbox should be near (245, 345, 210, 110)
    check("bbox_x_reasonable", 230 <= bx <= 260)
    check("bbox_y_reasonable", 330 <= by <= 360)
    check("bbox_w_reasonable", 190 <= bw <= 230)
    check("bbox_h_reasonable", 90 <= bh <= 130)

# No artifact in empty host
empty_spec = HostImageSpec(
    artifact_spec=fixture_adjacent_pair(),
    offset_x=-500, offset_y=-500,
    host_background=(220, 220, 220),
)
empty_host = generate_host_image(empty_spec)
empty_bbox = localize_artifact(empty_host)
check("no_artifact_no_bbox", empty_bbox is None)


# ════════════════════════════════════════════════════════════
# EXTRACTION + NORMALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Extraction + Normalization ===")

if bbox:
    norm_png = extract_and_normalize(host_png, bbox)
    check("norm_png_valid", norm_png[:4] == b'\x89PNG')
    check("norm_png_nonempty", len(norm_png) > 100)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — adjacent_pair across all placements
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds (adjacent_pair) ===")

for i, placement in enumerate(IN_BOUNDS_PLACEMENTS):
    hs = HostImageSpec(artifact_spec=spec_adj, **placement)
    r = localize_and_bridge(hs)
    check(f"inbound_adj_{i}", r.verdict == LocalizationVerdict.LOCALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — single_region across all placements
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds (single_region) ===")

spec_single = fixture_single_region()
for i, placement in enumerate(IN_BOUNDS_PLACEMENTS):
    hs = HostImageSpec(artifact_spec=spec_single, **placement)
    r = localize_and_bridge(hs)
    check(f"inbound_single_{i}", r.verdict == LocalizationVerdict.LOCALIZED)


# ════════════════════════════════════════════════════════════
# IN-BOUNDS — three_regions
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds (three_regions, center placement) ===")

spec_three = fixture_three_regions()
hs3 = HostImageSpec(artifact_spec=spec_three, offset_x=200, offset_y=200,
                    host_background=(220, 220, 220))
r3 = localize_and_bridge(hs3)
check("inbound_three_center", r3.verdict == LocalizationVerdict.LOCALIZED)
check("inbound_three_prims", r3.parsed_primitives == 3)


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS — must be rejected
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds ===")

for i, placement in enumerate(OUT_OF_BOUNDS_PLACEMENTS):
    hs = HostImageSpec(artifact_spec=spec_adj, **placement)
    r = localize_and_bridge(hs)
    check(f"oob_{i}", r.verdict != LocalizationVerdict.LOCALIZED)


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

hs_det = HostImageSpec(artifact_spec=spec_adj, offset_x=200, offset_y=200,
                       host_background=(220, 220, 220))
results = [localize_and_bridge(hs_det).to_dict() for _ in range(5)]
check("bridge_deterministic", all(r == results[0] for r in results))

hosts = [generate_host_image(hs_det) for _ in range(5)]
check("host_gen_deterministic", all(h == hosts[0] for h in hosts))


# ════════════════════════════════════════════════════════════
# RESULT SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

r_ser = localize_and_bridge(hs_det)
d = r_ser.to_dict()
check("ser_verdict", d["verdict"] == "LOCALIZED")
check("ser_bbox", d["detected_bbox"] is not None)
check("ser_parsed", d["parsed_primitives"] == 2)
check("ser_version", d["profile_version"] == LOCALIZATION_VERSION)
check("ser_bridge", d["bridge_verdict"] == "BRIDGED")


# ════════════════════════════════════════════════════════════
# ALL ALLOWED BACKGROUNDS
# ════════════════════════════════════════════════════════════

print("\n=== All Allowed Backgrounds ===")

for bg in ALLOWED_HOST_BACKGROUNDS:
    hs_bg = HostImageSpec(artifact_spec=spec_adj, offset_x=200, offset_y=200,
                          host_background=bg)
    r_bg = localize_and_bridge(hs_bg)
    check(f"bg_{bg}", r_bg.verdict == LocalizationVerdict.LOCALIZED)


# ════════════════════════════════════════════════════════════
# RESULTS
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed == 0:
    print("\nALL TESTS PASSED \u2713")
else:
    print(f"\n{failed} TESTS FAILED")
    sys.exit(1)
