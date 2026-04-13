"""
Pytest tests for Recovered Collection Global Consistency Bridge V1.

Proves that a locally-validated recovered collection is globally coherent
across its constituent pieces via cross-layer consistency checks, and that
"locally valid but globally contradictory" fabricated results are caught.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.recovered_collection_global_consistency_bridge_v1 import (
    GLOBAL_CONSISTENCY_VERSION, GLOBAL_CONSISTENCY_FROZEN,
    ConsistencyVerdict, ConsistencyCheck,
    ConsistencyCheckResult, ConsistencyResult,
    GlobalConsistencyProfile, V1_GLOBAL_CONSISTENCY_PROFILE,
    run_consistency_checks,
    check_collection_consistency, check_collection_consistency_from_contracts,
    IN_BOUNDS_CASES, UNSUPPORTED_CASES, CONTRADICTORY_CASES,
)
from aurexis_lang.recovered_sequence_collection_signature_match_bridge_v1 import (
    COLL_MATCH_VERSION, CollMatchVerdict, CollMatchResult,
    V1_COLL_MATCH_BASELINE,
    match_collection_signature_from_contracts,
)
from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    _get_expected_coll_sigs,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionContract, FROZEN_COLLECTION_CONTRACTS,
    generate_collection_host_png_groups,
    _get_collection_expected,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    _get_expected_seq_sigs,
)


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="module")
def all_host_groups():
    """Pre-generate host PNG groups for all frozen collection contracts."""
    groups = {}
    for cc in FROZEN_COLLECTION_CONTRACTS:
        groups[cc.name] = generate_collection_host_png_groups(cc)
    return groups


@pytest.fixture(scope="module")
def all_consistency_results(all_host_groups):
    """Pre-compute consistency results for all frozen contracts."""
    results = {}
    for cc in FROZEN_COLLECTION_CONTRACTS:
        results[cc.name] = check_collection_consistency(
            all_host_groups[cc.name], cc
        )
    return results


@pytest.fixture(scope="module")
def seq_expected():
    return _get_expected_seq_sigs()


@pytest.fixture(scope="module")
def coll_expected():
    return _get_collection_expected()


@pytest.fixture(scope="module")
def coll_sig_expected():
    return _get_expected_coll_sigs()


# ── Module Constants ───────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert GLOBAL_CONSISTENCY_VERSION == "V1.0"

    def test_frozen(self):
        assert GLOBAL_CONSISTENCY_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_GLOBAL_CONSISTENCY_PROFILE, GlobalConsistencyProfile)

    def test_profile_version(self):
        assert V1_GLOBAL_CONSISTENCY_PROFILE.version == "V1.0"

    def test_profile_require_all(self):
        assert V1_GLOBAL_CONSISTENCY_PROFILE.require_all is True

    def test_profile_check_count(self):
        assert len(V1_GLOBAL_CONSISTENCY_PROFILE.checks) == 6

    def test_predefined_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 3
        assert len(UNSUPPORTED_CASES) == 1
        assert len(CONTRADICTORY_CASES) == 6


# ── Enum Validation ────────────────────────────────────────

class TestEnums:
    def test_consistency_verdict_values(self):
        assert ConsistencyVerdict.CONSISTENT.value == "CONSISTENT"
        assert ConsistencyVerdict.INCONSISTENT.value == "INCONSISTENT"
        assert ConsistencyVerdict.UNSUPPORTED.value == "UNSUPPORTED"
        assert ConsistencyVerdict.ERROR.value == "ERROR"

    def test_consistency_check_values(self):
        assert ConsistencyCheck.MATCH_VERDICT_AGREEMENT.value == "MATCH_VERDICT_AGREEMENT"
        assert ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT.value == "VALIDATION_VERDICT_AGREEMENT"
        assert ConsistencyCheck.SIGNATURE_EQUALITY.value == "SIGNATURE_EQUALITY"
        assert ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN.value == "SEQUENCE_SIGNATURE_CHAIN"
        assert ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS.value == "PAIRWISE_SEQUENCE_DISTINCTNESS"
        assert ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY.value == "CROSS_LAYER_COUNT_CONSISTENCY"

    def test_profile_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            V1_GLOBAL_CONSISTENCY_PROFILE.version = "hacked"


# ── In-Bounds Consistency ──────────────────────────────────

class TestInBoundsConsistency:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_in_bounds_verdict(self, case, all_host_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = check_collection_consistency(all_host_groups[cc.name], cc)
        assert cr.verdict == ConsistencyVerdict.CONSISTENT

    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_in_bounds_all_checks_pass(self, case, all_host_groups):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = check_collection_consistency(all_host_groups[cc.name], cc)
        assert cr.checks_performed == 6
        assert cr.checks_passed == 6
        assert cr.checks_failed == 0

    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_from_contracts(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        cr = check_collection_consistency_from_contracts(cc)
        assert cr.verdict == ConsistencyVerdict.CONSISTENT


# ── Stability ──────────────────────────────────────────────

class TestStability:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=lambda c: c.name)
    def test_determinism(self, cc, all_host_groups):
        groups = all_host_groups[cc.name]
        cr1 = check_collection_consistency(groups, cc)
        cr2 = check_collection_consistency(groups, cc)
        assert cr1.verdict == cr2.verdict
        assert cr1.checks_passed == cr2.checks_passed


# ── Unsupported ────────────────────────────────────────────

class TestUnsupported:
    @pytest.mark.parametrize("case", UNSUPPORTED_CASES, ids=lambda c: c["label"])
    def test_unsupported_verdict(self, case, all_host_groups):
        fake = CollectionContract(
            name=case["contract_name"],
            expected_sequence_count=2,
            sequence_contract_names=("a", "b"),
        )
        cc0 = FROZEN_COLLECTION_CONTRACTS[0]
        cr = check_collection_consistency(all_host_groups[cc0.name], fake)
        assert cr.verdict == ConsistencyVerdict.UNSUPPORTED


# ── Contradictory Cases ────────────────────────────────────

class TestContradictory:
    @pytest.mark.parametrize("case", CONTRADICTORY_CASES, ids=lambda c: c["label"])
    def test_contradictory_verdict(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        mr = case["fabricator"]()
        cr = run_consistency_checks(mr, cc)
        assert cr.verdict == ConsistencyVerdict.INCONSISTENT

    @pytest.mark.parametrize("case", CONTRADICTORY_CASES, ids=lambda c: c["label"])
    def test_contradictory_failed_checks(self, case):
        cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
        mr = case["fabricator"]()
        cr = run_consistency_checks(mr, cc)
        for expected_check in case["expected_failed_checks"]:
            assert expected_check in cr.failed_checks


# ── Serialization ──────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=lambda c: c.name)
    def test_to_dict(self, cc):
        cr = check_collection_consistency_from_contracts(cc)
        d = cr.to_dict()
        assert d["verdict"] == "CONSISTENT"
        assert d["checks_performed"] == 6
        assert isinstance(d["check_results"], list)
        assert d["match_result"] is not None

    def test_check_result_to_dict(self):
        cc0 = FROZEN_COLLECTION_CONTRACTS[0]
        mr = match_collection_signature_from_contracts(cc0)
        cr = run_consistency_checks(mr, cc0)
        d = cr.check_results[0].to_dict()
        assert "check" in d
        assert "passed" in d
        assert "detail" in d


# ── Cross-Layer Chain ──────────────────────────────────────

class TestCrossLayerChain:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=lambda c: c.name)
    def test_seq_sigs_match_baseline(self, cc, seq_expected):
        cr = check_collection_consistency_from_contracts(cc)
        for i, seq_name in enumerate(cc.sequence_contract_names):
            assert cr.match_result.sequence_signatures[i] == seq_expected[seq_name]

    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=lambda c: c.name)
    def test_coll_sig_matches_baseline(self, cc, coll_sig_expected):
        cr = check_collection_consistency_from_contracts(cc)
        assert cr.match_result.computed_collection_signature == coll_sig_expected[cc.name]


# ── E2E ────────────────────────────────────────────────────

class TestE2E:
    @pytest.mark.parametrize("cc", FROZEN_COLLECTION_CONTRACTS,
                             ids=lambda c: c.name)
    def test_full_pipeline(self, cc):
        groups = generate_collection_host_png_groups(cc)
        cr = check_collection_consistency(groups, cc)
        assert cr.verdict == ConsistencyVerdict.CONSISTENT
        assert cr.checks_failed == 0

    def test_wrong_count_inconsistent(self):
        cc = FROZEN_COLLECTION_CONTRACTS[1]
        groups = generate_collection_host_png_groups(cc)
        cr = check_collection_consistency(groups[:2], cc)
        assert cr.verdict == ConsistencyVerdict.INCONSISTENT
