"""
Pytest tests for Recovered Sequence Collection Signature Match Bridge V1.

Proves that a computed collection-level signature can be compared against a
frozen expected-collection-signature baseline and return an honest deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-collection match proof, not general
archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest

from aurexis_lang.recovered_sequence_collection_signature_match_bridge_v1 import (
    COLL_MATCH_VERSION, COLL_MATCH_FROZEN,
    CollMatchVerdict, CollMatchResult,
    ExpectedCollectionSignatureBaseline, V1_COLL_MATCH_BASELINE,
    match_collection_signature, match_collection_signature_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    CollSigVerdict,
    sign_collection_from_contracts,
    _get_expected_coll_sigs,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionContract,
    FROZEN_COLLECTION_CONTRACTS,
    generate_collection_host_png_groups,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    _get_expected_seq_sigs,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def expected_coll_sigs():
    return _get_expected_coll_sigs()


@pytest.fixture(scope="module")
def expected_seq_sigs():
    return _get_expected_seq_sigs()


# ── Module Constants ──────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert COLL_MATCH_VERSION == "V1.0"

    def test_frozen(self):
        assert COLL_MATCH_FROZEN is True

    def test_baseline_type(self):
        assert isinstance(V1_COLL_MATCH_BASELINE, ExpectedCollectionSignatureBaseline)

    def test_baseline_version(self):
        assert V1_COLL_MATCH_BASELINE.version == "V1.0"

    def test_baseline_contracts(self):
        assert len(V1_COLL_MATCH_BASELINE.supported_collection_contracts) == 3


# ── Baseline Validation ──────────────────────────────────

class TestBaselineValidation:
    def test_has_3_signatures(self, expected_coll_sigs):
        assert len(expected_coll_sigs) == 3

    def test_all_sha256_len(self, expected_coll_sigs):
        for v in expected_coll_sigs.values():
            assert len(v) == 64

    def test_all_unique(self, expected_coll_sigs):
        assert len(set(expected_coll_sigs.values())) == 3

    def test_supports_all_frozen(self):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            assert V1_COLL_MATCH_BASELINE.is_supported(cc.name)

    def test_rejects_unknown(self):
        assert not V1_COLL_MATCH_BASELINE.is_supported("nonexistent")

    def test_frozen_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            V1_COLL_MATCH_BASELINE.version = "hacked"  # type: ignore

    def test_get_expected_valid(self, expected_coll_sigs):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            sig = V1_COLL_MATCH_BASELINE.get_expected(cc.name)
            assert sig == expected_coll_sigs[cc.name]

    def test_get_expected_unknown(self):
        assert V1_COLL_MATCH_BASELINE.get_expected("unknown") is None


# ── In-Bounds Match ──────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=[c["label"] for c in IN_BOUNDS_CASES])
class TestInBounds:
    def test_verdict_match(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        mr = match_collection_signature_from_contracts(cc)
        assert mr.verdict == CollMatchVerdict.MATCH

    def test_sig_nonempty(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        mr = match_collection_signature_from_contracts(cc)
        assert len(mr.computed_collection_signature) == 64

    def test_sigs_equal(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        mr = match_collection_signature_from_contracts(cc)
        assert mr.computed_collection_signature == mr.expected_collection_signature


# ── Stability ─────────────────────────────────────────────

@pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                         ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
class TestStability:
    def test_sig_stable(self, cc):
        mr1 = match_collection_signature_from_contracts(cc)
        mr2 = match_collection_signature_from_contracts(cc)
        assert mr1.computed_collection_signature == mr2.computed_collection_signature

    def test_verdict_stable(self, cc):
        mr1 = match_collection_signature_from_contracts(cc)
        mr2 = match_collection_signature_from_contracts(cc)
        assert mr1.verdict == mr2.verdict


# ── Wrong Sequence Count ──────────────────────────────────

@pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                         ids=[c["label"] for c in WRONG_COUNT_CASES])
class TestWrongCount:
    def test_verdict_sign_failed(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = generate_collection_host_png_groups(cc)
        provide = case["provide_count"]
        if provide < len(groups):
            test_groups = groups[:provide]
        else:
            test_groups = groups + (groups[-1],) * (provide - len(groups))
        mr = match_collection_signature(test_groups, cc)
        assert mr.verdict == CollMatchVerdict.SIGN_FAILED


# ── Wrong Sequence Order ──────────────────────────────────

@pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                         ids=[c["label"] for c in WRONG_ORDER_CASES])
class TestWrongOrder:
    def test_verdict_sign_failed(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = generate_collection_host_png_groups(cc)
        mr = match_collection_signature(tuple(reversed(groups)), cc)
        assert mr.verdict == CollMatchVerdict.SIGN_FAILED


# ── Unsupported ───────────────────────────────────────────

@pytest.mark.parametrize("case", UNSUPPORTED_CASES,
                         ids=[c["label"] for c in UNSUPPORTED_CASES])
class TestUnsupported:
    def test_verdict_unsupported(self, case):
        fake = CollectionContract(
            name=case["contract_name"],
            expected_sequence_count=2,
            sequence_contract_names=("a", "b"),
        )
        cc0 = FROZEN_COLLECTION_CONTRACTS[0]
        groups = generate_collection_host_png_groups(cc0)
        mr = match_collection_signature(groups, fake)
        assert mr.verdict == CollMatchVerdict.UNSUPPORTED


# ── Cross-Collection Distinctness ─────────────────────────

class TestDistinctness:
    def test_all_distinct(self):
        sigs = []
        for cc in FROZEN_COLLECTION_CONTRACTS:
            mr = match_collection_signature_from_contracts(cc)
            sigs.append(mr.computed_collection_signature)
        assert len(set(sigs)) == len(sigs)


# ── Serialization ─────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_to_dict(self, cc):
        mr = match_collection_signature_from_contracts(cc)
        d = mr.to_dict()
        assert d["verdict"] == "MATCH"
        assert d["computed_collection_signature"] == mr.computed_collection_signature
        assert d["collection_contract_name"] == cc.name
        assert len(d["sequence_signatures"]) == cc.expected_sequence_count


# ── Baseline Consistency ──────────────────────────────────

class TestBaselineConsistency:
    def test_match_baseline_equals_bridge(self, expected_coll_sigs):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            assert V1_COLL_MATCH_BASELINE.get_expected(cc.name) == expected_coll_sigs[cc.name]

    def test_match_sig_equals_sign_sig(self):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            mr = match_collection_signature_from_contracts(cc)
            sr = sign_collection_from_contracts(cc)
            assert mr.computed_collection_signature == sr.collection_signature

    def test_seq_sigs_from_per_sequence_baseline(self, expected_seq_sigs):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            mr = match_collection_signature_from_contracts(cc)
            for i, seq_name in enumerate(cc.sequence_contract_names):
                assert mr.sequence_signatures[i] == expected_seq_sigs[seq_name]
