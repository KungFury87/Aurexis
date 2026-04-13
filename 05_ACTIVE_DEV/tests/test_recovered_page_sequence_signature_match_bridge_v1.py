"""
Pytest tests for Recovered Page Sequence Signature Match Bridge V1.

Proves that a computed sequence-level signature can be compared against a
frozen expected-sequence-signature baseline and return an honest deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-sequence match proof, not general
document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest

from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SEQ_MATCH_VERSION, SEQ_MATCH_FROZEN,
    SeqMatchVerdict, SeqMatchResult,
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
    match_sequence_signature, match_sequence_signature_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SeqSigVerdict, sign_sequence_from_contracts,
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceContract, FROZEN_SEQUENCE_CONTRACTS,
    generate_sequence_host_pngs,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    _get_expected_signatures,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def expected_seq_sigs():
    return _get_expected_seq_sigs()


@pytest.fixture(scope="module")
def all_host_pngs():
    result = {}
    for sc in FROZEN_SEQUENCE_CONTRACTS:
        result[sc.name] = generate_sequence_host_pngs(sc)
    return result


# ── Module Constants ──────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert SEQ_MATCH_VERSION == "V1.0"

    def test_frozen(self):
        assert SEQ_MATCH_FROZEN is True

    def test_baseline_type(self):
        assert isinstance(V1_SEQ_MATCH_BASELINE, ExpectedSequenceSignatureBaseline)

    def test_baseline_version(self):
        assert V1_SEQ_MATCH_BASELINE.version == "V1.0"

    def test_baseline_contract_count(self):
        assert len(V1_SEQ_MATCH_BASELINE.supported_sequence_contracts) == 3

    def test_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 3
        assert len(WRONG_COUNT_CASES) == 2
        assert len(WRONG_ORDER_CASES) == 2
        assert len(UNSUPPORTED_CASES) == 1


# ── Baseline Validation ──────────────────────────────────

class TestBaselineValidation:
    def test_has_3_sigs(self, expected_seq_sigs):
        assert len(expected_seq_sigs) == 3

    def test_all_sha256_len(self, expected_seq_sigs):
        for v in expected_seq_sigs.values():
            assert len(v) == 64

    def test_all_unique(self, expected_seq_sigs):
        assert len(set(expected_seq_sigs.values())) == 3

    @pytest.mark.parametrize("sc", FROZEN_SEQUENCE_CONTRACTS,
                             ids=[sc.name for sc in FROZEN_SEQUENCE_CONTRACTS])
    def test_supports_frozen_contract(self, sc):
        assert V1_SEQ_MATCH_BASELINE.is_supported(sc.name)

    def test_rejects_unknown(self):
        assert not V1_SEQ_MATCH_BASELINE.is_supported("nonexistent")

    def test_frozen_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            V1_SEQ_MATCH_BASELINE.version = "hacked"  # type: ignore


# ── In-Bounds Match ──────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=[c["label"] for c in IN_BOUNDS_CASES])
class TestInBoundsMatch:
    def test_verdict_match(self, case, all_host_pngs):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        mr = match_sequence_signature(all_host_pngs[sc.name], sc)
        assert mr.verdict == SeqMatchVerdict.MATCH

    def test_sig_equals_expected(self, case, all_host_pngs):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        mr = match_sequence_signature(all_host_pngs[sc.name], sc)
        assert mr.computed_sequence_signature == mr.expected_sequence_signature

    def test_from_contracts(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        mr = match_sequence_signature_from_contracts(sc)
        assert mr.verdict == SeqMatchVerdict.MATCH


# ── Stability ────────────────────────────────────────────

@pytest.mark.parametrize("sc", FROZEN_SEQUENCE_CONTRACTS,
                         ids=[sc.name for sc in FROZEN_SEQUENCE_CONTRACTS])
class TestStability:
    def test_verdict_stable(self, sc):
        mr1 = match_sequence_signature_from_contracts(sc)
        mr2 = match_sequence_signature_from_contracts(sc)
        assert mr1.verdict == mr2.verdict

    def test_sig_stable(self, sc):
        mr1 = match_sequence_signature_from_contracts(sc)
        mr2 = match_sequence_signature_from_contracts(sc)
        assert mr1.computed_sequence_signature == mr2.computed_sequence_signature


# ── Wrong Page Count ─────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                         ids=[c["label"] for c in WRONG_COUNT_CASES])
class TestWrongCount:
    def test_verdict_sign_failed(self, case, all_host_pngs):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        pngs = all_host_pngs[sc.name]
        provide = case["provide_page_count"]
        if provide < len(pngs):
            test_pngs = pngs[:provide]
        else:
            test_pngs = pngs + (pngs[-1],) * (provide - len(pngs))
        mr = match_sequence_signature(test_pngs, sc)
        assert mr.verdict == SeqMatchVerdict.SIGN_FAILED


# ── Wrong Page Order ─────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                         ids=[c["label"] for c in WRONG_ORDER_CASES])
class TestWrongOrder:
    def test_verdict_sign_failed(self, case, all_host_pngs):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        pngs = all_host_pngs[sc.name]
        mr = match_sequence_signature(tuple(reversed(pngs)), sc)
        assert mr.verdict == SeqMatchVerdict.SIGN_FAILED


# ── Unsupported ──────────────────────────────────────────

@pytest.mark.parametrize("case", UNSUPPORTED_CASES,
                         ids=[c["label"] for c in UNSUPPORTED_CASES])
class TestUnsupported:
    def test_verdict_unsupported(self, case, all_host_pngs):
        fake = SequenceContract(
            name=case["contract_name"],
            expected_page_count=2,
            page_contract_names=("a", "b"),
        )
        sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
        mr = match_sequence_signature(all_host_pngs[sc0.name], fake)
        assert mr.verdict == SeqMatchVerdict.UNSUPPORTED


# ── Cross-Contract Distinctness ──────────────────────────

class TestDistinctness:
    def test_all_distinct(self):
        sigs = []
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            mr = match_sequence_signature_from_contracts(sc)
            sigs.append(mr.computed_sequence_signature)
        assert len(set(sigs)) == len(sigs)


# ── Serialization ────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("sc", FROZEN_SEQUENCE_CONTRACTS,
                             ids=[sc.name for sc in FROZEN_SEQUENCE_CONTRACTS])
    def test_to_dict(self, sc):
        mr = match_sequence_signature_from_contracts(sc)
        d = mr.to_dict()
        assert d["verdict"] == "MATCH"
        assert d["computed_sequence_signature"] == mr.computed_sequence_signature
        assert d["sequence_contract_name"] == sc.name
        assert len(d["page_signatures"]) == sc.expected_page_count
        assert d["version"] == "V1.0"


# ── Baseline Consistency ─────────────────────────────────

class TestBaselineConsistency:
    def test_matches_bridge_expected(self):
        bridge_expected = _get_expected_seq_sigs()
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            baseline_sig = V1_SEQ_MATCH_BASELINE.get_expected(sc.name)
            assert baseline_sig == bridge_expected[sc.name]

    def test_match_sig_equals_sign_sig(self):
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            mr = match_sequence_signature_from_contracts(sc)
            sr = sign_sequence_from_contracts(sc)
            assert mr.computed_sequence_signature == sr.sequence_signature
