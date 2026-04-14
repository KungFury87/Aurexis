"""
Pytest tests for Recovered Sequence Collection Contract Bridge V1.

Proves that a small ordered collection of recovered page sequences can be
validated against a frozen collection-level contract, with honest failure
for wrong count, wrong order, wrong content, and unsupported collections.

This is a narrow deterministic recovered-collection proof, not general
archive management or open-ended multi-sequence intelligence.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest

from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionVerdict, CollectionResult,
    CollectionContract, CollectionProfile,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    validate_collection, validate_collection_from_contracts,
    generate_collection_host_png_groups,
    _get_collection_expected,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, WRONG_CONTENT_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SeqMatchVerdict,
    match_sequence_signature_from_contracts,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    FROZEN_SEQUENCE_CONTRACTS,
    generate_sequence_host_pngs,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def coll_expected():
    return _get_collection_expected()


@pytest.fixture(scope="module")
def all_groups():
    result = {}
    for cc in FROZEN_COLLECTION_CONTRACTS:
        result[cc.name] = generate_collection_host_png_groups(cc)
    return result


# ── Module Constants ──────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert COLLECTION_VERSION == "V1.0"

    def test_frozen(self):
        assert COLLECTION_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_COLLECTION_PROFILE, CollectionProfile)

    def test_profile_count(self):
        assert len(V1_COLLECTION_PROFILE.contracts) == 3

    def test_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 3
        assert len(WRONG_COUNT_CASES) == 2
        assert len(WRONG_ORDER_CASES) == 2
        assert len(WRONG_CONTENT_CASES) == 1
        assert len(UNSUPPORTED_CASES) == 1


# ── Frozen Contract Definitions ──────────────────────────

class TestFrozenContracts:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_immutable(self, cc):
        with pytest.raises((AttributeError, TypeError)):
            cc.name = "hacked"  # type: ignore

    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_get_sequence_contract(self, cc):
        for i in range(cc.expected_sequence_count):
            assert cc.get_sequence_contract(i) is not None
        assert cc.get_sequence_contract(-1) is None
        assert cc.get_sequence_contract(cc.expected_sequence_count) is None


# ── Expected Collection Signatures ───────────────────────

class TestExpectedSignatures:
    def test_count(self, coll_expected):
        assert len(coll_expected) == 3

    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_sig_count_matches(self, cc, coll_expected):
        assert len(coll_expected[cc.name]) == cc.expected_sequence_count


# ── In-Bounds Validation ─────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES,
                         ids=[c["label"] for c in IN_BOUNDS_CASES])
class TestInBounds:
    def test_verdict_satisfied(self, case, all_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = validate_collection(all_groups[cc.name], cc)
        assert cr.verdict == CollectionVerdict.COLLECTION_SATISFIED

    def test_sigs_match(self, case, all_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = validate_collection(all_groups[cc.name], cc)
        assert cr.sequence_signatures == cr.expected_sequence_signatures

    def test_from_contracts(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = validate_collection_from_contracts(cc)
        assert cr.verdict == CollectionVerdict.COLLECTION_SATISFIED


# ── Stability ────────────────────────────────────────────

@pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                         ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
class TestStability:
    def test_verdict_stable(self, cc):
        cr1 = validate_collection_from_contracts(cc)
        cr2 = validate_collection_from_contracts(cc)
        assert cr1.verdict == cr2.verdict

    def test_sigs_stable(self, cc):
        cr1 = validate_collection_from_contracts(cc)
        cr2 = validate_collection_from_contracts(cc)
        assert cr1.sequence_signatures == cr2.sequence_signatures


# ── Wrong Count ──────────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                         ids=[c["label"] for c in WRONG_COUNT_CASES])
class TestWrongCount:
    def test_verdict(self, case, all_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = all_groups[cc.name]
        provide = case["provide_count"]
        if provide < len(groups):
            test_groups = groups[:provide]
        else:
            test_groups = groups + (groups[-1],) * (provide - len(groups))
        cr = validate_collection(test_groups, cc)
        assert cr.verdict == CollectionVerdict.WRONG_SEQUENCE_COUNT


# ── Wrong Order ──────────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                         ids=[c["label"] for c in WRONG_ORDER_CASES])
class TestWrongOrder:
    def test_verdict(self, case, all_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = all_groups[cc.name]
        cr = validate_collection(tuple(reversed(groups)), cc)
        assert cr.verdict == CollectionVerdict.WRONG_SEQUENCE_ORDER


# ── Wrong Content ────────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_CONTENT_CASES,
                         ids=[c["label"] for c in WRONG_CONTENT_CASES])
class TestWrongContent:
    def test_verdict(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        sub_groups = []
        for idx in case["substitute_seq_indices"]:
            sc = FROZEN_SEQUENCE_CONTRACTS[idx]
            sub_groups.append(generate_sequence_host_pngs(sc))
        cr = validate_collection(tuple(sub_groups), cc)
        assert cr.verdict == CollectionVerdict.SEQUENCE_MATCH_FAILED


# ── Unsupported ──────────────────────────────────────────

@pytest.mark.parametrize("case", UNSUPPORTED_CASES,
                         ids=[c["label"] for c in UNSUPPORTED_CASES])
class TestUnsupported:
    def test_verdict(self, case, all_groups):
        fake = CollectionContract(
            name=case["contract_name"],
            expected_sequence_count=2,
            sequence_contract_names=("a", "b"),
        )
        groups = all_groups[FROZEN_COLLECTION_CONTRACTS[0].name]
        cr = validate_collection(groups, fake)
        assert cr.verdict == CollectionVerdict.UNSUPPORTED_COLLECTION


# ── Distinctness ─────────────────────────────────────────

class TestDistinctness:
    def test_all_distinct(self):
        sig_tuples = []
        for cc in FROZEN_COLLECTION_CONTRACTS:
            cr = validate_collection_from_contracts(cc)
            sig_tuples.append(cr.sequence_signatures)
        assert len(set(sig_tuples)) == len(sig_tuples)


# ── Serialization ────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_to_dict(self, cc):
        cr = validate_collection_from_contracts(cc)
        d = cr.to_dict()
        assert d["verdict"] == "COLLECTION_SATISFIED"
        assert d["collection_contract_name"] == cc.name
        assert d["version"] == "V1.0"
        assert len(d["sequence_match_results"]) == cc.expected_sequence_count


# ── Baseline Consistency ─────────────────────────────────

class TestBaselineConsistency:
    def test_sigs_match_standalone(self):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            cr = validate_collection_from_contracts(cc)
            for i, seq_name in enumerate(cc.sequence_contract_names):
                sc = next(s for s in FROZEN_SEQUENCE_CONTRACTS
                          if s.name == seq_name)
                standalone = match_sequence_signature_from_contracts(sc)
                assert cr.sequence_signatures[i] == \
                    standalone.computed_sequence_signature
