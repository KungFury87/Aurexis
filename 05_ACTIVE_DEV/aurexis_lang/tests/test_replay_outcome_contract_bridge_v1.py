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

    def test_global_checks_all_passed(self, replay_summary):
        """Contract.checks holds all checks (global + per-fixture). The
        per-fixture subset lives in fixture_checks. Global checks have
        names starting with 'global/'."""
        contract = validate_replay_outcomes(replay_summary)
        global_checks = [c for c in contract.checks if c.name.startswith("global/")]
        assert len(global_checks) == EXPECTED_GLOBAL_CHECKS
        for check in global_checks:
            assert check.passed is True, (
                f"Global check {check.name} failed: {check.detail}"
            )

    def test_all_checks_passed(self, replay_summary):
        """Every check in contract.checks must pass for SATISFIED verdict."""
        contract = validate_replay_outcomes(replay_summary)
        for check in contract.checks:
            assert check.passed is True, (
                f"Check {check.name} failed: {check.detail}"
            )

    def test_fixture_checks_summary(self, replay_summary):
        """contract.fixture_checks is a list of dicts summarizing each fixture's
        per-fixture check count. Each entry has fixture_name, checks_passed,
        checks_total."""
        contract = validate_replay_outcomes(replay_summary)
        assert isinstance(contract.fixture_checks, list)
        assert len(contract.fixture_checks) == replay_summary.total_fixtures
        for entry in contract.fixture_checks:
            assert "fixture_name" in entry
            assert "checks_passed" in entry
            assert "checks_total" in entry
            assert entry["checks_passed"] == entry["checks_total"]

    def test_totals_reconcile(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        assert contract.passed_checks + contract.failed_checks == contract.total_checks
        assert contract.failed_checks == 0

    def test_contract_hash_deterministic(self, replay_summary):
        c1 = validate_replay_outcomes(replay_summary)
        c2 = validate_replay_outcomes(replay_summary)
        assert c1.contract_hash == c2.contract_hash
        assert len(c1.contract_hash) == 64  # SHA-256 hex

    def test_contract_evidence_tier_authored(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        assert contract.evidence_tier == "authored"

    def test_contract_serialization(self, replay_summary):
        contract = validate_replay_outcomes(replay_summary)
        d = contract.to_dict()
        assert "verdict" in d
        assert "checks" in d
        assert "fixture_checks" in d
        j = contract.to_json()
        assert isinstance(j, str)
        assert "SATISFIED" in j


class TestSingleOutcomeValidation:
    """Validate individual fixture outcomes."""

    def test_valid_fixture_single(self):
        valid = [f for f in V1_FIXTURE_PACK.fixtures if f.is_valid][0]
        result = run_replay(valid)
        checks = validate_single_outcome(result, valid)
        assert len(checks) > 0
        for check in checks:
            assert check.passed is True, (
                f"Check {check.name} failed for valid fixture {valid.name}: {check.detail}"
            )

    def test_invalid_fixture_single(self):
        invalid = [f for f in V1_FIXTURE_PACK.fixtures if not f.is_valid][0]
        result = run_replay(invalid)
        checks = validate_single_outcome(result, invalid)
        assert len(checks) > 0
        for check in checks:
            assert check.passed is True, (
                f"Check {check.name} failed for invalid fixture {invalid.name}: {check.detail}"
            )

    def test_check_returns_checks_with_name_field(self):
        valid = [f for f in V1_FIXTURE_PACK.fixtures if f.is_valid][0]
        result = run_replay(valid)
        checks = validate_single_outcome(result, valid)
        for c in checks:
            # ContractCheck has: name, passed, expected, actual, detail
            assert hasattr(c, "name")
            assert hasattr(c, "passed")
            assert hasattr(c, "expected")
            assert hasattr(c, "actual")
            assert hasattr(c, "detail")
