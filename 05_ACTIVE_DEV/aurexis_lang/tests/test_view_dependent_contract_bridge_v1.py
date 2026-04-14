"""
Pytest suite for View-Dependent Contract Bridge V1 (36th bridge).
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    generate_observation,
)
from aurexis_lang.view_facet_recovery_bridge_v1 import (
    RecoveryVerdict, recover_full,
)
from aurexis_lang.view_dependent_contract_bridge_v1 import (
    CONTRACT_VERSION, CONTRACT_FROZEN, ContractVerdict,
    MarkerContract, ViewDependentContractProfile, ContractValidationResult,
    V1_CONTRACT_PROFILE,
    validate_recovery, validate_all_recoveries,
    make_incomplete_recovery, make_unknown_marker_recovery,
    make_identity_mismatch_recovery, make_facet_mismatch_recovery,
    EXPECTED_CONTRACT_COUNT, EXPECTED_VALID_COUNT, VIOLATION_CASE_COUNT,
)


class TestModuleVersion:
    def test_version(self):
        assert CONTRACT_VERSION == "V1.0"

    def test_frozen(self):
        assert CONTRACT_FROZEN is True

    def test_counts(self):
        assert EXPECTED_CONTRACT_COUNT == 4
        assert EXPECTED_VALID_COUNT == 16
        assert VIOLATION_CASE_COUNT == 4


class TestContractProfile:
    def test_count(self):
        assert V1_CONTRACT_PROFILE.contract_count == EXPECTED_CONTRACT_COUNT

    @pytest.mark.parametrize("name", FROZEN_MARKER_NAMES)
    def test_lookup(self, name):
        c = V1_CONTRACT_PROFILE.get_contract(name)
        assert c is not None
        assert c.marker_name == name

    def test_unknown(self):
        assert V1_CONTRACT_PROFILE.get_contract("nonexistent") is None


class TestContractMatchesFrozen:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_identity_hash(self, marker):
        c = V1_CONTRACT_PROFILE.get_contract(marker.name)
        assert c.expected_identity_hash == marker.identity_hash

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    def test_structural_class(self, marker):
        c = V1_CONTRACT_PROFILE.get_contract(marker.name)
        assert c.expected_structural_class == marker.structural_class

    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_facet_hash(self, marker, vp):
        c = V1_CONTRACT_PROFILE.get_contract(marker.name)
        expected_fh = c.get_expected_facet_hash(vp)
        actual_facet = marker.get_facet(vp)
        assert expected_fh == actual_facet.facet_hash


class TestValidRecovery:
    @pytest.mark.parametrize("marker", FROZEN_MARKER_FAMILY, ids=FROZEN_MARKER_NAMES)
    @pytest.mark.parametrize("vp", ALL_VIEWPOINTS)
    def test_valid(self, marker, vp):
        obs = generate_observation(marker, vp)
        recovery = recover_full(obs)
        result = validate_recovery(recovery)
        assert result.verdict == ContractVerdict.VALID
        assert result.identity_check is True
        assert result.viewpoint_check is True
        assert result.facet_check is True


class TestBatchValidation:
    def test_all_valid(self):
        results = validate_all_recoveries()
        assert len(results) == EXPECTED_VALID_COUNT
        assert all(r.verdict == ContractVerdict.VALID for r in results)


class TestViolationIncomplete:
    def test_incomplete(self):
        r = validate_recovery(make_incomplete_recovery())
        assert r.verdict == ContractVerdict.RECOVERY_INCOMPLETE


class TestViolationUnknown:
    def test_unknown(self):
        r = validate_recovery(make_unknown_marker_recovery())
        assert r.verdict == ContractVerdict.UNKNOWN_MARKER


class TestViolationIdentity:
    def test_mismatch(self):
        r = validate_recovery(make_identity_mismatch_recovery())
        assert r.verdict == ContractVerdict.INVALID_IDENTITY
        assert r.identity_check is False


class TestViolationFacet:
    def test_mismatch(self):
        r = validate_recovery(make_facet_mismatch_recovery())
        assert r.verdict == ContractVerdict.INVALID_FACET
        assert r.identity_check is True
        assert r.facet_check is False


class TestSerialization:
    def test_validation_to_dict(self):
        obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
        recovery = recover_full(obs)
        result = validate_recovery(recovery)
        d = result.to_dict()
        assert d["verdict"] == "VALID"
        assert d["version"] == CONTRACT_VERSION

    def test_profile_to_dict(self):
        d = V1_CONTRACT_PROFILE.to_dict()
        assert d["contract_count"] == EXPECTED_CONTRACT_COUNT

    def test_contract_to_dict(self):
        c = V1_CONTRACT_PROFILE.contracts[0]
        d = c.to_dict()
        assert d["marker_name"] == "alpha_planar"


class TestImmutability:
    def test_result_immutable(self):
        obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
        recovery = recover_full(obs)
        result = validate_recovery(recovery)
        with pytest.raises((AttributeError, TypeError)):
            result.verdict = ContractVerdict.ERROR
