"""
Tests for Artifact Dispatch Bridge V1.

Proves that recovered V1 artifacts can be identified by structural
fingerprint and routed to the correct decode path among a small
frozen family of known V1 artifact types.

This is a narrow deterministic dispatch proof, not general artifact
classification or open-ended versioning.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'aurexis_lang', 'src'))

import pytest

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
    fixture_single_region, render_artifact, _encode_png,
    ArtifactSpec, ArtifactPrimitive, PRIMITIVE_PALETTE,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE,
)
from aurexis_lang.artifact_localization_bridge_v1 import (
    HostImageSpec, generate_host_image,
)


class TestModuleConstants:
    def test_version(self):
        assert DISPATCH_VERSION == "V1.0"

    def test_frozen(self):
        assert DISPATCH_FROZEN is True

    def test_family_count(self):
        assert len(FROZEN_FAMILIES) == 3

    def test_in_bounds_count(self):
        assert len(IN_BOUNDS_CASES) == 3

    def test_oob_count(self):
        assert len(OUT_OF_BOUNDS_CASES) == 3


class TestStructuralFingerprints:
    def test_adjacent_pair_fingerprint(self):
        fp = fingerprint_from_spec(fixture_adjacent_pair())
        assert fp.primitive_count == 2
        assert fp.operation_kinds == ("ADJACENT",)

    def test_containment_fingerprint(self):
        fp = fingerprint_from_spec(fixture_containment())
        assert fp.primitive_count == 2
        assert fp.operation_kinds == ("CONTAINS",)

    def test_three_regions_fingerprint(self):
        fp = fingerprint_from_spec(fixture_three_regions())
        assert fp.primitive_count == 3
        assert fp.operation_kinds == ("ADJACENT", "ADJACENT")

    def test_each_family_matches_its_fingerprint(self):
        for family in FROZEN_FAMILIES:
            fp = fingerprint_from_spec(family.spec_factory())
            assert fp == family.fingerprint, f"{family.name} mismatch"

    def test_fingerprints_are_unique(self):
        fps = [f.fingerprint for f in FROZEN_FAMILIES]
        assert len(fps) == len(set(fps))


class TestContainmentDetection:
    def test_adjacent_not_containment(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_adjacent_pair()), V1_TOLERANCE_PROFILE)
        assert not _detect_containment(parsed)

    def test_containment_detected(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_containment()), V1_TOLERANCE_PROFILE)
        assert _detect_containment(parsed)

    def test_bbox_contains_true(self):
        assert _bbox_contains([50, 50, 300, 300], [100, 100, 100, 100])

    def test_bbox_contains_false_side_by_side(self):
        assert not _bbox_contains([50, 150, 100, 100], [150, 150, 100, 100])


class TestFamilyIdentification:
    def test_adjacent_pair_identified(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_adjacent_pair()), V1_TOLERANCE_PROFILE)
        fams = identify_artifact_family(parsed)
        assert len(fams) == 1
        assert fams[0].name == "adjacent_pair"

    def test_containment_identified(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_containment()), V1_TOLERANCE_PROFILE)
        fams = identify_artifact_family(parsed)
        assert len(fams) == 1
        assert fams[0].name == "containment"

    def test_three_regions_identified(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_three_regions()), V1_TOLERANCE_PROFILE)
        fams = identify_artifact_family(three_parsed := parsed)
        assert len(fams) == 1
        assert fams[0].name == "three_regions"

    def test_single_region_no_match(self):
        parsed = parse_artifact_tolerant(
            render_artifact(fixture_single_region()), V1_TOLERANCE_PROFILE)
        fams = identify_artifact_family(parsed)
        assert len(fams) == 0


class TestInBoundsDispatch:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_dispatch_correct(self, idx):
        case = IN_BOUNDS_CASES[idx]
        factories = {
            "fixture_adjacent_pair": fixture_adjacent_pair,
            "fixture_containment": fixture_containment,
            "fixture_three_regions": fixture_three_regions,
        }
        result = dispatch_from_spec(factories[case["spec_factory"]]())
        assert result.verdict == DispatchVerdict.DISPATCHED
        assert result.family_name == case["expected_family"]


class TestOutOfBounds:
    def test_blank_image(self):
        blank_buf = bytearray(400 * 400 * 3)
        for i in range(400 * 400):
            blank_buf[i * 3] = 255
            blank_buf[i * 3 + 1] = 255
            blank_buf[i * 3 + 2] = 255
        blank = _encode_png(400, 400, blank_buf)
        r = dispatch_and_bridge(blank)
        assert r.verdict == DispatchVerdict.NO_PRIMITIVES

    def test_single_region(self):
        r = dispatch_from_spec(fixture_single_region())
        assert r.verdict == DispatchVerdict.UNKNOWN_FAMILY

    def test_four_primitives(self):
        spec = ArtifactSpec(
            primitives=(
                ArtifactPrimitive(PRIMITIVE_PALETTE[0], 20, 150, 60, 60),
                ArtifactPrimitive(PRIMITIVE_PALETTE[1], 90, 150, 60, 60),
                ArtifactPrimitive(PRIMITIVE_PALETTE[2], 160, 150, 60, 60),
                ArtifactPrimitive(PRIMITIVE_PALETTE[3], 230, 150, 60, 60),
            ),
            bindings={"a": 0, "b": 1, "c": 2, "d": 3},
        )
        r = dispatch_from_spec(spec)
        assert r.verdict == DispatchVerdict.UNKNOWN_FAMILY


class TestRecoverAndDispatch:
    @pytest.mark.parametrize("name,factory,expected", [
        ("adjacent_pair", "fixture_adjacent_pair", "adjacent_pair"),
        ("containment", "fixture_containment", "containment"),
        ("three_regions", "fixture_three_regions", "three_regions"),
    ])
    def test_recover_dispatch(self, name, factory, expected):
        factories = {
            "fixture_adjacent_pair": fixture_adjacent_pair,
            "fixture_containment": fixture_containment,
            "fixture_three_regions": fixture_three_regions,
        }
        host_spec = HostImageSpec(
            artifact_spec=factories[factory](),
            offset_x=200, offset_y=200,
            embed_scale=1.0,
            host_background=(220, 220, 220),
        )
        host_png = generate_host_image(host_spec)
        result = recover_and_dispatch(host_png)
        assert result.verdict == DispatchVerdict.DISPATCHED
        assert result.family_name == expected


class TestDeterminism:
    def test_repeated_runs_identical(self):
        r1 = dispatch_from_spec(fixture_adjacent_pair())
        r2 = dispatch_from_spec(fixture_adjacent_pair())
        assert r1.verdict == r2.verdict
        assert r1.family_name == r2.family_name
        assert r1.parsed_primitive_count == r2.parsed_primitive_count


class TestSerialization:
    def test_result_to_dict(self):
        r = dispatch_from_spec(fixture_containment())
        d = r.to_dict()
        assert d["verdict"] == "DISPATCHED"
        assert d["family_name"] == "containment"
        assert d["version"] == "V1.0"


class TestProfileValidation:
    def test_unique_names(self):
        names = [f.name for f in FROZEN_FAMILIES]
        assert len(names) == len(set(names))

    def test_canonical_roundtrip(self):
        for family in FROZEN_FAMILIES:
            r = dispatch_from_spec(family.spec_factory())
            assert r.verdict == DispatchVerdict.DISPATCHED
            assert r.family_name == family.name
