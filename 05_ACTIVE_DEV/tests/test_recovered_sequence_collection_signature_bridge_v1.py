"""
Pytest tests for Recovered Sequence Collection Signature Bridge V1.

Proves that a validated ordered collection of recovered page sequences
can be reduced to a single deterministic collection-level SHA-256
fingerprint, and that changes in sequence order, sequence content, or
sequence count produce honest signature mismatch.

This is a narrow deterministic recovered-collection identity proof, not
general archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
import hashlib

from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    COLL_SIG_VERSION, COLL_SIG_FROZEN,
    CollectionSignatureProfile, V1_COLL_SIG_PROFILE,
    canonicalize_collection, compute_collection_signature,
    CollSigVerdict, CollSigResult,
    _get_expected_coll_sigs, _build_expected_coll_sig,
    sign_collection, sign_collection_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionVerdict, CollectionContract,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    validate_collection_from_contracts,
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
        assert COLL_SIG_VERSION == "V1.0"

    def test_frozen(self):
        assert COLL_SIG_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_COLL_SIG_PROFILE, CollectionSignatureProfile)

    def test_hash_algorithm(self):
        assert V1_COLL_SIG_PROFILE.hash_algorithm == "sha256"

    def test_canonical_fields(self):
        assert len(V1_COLL_SIG_PROFILE.canonical_fields) == 3
        assert "collection_contract_name" in V1_COLL_SIG_PROFILE.canonical_fields
        assert "sequence_count" in V1_COLL_SIG_PROFILE.canonical_fields
        assert "ordered_sequence_signatures" in V1_COLL_SIG_PROFILE.canonical_fields


# ── Canonicalization ──────────────────────────────────────

class TestCanonicalization:
    def test_valid(self):
        sigs = ("a" * 64, "b" * 64)
        c = canonicalize_collection("test", 2, sigs)
        assert c is not None
        assert "coll_contract=test" in c
        assert "seq_count=2" in c

    def test_count_mismatch(self):
        sigs = ("a" * 64, "b" * 64)
        assert canonicalize_collection("test", 3, sigs) is None

    def test_empty(self):
        assert canonicalize_collection("test", 0, ()) is None

    def test_short_sig(self):
        assert canonicalize_collection("test", 1, ("abc",)) is None

    def test_deterministic(self):
        sigs = ("a" * 64, "b" * 64)
        c1 = canonicalize_collection("test", 2, sigs)
        c2 = canonicalize_collection("test", 2, sigs)
        assert c1 == c2

    def test_different_inputs(self):
        s1 = ("a" * 64, "b" * 64)
        s2 = ("c" * 64, "d" * 64)
        c1 = canonicalize_collection("test", 2, s1)
        c2 = canonicalize_collection("test", 2, s2)
        assert c1 != c2


# ── Signature Computation ─────────────────────────────────

class TestSignatureComputation:
    def test_returns_64_chars(self):
        sig = compute_collection_signature("test")
        assert len(sig) == 64

    def test_matches_stdlib(self):
        sig = compute_collection_signature("test")
        assert sig == hashlib.sha256(b"test").hexdigest()

    def test_deterministic(self):
        s1 = compute_collection_signature("test")
        s2 = compute_collection_signature("test")
        assert s1 == s2

    def test_different_input(self):
        s1 = compute_collection_signature("test1")
        s2 = compute_collection_signature("test2")
        assert s1 != s2


# ── Expected Collection Signatures ────────────────────────

class TestExpectedSignatures:
    def test_count(self, expected_coll_sigs):
        assert len(expected_coll_sigs) == 3

    def test_all_present(self, expected_coll_sigs):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            assert cc.name in expected_coll_sigs

    def test_all_64_chars(self, expected_coll_sigs):
        for sig in expected_coll_sigs.values():
            assert len(sig) == 64

    def test_all_distinct(self, expected_coll_sigs):
        sigs = list(expected_coll_sigs.values())
        assert len(set(sigs)) == len(sigs)

    def test_idempotent(self, expected_coll_sigs):
        sigs2 = _get_expected_coll_sigs()
        for cc in FROZEN_COLLECTION_CONTRACTS:
            assert expected_coll_sigs[cc.name] == sigs2[cc.name]


# ── In-Bounds Signing ─────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=[c["label"] for c in IN_BOUNDS_CASES])
class TestInBounds:
    def test_verdict_match(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        r = sign_collection_from_contracts(cc)
        assert r.verdict == CollSigVerdict.MATCH

    def test_sig_nonempty(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        r = sign_collection_from_contracts(cc)
        assert len(r.collection_signature) == 64

    def test_sig_equals_expected(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        r = sign_collection_from_contracts(cc)
        assert r.collection_signature == r.expected_signature


# ── Stability ─────────────────────────────────────────────

@pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                         ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
class TestStability:
    def test_sig_stable(self, cc):
        r1 = sign_collection_from_contracts(cc)
        r2 = sign_collection_from_contracts(cc)
        assert r1.collection_signature == r2.collection_signature

    def test_canonical_stable(self, cc):
        r1 = sign_collection_from_contracts(cc)
        r2 = sign_collection_from_contracts(cc)
        assert r1.canonical_form == r2.canonical_form


# ── Wrong Sequence Count ──────────────────────────────────

@pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                         ids=[c["label"] for c in WRONG_COUNT_CASES])
class TestWrongCount:
    def test_verdict_not_satisfied(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = generate_collection_host_png_groups(cc)
        provide = case["provide_count"]
        if provide < len(groups):
            test_groups = groups[:provide]
        else:
            test_groups = groups + (groups[-1],) * (provide - len(groups))
        r = sign_collection(test_groups, cc)
        assert r.verdict == CollSigVerdict.COLLECTION_NOT_SATISFIED


# ── Wrong Sequence Order ──────────────────────────────────

@pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                         ids=[c["label"] for c in WRONG_ORDER_CASES])
class TestWrongOrder:
    def test_verdict_not_satisfied(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        groups = generate_collection_host_png_groups(cc)
        r = sign_collection(tuple(reversed(groups)), cc)
        assert r.verdict == CollSigVerdict.COLLECTION_NOT_SATISFIED


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
        r = sign_collection(groups, fake)
        assert r.verdict == CollSigVerdict.UNSUPPORTED


# ── Cross-Collection Distinctness ─────────────────────────

class TestDistinctness:
    def test_all_distinct(self):
        sigs = []
        for cc in FROZEN_COLLECTION_CONTRACTS:
            r = sign_collection_from_contracts(cc)
            sigs.append(r.collection_signature)
        assert len(set(sigs)) == len(sigs)


# ── Serialization ─────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=[cc.name for cc in FROZEN_COLLECTION_CONTRACTS])
    def test_to_dict(self, cc):
        r = sign_collection_from_contracts(cc)
        d = r.to_dict()
        assert d["verdict"] == "MATCH"
        assert d["collection_signature"] == r.collection_signature
        assert d["collection_contract_name"] == cc.name
        assert len(d["sequence_signatures"]) == cc.expected_sequence_count


# ── Baseline Consistency ──────────────────────────────────

class TestBaselineConsistency:
    def test_seq_sigs_from_per_sequence_baseline(self, expected_seq_sigs):
        for cc in FROZEN_COLLECTION_CONTRACTS:
            cr = validate_collection_from_contracts(cc)
            for i, seq_name in enumerate(cc.sequence_contract_names):
                assert cr.sequence_signatures[i] == expected_seq_sigs[seq_name]
