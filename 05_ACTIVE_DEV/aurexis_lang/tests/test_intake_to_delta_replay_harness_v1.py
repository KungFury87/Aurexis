"""
Aurexis Core — Intake-to-Delta Replay Harness Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.intake_to_delta_replay_harness_v1 import (
    REPLAY_HARNESS_VERSION, REPLAY_HARNESS_FROZEN,
    ReplayStage, ReplayVerdict, ReplayStageResult, ReplayResult, ReplaySummary,
    run_replay, run_all_replays,
    EXPECTED_STAGE_COUNT, EXPECTED_REPLAY_VERDICT_COUNT,
)
from aurexis_lang.authored_capture_fixtures_v1 import V1_FIXTURE_PACK


def test_version():
    assert REPLAY_HARNESS_VERSION == "V1.0"


def test_frozen():
    assert REPLAY_HARNESS_FROZEN is True


def test_stage_count():
    assert len(ReplayStage) == EXPECTED_STAGE_COUNT


def test_verdict_count():
    assert len(ReplayVerdict) == EXPECTED_REPLAY_VERDICT_COUNT


def test_fixture_pack_populated():
    assert len(V1_FIXTURE_PACK.fixtures) >= 6


class TestValidFixtures:
    """All valid fixtures should reach ALL_STAGES_PASSED."""

    @pytest.fixture
    def valid_fixtures(self):
        return [f for f in V1_FIXTURE_PACK.fixtures if f.is_valid]

    def test_valid_count(self, valid_fixtures):
        assert len(valid_fixtures) >= 3

    def test_all_stages_passed(self, valid_fixtures):
        for f in valid_fixtures:
            result = run_replay(f)
            assert result.verdict == ReplayVerdict.ALL_STAGES_PASSED, (
                f"{f.name} expected ALL_STAGES_PASSED, got {result.verdict}"
            )

    def test_all_stages_completed(self, valid_fixtures):
        for f in valid_fixtures:
            result = run_replay(f)
            assert result.stages_completed == EXPECTED_STAGE_COUNT
            assert result.stages_total == EXPECTED_STAGE_COUNT

    def test_stages_field_populated(self, valid_fixtures):
        """Each valid fixture's ReplayResult.stages lists all 5 stages."""
        for f in valid_fixtures:
            result = run_replay(f)
            assert len(result.stages) == EXPECTED_STAGE_COUNT
            for sr in result.stages:
                assert sr.passed is True, (
                    f"{f.name} stage {sr.stage.value} failed: {sr.detail}"
                )

    def test_verdict_matches_all_three_layers(self, valid_fixtures):
        for f in valid_fixtures:
            result = run_replay(f)
            assert result.preflight_verdict_match is True
            assert result.ingest_verdict_match is True
            assert result.delta_verdict_match is True


class TestInvalidFixtures:
    """All invalid fixtures should be rejected at preflight."""

    @pytest.fixture
    def invalid_fixtures(self):
        return [f for f in V1_FIXTURE_PACK.fixtures if not f.is_valid]

    def test_invalid_count(self, invalid_fixtures):
        assert len(invalid_fixtures) >= 3

    def test_expected_rejection(self, invalid_fixtures):
        for f in invalid_fixtures:
            result = run_replay(f)
            assert result.verdict == ReplayVerdict.EXPECTED_REJECTION, (
                f"{f.name} expected EXPECTED_REJECTION, got {result.verdict}"
            )

    def test_stops_at_preflight(self, invalid_fixtures):
        """Invalid fixtures complete only 1 stage (preflight) before rejection."""
        for f in invalid_fixtures:
            result = run_replay(f)
            assert result.stages_completed == 1
            assert result.stages_total == EXPECTED_STAGE_COUNT


class TestFullPack:
    """Run all fixtures through the replay harness as a summary."""

    def test_run_all_replays(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        assert summary.total_fixtures == len(V1_FIXTURE_PACK.fixtures)

    def test_no_unexpected_failures(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        for r in summary.results:
            assert r.verdict != ReplayVerdict.UNEXPECTED_FAILURE
            assert r.verdict != ReplayVerdict.STAGE_MISMATCH
            assert r.verdict != ReplayVerdict.ERROR

    def test_summary_counts(self):
        """passed_count includes both ALL_STAGES_PASSED and EXPECTED_REJECTION
        outcomes; failed_count tracks only UNEXPECTED_FAILURE / STAGE_MISMATCH /
        ERROR. See ReplaySummary bookkeeping."""
        summary = run_all_replays(V1_FIXTURE_PACK)
        assert summary.total_fixtures == len(V1_FIXTURE_PACK.fixtures)
        assert summary.failed_count == 0
        assert summary.passed_count >= 3
        assert summary.expected_rejection_count >= 3

    def test_summary_hash_deterministic(self):
        s1 = run_all_replays(V1_FIXTURE_PACK)
        s2 = run_all_replays(V1_FIXTURE_PACK)
        assert s1.summary_hash == s2.summary_hash
        assert len(s1.summary_hash) == 64  # SHA-256 hex

    def test_summary_serialization(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        d = summary.to_dict()
        assert "version" in d
        assert "total_fixtures" in d
        assert "results" in d
        j = summary.to_json()
        assert isinstance(j, str)
        assert "authored" in j.lower() or "fixture" in j.lower() or "results" in j.lower()

    def test_summary_evidence_tier_authored(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        assert summary.evidence_tier == "authored"

    def test_all_passed_method(self):
        """ReplaySummary.all_passed() returns True iff failed_count == 0."""
        summary = run_all_replays(V1_FIXTURE_PACK)
        assert summary.all_passed() is True
