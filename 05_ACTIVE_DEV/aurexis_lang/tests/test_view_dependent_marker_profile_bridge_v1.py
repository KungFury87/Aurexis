"""
Pytest suite for View-Dependent Marker Profile Bridge V1 (33rd bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    MARKER_PROFILE_VERSION, MARKER_PROFILE_FROZEN,
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    MarkerFacet, ViewDependentMarker, ViewDependentMarkerProfile,
    V1_MARKER_PROFILE, FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    FROZEN_MARKER_COUNT,
    compute_identity_hash, compute_facet_hash,
    EXPECTED_MARKER_COUNT, EXPECTED_VIEWPOINT_COUNT,
    EXPECTED_FACET_COUNT_PER_MARKER, EXPECTED_TOTAL_FACETS,
)


class TestModuleVersion:
    def test_version(self):
        assert MARKER_PROFILE_VERSION == "V1.0"

    def test_frozen(self):
        assert MARKER_PROFILE_FROZEN is True


class TestViewpointBucket:
    def test_count(self):
        assert len(ALL_VIEWPOINTS) == 4
        assert VIEWPOINT_COUNT == 4

    def test_values(self):
        assert ViewpointBucket.FRONT.value == "FRONT"
        assert ViewpointBucket.LEFT.value == "LEFT"
        assert ViewpointBucket.RIGHT.value == "RIGHT"
        assert ViewpointBucket.TILT_PLUS.value == "TILT_PLUS"


class TestExpectedCounts:
    def test_marker_count(self):
        assert EXPECTED_MARKER_COUNT == 4

    def test_viewpoint_count(self):
        assert EXPECTED_VIEWPOINT_COUNT == 4

    def test_facet_count_per_marker(self):
        assert EXPECTED_FACET_COUNT_PER_MARKER == 4

    def test_total_facets(self):
        assert EXPECTED_TOTAL_FACETS == 16


class TestFrozenMarkerFamily:
    def test_count(self):
        assert FROZEN_MARKER_COUNT == 4
        assert len(FROZEN_MARKER_FAMILY) == 4

    def test_names(self):
        expected = ("alpha_planar", "beta_relief", "gamma_prismatic", "delta_pyramidal")
        assert FROZEN_MARKER_NAMES == expected

    def test_structural_classes(self):
        classes = [m.structural_class for m in FROZEN_MARKER_FAMILY]
        assert classes == ["planar", "relief", "prismatic", "pyramidal"]

    def test_region_counts(self):
        counts = [m.region_count for m in FROZEN_MARKER_FAMILY]
        assert counts == [4, 6, 5, 3]


class TestMarkerFacets:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_facet_count(self, marker):
        assert marker.viewpoint_count == 4

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_all_viewpoints_covered(self, marker):
        vps = {f.viewpoint for f in marker.facets}
        assert vps == set(ALL_VIEWPOINTS)

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_facet_hashes_unique(self, marker):
        fhs = {f.facet_hash for f in marker.facets}
        assert len(fhs) == 4

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_facet_hash_determinism(self, marker):
        for f in marker.facets:
            expected = compute_facet_hash(marker.name, f.viewpoint, f.visible_regions, f.dominant_axis, f.aspect_ratio_bucket)
            assert f.facet_hash == expected


class TestIdentityHash:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_identity_matches_recomputed(self, marker):
        expected = compute_identity_hash(marker.name, marker.structural_class, marker.region_count)
        assert marker.identity_hash == expected

    def test_unique_across_markers(self):
        hashes = {m.identity_hash for m in FROZEN_MARKER_FAMILY}
        assert len(hashes) == 4

    def test_deterministic(self):
        h1 = compute_identity_hash("x", "y", 1)
        h2 = compute_identity_hash("x", "y", 1)
        assert h1 == h2

    def test_different_inputs(self):
        h1 = compute_identity_hash("x", "y", 1)
        h2 = compute_identity_hash("x", "y", 2)
        assert h1 != h2


class TestProfileObject:
    def test_marker_count(self):
        assert V1_MARKER_PROFILE.marker_count == 4

    def test_version(self):
        assert V1_MARKER_PROFILE.version == "V1.0"

    @pytest.mark.parametrize("name", FROZEN_MARKER_NAMES)
    def test_lookup(self, name):
        m = V1_MARKER_PROFILE.get_marker(name)
        assert m is not None
        assert m.name == name

    def test_lookup_unknown(self):
        assert V1_MARKER_PROFILE.get_marker("nonexistent") is None


class TestSerialization:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_marker_to_dict(self, marker):
        d = marker.to_dict()
        assert d["name"] == marker.name
        assert len(d["facets"]) == 4

    def test_profile_to_dict(self):
        d = V1_MARKER_PROFILE.to_dict()
        assert d["marker_count"] == 4
        assert len(d["markers"]) == 4


class TestImmutability:
    def test_marker_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            FROZEN_MARKER_FAMILY[0].name = "hacked"

    def test_facet_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            FROZEN_MARKER_FAMILY[0].facets[0].visible_regions = 999


class TestFacetGetAccess:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_get_facet(self, marker, vp):
        f = marker.get_facet(vp)
        assert f is not None
        assert f.viewpoint == vp


class TestTotalFacets:
    def test_sum(self):
        total = sum(m.viewpoint_count for m in FROZEN_MARKER_FAMILY)
        assert total == EXPECTED_TOTAL_FACETS
