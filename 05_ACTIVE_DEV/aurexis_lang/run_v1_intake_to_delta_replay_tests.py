#!/usr/bin/env python3
"""
Standalone runner — Intake-to-Delta Replay Harness V1

Exercises the full observed-evidence pipeline using authored fixtures.
Evidence tier: AUTHORED only. NOT real-capture.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

passed = 0
failed = 0

def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  1. Module Version and Frozen State")
print("=" * 60)

from aurexis_lang.intake_to_delta_replay_harness_v1 import (
    REPLAY_HARNESS_VERSION, REPLAY_HARNESS_FROZEN,
    EXPECTED_STAGE_COUNT, EXPECTED_REPLAY_VERDICT_COUNT,
    ReplayStage, ReplayVerdict, ReplayResult, ReplaySummary,
    run_replay, run_all_replays,
)

check("Version V1.0", REPLAY_HARNESS_VERSION == "V1.0")
check("Module frozen", REPLAY_HARNESS_FROZEN is True)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  2. Stage and Verdict Counts")
print("=" * 60)

check("5 stages", len(ReplayStage) == EXPECTED_STAGE_COUNT)
check("5 replay verdicts", len(ReplayVerdict) == EXPECTED_REPLAY_VERDICT_COUNT)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  3. Fixture Pack Availability")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import (
    V1_FIXTURE_PACK, EXPECTED_FIXTURE_COUNT,
    EXPECTED_VALID_COUNT, EXPECTED_INVALID_COUNT,
)

check(f"Fixture count == {EXPECTED_FIXTURE_COUNT}", len(V1_FIXTURE_PACK.fixtures) == EXPECTED_FIXTURE_COUNT)
check(f"Valid count == {EXPECTED_VALID_COUNT}", len(V1_FIXTURE_PACK.valid_fixtures()) == EXPECTED_VALID_COUNT)
check(f"Invalid count == {EXPECTED_INVALID_COUNT}", len(V1_FIXTURE_PACK.invalid_fixtures()) == EXPECTED_INVALID_COUNT)
check("Evidence tier authored", V1_FIXTURE_PACK.evidence_tier == "authored")


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  4. Replay: valid_phone_jpeg — Full Pipeline")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_VALID_PHONE_JPEG
r = run_replay(FIXTURE_VALID_PHONE_JPEG)
check("Verdict ALL_STAGES_PASSED", r.verdict == ReplayVerdict.ALL_STAGES_PASSED)
check("5 stages completed", r.stages_completed == 5)
check("Preflight verdict match", r.preflight_verdict_match)
check("Ingest verdict match", r.ingest_verdict_match)
check("Delta verdict match", r.delta_verdict_match)
check("Evidence tier authored", r.evidence_tier == "authored")
check("Replay hash SHA-256", len(r.replay_hash) == 64)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  5. Replay: valid_scanner_tiff — Full Pipeline")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_VALID_SCANNER_TIFF
r2 = run_replay(FIXTURE_VALID_SCANNER_TIFF)
check("Verdict ALL_STAGES_PASSED", r2.verdict == ReplayVerdict.ALL_STAGES_PASSED)
check("5 stages completed", r2.stages_completed == 5)
check("Preflight verdict match", r2.preflight_verdict_match)
check("Delta verdict match", r2.delta_verdict_match)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  6. Replay: valid_two_file — Full Pipeline")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_VALID_TWO_FILE
r3 = run_replay(FIXTURE_VALID_TWO_FILE)
check("Verdict ALL_STAGES_PASSED", r3.verdict == ReplayVerdict.ALL_STAGES_PASSED)
check("5 stages completed", r3.stages_completed == 5)
check("Delta verdict WITHIN_TOLERANCE match", r3.delta_verdict_match)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  7. Replay: invalid_missing_fields — Expected Rejection")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_INVALID_MISSING_FIELDS
r4 = run_replay(FIXTURE_INVALID_MISSING_FIELDS)
check("Verdict EXPECTED_REJECTION", r4.verdict == ReplayVerdict.EXPECTED_REJECTION)
check("Preflight verdict match (REJECTED)", r4.preflight_verdict_match)
check("1 stage completed", r4.stages_completed == 1)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  8. Replay: invalid_bad_extension — Expected Rejection")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_INVALID_BAD_EXTENSION
r5 = run_replay(FIXTURE_INVALID_BAD_EXTENSION)
check("Verdict EXPECTED_REJECTION", r5.verdict == ReplayVerdict.EXPECTED_REJECTION)
check("Preflight verdict match (REJECTED)", r5.preflight_verdict_match)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  9. Replay: invalid_duplicate_files — Expected Rejection")
print("=" * 60)

from aurexis_lang.authored_capture_fixtures_v1 import FIXTURE_INVALID_DUPLICATE_FILES
r6 = run_replay(FIXTURE_INVALID_DUPLICATE_FILES)
check("Verdict EXPECTED_REJECTION", r6.verdict == ReplayVerdict.EXPECTED_REJECTION)
check("Preflight verdict match (REJECTED)", r6.preflight_verdict_match)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  10. Run All Replays — Full Pack")
print("=" * 60)

summary = run_all_replays()
check(f"Total fixtures == {EXPECTED_FIXTURE_COUNT}", summary.total_fixtures == EXPECTED_FIXTURE_COUNT)
check("All passed", summary.all_passed())
check("0 failures", summary.failed_count == 0)
check(f"Passed count == {EXPECTED_FIXTURE_COUNT}", summary.passed_count == EXPECTED_FIXTURE_COUNT)
check(f"Expected rejections == {EXPECTED_INVALID_COUNT}", summary.expected_rejection_count == EXPECTED_INVALID_COUNT)
check("Evidence tier authored", summary.evidence_tier == "authored")
check("Summary hash SHA-256", len(summary.summary_hash) == 64)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  11. Serialization")
print("=" * 60)

d = summary.to_dict()
check("to_dict has version", "version" in d)
check("to_dict has total_fixtures", "total_fixtures" in d)
check("to_dict has results", "results" in d)
j = summary.to_json()
check("to_json has authored", "authored" in j)
txt = summary.to_summary_text()
check("Summary text has fixture count", str(EXPECTED_FIXTURE_COUNT) in txt)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  12. Hash Determinism")
print("=" * 60)

summary2 = run_all_replays()
check("Summary hash deterministic", summary.summary_hash == summary2.summary_hash)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"  INTAKE-TO-DELTA REPLAY HARNESS V1 — STANDALONE RESULTS")
print(f"  PASSED: {passed}  FAILED: {failed}")
print(f"  TOTAL ASSERTIONS: {passed + failed}")
if failed == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
