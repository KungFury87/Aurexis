"""
Pytest suite — Temporal Global Consistency Bridge V1

28th bridge (10th temporal transport milestone).
Bounded temporal cross-layer coherence verification proof.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import json
import pytest

from aurexis_lang.temporal_global_consistency_bridge_v1 import (
    TEMPORAL_CONSISTENCY_V2_VERSION, TEMPORAL_CONSISTENCY_V2_FROZEN,
    TemporalGlobalVerdict, TemporalConsistencyCheck,
    TemporalCheckResult, TemporalConsistencyProfile,
    V1_TEMPORAL_GLOBAL_PROFILE, TemporalConsistencyResult,
    check_temporal_consistency, check_temporal_consistency_from_match,
    CONSISTENT_CASES, CONTRADICTORY_CASES, UNSUPPORTED_CASES,
    _expected_family_for_payload,
)
from aurexis_lang.temporal_payload_signature_match_bridge_v1 import (
    TemporalMatchVerdict, match_temporal_signature, MATCH_CASES,
)


class TestModuleConstants:
    def test_version(self):
        assert TEMPORAL_CONSISTENCY_V2_VERSION == "V1.0"

    def test_frozen(self):
        assert TEMPORAL_CONSISTENCY_V2_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_TEMPORAL_GLOBAL_PROFILE, TemporalConsistencyProfile)


class TestVerdictEnum:
    def test_all_verdicts(self):
        expected = {"CONSISTENT", "INCONSISTENT", "UNSUPPORTED", "ERROR"}
        assert {v.value for v in TemporalGlobalVerdict} == expected

    @pytest.mark.parametrize("v", ["CONSISTENT", "INCONSISTENT", "UNSUPPORTED", "ERROR"])
    def test_round_trip(self, v):
        assert TemporalGlobalVerdict(v).value == v


class TestCheckEnum:
    def test_all_checks(self):
        expected = {
            "MATCH_VERDICT_AGREEMENT", "CONTRACT_VERDICT_AGREEMENT",
            "SIGNATURE_EQUALITY", "CANONICAL_FIELD_CONSISTENCY",
            "PAYLOAD_LENGTH_CONSISTENCY", "CROSS_CASE_DISTINCTNESS",
        }
        assert {c.value for c in TemporalConsistencyCheck} == expected


class TestProfileStructure:
    def test_check_count(self):
        assert len(V1_TEMPORAL_GLOBAL_PROFILE.checks) == 6

    def test_require_all(self):
        assert V1_TEMPORAL_GLOBAL_PROFILE.require_all is True


class TestRouteTable:
    def test_adjacent_pair(self):
        assert _expected_family_for_payload((0, 0, 1, 0)) == "adjacent_pair"

    def test_containment(self):
        assert _expected_family_for_payload((0, 1, 1, 0)) == "containment"

    def test_three_regions(self):
        assert _expected_family_for_payload((1, 0, 1, 0, 1)) == "three_regions"

    def test_reserved(self):
        assert _expected_family_for_payload((1, 1, 0, 0)) is None

    def test_too_short(self):
        assert _expected_family_for_payload((0,)) is None

    def test_empty(self):
        assert _expected_family_for_payload(()) is None


class TestConsistentCases:
    @pytest.mark.parametrize("case", CONSISTENT_CASES, ids=[c["label"] for c in CONSISTENT_CASES])
    def test_consistent_verdict(self, case):
        cr = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        assert cr.verdict == TemporalGlobalVerdict.CONSISTENT

    @pytest.mark.parametrize("case", CONSISTENT_CASES, ids=[c["label"] for c in CONSISTENT_CASES])
    def test_all_checks_pass(self, case):
        cr = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        assert cr.checks_performed == 6
        assert cr.checks_passed == 6
        assert cr.checks_failed == 0


class TestContradictoryCases:
    @pytest.mark.parametrize("case", CONTRADICTORY_CASES, ids=[c["label"] for c in CONTRADICTORY_CASES])
    def test_inconsistent_verdict(self, case):
        fabricated = case["fabricate"]()
        cr = check_temporal_consistency_from_match(fabricated)
        assert cr.verdict == TemporalGlobalVerdict.INCONSISTENT

    @pytest.mark.parametrize("case", CONTRADICTORY_CASES, ids=[c["label"] for c in CONTRADICTORY_CASES])
    def test_expected_failures(self, case):
        fabricated = case["fabricate"]()
        cr = check_temporal_consistency_from_match(fabricated)
        for expected_fail in case["expected_fails"]:
            assert expected_fail in cr.failed_checks


class TestUnsupportedCases:
    @pytest.mark.parametrize("case", UNSUPPORTED_CASES, ids=[c["label"] for c in UNSUPPORTED_CASES])
    def test_unsupported_verdict(self, case):
        cr = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["case_label"],
            transport_mode=case["mode"],
        )
        assert cr.verdict == TemporalGlobalVerdict.UNSUPPORTED


class TestDeterminism:
    @pytest.mark.parametrize("case", list(CONSISTENT_CASES)[:3], ids=[c["label"] for c in list(CONSISTENT_CASES)[:3]])
    def test_repeated_runs(self, case):
        verdicts = set()
        for _ in range(3):
            cr = check_temporal_consistency(
                payload=case["payload"],
                contract_name=case["contract"],
                case_label=case["label"],
                transport_mode=case["mode"],
            )
            verdicts.add(cr.verdict.value)
        assert len(verdicts) == 1


class TestConveniencePath:
    @pytest.mark.parametrize("case", list(CONSISTENT_CASES)[:3], ids=[c["label"] for c in list(CONSISTENT_CASES)[:3]])
    def test_convenience_consistent(self, case):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        cr = check_temporal_consistency_from_match(mr)
        assert cr.verdict == TemporalGlobalVerdict.CONSISTENT


class TestCrossPathConsistency:
    @pytest.mark.parametrize("case", list(CONSISTENT_CASES)[:3], ids=[c["label"] for c in list(CONSISTENT_CASES)[:3]])
    def test_e2e_vs_convenience(self, case):
        cr_e2e = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        cr_conv = check_temporal_consistency_from_match(mr)
        assert cr_e2e.verdict == cr_conv.verdict
        assert cr_e2e.checks_passed == cr_conv.checks_passed


class TestSerialization:
    @pytest.mark.parametrize("case", list(CONSISTENT_CASES)[:2], ids=[c["label"] for c in list(CONSISTENT_CASES)[:2]])
    def test_json_round_trip(self, case):
        cr = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        d = cr.to_dict()
        assert d["verdict"] == "CONSISTENT"
        j = json.dumps(d)
        d2 = json.loads(j)
        assert d2["verdict"] == "CONSISTENT"


class TestIndividualChecks:
    def test_all_checks_accessible(self):
        cr = check_temporal_consistency(
            payload=CONSISTENT_CASES[0]["payload"],
            contract_name=CONSISTENT_CASES[0]["contract"],
            case_label=CONSISTENT_CASES[0]["label"],
            transport_mode=CONSISTENT_CASES[0]["mode"],
        )
        assert len(cr.check_results) == 6
        for check_result in cr.check_results:
            assert check_result.passed is True
            assert isinstance(check_result.detail, str)


class TestCaseCounts:
    def test_consistent(self):
        assert len(CONSISTENT_CASES) == 6

    def test_contradictory(self):
        assert len(CONTRADICTORY_CASES) == 5

    def test_unsupported(self):
        assert len(UNSUPPORTED_CASES) == 1
