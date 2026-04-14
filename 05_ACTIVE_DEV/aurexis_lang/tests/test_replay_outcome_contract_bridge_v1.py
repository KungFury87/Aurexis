"""
Aurexis Core — Replay Outcome Contract Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.replay_outcome_contract_bridge_v1 import (
    REPLAY_CONTRACT_VERSION, REPLAY_CONTRACT_FROZEN,
    ContractCheck, ContractVerdict, OutcomeContract,
    validate_replay_outcomes, validate_single_outcome,
    EXPECTED_VERDICT_COUNT, EXPECTED_GLOBAL_CHECKS,
)
from aurexis_lang.intake_to_delta_replay_harness_v1 import (
    run_all_replays, run_replay, ReplayVerdict,
)
from aurexis_lang.authored_capture_fixtures_v1 import V1_FIXTURE_PACK


@pytest.fixture
def replay_summary():
    return run_all_replays(V1_FIXTURE_PACK)


def test_version():
    assert REPLAY_CONTRACT_VERSION == "V1.0"


def test_frozen():
    assert REPLAY_CONTRACT_FROZEN is True


def test_verdict_count():
    assert len(ContractVerdict) == EXPECTED_VERDICT_COUNT


def test_global_checks_count():
    assert EXPECTED_GLOBAL_CHECKS == 4


class TestFullContractValidation:
    """Validate replay outcomes against the outcome contract."""

    def test_contract_satisfied(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        assert contract.verdict == ContractVerdict.SATISFIED

    def test_all_global_checks_passed(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        for check in contract.global_checks:
            assert check.passed is True, (
                f"Global check {check.check_name} failed"
            )

    def test_all_fixture_checks_passed(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        for fixture_name, checks in contract.fixture_checks.items():
            for check in checks:
                assert check.passed is True, (
                    f"Fixture {fixture_name} check {check.check_name} failed"
                )

    def test_contract_hash_deterministic(self, replay_summary):
        c1 = validate_replay_outcomes(replay_summary)
        c2 = validate_replay_outcomes(replay_summary)
        assert c1.contract_hash == c2.contract_hash

    def test_contract_serialization(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        d = contract.to_dict()
        assert "verdict" in d
        assert "checks" in d or "global_checks" in d
        j = contract.to_json()
        assert "SATISFIED" in j


class TestSingleOutcomeValidation:
    """Validate individual fixture outcomes."""

    def test_valid_fixture_single(self):
        valid = [f for f in V1_FIXTURE_PACK.fixtures if f.is_valid][0]
        result = run_replay(valid)
        checks = validate_single_outcome(valid, result)
        for check in checks:
            assert check.passed is True, (
                f"Check {check.check_name} failed for valid fixture {valid.name}"
            )

    def test_invalid_fixture_single(self):
        invalid = [f for f in V1_FIXTURE_PACK.fixtures if not f.is_valid][0]
        result = run_replay(invalid)
        checks = validate_single_outcome(invalid, result)
        for check in checks:
            assert check.passed is True, (
                f"Check {check.check_name} failed for invalid fixture {invalid.name}"
            )
