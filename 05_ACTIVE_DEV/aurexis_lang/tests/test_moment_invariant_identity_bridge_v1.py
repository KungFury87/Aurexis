"""
Pytest suite for Moment-Invariant Identity Bridge V1 (34th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    compute_identity_hash,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    IDENTITY_VERSION, IDENTITY_FROZEN,
    IdentityVerdict,
    MarkerObservation, InvariantFeatures, IdentityVerificationResult,
    extract_invariant_features, generate_observation, generate_all_observations,
    verify_identity_across_viewpoints, verify_all_markers,
    identify_marker,
    make_unknown_observation, make_corrupted_observation,
    STABLE_MARKER_COUNT,
)


class TestModuleVersion:
    def test_version(self):
        assert IDENTITY_VERSION == "V1.0"

    def test_frozen(self):
        assert IDENTITY_FROZEN is True

    def test_stable_count(self):
        assert STABLE_MARKER_COUNT == 4


class TestMarkerObservation:
    def test_construction(self):
        obs = MarkerObservation(marker_name="test", viewpoint=ViewpointBucket.FRONT,
                                structural_class="planar", region_count=4)
        assert obs.marker_name == "test"

    def test_to_dict(self):
        obs = MarkerObservation(marker_name="test", viewpoint=ViewpointBucket.LEFT)
        d = obs.to_dict()
        assert d["marker_name"] == "test"
        assert d["viewpoint"] == "LEFT"

    def test_immutable(self):
        obs = MarkerObservation(marker_name="test")
        with pytest.raises((AttributeError, TypeError)):
            obs.marker_name = "hacked"


class TestInvariantFeatures:
    def test_extraction(self):
        obs = MarkerObservation(marker_name="alpha_planar",
                                structural_class="planar", region_count=4)
        f = extract_invariant_features(obs)
        assert f.marker_name == "alpha_planar"
        assert f.structural_class == "planar"
        assert f.region_count == 4

    def test_hash_matches(self):
        obs = MarkerObservation(marker_name="alpha_planar",
                                structural_class="planar", region_count=4)
        f = extract_invariant_features(obs)
        expected = compute_identity_hash("alpha_planar", "planar", 4)
        assert f.identity_hash == expected

    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_viewpoint_independent(self, vp):
        marker = FROZEN_MARKER_FAMILY[0]
        obs = generate_observation(marker, vp)
        f = extract_invariant_features(obs)
        expected = compute_identity_hash(marker.name, marker.structural_class, marker.region_count)
        assert f.identity_hash == expected


class TestGenerateObservation:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_generates(self, marker, vp):
        obs = generate_observation(marker, vp)
        assert obs is not None
        assert obs.marker_name == marker.name
        assert obs.viewpoint == vp

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_all_observations(self, marker):
        all_obs = generate_all_observations(marker)
        assert len(all_obs) == VIEWPOINT_COUNT


class TestVerifyIdentity:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_stable(self, marker):
        r = verify_identity_across_viewpoints(marker)
        assert r.verdict == IdentityVerdict.IDENTITY_STABLE
        assert r.all_identical is True
        assert r.viewpoints_checked == VIEWPOINT_COUNT

    def test_batch(self):
        results = verify_all_markers()
        assert len(results) == STABLE_MARKER_COUNT
        assert all(r.verdict == IdentityVerdict.IDENTITY_STABLE for r in results)


class TestIdentifyMarker:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_identifies(self, marker, vp):
        obs = generate_observation(marker, vp)
        assert identify_marker(obs) == marker.name

    def test_unknown_rejected(self):
        obs = make_unknown_observation()
        assert identify_marker(obs) is None

    def test_corrupted_rejected(self):
        obs = make_corrupted_observation()
        assert identify_marker(obs) is None


class TestSerialization:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_result_to_dict(self, marker):
        r = verify_identity_across_viewpoints(marker)
        d = r.to_dict()
        assert d["marker_name"] == marker.name
        assert d["verdict"] == "IDENTITY_STABLE"
        assert d["version"] == IDENTITY_VERSION


class TestCollisionResistance:
    def test_unique_hashes(self):
        hashes = {m.identity_hash for m in FROZEN_MARKER_FAMILY}
        assert len(hashes) == len(FROZEN_MARKER_FAMILY)

    def test_different_class(self):
        h1 = compute_identity_hash("t", "planar", 5)
        h2 = compute_identity_hash("t", "relief", 5)
        assert h1 != h2

    def test_different_count(self):
        h1 = compute_identity_hash("t", "planar", 5)
        h2 = compute_identity_hash("t", "planar", 6)
        assert h1 != h2
