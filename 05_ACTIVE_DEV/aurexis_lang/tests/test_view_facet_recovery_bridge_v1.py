"""
Pytest suite for View-Facet Recovery Bridge V1 (35th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    generate_observation, generate_all_observations,
)
from aurexis_lang.view_facet_recovery_bridge_v1 import (
    RECOVERY_VERSION, RECOVERY_FROZEN, RecoveryVerdict,
    RecoveryResult, FacetVariationResult,
    compute_observation_facet_hash,
    recover_marker_identity, recover_viewpoint, recover_full,
    recover_all_observations, verify_facet_variation, verify_all_facet_variations,
    make_unknown_marker_observation, make_identity_only_observation,
    TOTAL_RECOVERY_COUNT, FULL_RECOVERY_EXPECTED, FACET_VARIATION_MARKER_COUNT,
)


class TestModuleVersion:
    def test_version(self):
        assert RECOVERY_VERSION == "V1.0"

    def test_frozen(self):
        assert RECOVERY_FROZEN is True

    def test_counts(self):
        assert TOTAL_RECOVERY_COUNT == 16
        assert FULL_RECOVERY_EXPECTED == 16
        assert FACET_VARIATION_MARKER_COUNT == 4


class TestObservationFacetHash:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_matches_frozen(self, marker, vp):
        obs = generate_observation(marker, vp)
        fh = compute_observation_facet_hash(obs)
        assert fh == marker.get_facet(vp).facet_hash


class TestRecoverIdentity:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_recovers(self, marker):
        obs = generate_observation(marker, ViewpointBucket.FRONT)
        recovered = recover_marker_identity(obs)
        assert recovered is not None
        assert recovered.name == marker.name


class TestRecoverViewpoint:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_recovers(self, marker, vp):
        obs = generate_observation(marker, vp)
        result = recover_viewpoint(obs, marker)
        assert result is not None
        recovered_vp, recovered_facet = result
        assert recovered_vp == vp


class TestFullRecovery:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_full(self, marker, vp):
        obs = generate_observation(marker, vp)
        r = recover_full(obs)
        assert r.verdict == RecoveryVerdict.FULL_RECOVERY
        assert r.recovered_marker_name == marker.name
        assert r.recovered_viewpoint == vp
        assert r.recovered_facet is not None


class TestBatchRecovery:
    def test_count(self):
        results = recover_all_observations()
        assert len(results) == TOTAL_RECOVERY_COUNT

    def test_all_full(self):
        results = recover_all_observations()
        assert all(r.verdict == RecoveryVerdict.FULL_RECOVERY for r in results)


class TestFacetVariation:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_individual(self, marker):
        v = verify_facet_variation(marker)
        assert v.identity_stable is True
        assert v.facets_vary is True
        assert v.unique_facet_hashes == VIEWPOINT_COUNT

    def test_batch(self):
        results = verify_all_facet_variations()
        assert len(results) == FACET_VARIATION_MARKER_COUNT
        assert all(v.identity_stable and v.facets_vary for v in results)


class TestUnknownMarker:
    def test_no_identity(self):
        obs = make_unknown_marker_observation()
        r = recover_full(obs)
        assert r.verdict == RecoveryVerdict.NO_IDENTITY
        assert r.recovered_marker_name == ""
        assert r.recovered_viewpoint is None


class TestIdentityOnly:
    def test_corrupted_facet(self):
        obs = make_identity_only_observation()
        r = recover_full(obs)
        assert r.verdict == RecoveryVerdict.IDENTITY_ONLY
        assert r.recovered_marker_name == "alpha_planar"
        assert r.recovered_viewpoint is None


class TestSerialization:
    def test_recovery_to_dict(self):
        obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
        r = recover_full(obs)
        d = r.to_dict()
        assert d["verdict"] == "FULL_RECOVERY"
        assert d["recovered_marker_name"] == "alpha_planar"

    def test_variation_to_dict(self):
        v = verify_facet_variation(FROZEN_MARKER_FAMILY[0])
        d = v.to_dict()
        assert d["identity_stable"] is True
        assert d["facets_vary"] is True


class TestImmutability:
    def test_result_immutable(self):
        obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
        r = recover_full(obs)
        with pytest.raises((AttributeError, TypeError)):
            r.verdict = RecoveryVerdict.ERROR
