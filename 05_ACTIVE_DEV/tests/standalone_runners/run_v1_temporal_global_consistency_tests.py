#!/usr/bin/env python3
"""
Standalone runner — Temporal Global Consistency Bridge V1

Runs all assertions for the 28th bridge (10th temporal transport milestone).
Requires only Python 3.x and the aurexis_lang package (no external deps).

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

# ── path setup ──────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, "..", "..", "aurexis_lang", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

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
    TemporalMatchVerdict, TemporalMatchResult,
    match_temporal_signature, V1_MATCH_BASELINE,
    _get_expected_temporal_signatures,
    MATCH_CASES,
)
from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SignatureVerdict, sign_temporal_payload, SIGN_CASES,
)

passed = 0
failed = 0

def check(cond, label):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}")


# ════════════════════════════════════════════════════════════
# Section 1: Module constants
# ════════════════════════════════════════════════════════════
print("Section 1: Module constants")
check(TEMPORAL_CONSISTENCY_V2_VERSION == "V1.0", "version == V1.0")
check(TEMPORAL_CONSISTENCY_V2_FROZEN is True, "frozen is True")
check(isinstance(V1_TEMPORAL_GLOBAL_PROFILE, TemporalConsistencyProfile), "profile type")


# ════════════════════════════════════════════════════════════
# Section 2: Verdict enum
# ════════════════════════════════════════════════════════════
print("Section 2: Verdict enum")
expected_verdicts = {"CONSISTENT", "INCONSISTENT", "UNSUPPORTED", "ERROR"}
actual_verdicts = {v.value for v in TemporalGlobalVerdict}
check(actual_verdicts == expected_verdicts, "all 4 TemporalGlobalVerdict values")
for v in expected_verdicts:
    check(TemporalGlobalVerdict(v).value == v, f"TemporalGlobalVerdict.{v} round-trips")


# ════════════════════════════════════════════════════════════
# Section 3: Check enum
# ════════════════════════════════════════════════════════════
print("Section 3: Check enum")
expected_checks = {
    "MATCH_VERDICT_AGREEMENT", "CONTRACT_VERDICT_AGREEMENT",
    "SIGNATURE_EQUALITY", "CANONICAL_FIELD_CONSISTENCY",
    "PAYLOAD_LENGTH_CONSISTENCY", "CROSS_CASE_DISTINCTNESS",
}
actual_checks = {c.value for c in TemporalConsistencyCheck}
check(actual_checks == expected_checks, "all 6 TemporalConsistencyCheck values")


# ════════════════════════════════════════════════════════════
# Section 4: Profile structure
# ════════════════════════════════════════════════════════════
print("Section 4: Profile structure")
check(len(V1_TEMPORAL_GLOBAL_PROFILE.checks) == 6, "profile has 6 checks")
check(V1_TEMPORAL_GLOBAL_PROFILE.require_all is True, "require_all is True")
check(V1_TEMPORAL_GLOBAL_PROFILE.version == "V1.0", "profile version")


# ════════════════════════════════════════════════════════════
# Section 5: Route table helper
# ════════════════════════════════════════════════════════════
print("Section 5: Route table helper")
check(_expected_family_for_payload((0, 0, 1, 0)) == "adjacent_pair", "route 00→adjacent_pair")
check(_expected_family_for_payload((0, 1, 1, 0)) == "containment", "route 01→containment")
check(_expected_family_for_payload((1, 0, 1, 0, 1)) == "three_regions", "route 10→three_regions")
check(_expected_family_for_payload((1, 1, 0, 0)) is None, "route 11→None (RESERVED)")
check(_expected_family_for_payload((0,)) is None, "too short→None")
check(_expected_family_for_payload(()) is None, "empty→None")


# ════════════════════════════════════════════════════════════
# Section 6: Consistent cases — E2E
# ════════════════════════════════════════════════════════════
print("Section 6: Consistent cases — E2E")
check(len(CONSISTENT_CASES) == 6, "exactly 6 CONSISTENT_CASES")
for case in CONSISTENT_CASES:
    cr = check_temporal_consistency(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    check(cr.verdict == TemporalGlobalVerdict.CONSISTENT, f"consistent {case['label']} → CONSISTENT")
    check(cr.checks_performed == 6, f"consistent {case['label']} 6 checks performed")
    check(cr.checks_passed == 6, f"consistent {case['label']} 6 checks passed")
    check(cr.checks_failed == 0, f"consistent {case['label']} 0 checks failed")
    check(len(cr.failed_checks) == 0, f"consistent {case['label']} no failed checks")
    check(cr.match_result is not None, f"consistent {case['label']} match result present")


# ════════════════════════════════════════════════════════════
# Section 7: Contradictory cases — fabricated
# ════════════════════════════════════════════════════════════
print("Section 7: Contradictory cases — fabricated")
check(len(CONTRADICTORY_CASES) == 5, "exactly 5 CONTRADICTORY_CASES")
for case in CONTRADICTORY_CASES:
    fabricated = case["fabricate"]()
    cr = check_temporal_consistency_from_match(fabricated)
    check(cr.verdict == TemporalGlobalVerdict.INCONSISTENT, f"contradictory {case['label']} → INCONSISTENT")
    check(cr.checks_failed > 0, f"contradictory {case['label']} has failures")
    # Verify the expected failing checks
    for expected_fail in case["expected_fails"]:
        check(expected_fail in cr.failed_checks, f"contradictory {case['label']} fails {expected_fail}")


# ════════════════════════════════════════════════════════════
# Section 8: Unsupported cases
# ════════════════════════════════════════════════════════════
print("Section 8: Unsupported cases")
check(len(UNSUPPORTED_CASES) == 1, "exactly 1 UNSUPPORTED_CASE")
for case in UNSUPPORTED_CASES:
    cr = check_temporal_consistency(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["case_label"],
        transport_mode=case["mode"],
    )
    check(cr.verdict == TemporalGlobalVerdict.UNSUPPORTED, f"unsupported {case['label']} → UNSUPPORTED")


# ════════════════════════════════════════════════════════════
# Section 9: Determinism — repeated consistency runs
# ════════════════════════════════════════════════════════════
print("Section 9: Determinism — repeated consistency runs")
for case in CONSISTENT_CASES[:3]:
    verdicts = set()
    for _ in range(3):
        cr = check_temporal_consistency(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        verdicts.add(cr.verdict.value)
    check(len(verdicts) == 1, f"determinism {case['label']} same verdict over 3 runs")


# ════════════════════════════════════════════════════════════
# Section 10: Convenience path — check_from_match
# ════════════════════════════════════════════════════════════
print("Section 10: Convenience path — check_from_match")
for case in CONSISTENT_CASES[:3]:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    cr = check_temporal_consistency_from_match(mr)
    check(cr.verdict == TemporalGlobalVerdict.CONSISTENT, f"convenience {case['label']} → CONSISTENT")


# ════════════════════════════════════════════════════════════
# Section 11: Cross-path consistency (E2E vs convenience)
# ════════════════════════════════════════════════════════════
print("Section 11: Cross-path consistency — E2E vs convenience")
for case in CONSISTENT_CASES[:3]:
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
    check(cr_e2e.verdict == cr_conv.verdict, f"cross-path {case['label']} verdict match")
    check(cr_e2e.checks_passed == cr_conv.checks_passed, f"cross-path {case['label']} pass count match")


# ════════════════════════════════════════════════════════════
# Section 12: Result serialization
# ════════════════════════════════════════════════════════════
print("Section 12: Result serialization")
for case in CONSISTENT_CASES[:2]:
    cr = check_temporal_consistency(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    d = cr.to_dict()
    check(d["verdict"] == "CONSISTENT", f"serialization {case['label']} verdict")
    check(d["checks_performed"] == 6, f"serialization {case['label']} checks_performed")
    j = json.dumps(d)
    d2 = json.loads(j)
    check(d2["verdict"] == "CONSISTENT", f"serialization {case['label']} JSON round-trip")


# ════════════════════════════════════════════════════════════
# Section 13: Individual check results accessible
# ════════════════════════════════════════════════════════════
print("Section 13: Individual check results accessible")
cr = check_temporal_consistency(
    payload=CONSISTENT_CASES[0]["payload"],
    contract_name=CONSISTENT_CASES[0]["contract"],
    case_label=CONSISTENT_CASES[0]["label"],
    transport_mode=CONSISTENT_CASES[0]["mode"],
)
check(len(cr.check_results) == 6, "6 individual check results")
for i, check_result in enumerate(cr.check_results):
    check(check_result.passed is True, f"individual check {i} passed")
    check(isinstance(check_result.detail, str), f"individual check {i} has detail string")
    check(isinstance(check_result.check, TemporalConsistencyCheck), f"individual check {i} has check enum")


# ════════════════════════════════════════════════════════════
# Section 14: Predefined case counts
# ════════════════════════════════════════════════════════════
print("Section 14: Predefined case counts")
check(len(CONSISTENT_CASES) == 6, "CONSISTENT_CASES count == 6")
check(len(CONTRADICTORY_CASES) == 5, "CONTRADICTORY_CASES count == 5")
check(len(UNSUPPORTED_CASES) == 1, "UNSUPPORTED_CASES count == 1")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
total = passed + failed
print()
print("=" * 60)
print(f"Temporal Global Consistency Bridge V1 — {total} assertions: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
