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


def test_fixture_pack_not_empty():
    assert len(V1_FIXTURE_PACK.fixtures) >= 6


class TestValidFixtures:
    """All valid fixtures should pass all 5 pipeline stages."""

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

    def test_stage_results_complete(self, valid_fixtures):
        for f in valid_fixtures:
            result = run_replay(f)
            assert len(result.stage_results) == EXPECTED_STAGE_COUNT

    def test_each_stage_passed(self, valid_fixtures):
        for f in valid_fixtures:
            result = run_replay(f)
            for sr in result.stage_results:
                assert sr.passed is True, (
                    f"{f.name} stage {sr.stage} failed"
                )


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


class TestFullPack:
    """Run all fixtures through the replay harness."""

    def test_run_all_replays(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        assert summary.total_fixtures == len(V1_FIXTURE_PACK.fixtures)

    def test_no_unexpected_failures(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        for r in summary.results:
            assert r.verdict != ReplayVerdict.UNEXPECTED_FAILURE

    def test_summary_hash_deterministic(self):
        s1 = run_all_replays(V1_FIXTURE_PACK)
        s2 = run_all_replays(V1_FIXTURE_PACK)
        assert s1.summary_hash == s2.summary_hash

    def test_summary_serialization(self):
        summary = run_all_replays(V1_FIXTURE_PACK)
        d = summary.to_dict()
        assert "version" in d
        assert "total_fixtures" in d
        assert "results" in d
        j = summary.to_json()
        assert "authored" in j.lower() or "fixture" in j.lower() or "results" in j.lower()
