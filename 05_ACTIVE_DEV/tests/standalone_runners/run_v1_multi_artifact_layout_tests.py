#!/usr/bin/env python3
"""
Standalone test runner for Multi-Artifact Layout Bridge V1.
No external dependencies — pure Python 3.

Proves that 2–3 canonical V1 artifacts embedded in one larger host
image can be independently localized, recovered, dispatched, and
decoded in one deterministic pass.

This is a narrow deterministic multi-artifact layout proof, not
general multi-object detection or scene understanding.

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

from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    LAYOUT_VERSION, LAYOUT_FROZEN, V1_MULTI_LAYOUT_PROFILE,
    MultiLayoutProfile, MultiLayoutVerdict, MultiLayoutResult,
    CandidateResult, ArtifactEntry, MultiLayoutSpec,
    FROZEN_LAYOUTS, OUT_OF_BOUNDS_LAYOUTS,
    _FAMILY_FACTORIES,
    generate_multi_artifact_host,
    localize_multiple_artifacts,
    multi_artifact_recover_and_dispatch,
    build_layout_spec,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
    _encode_png,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import DispatchVerdict


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
check(LAYOUT_VERSION == "V1.0", "version")
check(LAYOUT_FROZEN is True, "frozen")
check(isinstance(V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile), "profile_type")
check(len(FROZEN_LAYOUTS) == 5, "frozen_layout_count")
check(len(OUT_OF_BOUNDS_LAYOUTS) == 3, "oob_layout_count")
check(
    set(_FAMILY_FACTORIES.keys()) == {"adjacent_pair", "containment", "three_regions"},
    "family_factories"
)


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Host Image Generation ===")

spec_2h = build_layout_spec(FROZEN_LAYOUTS[0])
png_2h = generate_multi_artifact_host(spec_2h)
check(isinstance(png_2h, bytes), "two_horiz_is_bytes")
check(len(png_2h) > 100, "two_horiz_has_data")

spec_3r = build_layout_spec(FROZEN_LAYOUTS[2])
png_3r = generate_multi_artifact_host(spec_3r)
check(isinstance(png_3r, bytes), "three_row_is_bytes")
check(len(png_3r) > 100, "three_row_has_data")

# Empty host
spec_empty = MultiLayoutSpec(entries=(), host_background=(220, 220, 220))
png_empty = generate_multi_artifact_host(spec_empty)
check(isinstance(png_empty, bytes), "empty_host_is_bytes")

# Determinism
png_2h_2 = generate_multi_artifact_host(spec_2h)
check(png_2h == png_2h_2, "generation_deterministic")


# ════════════════════════════════════════════════════════════
# MULTI-CANDIDATE LOCALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Multi-Candidate Localization ===")

# Two horizontal → 2 clusters
bboxes_2h = localize_multiple_artifacts(png_2h)
check(len(bboxes_2h) == 2, "two_horiz_finds_two")

# Two vertical → 2 clusters
spec_2v = build_layout_spec(FROZEN_LAYOUTS[1])
png_2v = generate_multi_artifact_host(spec_2v)
bboxes_2v = localize_multiple_artifacts(png_2v)
check(len(bboxes_2v) == 2, "two_vert_finds_two")

# Three in row → 3 clusters
bboxes_3r = localize_multiple_artifacts(png_3r)
check(len(bboxes_3r) == 3, "three_row_finds_three")

# Empty host → 0 clusters
bboxes_empty = localize_multiple_artifacts(png_empty)
check(len(bboxes_empty) == 0, "empty_finds_none")

# Bbox format check
for bb in bboxes_2h:
    check(len(bb) == 4, f"bbox_len_{bb[0]}")
    check(all(isinstance(v, int) for v in bb), f"bbox_ints_{bb[0]}")


# ════════════════════════════════════════════════════════════
# ORDERING
# ════════════════════════════════════════════════════════════

print("\n=== Ordering ===")

# Horizontal: left < right by centroid x
cx_2h = [bb[0] + bb[2] / 2 for bb in bboxes_2h]
check(cx_2h[0] < cx_2h[1], "horiz_left_to_right")

# Vertical: top < bottom by centroid y
cy_2v = [bb[1] + bb[3] / 2 for bb in bboxes_2v]
check(cy_2v[0] < cy_2v[1], "vert_top_to_bottom")

# Three in row: left to right
cx_3r = [bb[0] + bb[2] / 2 for bb in bboxes_3r]
check(cx_3r[0] < cx_3r[1] < cx_3r[2], "three_row_left_to_right")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS FULL PIPELINE
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Full Pipeline ===")

for layout in FROZEN_LAYOUTS:
    name = layout["name"]
    expected = layout["expected_families"]
    spec = build_layout_spec(layout)
    png = generate_multi_artifact_host(spec)
    result = multi_artifact_recover_and_dispatch(png, expected_families=expected)

    check(
        result.verdict == MultiLayoutVerdict.RECOVERED,
        f"{name}_verdict_recovered"
    )
    check(
        result.dispatched_count == len(expected),
        f"{name}_correct_count"
    )
    check(
        result.dispatched_families == expected,
        f"{name}_correct_families"
    )
    check(
        result.ordering_correct is True,
        f"{name}_ordering_correct"
    )


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds ===")

# Overlapping — clusters merge, cannot recover both
oob_overlap = OUT_OF_BOUNDS_LAYOUTS[0]
spec_ov = build_layout_spec(oob_overlap)
png_ov = generate_multi_artifact_host(spec_ov)
r_ov = multi_artifact_recover_and_dispatch(
    png_ov, expected_families=("adjacent_pair", "containment"))
check(
    r_ov.verdict != MultiLayoutVerdict.RECOVERED,
    "overlap_not_recovered"
)
check(r_ov.found_count < 2, "overlap_merged_clusters")

# One too small — second artifact below detection threshold
oob_small = OUT_OF_BOUNDS_LAYOUTS[1]
spec_sm = build_layout_spec(oob_small)
png_sm = generate_multi_artifact_host(spec_sm)
r_sm = multi_artifact_recover_and_dispatch(
    png_sm, expected_families=("adjacent_pair", "containment"))
check(
    r_sm.verdict != MultiLayoutVerdict.RECOVERED,
    "too_small_not_recovered"
)
check(r_sm.found_count < 2, "too_small_missing_candidate")

# Empty host — no candidates
oob_empty = OUT_OF_BOUNDS_LAYOUTS[2]
spec_e = build_layout_spec(oob_empty)
png_e = generate_multi_artifact_host(spec_e)
r_e = multi_artifact_recover_and_dispatch(png_e, expected_families=())
check(r_e.found_count == 0, "empty_no_candidates")
check(
    r_e.verdict == MultiLayoutVerdict.NO_CANDIDATES,
    "empty_verdict"
)


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

layout_det = FROZEN_LAYOUTS[0]
spec_det = build_layout_spec(layout_det)
png_det = generate_multi_artifact_host(spec_det)
r_d1 = multi_artifact_recover_and_dispatch(
    png_det, expected_families=layout_det["expected_families"])
r_d2 = multi_artifact_recover_and_dispatch(
    png_det, expected_families=layout_det["expected_families"])
check(r_d1.verdict == r_d2.verdict, "det_verdict")
check(r_d1.dispatched_families == r_d2.dispatched_families, "det_families")
check(r_d1.found_count == r_d2.found_count, "det_found_count")
check(r_d1.dispatched_count == r_d2.dispatched_count, "det_dispatched_count")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

layout_ser = FROZEN_LAYOUTS[0]
spec_ser = build_layout_spec(layout_ser)
png_ser = generate_multi_artifact_host(spec_ser)
r_ser = multi_artifact_recover_and_dispatch(
    png_ser, expected_families=layout_ser["expected_families"])
d = r_ser.to_dict()
check(d["verdict"] == "RECOVERED", "ser_verdict")
check(d["dispatched_count"] == 2, "ser_count")
check(d["version"] == "V1.0", "ser_version")
check(isinstance(d["candidates"], list), "ser_candidates_list")
check(len(d["candidates"]) == 2, "ser_candidates_count")

cd = r_ser.candidates[0].to_dict()
check("bbox" in cd, "ser_candidate_has_bbox")
check("dispatch" in cd, "ser_candidate_has_dispatch")
check(len(cd["bbox"]) == 4, "ser_candidate_bbox_len")


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

# Unique layout names
layout_names = [l["name"] for l in FROZEN_LAYOUTS]
check(len(layout_names) == len(set(layout_names)), "unique_layout_names")

# All layouts have expected families
for layout in FROZEN_LAYOUTS:
    check(
        "expected_families" in layout and len(layout["expected_families"]) >= 2,
        f"layout_{layout['name']}_has_families"
    )

# All entries use frozen families
valid_families = set(_FAMILY_FACTORIES.keys())
all_valid = True
for layout in FROZEN_LAYOUTS:
    for entry in layout["entries"]:
        if entry["family"] not in valid_families:
            all_valid = False
check(all_valid, "all_entries_use_frozen_families")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Multi-Artifact Layout Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
