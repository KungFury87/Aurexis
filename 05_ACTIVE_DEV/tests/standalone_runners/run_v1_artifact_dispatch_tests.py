#!/usr/bin/env python3
"""
Standalone test runner for Artifact Dispatch Bridge V1.
No external dependencies — pure Python 3.

Proves that recovered V1 artifacts can be identified by structural
fingerprint and routed to the correct decode path among a small
frozen family of known V1 artifact types.

This is a narrow deterministic dispatch proof, not general artifact
classification or open-ended versioning.

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

from aurexis_lang.artifact_dispatch_bridge_v1 import (
    DISPATCH_VERSION, DISPATCH_FROZEN, V1_DISPATCH_PROFILE,
    DispatchProfile, DispatchVerdict, DispatchResult,
    StructuralFingerprint, ArtifactFamily,
    FROZEN_FAMILIES, IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
    fingerprint_from_spec, identify_artifact_family,
    dispatch_and_bridge, dispatch_from_spec,
    recover_and_dispatch,
    _bbox_contains, _detect_containment,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
    fixture_single_region, fixture_non_adjacent,
    render_artifact, _encode_png, _decode_png_to_rgb,
    ArtifactSpec, ArtifactPrimitive, PRIMITIVE_PALETTE,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE,
)
from aurexis_lang.visual_grammar_v1 import OperationKind
from aurexis_lang.artifact_localization_bridge_v1 import (
    HostImageSpec, generate_host_image,
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
check(DISPATCH_VERSION == "V1.0", "version")
check(DISPATCH_FROZEN is True, "frozen")
check(isinstance(V1_DISPATCH_PROFILE, DispatchProfile), "profile_type")
check(len(FROZEN_FAMILIES) == 3, "family_count")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count")
check(len(OUT_OF_BOUNDS_CASES) == 3, "oob_count")

# Check family names
family_names = {f.name for f in FROZEN_FAMILIES}
check(family_names == {"adjacent_pair", "containment", "three_regions"}, "family_names")


# ════════════════════════════════════════════════════════════
# STRUCTURAL FINGERPRINTS
# ════════════════════════════════════════════════════════════

print("\n=== Structural Fingerprints ===")

fp_adj = fingerprint_from_spec(fixture_adjacent_pair())
check(fp_adj.primitive_count == 2, "fp_adjacent_count")
check(fp_adj.operation_kinds == ("ADJACENT",), "fp_adjacent_ops")

fp_cont = fingerprint_from_spec(fixture_containment())
check(fp_cont.primitive_count == 2, "fp_containment_count")
check(fp_cont.operation_kinds == ("CONTAINS",), "fp_containment_ops")

fp_three = fingerprint_from_spec(fixture_three_regions())
check(fp_three.primitive_count == 3, "fp_three_count")
check(fp_three.operation_kinds == ("ADJACENT", "ADJACENT"), "fp_three_ops")

# Each fingerprint matches its family
for family in FROZEN_FAMILIES:
    spec = family.spec_factory()
    fp = fingerprint_from_spec(spec)
    check(fp == family.fingerprint, f"fp_matches_{family.name}")


# ════════════════════════════════════════════════════════════
# CONTAINMENT DETECTION
# ════════════════════════════════════════════════════════════

print("\n=== Containment Detection ===")

adj_parsed = parse_artifact_tolerant(render_artifact(fixture_adjacent_pair()), V1_TOLERANCE_PROFILE)
cont_parsed = parse_artifact_tolerant(render_artifact(fixture_containment()), V1_TOLERANCE_PROFILE)

check(not _detect_containment(adj_parsed), "adjacent_not_containment")
check(_detect_containment(cont_parsed), "containment_detected")

# Bbox contains checks
check(_bbox_contains([50, 50, 300, 300], [100, 100, 100, 100]), "outer_contains_inner")
check(not _bbox_contains([100, 100, 100, 100], [50, 50, 300, 300]), "inner_not_contains_outer")
check(not _bbox_contains([50, 150, 100, 100], [150, 150, 100, 100]), "side_by_side_no_contain")


# ════════════════════════════════════════════════════════════
# FAMILY IDENTIFICATION
# ════════════════════════════════════════════════════════════

print("\n=== Family Identification ===")

# Adjacent pair
adj_fams = identify_artifact_family(adj_parsed)
check(len(adj_fams) == 1, "adj_one_candidate")
check(adj_fams[0].name == "adjacent_pair", "adj_correct_family")

# Containment
cont_fams = identify_artifact_family(cont_parsed)
check(len(cont_fams) == 1, "cont_one_candidate")
check(cont_fams[0].name == "containment", "cont_correct_family")

# Three regions
three_parsed = parse_artifact_tolerant(render_artifact(fixture_three_regions()), V1_TOLERANCE_PROFILE)
three_fams = identify_artifact_family(three_parsed)
check(len(three_fams) == 1, "three_one_candidate")
check(three_fams[0].name == "three_regions", "three_correct_family")

# Single region — no match
single_parsed = parse_artifact_tolerant(render_artifact(fixture_single_region()), V1_TOLERANCE_PROFILE)
single_fams = identify_artifact_family(single_parsed)
check(len(single_fams) == 0, "single_no_match")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS DISPATCH (canonical spec → render → dispatch)
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Dispatch ===")

spec_factories = {
    "fixture_adjacent_pair": fixture_adjacent_pair,
    "fixture_containment": fixture_containment,
    "fixture_three_regions": fixture_three_regions,
}

for case in IN_BOUNDS_CASES:
    factory = spec_factories[case["spec_factory"]]
    result = dispatch_from_spec(factory())
    check(
        result.verdict == DispatchVerdict.DISPATCHED,
        f"dispatch_{case['label']}_verdict"
    )
    check(
        result.family_name == case["expected_family"],
        f"dispatch_{case['label']}_family"
    )


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS DISPATCH
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds Dispatch ===")

# Blank image (0 primitives)
blank_buf = bytearray(400 * 400 * 3)
for i in range(400 * 400):
    blank_buf[i * 3] = 255
    blank_buf[i * 3 + 1] = 255
    blank_buf[i * 3 + 2] = 255
blank_png = _encode_png(400, 400, blank_buf)
r_blank = dispatch_and_bridge(blank_png)
check(r_blank.verdict == DispatchVerdict.NO_PRIMITIVES, "oob_blank_verdict")

# Single region (1 primitive — not in frozen family)
r_single = dispatch_from_spec(fixture_single_region())
check(r_single.verdict == DispatchVerdict.UNKNOWN_FAMILY, "oob_single_verdict")
check(r_single.family_name is None, "oob_single_no_family")

# Non-adjacent (2 prims, ADJACENT op but bboxes far apart — still dispatches
# as adjacent_pair since structural match works, execution just gives different result)
r_nonadj = dispatch_from_spec(fixture_non_adjacent())
check(
    r_nonadj.verdict in (DispatchVerdict.DISPATCHED, DispatchVerdict.AMBIGUOUS),
    "oob_nonadj_honest"
)

# 4-primitive artifact (not in frozen family)
four_prim_spec = ArtifactSpec(
    primitives=(
        ArtifactPrimitive(PRIMITIVE_PALETTE[0], 20, 150, 60, 60),
        ArtifactPrimitive(PRIMITIVE_PALETTE[1], 90, 150, 60, 60),
        ArtifactPrimitive(PRIMITIVE_PALETTE[2], 160, 150, 60, 60),
        ArtifactPrimitive(PRIMITIVE_PALETTE[3], 230, 150, 60, 60),
    ),
    bindings={"a": 0, "b": 1, "c": 2, "d": 3},
)
r_four = dispatch_from_spec(four_prim_spec)
check(r_four.verdict == DispatchVerdict.UNKNOWN_FAMILY, "oob_four_prims_verdict")


# ════════════════════════════════════════════════════════════
# RECOVER-AND-DISPATCH (host image → localize → dispatch)
# ════════════════════════════════════════════════════════════

print("\n=== Recover-and-Dispatch ===")

for name, factory, expected in [
    ("adjacent_pair", fixture_adjacent_pair, "adjacent_pair"),
    ("containment", fixture_containment, "containment"),
    ("three_regions", fixture_three_regions, "three_regions"),
]:
    host_spec = HostImageSpec(
        artifact_spec=factory(),
        offset_x=200, offset_y=200,
        embed_scale=1.0,
        host_background=(220, 220, 220),
    )
    host_png = generate_host_image(host_spec)
    result = recover_and_dispatch(host_png)
    check(result.verdict == DispatchVerdict.DISPATCHED, f"rad_{name}_verdict")
    check(result.family_name == expected, f"rad_{name}_family")


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

r1 = dispatch_from_spec(fixture_adjacent_pair())
r2 = dispatch_from_spec(fixture_adjacent_pair())
check(r1.verdict == r2.verdict, "det_verdict")
check(r1.family_name == r2.family_name, "det_family")
check(r1.parsed_primitive_count == r2.parsed_primitive_count, "det_prims")
check(r1.execution_verdict == r2.execution_verdict, "det_exec")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

r = dispatch_from_spec(fixture_containment())
d = r.to_dict()
check(d["verdict"] == "DISPATCHED", "ser_verdict")
check(d["family_name"] == "containment", "ser_family")
check(d["version"] == "V1.0", "ser_version")
check(d["parsed_primitive_count"] == 2, "ser_prims")


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

# All families have unique names
names = [f.name for f in FROZEN_FAMILIES]
check(len(names) == len(set(names)), "unique_family_names")

# All families have unique fingerprints
fps = [f.fingerprint for f in FROZEN_FAMILIES]
check(len(fps) == len(set(fps)), "unique_fingerprints")

# All families can be dispatched from their canonical spec
for family in FROZEN_FAMILIES:
    r = dispatch_from_spec(family.spec_factory())
    check(
        r.verdict == DispatchVerdict.DISPATCHED and r.family_name == family.name,
        f"canonical_roundtrip_{family.name}"
    )


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Artifact Dispatch Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
