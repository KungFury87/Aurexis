"""
Pytest tests for Recovered Page Sequence Signature Bridge V1.

Proves that a validated ordered page sequence can be reduced to a
deterministic sequence-level signature/fingerprint, and that changes
in page order, page content, or page count produce honest signature
mismatch or validation failure.

This is a narrow deterministic recovered-sequence identity proof, not
general document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
import hashlib

from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SEQ_SIG_VERSION, SEQ_SIG_FROZEN,
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    SeqSigVerdict, SeqSigResult,
    canonicalize_sequence, compute_sequence_signature,
    sign_sequence, sign_sequence_from_contracts,
    _get_expected_seq_sigs, _build_expected_seq_sig,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceVerdict, SequenceContract,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    generate_sequence_host_pngs,
    _get_sequence_expected,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    _get_expected_signatures,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def expected_seq_sigs():
    return _get_expected_seq_sigs()


@pytest.fixture(scope="module")
def page_expected_sigs():
    return _get_expected_signatures()


@pytest.fixture(scope="module")
def seq_page_expected():
    return _get_sequence_expected()


# ── Module Constants ──────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert SEQ_SIG_VERSION == "V1.0"

    def test_frozen(self):
        assert SEQ_SIG_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_SEQ_SIG_PROFILE, SequenceSignatureProfile)

    def test_hash_algorithm(self):
        assert V1_SEQ_SIG_PROFILE.hash_algorithm == "sha256"

    def test_canonical_fields(self):
        assert len(V1_SEQ_SIG_PROFILE.canonical_fields) == 3
        assert "sequence_contract_name" in V1_SEQ_SIG_PROFILE.canonical_fields
        assert "page_count" in V1_SEQ_SIG_PROFILE.canonical_fields
        assert "ordered_page_signatures" in V1_SEQ_SIG_PROFILE.canonical_fields


# ── Canonicalization ──────────────────────────────────────

class TestCanonicalization:
    def test_valid(self):
        sigs = ("a" * 64, "b" * 64)
        c = canonicalize_sequence("test", 2, sigs)
        assert c is not None
        assert "seq_contract=test" in c
        assert "page_count=2" in c

    def test_count_mismatch(self):
        sigs = ("a" * 64, "b" * 64)
        assert canonicalize_sequence("test", 3, sigs) is None

    def test_empty(self):
        assert canonicalize_sequence("test", 0, ()) is None

    def test_short_sig(self):
        assert canonicalize_sequence("test", 1, ("abc",)) is None

    def test_deterministic(self):
        sigs = ("a" * 64, "b" * 64)
        c1 = canonicalize_sequence("test", 2, sigs)
        c2 = canonicalize_sequence("test", 2, sigs)
        assert c1 == c2

    def test_different_inputs(self):
        s1 = ("a" * 64, "b" * 64)
        s2 = ("c" * 64, "d" * 64)
        c1 = canonicalize_sequence("test", 2, s1)
        c2 = canonicalize_sequence("test", 2, s2)
        assert c1 != c2


# ── Signature Computation ─────────────────────────────────

class TestSignatureComputation:
    def test_returns_64_chars(self):
        sig = compute_sequence_signature("test")
        assert len(sig) == 64

    def test_matches_stdlib(self):
        sig = compute_sequence_signature("test")
        assert sig == hashlib.sha256(b"test").hexdigest()

    def test_deterministic(self):
        s1 = compute_sequence_signature("test")
        s2 = compute_sequence_signature("test")
        assert s1 == s2

    def test_different_input(self):
        s1 = compute_sequence_signature("test1")
        s2 = compute_sequence_signature("test2")
        assert s1 != s2


# ── Expected Sequence Signatures ──────────────────────────

class TestExpectedSignatures:
    def test_count(self, expected_seq_sigs):
        assert len(expected_seq_sigs) == 3

    def test_all_present(self, expected_seq_sigs):
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            assert sc.name in expected_seq_sigs

    def test_all_64_chars(self, expected_seq_sigs):
        for sig in expected_seq_sigs.values():
            assert len(sig) == 64

    def test_all_distinct(self, expected_seq_sigs):
        sigs = list(expected_seq_sigs.values())
        assert len(set(sigs)) == len(sigs)

    def test_idempotent(self, expected_seq_sigs):
        sigs2 = _get_expected_seq_sigs()
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            assert expected_seq_sigs[sc.name] == sigs2[sc.name]


# ── In-Bounds Signing ─────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=[c["label"] for c in IN_BOUNDS_CASES])
class TestInBounds:
    def test_verdict_match(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        r = sign_sequence_from_contracts(sc)
        assert r.verdict == SeqSigVerdict.MATCH

    def test_sig_nonempty(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        r = sign_sequence_from_contracts(sc)
        assert len(r.sequence_signature) == 64

    def test_sig_equals_expected(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        r = sign_sequence_from_contracts(sc)
        assert r.sequence_signature == r.expected_signature


# ── Stability ─────────────────────────────────────────────

@pytest.mark.parametrize("sc", FROZEN_SEQUENCE_CONTRACTS,
                         ids=[sc.name for sc in FROZEN_SEQUENCE_CONTRACTS])
class TestStability:
    def test_sig_stable(self, sc):
        r1 = sign_sequence_from_contracts(sc)
        r2 = sign_sequence_from_contracts(sc)
        assert r1.sequence_signature == r2.sequence_signature

    def test_canonical_stable(self, sc):
        r1 = sign_sequence_from_contracts(sc)
        r2 = sign_sequence_from_contracts(sc)
        assert r1.canonical_form == r2.canonical_form


# ── Wrong Page Count ──────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                         ids=[c["label"] for c in WRONG_COUNT_CASES])
class TestWrongCount:
    def test_verdict_not_satisfied(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        all_pngs = generate_sequence_host_pngs(sc)
        provide = case["provide_page_count"]
        if provide < len(all_pngs):
            pngs = all_pngs[:provide]
        else:
            pngs = all_pngs + (all_pngs[-1],) * (provide - len(all_pngs))
        r = sign_sequence(pngs, sc)
        assert r.verdict == SeqSigVerdict.SEQUENCE_NOT_SATISFIED


# ── Wrong Page Order ──────────────────────────────────────

@pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                         ids=[c["label"] for c in WRONG_ORDER_CASES])
class TestWrongOrder:
    def test_verdict_not_satisfied(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        pngs = generate_sequence_host_pngs(sc)
        r = sign_sequence(tuple(reversed(pngs)), sc)
        assert r.verdict == SeqSigVerdict.SEQUENCE_NOT_SATISFIED


# ── Unsupported ───────────────────────────────────────────

@pytest.mark.parametrize("case", UNSUPPORTED_CASES,
                         ids=[c["label"] for c in UNSUPPORTED_CASES])
class TestUnsupported:
    def test_verdict_unsupported(self, case):
        fake = SequenceContract(
            name=case["contract_name"],
            expected_page_count=2,
            page_contract_names=("a", "b"),
        )
        sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
        pngs = generate_sequence_host_pngs(sc0)
        r = sign_sequence(pngs, fake)
        assert r.verdict == SeqSigVerdict.UNSUPPORTED


# ── Cross-Contract Distinctness ───────────────────────────

class TestDistinctness:
    def test_all_distinct(self):
        sigs = []
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            r = sign_sequence_from_contracts(sc)
            sigs.append(r.sequence_signature)
        assert len(set(sigs)) == len(sigs)


# ── Serialization ─────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("sc", FROZEN_SEQUENCE_CONTRACTS,
                             ids=[sc.name for sc in FROZEN_SEQUENCE_CONTRACTS])
    def test_to_dict(self, sc):
        r = sign_sequence_from_contracts(sc)
        d = r.to_dict()
        assert d["verdict"] == "MATCH"
        assert d["sequence_signature"] == r.sequence_signature
        assert d["sequence_contract_name"] == sc.name
        assert len(d["page_signatures"]) == sc.expected_page_count


# ── Baseline Consistency ──────────────────────────────────

class TestBaselineConsistency:
    def test_page_sigs_from_single_page_baseline(self, page_expected_sigs, seq_page_expected):
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            seq_page_sigs = seq_page_expected[sc.name]
            for i, pname in enumerate(sc.page_contract_names):
                assert seq_page_sigs[i] == page_expected_sigs.get(pname, "")
