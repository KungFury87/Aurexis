"""
Pytest suite — Temporal Payload Signature Match Bridge V1

27th bridge (9th temporal transport milestone).
Bounded expected-temporal-signature verification proof.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import json
import pytest

from aurexis_lang.temporal_payload_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    TemporalMatchVerdict, TemporalMatchResult,
    ExpectedTemporalSignatureBaseline, V1_MATCH_BASELINE,
    match_temporal_signature, match_from_signature_result,
    _get_expected_temporal_signatures,
    MATCH_CASES, MISMATCH_CASES, SIGN_FAIL_CASES,
    UNSUPPORTED_CASES, OOB_CASES,
)
from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION, SignatureVerdict,
    sign_temporal_payload, SIGN_CASES,
)


# ════════════════════════════════════════════════════════════
# Module constants
# ════════════════════════════════════════════════════════════

class TestModuleConstants:

    def test_match_version(self):
        assert MATCH_VERSION == "V1.0"

    def test_match_frozen(self):
        assert MATCH_FROZEN is True

    def test_baseline_type(self):
        assert isinstance(V1_MATCH_BASELINE, ExpectedTemporalSignatureBaseline)


# ════════════════════════════════════════════════════════════
# Match verdict enum
# ════════════════════════════════════════════════════════════

class TestMatchVerdict:

    def test_all_verdicts_present(self):
        expected = {"MATCH", "MISMATCH", "UNSUPPORTED", "SIGN_FAILED", "EMPTY_PAYLOAD", "ERROR"}
        actual = {v.value for v in TemporalMatchVerdict}
        assert actual == expected

    @pytest.mark.parametrize("v", ["MATCH", "MISMATCH", "UNSUPPORTED", "SIGN_FAILED", "EMPTY_PAYLOAD", "ERROR"])
    def test_verdict_round_trip(self, v):
        assert TemporalMatchVerdict(v).value == v


# ════════════════════════════════════════════════════════════
# Expected baseline structure
# ════════════════════════════════════════════════════════════

class TestBaselineStructure:

    def test_baseline_version(self):
        assert V1_MATCH_BASELINE.version == "V1.0"

    def test_baseline_supported_count(self):
        assert len(V1_MATCH_BASELINE.supported_cases) == 6

    @pytest.mark.parametrize("case", SIGN_CASES, ids=[c["label"] for c in SIGN_CASES])
    def test_baseline_supports_sign_case(self, case):
        assert V1_MATCH_BASELINE.is_supported(case["label"])

    def test_baseline_rejects_nonexistent(self):
        assert not V1_MATCH_BASELINE.is_supported("nonexistent")

    def test_baseline_rejects_empty(self):
        assert not V1_MATCH_BASELINE.is_supported("")


# ════════════════════════════════════════════════════════════
# Expected signature generation
# ════════════════════════════════════════════════════════════

class TestExpectedSignatures:

    def test_exactly_6_signatures(self):
        sigs = _get_expected_temporal_signatures()
        assert len(sigs) == 6

    def test_all_sigs_valid_hex(self):
        sigs = _get_expected_temporal_signatures()
        for label, sig in sigs.items():
            assert isinstance(sig, str)
            assert len(sig) == 64
            assert all(c in "0123456789abcdef" for c in sig)

    def test_all_sigs_distinct(self):
        sigs = _get_expected_temporal_signatures()
        vals = list(sigs.values())
        assert len(vals) == len(set(vals))


# ════════════════════════════════════════════════════════════
# Match cases — E2E
# ════════════════════════════════════════════════════════════

class TestMatchCases:

    @pytest.mark.parametrize("case", MATCH_CASES, ids=[c["label"] for c in MATCH_CASES])
    def test_match_verdict(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        assert mr.verdict == TemporalMatchVerdict.MATCH

    @pytest.mark.parametrize("case", MATCH_CASES, ids=[c["label"] for c in MATCH_CASES])
    def test_match_sigs_equal(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        assert mr.computed_signature == mr.expected_signature
        assert len(mr.computed_signature) == 64


# ════════════════════════════════════════════════════════════
# Mismatch cases
# ════════════════════════════════════════════════════════════

class TestMismatchCases:

    @pytest.mark.parametrize("case", MISMATCH_CASES, ids=[c["label"] for c in MISMATCH_CASES])
    def test_mismatch_verdict(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert mr.verdict == TemporalMatchVerdict.MISMATCH

    @pytest.mark.parametrize("case", MISMATCH_CASES, ids=[c["label"] for c in MISMATCH_CASES])
    def test_mismatch_sigs_differ(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert mr.computed_signature != mr.expected_signature
        assert len(mr.computed_signature) == 64
        assert len(mr.expected_signature) == 64


# ════════════════════════════════════════════════════════════
# Sign-fail cases
# ════════════════════════════════════════════════════════════

class TestSignFailCases:

    @pytest.mark.parametrize("case", SIGN_FAIL_CASES, ids=[c["label"] for c in SIGN_FAIL_CASES])
    def test_sign_fail_verdict(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert mr.verdict == TemporalMatchVerdict.SIGN_FAILED


# ════════════════════════════════════════════════════════════
# Unsupported cases
# ════════════════════════════════════════════════════════════

class TestUnsupportedCases:

    @pytest.mark.parametrize("case", UNSUPPORTED_CASES, ids=[c["label"] for c in UNSUPPORTED_CASES])
    def test_unsupported_verdict(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert mr.verdict == TemporalMatchVerdict.UNSUPPORTED


# ════════════════════════════════════════════════════════════
# OOB cases
# ════════════════════════════════════════════════════════════

class TestOOBCases:

    @pytest.mark.parametrize("case", OOB_CASES, ids=[c["label"] for c in OOB_CASES])
    def test_oob_verdict(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert mr.verdict == TemporalMatchVerdict.EMPTY_PAYLOAD


# ════════════════════════════════════════════════════════════
# Determinism
# ════════════════════════════════════════════════════════════

class TestDeterminism:

    @pytest.mark.parametrize("case", list(MATCH_CASES)[:3], ids=[c["label"] for c in list(MATCH_CASES)[:3]])
    def test_repeated_runs_same_signature(self, case):
        results = set()
        for _ in range(3):
            mr = match_temporal_signature(
                payload=case["payload"],
                contract_name=case["contract"],
                case_label=case["label"],
                transport_mode=case["mode"],
            )
            results.add(mr.computed_signature)
        assert len(results) == 1


# ════════════════════════════════════════════════════════════
# Convenience path
# ════════════════════════════════════════════════════════════

class TestConveniencePath:

    @pytest.mark.parametrize("case", MATCH_CASES, ids=[c["label"] for c in MATCH_CASES])
    def test_convenience_match(self, case):
        sr = sign_temporal_payload(
            payload=case["payload"],
            contract_name=case["contract"],
            transport_mode=case["mode"],
        )
        assert sr.verdict == SignatureVerdict.SIGNED
        mr = match_from_signature_result(sr, case["label"])
        assert mr.verdict == TemporalMatchVerdict.MATCH
        assert mr.computed_signature == mr.expected_signature

    def test_convenience_sign_failed(self):
        sr = sign_temporal_payload(
            payload=(0, 0, 1, 0),
            contract_name="rs_4bit_adjacent",
            transport_mode="complementary_color",
        )
        mr = match_from_signature_result(sr, "rs_4bit_adj_sign")
        assert mr.verdict == TemporalMatchVerdict.SIGN_FAILED

    def test_convenience_unsupported_label(self):
        sr = sign_temporal_payload(
            payload=(0, 0, 1, 0),
            contract_name="rs_4bit_adjacent",
            transport_mode="rolling_shutter",
        )
        mr = match_from_signature_result(sr, "nonexistent_label")
        assert mr.verdict == TemporalMatchVerdict.UNSUPPORTED


# ════════════════════════════════════════════════════════════
# Serialization
# ════════════════════════════════════════════════════════════

class TestSerialization:

    @pytest.mark.parametrize("case", list(MATCH_CASES)[:2], ids=[c["label"] for c in list(MATCH_CASES)[:2]])
    def test_json_round_trip(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        d = mr.to_dict()
        assert d["verdict"] == "MATCH"
        j = json.dumps(d)
        d2 = json.loads(j)
        assert d2 == d


# ════════════════════════════════════════════════════════════
# Cross-path consistency
# ════════════════════════════════════════════════════════════

class TestCrossPathConsistency:

    @pytest.mark.parametrize("case", MATCH_CASES, ids=[c["label"] for c in MATCH_CASES])
    def test_e2e_vs_convenience_same_result(self, case):
        mr_e2e = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        sr = sign_temporal_payload(
            payload=case["payload"],
            contract_name=case["contract"],
            transport_mode=case["mode"],
        )
        mr_conv = match_from_signature_result(sr, case["label"])
        assert mr_e2e.verdict == mr_conv.verdict
        assert mr_e2e.computed_signature == mr_conv.computed_signature


# ════════════════════════════════════════════════════════════
# Case counts
# ════════════════════════════════════════════════════════════

class TestCaseCounts:

    def test_match_cases_count(self):
        assert len(MATCH_CASES) == 6

    def test_mismatch_cases_count(self):
        assert len(MISMATCH_CASES) == 3

    def test_sign_fail_cases_count(self):
        assert len(SIGN_FAIL_CASES) == 2

    def test_unsupported_cases_count(self):
        assert len(UNSUPPORTED_CASES) == 2

    def test_oob_cases_count(self):
        assert len(OOB_CASES) == 1
