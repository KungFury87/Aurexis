#!/usr/bin/env python3
"""
Standalone runner — Replay Outcome Contract Bridge V1

Validates that replay outcomes match explicit expected dry-run verdicts.
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

from aurexis_lang.replay_outcome_contract_bridge_v1 import (
    REPLAY_CONTRACT_VERSION, REPLAY_CONTRACT_FROZEN,
    EXPECTED_VERDICT_COUNT, EXPECTED_GLOBAL_CHECKS,
    ContractVerdict, ContractCheck, OutcomeContract,
    validate_replay_outcomes, validate_single_outcome,
)

check("Version V1.0", REPLAY_CONTRACT_VERSION == "V1.0")
check("Module frozen", REPLAY_CONTRACT_FROZEN is True)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  2. Verdict and Check Counts")
print("=" * 60)

check(f"3 contract verdicts", len(ContractVerdict) == EXPECTED_VERDICT_COUNT)
check(f"4 global checks expected", EXPECTED_GLOBAL_CHECKS == 4)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  3. Run Full Replay + Contract Validation")
print("=" * 60)

from aurexis_lang.intake_to_delta_replay_harness_v1 import run_all_replays
from aurexis_lang.authored_capture_fixtures_v1 import V1_FIXTURE_PACK

summary = run_all_replays()
contract = validate_replay_outcomes(summary, V1_FIXTURE_PACK)

check("Contract SATISFIED", contract.verdict == ContractVerdict.SATISFIED)
check("0 failed checks", contract.failed_checks == 0)
check("Evidence tier authored", contract.evidence_tier == "authored")
check("Contract hash SHA-256", len(contract.contract_hash) == 64)
check(f"Total checks > 0", contract.total_checks > 0)
check(f"All checks passed", contract.passed_checks == contract.total_checks)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  4. Global Checks Present")
print("=" * 60)

global_checks = [c for c in contract.checks if c.name.startswith("global/")]
check(f"4 global checks", len(global_checks) == EXPECTED_GLOBAL_CHECKS)
check("fixture_count check passed", any(c.name == "global/fixture_count" and c.passed for c in global_checks))
check("evidence_tier check passed", any(c.name == "global/evidence_tier" and c.passed for c in global_checks))
check("no_failures check passed", any(c.name == "global/no_failures" and c.passed for c in global_checks))
check("summary_hash check passed", any(c.name == "global/summary_hash" and c.passed for c in global_checks))


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  5. Per-Fixture Checks — Valid Fixtures")
print("=" * 60)

valid_names = ["valid_phone_jpeg", "valid_scanner_tiff", "valid_two_file"]
for name in valid_names:
    fixture_checks = [c for c in contract.checks if c.name.startswith(f"{name}/")]
    all_passed = all(c.passed for c in fixture_checks)
    check(f"{name}: all checks passed ({len(fixture_checks)} checks)", all_passed)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  6. Per-Fixture Checks — Invalid Fixtures")
print("=" * 60)

invalid_names = ["invalid_missing_fields", "invalid_bad_extension", "invalid_duplicate_files"]
for name in invalid_names:
    fixture_checks = [c for c in contract.checks if c.name.startswith(f"{name}/")]
    all_passed = all(c.passed for c in fixture_checks)
    check(f"{name}: all checks passed ({len(fixture_checks)} checks)", all_passed)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  7. Fixture Check Summary")
print("=" * 60)

check(f"6 fixture check groups", len(contract.fixture_checks) == 6)
for fc in contract.fixture_checks:
    check(f"{fc['fixture_name']}: {fc['checks_passed']}/{fc['checks_total']}", fc['checks_passed'] == fc['checks_total'])


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  8. Serialization")
print("=" * 60)

d = contract.to_dict()
check("to_dict has verdict", "verdict" in d)
check("to_dict has checks", "checks" in d)
check("to_dict has fixture_checks", "fixture_checks" in d)
j = contract.to_json()
check("to_json has SATISFIED", "SATISFIED" in j)
txt = contract.to_summary_text()
check("Summary text has SATISFIED", "SATISFIED" in txt)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  9. Hash Determinism")
print("=" * 60)

summary2 = run_all_replays()
contract2 = validate_replay_outcomes(summary2, V1_FIXTURE_PACK)
check("Contract hash deterministic", contract.contract_hash == contract2.contract_hash)


# ════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"  REPLAY OUTCOME CONTRACT V1 — STANDALONE RESULTS")
print(f"  PASSED: {passed}  FAILED: {failed}")
print(f"  TOTAL ASSERTIONS: {passed + failed}")
if failed == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
