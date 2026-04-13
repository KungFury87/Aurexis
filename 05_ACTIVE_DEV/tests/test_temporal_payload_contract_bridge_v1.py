"""
Pytest test suite — Temporal Payload Contract Bridge V1 (25th bridge)

Tests the bounded temporal structure validation proof.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import json
import pytest
import sys, os

_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(_here)
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    CONTRACT_VERSION,
    CONTRACT_FROZEN,
    ContractVerdict,
    TemporalContract,
    TemporalContractProfile,
    V1_CONTRACT_PROFILE,
    TemporalContractResult,
    compute_contract_signature,
    validate_temporal_contract,
    FROZEN_CONTRACTS,
    CONTRACT_MAP,
    RS_4BIT_ADJACENT,
    CC_ANY_FAMILY,
    EITHER_CONTAINMENT,
    FUSED_ANY_FAMILY,
    RS_LARGE_THREE_REGIONS,
    SATISFY_CASES,
    WRONG_LENGTH_CASES,
    WRONG_FAMILY_CASES,
    WRONG_MODE_CASES,
    FUSED_REQUIRED_CASES,
    OOB_CASES,
)


class TestModuleConstants:
    def test_version(self):
        assert CONTRACT_VERSION == "V1.0"

    def test_frozen(self):
        assert CONTRACT_FROZEN is True


class TestVerdictEnum:
    def test_all_verdicts(self):
        expected = ["CONTRACT_SATISFIED", "WRONG_PAYLOAD_LENGTH",
                    "WRONG_PAYLOAD_FAMILY", "WRONG_TRANSPORT_MODE",
                    "FUSED_REQUIRED", "DECODE_FAILED", "EMPTY_PAYLOAD",
                    "UNSUPPORTED_CONTRACT", "ERROR"]
        for v in expected:
            assert hasattr(ContractVerdict, v)

    def test_count(self):
        assert len(ContractVerdict) == 9


class TestProfile:
    def test_contract_count(self):
        assert len(V1_CONTRACT_PROFILE.supported_contracts) == 5

    def test_version(self):
        assert V1_CONTRACT_PROFILE.version == "V1.0"

    def test_immutable(self):
        with pytest.raises(Exception):
            V1_CONTRACT_PROFILE.version = "other"


class TestFrozenContracts:
    def test_count(self):
        assert len(FROZEN_CONTRACTS) == 5

    def test_map_count(self):
        assert len(CONTRACT_MAP) == 5

    def test_all_in_map(self):
        for c in FROZEN_CONTRACTS:
            assert c.name in CONTRACT_MAP

    def test_rs_4bit_adjacent(self):
        assert RS_4BIT_ADJACENT.allowed_payload_lengths == (4,)
        assert RS_4BIT_ADJACENT.allowed_payload_families == ("adjacent_pair",)
        assert RS_4BIT_ADJACENT.require_fused is False

    def test_cc_any_family(self):
        assert CC_ANY_FAMILY.allowed_payload_lengths == (3, 4, 5, 6)
        assert len(CC_ANY_FAMILY.allowed_payload_families) == 3

    def test_either_containment(self):
        assert EITHER_CONTAINMENT.allowed_payload_families == ("containment",)
        assert len(EITHER_CONTAINMENT.allowed_transport_modes) == 3

    def test_fused_any_family(self):
        assert FUSED_ANY_FAMILY.require_fused is True
        assert FUSED_ANY_FAMILY.allowed_transport_modes == ("fused",)

    def test_rs_large_three_regions(self):
        assert RS_LARGE_THREE_REGIONS.allowed_payload_lengths == (5, 6, 7, 8)

    def test_contract_immutable(self):
        with pytest.raises(Exception):
            RS_4BIT_ADJACENT.name = "hacked"


class TestContractSerialization:
    @pytest.mark.parametrize("contract", FROZEN_CONTRACTS, ids=lambda c: c.name)
    def test_serializes(self, contract):
        d = contract.to_dict()
        assert isinstance(json.dumps(d), str)
        assert d["name"] == contract.name


class TestResultDefaults:
    def test_defaults(self):
        r = TemporalContractResult()
        assert r.verdict == ContractVerdict.ERROR
        assert r.payload == ()
        assert r.contract_signature == ""

    def test_serialization(self):
        r = TemporalContractResult(
            verdict=ContractVerdict.CONTRACT_SATISFIED,
            contract_name="test",
            payload=(0, 0, 1, 0),
        )
        d = r.to_dict()
        assert d["verdict"] == "CONTRACT_SATISFIED"
        assert isinstance(json.dumps(d), str)


class TestSignature:
    def test_deterministic(self):
        a = compute_contract_signature("CONTRACT_SATISFIED", "test", (0, 0, 1, 0), "adj", "rs")
        b = compute_contract_signature("CONTRACT_SATISFIED", "test", (0, 0, 1, 0), "adj", "rs")
        assert a == b
        assert len(a) == 64

    def test_different_verdicts(self):
        a = compute_contract_signature("CONTRACT_SATISFIED", "test", (0, 0, 1, 0), "adj", "rs")
        b = compute_contract_signature("WRONG_PAYLOAD_LENGTH", "test", (0, 0, 1, 0), "adj", "rs")
        assert a != b


class TestSatisfyCases:
    @pytest.mark.parametrize("case", SATISFY_CASES, ids=lambda c: c["label"])
    def test_satisfied(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict.CONTRACT_SATISFIED
        assert len(result.contract_signature) == 64
        assert result.payload_length > 0
        assert result.payload_family != ""


class TestWrongLengthCases:
    @pytest.mark.parametrize("case", WRONG_LENGTH_CASES, ids=lambda c: c["label"])
    def test_wrong_length(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict.WRONG_PAYLOAD_LENGTH


class TestWrongFamilyCases:
    @pytest.mark.parametrize("case", WRONG_FAMILY_CASES, ids=lambda c: c["label"])
    def test_wrong_family(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict.WRONG_PAYLOAD_FAMILY


class TestWrongModeCases:
    @pytest.mark.parametrize("case", WRONG_MODE_CASES, ids=lambda c: c["label"])
    def test_wrong_mode(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict.WRONG_TRANSPORT_MODE


class TestFusedRequiredCases:
    @pytest.mark.parametrize("case", FUSED_REQUIRED_CASES, ids=lambda c: c["label"])
    def test_fused_required(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict[case["expected_verdict"]]


class TestOOBCases:
    @pytest.mark.parametrize("case", OOB_CASES, ids=lambda c: c["label"])
    def test_oob(self, case):
        result = validate_temporal_contract(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == ContractVerdict[case["expected_verdict"]]


class TestDeterminism:
    def test_repeated_identical(self):
        for _ in range(3):
            r1 = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
            r2 = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
            assert r1.contract_signature == r2.contract_signature
            assert r1.verdict == r2.verdict


class TestSignatureDistinctness:
    def test_all_satisfy_sigs_unique(self):
        sigs = set()
        for case in SATISFY_CASES:
            result = validate_temporal_contract(
                tuple(case["payload"]), case["contract"], case["mode"],
            )
            sigs.add(result.contract_signature)
        assert len(sigs) == len(SATISFY_CASES)


class TestCrossMode:
    def test_same_payload_different_modes(self):
        r_rs = validate_temporal_contract((0, 1, 1, 0), "either_containment", "rolling_shutter")
        r_cc = validate_temporal_contract((0, 1, 1, 0), "either_containment", "complementary_color")
        r_fused = validate_temporal_contract((0, 1, 1, 0), "either_containment", "fused")
        assert r_rs.verdict == ContractVerdict.CONTRACT_SATISFIED
        assert r_cc.verdict == ContractVerdict.CONTRACT_SATISFIED
        assert r_fused.verdict == ContractVerdict.CONTRACT_SATISFIED
        assert r_rs.transport_mode != r_cc.transport_mode
        assert r_fused.is_fused is True


class TestJSONRoundTrip:
    def test_full_result(self):
        result = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        d = result.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["verdict"] == "CONTRACT_SATISFIED"
        assert d2["contract_name"] == "rs_4bit_adjacent"
        assert d2["payload"] == [0, 0, 1, 0]


class TestPredefinedCaseCounts:
    def test_satisfy_count(self):
        assert len(SATISFY_CASES) == 8

    def test_wrong_length_count(self):
        assert len(WRONG_LENGTH_CASES) == 2

    def test_wrong_family_count(self):
        assert len(WRONG_FAMILY_CASES) == 2

    def test_wrong_mode_count(self):
        assert len(WRONG_MODE_CASES) == 2

    def test_fused_required_count(self):
        assert len(FUSED_REQUIRED_CASES) == 2

    def test_oob_count(self):
        assert len(OOB_CASES) == 3
