"""
Tests for Composed Recovery Bridge V1.

Proves that a frozen bounded composition of already-proven transform
families (localization, orientation, perspective, capture tolerance)
works as an integrated end-to-end recovery path.

This is a narrow integrated recovery proof, not general invariance
or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'aurexis_lang', 'src'))

import pytest

from aurexis_lang.composed_recovery_bridge_v1 import (
    COMPOSED_VERSION, COMPOSED_FROZEN, V1_COMPOSED_PROFILE,
    ComposedProfile, ComposedHostSpec, DegradationSpec, NO_DEGRADATION,
    ComposedVerdict, ComposedResult,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
    generate_composed_host_image, detect_composed_transform,
    composed_recovery, build_composed_host_spec,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
)


class TestModuleConstants:
    def test_version(self):
        assert COMPOSED_VERSION == "V1.0"

    def test_frozen(self):
        assert COMPOSED_FROZEN is True

    def test_profile(self):
        assert isinstance(V1_COMPOSED_PROFILE, ComposedProfile)

    def test_in_bounds_count(self):
        assert len(IN_BOUNDS_CASES) == 10

    def test_oob_count(self):
        assert len(OUT_OF_BOUNDS_CASES) == 4

    def test_supported_angles(self):
        assert V1_COMPOSED_PROFILE.supported_angles == (0, 90, 180, 270)


class TestHostImageGeneration:
    def test_valid_png(self):
        spec = build_composed_host_spec(IN_BOUNDS_CASES[0])
        host_png = generate_composed_host_image(spec)
        assert host_png[:4] == b'\x89PNG'

    def test_deterministic(self):
        spec = build_composed_host_spec(IN_BOUNDS_CASES[0])
        assert generate_composed_host_image(spec) == generate_composed_host_image(spec)

    def test_different_cases_different_hosts(self):
        s1 = build_composed_host_spec(IN_BOUNDS_CASES[0])
        s2 = build_composed_host_spec(IN_BOUNDS_CASES[7])
        assert generate_composed_host_image(s1) != generate_composed_host_image(s2)


class TestInBoundsCases:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_inbound_adjacent_pair(self, idx):
        case = IN_BOUNDS_CASES[idx]
        spec = build_composed_host_spec(case, artifact_spec=fixture_adjacent_pair())
        result = composed_recovery(spec)
        assert result.verdict == ComposedVerdict.RECOVERED, (
            f"Case {idx} ({case['label']}): {result.verdict.value}"
        )

    @pytest.mark.parametrize("idx", [0, 4, 7, 9])
    def test_inbound_containment(self, idx):
        case = IN_BOUNDS_CASES[idx]
        spec = build_composed_host_spec(case, artifact_spec=fixture_containment())
        result = composed_recovery(spec)
        assert result.verdict == ComposedVerdict.RECOVERED

    @pytest.mark.parametrize("idx", [0, 7, 8])
    def test_inbound_three_regions(self, idx):
        case = IN_BOUNDS_CASES[idx]
        spec = build_composed_host_spec(case, artifact_spec=fixture_three_regions())
        result = composed_recovery(spec)
        assert result.verdict == ComposedVerdict.RECOVERED


class TestOutOfBounds:
    @pytest.mark.parametrize("idx", list(range(len(OUT_OF_BOUNDS_CASES))))
    def test_oob_rejected(self, idx):
        case = OUT_OF_BOUNDS_CASES[idx]
        spec = build_composed_host_spec(case)
        result = composed_recovery(spec)
        assert result.verdict != ComposedVerdict.RECOVERED, (
            f"OOB {idx} ({case['label']}): should not recover"
        )


class TestDeterminism:
    def test_repeated_runs_identical(self):
        case = IN_BOUNDS_CASES[7]
        spec = build_composed_host_spec(case)
        r1 = composed_recovery(spec)
        r2 = composed_recovery(spec)
        assert r1.verdict == r2.verdict
        assert r1.detected_angle == r2.detected_angle
        assert r1.detected_distortion == r2.detected_distortion
        assert r1.parsed_primitives == r2.parsed_primitives


class TestSerialization:
    def test_result_to_dict(self):
        spec = build_composed_host_spec(IN_BOUNDS_CASES[0])
        result = composed_recovery(spec)
        d = result.to_dict()
        assert d["verdict"] == "RECOVERED"
        assert d["version"] == "V1.0"
        assert d["parsed_primitives"] == d["expected_primitives"]


class TestProfileValidation:
    def test_all_inbound_within_profile(self):
        p = V1_COMPOSED_PROFILE
        for i, case in enumerate(IN_BOUNDS_CASES):
            assert p.min_offset_x <= case["offset_x"] <= p.max_offset_x, f"case {i}"
            assert p.min_offset_y <= case["offset_y"] <= p.max_offset_y, f"case {i}"
            assert p.min_embed_scale <= case.get("embed_scale", 1.0) <= p.max_embed_scale
            assert case.get("rotation_angle", 0) in p.supported_angles

    def test_all_inbound_degradation_within_bounds(self):
        p = V1_COMPOSED_PROFILE
        for i, case in enumerate(IN_BOUNDS_CASES):
            deg = case.get("degradation", NO_DEGRADATION)
            assert abs(deg.brightness_shift) <= p.max_brightness_shift
            assert abs(deg.contrast_factor - 1.0) <= p.max_contrast_deviation + 0.001
            assert deg.noise_amplitude <= p.max_noise_amplitude


class TestCoverage:
    def test_has_full_composition_cases(self):
        """At least one case exercises rotation + distortion + degradation."""
        has_full = any(
            c.get("rotation_angle", 0) != 0 and
            c.get("distortion", "identity") != "identity" and
            c.get("degradation", NO_DEGRADATION) != NO_DEGRADATION
            for c in IN_BOUNDS_CASES
        )
        assert has_full
