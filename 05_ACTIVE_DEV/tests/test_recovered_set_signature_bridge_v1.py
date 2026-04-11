"""
Tests for Recovered Set Signature Bridge V1.

Proves that a validated recovered artifact set can be reduced to a
deterministic SHA-256 signature, and that changed content produces
an honest signature mismatch.

This is a narrow deterministic recovered-set identity proof, not
general document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'aurexis_lang', 'src'))

import pytest

from aurexis_lang.recovered_set_signature_bridge_v1 import (
    SIGNATURE_VERSION, SIGNATURE_FROZEN,
    V1_SIGNATURE_PROFILE, SignatureProfile,
    SignatureVerdict, SignatureResult,
    canonicalize_recovered_set, compute_signature,
    sign_recovered_set, sign_from_png,
    verify_signature, verify_from_png,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    FROZEN_CONTRACTS, ContractVerdict,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
)


# ════════════════════════════════════════════════════════════
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

class TestModuleConstants:
    def test_version(self):
        assert SIGNATURE_VERSION == "V1.0"

    def test_frozen(self):
        assert SIGNATURE_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_SIGNATURE_PROFILE, SignatureProfile)

    def test_hash_algorithm(self):
        assert V1_SIGNATURE_PROFILE.hash_algorithm == "sha256"

    def test_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 5
        assert len(OUT_OF_BOUNDS_CASES) == 3


# ════════════════════════════════════════════════════════════
# FIXTURES
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def all_recoveries():
    """Pre-generate all recovery results (expensive, do once)."""
    results = []
    for layout in FROZEN_LAYOUTS:
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        recovery = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        results.append((png, recovery))
    return results


# ════════════════════════════════════════════════════════════
# CANONICALIZATION
# ════════════════════════════════════════════════════════════

class TestCanonicalization:
    def test_valid_canonical_not_none(self, all_recoveries):
        for i, case in enumerate(IN_BOUNDS_CASES):
            _, recovery = all_recoveries[case["layout_index"]]
            contract = FROZEN_CONTRACTS[case["contract_index"]]
            canonical = canonicalize_recovered_set(recovery, contract)
            assert canonical is not None, f"Case {case['label']}"

    def test_canonical_contains_fields(self, all_recoveries):
        _, recovery = all_recoveries[0]
        contract = FROZEN_CONTRACTS[0]
        canonical = canonicalize_recovered_set(recovery, contract)
        assert f"contract={contract.name}" in canonical
        assert "families=" in canonical
        assert "verdicts=" in canonical
        assert f"version={SIGNATURE_VERSION}" in canonical

    def test_empty_recovery_returns_none(self):
        empty = MultiLayoutResult(
            verdict=MultiLayoutVerdict.NO_CANDIDATES,
            dispatched_count=0,
            dispatched_families=(),
        )
        assert canonicalize_recovered_set(empty, FROZEN_CONTRACTS[0]) is None


# ════════════════════════════════════════════════════════════
# SIGNATURE GENERATION
# ════════════════════════════════════════════════════════════

class TestSignatureGeneration:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_signed(self, idx, all_recoveries):
        case = IN_BOUNDS_CASES[idx]
        _, recovery = all_recoveries[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        sr = sign_recovered_set(recovery, contract)
        assert sr.verdict == SignatureVerdict.SIGNED

    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_sha256_length(self, idx, all_recoveries):
        case = IN_BOUNDS_CASES[idx]
        _, recovery = all_recoveries[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        sr = sign_recovered_set(recovery, contract)
        assert len(sr.signature) == 64

    def test_all_signatures_unique(self, all_recoveries):
        sigs = []
        for case in IN_BOUNDS_CASES:
            _, recovery = all_recoveries[case["layout_index"]]
            contract = FROZEN_CONTRACTS[case["contract_index"]]
            sr = sign_recovered_set(recovery, contract)
            sigs.append(sr.signature)
        assert len(set(sigs)) == len(sigs)


# ════════════════════════════════════════════════════════════
# STABILITY / DETERMINISM
# ════════════════════════════════════════════════════════════

class TestStability:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_repeated_identical(self, idx, all_recoveries):
        case = IN_BOUNDS_CASES[idx]
        _, recovery = all_recoveries[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        sr1 = sign_recovered_set(recovery, contract)
        sr2 = sign_recovered_set(recovery, contract)
        assert sr1.signature == sr2.signature

    def test_from_png_stable(self, all_recoveries):
        png, _ = all_recoveries[0]
        sr1 = sign_from_png(png, FROZEN_CONTRACTS[0])
        sr2 = sign_from_png(png, FROZEN_CONTRACTS[0])
        assert sr1.signature == sr2.signature


# ════════════════════════════════════════════════════════════
# VERIFICATION
# ════════════════════════════════════════════════════════════

class TestVerification:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_correct_signature_verified(self, idx, all_recoveries):
        case = IN_BOUNDS_CASES[idx]
        _, recovery = all_recoveries[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        sr = sign_recovered_set(recovery, contract)
        vr = verify_signature(recovery, contract, sr.signature)
        assert vr.verdict == SignatureVerdict.VERIFIED

    def test_wrong_signature_mismatch(self, all_recoveries):
        _, recovery = all_recoveries[0]
        vr = verify_signature(recovery, FROZEN_CONTRACTS[0], "0" * 64)
        assert vr.verdict == SignatureVerdict.MISMATCH

    def test_cross_layout_mismatch(self, all_recoveries):
        _, r0 = all_recoveries[0]
        _, r1 = all_recoveries[1]
        sr0 = sign_recovered_set(r0, FROZEN_CONTRACTS[0])
        vr = verify_signature(r1, FROZEN_CONTRACTS[1], sr0.signature)
        assert vr.verdict == SignatureVerdict.MISMATCH


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS
# ════════════════════════════════════════════════════════════

class TestOutOfBounds:
    @pytest.mark.parametrize("idx", list(range(len(OUT_OF_BOUNDS_CASES))))
    def test_not_signed(self, idx, all_recoveries):
        case = OUT_OF_BOUNDS_CASES[idx]
        _, recovery = all_recoveries[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        sr = sign_recovered_set(recovery, contract)
        assert sr.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED
        assert sr.signature == ""

    def test_empty_recovery_not_signed(self):
        empty = MultiLayoutResult(
            verdict=MultiLayoutVerdict.NO_CANDIDATES,
            dispatched_count=0,
            dispatched_families=(),
        )
        sr = sign_recovered_set(empty, FROZEN_CONTRACTS[0])
        assert sr.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

class TestSerialization:
    def test_result_to_dict(self, all_recoveries):
        _, recovery = all_recoveries[0]
        sr = sign_recovered_set(recovery, FROZEN_CONTRACTS[0])
        d = sr.to_dict()
        assert d["verdict"] == "SIGNED"
        assert len(d["signature"]) == 64
        assert d["version"] == "V1.0"
        assert isinstance(d["dispatched_families"], list)
        assert isinstance(d["canonical_form"], str)
        assert len(d["canonical_form"]) > 0
