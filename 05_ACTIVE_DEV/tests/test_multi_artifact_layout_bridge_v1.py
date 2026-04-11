"""
Tests for Multi-Artifact Layout Bridge V1.

Proves that 2–3 canonical V1 artifacts embedded in one larger host
image can be independently localized, recovered, dispatched, and
decoded in one deterministic pass.

This is a narrow deterministic multi-artifact layout proof, not
general multi-object detection or scene understanding.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'aurexis_lang', 'src'))

import pytest

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


# ════════════════════════════════════════════════════════════
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

class TestModuleConstants:
    def test_version(self):
        assert LAYOUT_VERSION == "V1.0"

    def test_frozen(self):
        assert LAYOUT_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile)

    def test_frozen_layout_count(self):
        assert len(FROZEN_LAYOUTS) == 5

    def test_oob_layout_count(self):
        assert len(OUT_OF_BOUNDS_LAYOUTS) == 3

    def test_family_factories(self):
        assert set(_FAMILY_FACTORIES.keys()) == {
            "adjacent_pair", "containment", "three_regions"
        }


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

class TestHostGeneration:
    def test_two_artifact_host_is_bytes(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        assert isinstance(png, bytes)
        assert len(png) > 100

    def test_three_artifact_host_is_bytes(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[2])
        png = generate_multi_artifact_host(spec)
        assert isinstance(png, bytes)
        assert len(png) > 100

    def test_empty_host_is_bytes(self):
        spec = MultiLayoutSpec(entries=(), host_background=(220, 220, 220))
        png = generate_multi_artifact_host(spec)
        assert isinstance(png, bytes)

    def test_deterministic_generation(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png1 = generate_multi_artifact_host(spec)
        png2 = generate_multi_artifact_host(spec)
        assert png1 == png2


# ════════════════════════════════════════════════════════════
# MULTI-CANDIDATE LOCALIZATION
# ════════════════════════════════════════════════════════════

class TestLocalization:
    def test_two_horizontal_finds_two(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 2

    def test_two_vertical_finds_two(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[1])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 2

    def test_three_in_row_finds_three(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[2])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 3

    def test_empty_host_finds_none(self):
        spec = MultiLayoutSpec(entries=(), host_background=(220, 220, 220))
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 0

    def test_bboxes_are_tuples(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        for bb in bboxes:
            assert len(bb) == 4
            assert all(isinstance(v, int) for v in bb)


# ════════════════════════════════════════════════════════════
# ORDERING
# ════════════════════════════════════════════════════════════

class TestOrdering:
    def test_horizontal_left_to_right(self):
        """Two horizontal artifacts: left one first."""
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 2
        # Left bbox centroid x < right bbox centroid x
        cx0 = bboxes[0][0] + bboxes[0][2] / 2
        cx1 = bboxes[1][0] + bboxes[1][2] / 2
        assert cx0 < cx1

    def test_vertical_top_to_bottom(self):
        """Two vertical artifacts: top one first."""
        spec = build_layout_spec(FROZEN_LAYOUTS[1])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 2
        # Top bbox centroid y < bottom bbox centroid y
        cy0 = bboxes[0][1] + bboxes[0][3] / 2
        cy1 = bboxes[1][1] + bboxes[1][3] / 2
        assert cy0 < cy1

    def test_three_in_row_left_to_right(self):
        """Three-in-row: left to right order."""
        spec = build_layout_spec(FROZEN_LAYOUTS[2])
        png = generate_multi_artifact_host(spec)
        bboxes = localize_multiple_artifacts(png)
        assert len(bboxes) == 3
        cx = [b[0] + b[2] / 2 for b in bboxes]
        assert cx[0] < cx[1] < cx[2]


# ════════════════════════════════════════════════════════════
# IN-BOUNDS FULL PIPELINE
# ════════════════════════════════════════════════════════════

class TestInBoundsRecovery:
    @pytest.mark.parametrize("idx", list(range(len(FROZEN_LAYOUTS))))
    def test_layout_recovered(self, idx):
        layout = FROZEN_LAYOUTS[idx]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        assert result.verdict == MultiLayoutVerdict.RECOVERED, (
            f"Layout {layout['name']}: expected RECOVERED, got {result.verdict}"
        )

    @pytest.mark.parametrize("idx", list(range(len(FROZEN_LAYOUTS))))
    def test_layout_correct_count(self, idx):
        layout = FROZEN_LAYOUTS[idx]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        assert result.dispatched_count == len(layout["expected_families"])

    @pytest.mark.parametrize("idx", list(range(len(FROZEN_LAYOUTS))))
    def test_layout_correct_families(self, idx):
        layout = FROZEN_LAYOUTS[idx]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        assert result.dispatched_families == layout["expected_families"], (
            f"Layout {layout['name']}: expected {layout['expected_families']}, "
            f"got {result.dispatched_families}"
        )

    @pytest.mark.parametrize("idx", list(range(len(FROZEN_LAYOUTS))))
    def test_layout_ordering_correct(self, idx):
        layout = FROZEN_LAYOUTS[idx]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        assert result.ordering_correct is True


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS
# ════════════════════════════════════════════════════════════

class TestOutOfBounds:
    def test_overlapping_not_recovered(self):
        layout = OUT_OF_BOUNDS_LAYOUTS[0]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=("adjacent_pair", "containment"))
        assert result.verdict != MultiLayoutVerdict.RECOVERED

    def test_one_too_small_not_recovered(self):
        layout = OUT_OF_BOUNDS_LAYOUTS[1]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=("adjacent_pair", "containment"))
        assert result.verdict != MultiLayoutVerdict.RECOVERED

    def test_empty_host_no_candidates(self):
        layout = OUT_OF_BOUNDS_LAYOUTS[2]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=())
        assert result.found_count == 0


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

class TestDeterminism:
    def test_repeated_runs_identical(self):
        layout = FROZEN_LAYOUTS[0]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        r1 = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        r2 = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        assert r1.verdict == r2.verdict
        assert r1.dispatched_families == r2.dispatched_families
        assert r1.found_count == r2.found_count


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

class TestSerialization:
    def test_result_to_dict(self):
        layout = FROZEN_LAYOUTS[0]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        d = result.to_dict()
        assert d["verdict"] == "RECOVERED"
        assert d["dispatched_count"] == 2
        assert d["version"] == "V1.0"
        assert isinstance(d["candidates"], list)
        assert len(d["candidates"]) == 2

    def test_candidate_to_dict(self):
        layout = FROZEN_LAYOUTS[0]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        result = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        cd = result.candidates[0].to_dict()
        assert "bbox" in cd
        assert "dispatch" in cd
        assert len(cd["bbox"]) == 4


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

class TestProfileValidation:
    def test_unique_layout_names(self):
        names = [l["name"] for l in FROZEN_LAYOUTS]
        assert len(names) == len(set(names))

    def test_all_layouts_have_expected_families(self):
        for layout in FROZEN_LAYOUTS:
            assert "expected_families" in layout
            assert len(layout["expected_families"]) >= 2

    def test_all_entries_use_frozen_families(self):
        valid = set(_FAMILY_FACTORIES.keys())
        for layout in FROZEN_LAYOUTS:
            for entry in layout["entries"]:
                assert entry["family"] in valid
