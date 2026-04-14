"""
Pytest test suite — Temporal Payload Signature Bridge V1 (26th bridge)

Tests the bounded temporal fingerprint proof.

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

from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION,
    SIGNATURE_FROZEN,
    SignatureVerdict,
    TemporalSignatureProfile,
    V1_SIGNATURE_PROFILE,
    TemporalSignatureResult,
    compute_temporal_signature,
    sign_temporal_payload,
    sign_from_contract_result,
    SIGN_CASES,
    REJECT_CASES,
    OOB_CASES,
    DIFFERENCE_CASES,
)

from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    validate_temporal_contract,
    ContractVerdict,
)


class TestModuleConstants:
    def test_version(self):
        assert SIGNATURE_VERSION == "V1.0"

    def test_frozen(self):
        assert SIGNATURE_FROZEN is True


class TestVerdictEnum:
    def test_all_verdicts(self):
        expected = ["SIGNED", "CONTRACT_NOT_SATISFIED", "EMPTY_PAYLOAD",
                    "UNSUPPORTED_CONTRACT", "ERROR"]
        for v in expected:
            assert hasattr(SignatureVerdict, v)

    def test_count(self):
        assert len(SignatureVerdict) == 5


class TestProfile:
    def test_canonical_fields(self):
        assert len(V1_SIGNATURE_PROFILE.canonical_fields) == 6

    def test_hash_algorithm(self):
        assert V1_SIGNATURE_PROFILE.hash_algorithm == "sha256"

    def test_immutable(self):
        with pytest.raises(Exception):
            V1_SIGNATURE_PROFILE.version = "other"


class TestResultDefaults:
    def test_defaults(self):
        r = TemporalSignatureResult()
        assert r.verdict == SignatureVerdict.ERROR
        assert r.temporal_signature == ""
        assert r.payload == ()

    def test_serialization(self):
        r = TemporalSignatureResult(
            verdict=SignatureVerdict.SIGNED,
            temporal_signature="abc",
            contract_name="test",
        )
        d = r.to_dict()
        assert d["verdict"] == "SIGNED"
        assert isinstance(json.dumps(d), str)


class TestRawSignature:
    def test_deterministic(self):
        a = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        b = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        assert a == b
        assert len(a) == 64

    def test_different_payload(self):
        a = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        b = compute_temporal_signature("t", (0, 1, 1, 0), "adj", "rs", False)
        assert a != b

    def test_different_family(self):
        a = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        b = compute_temporal_signature("t", (0, 0, 1, 0), "cont", "rs", False)
        assert a != b

    def test_different_mode(self):
        a = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        b = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "cc", False)
        assert a != b

    def test_different_fused(self):
        a = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", False)
        b = compute_temporal_signature("t", (0, 0, 1, 0), "adj", "rs", True)
        assert a != b


class TestSignCases:
    @pytest.mark.parametrize("case", SIGN_CASES, ids=lambda c: c["label"])
    def test_signed(self, case):
        result = sign_temporal_payload(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == SignatureVerdict.SIGNED
        assert len(result.temporal_signature) == 64
        assert result.payload_length > 0
        assert result.contract_verdict == "CONTRACT_SATISFIED"


class TestRejectCases:
    @pytest.mark.parametrize("case", REJECT_CASES, ids=lambda c: c["label"])
    def test_rejected(self, case):
        result = sign_temporal_payload(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED
        assert result.temporal_signature == ""


class TestOOBCases:
    @pytest.mark.parametrize("case", OOB_CASES, ids=lambda c: c["label"])
    def test_oob(self, case):
        result = sign_temporal_payload(
            tuple(case["payload"]), case["contract"], case["mode"],
        )
        assert result.verdict == SignatureVerdict[case["expected_verdict"]]


class TestDifferenceCases:
    @pytest.mark.parametrize("case", DIFFERENCE_CASES, ids=lambda c: c["label"])
    def test_different_sigs(self, case):
        r_a = sign_temporal_payload(
            tuple(case["payload_a"]), case["contract_a"], case["mode_a"],
        )
        r_b = sign_temporal_payload(
            tuple(case["payload_b"]), case["contract_b"], case["mode_b"],
        )
        assert r_a.verdict == SignatureVerdict.SIGNED
        assert r_b.verdict == SignatureVerdict.SIGNED
        assert r_a.temporal_signature != r_b.temporal_signature


class TestDeterminism:
    def test_repeated(self):
        for _ in range(3):
            r1 = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
            r2 = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
            assert r1.temporal_signature == r2.temporal_signature


class TestSignatureDistinctness:
    def test_all_unique(self):
        sigs = set()
        for case in SIGN_CASES:
            result = sign_temporal_payload(
                tuple(case["payload"]), case["contract"], case["mode"],
            )
            sigs.add(result.temporal_signature)
        assert len(sigs) == len(SIGN_CASES)


class TestFromContractResult:
    def test_satisfied(self):
        cr = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        sr = sign_from_contract_result(cr)
        assert sr.verdict == SignatureVerdict.SIGNED
        assert len(sr.temporal_signature) == 64

    def test_failed(self):
        cr = validate_temporal_contract((0, 1, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        sr = sign_from_contract_result(cr)
        assert sr.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED

    def test_matches_e2e(self):
        cr = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        sr = sign_from_contract_result(cr)
        r_e2e = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        assert sr.temporal_signature == r_e2e.temporal_signature


class TestCrossMode:
    def test_different_modes_different_sigs(self):
        r_rs = sign_temporal_payload((0, 1, 1, 0), "either_containment", "rolling_shutter")
        r_cc = sign_temporal_payload((0, 1, 1, 0), "either_containment", "complementary_color")
        r_fused = sign_temporal_payload((0, 1, 1, 0), "either_containment", "fused")
        assert r_rs.verdict == SignatureVerdict.SIGNED
        assert r_cc.verdict == SignatureVerdict.SIGNED
        assert r_fused.verdict == SignatureVerdict.SIGNED
        sigs = {r_rs.temporal_signature, r_cc.temporal_signature, r_fused.temporal_signature}
        assert len(sigs) == 3


class TestJSONRoundTrip:
    def test_full(self):
        result = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
        d = result.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["verdict"] == "SIGNED"
        assert len(d2["temporal_signature"]) == 64


class TestPredefinedCounts:
    def test_sign_count(self):
        assert len(SIGN_CASES) == 6

    def test_reject_count(self):
        assert len(REJECT_CASES) == 3

    def test_oob_count(self):
        assert len(OOB_CASES) == 2

    def test_difference_count(self):
        assert len(DIFFERENCE_CASES) == 3
