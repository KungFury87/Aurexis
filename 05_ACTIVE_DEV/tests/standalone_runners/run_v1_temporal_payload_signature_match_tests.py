#!/usr/bin/env python3
"""
Standalone runner — Temporal Payload Signature Match Bridge V1

Runs all assertions for the 27th bridge (9th temporal transport milestone).
Requires only Python 3.x and the aurexis_lang package (no external deps).

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

# ── path setup ──────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_HERE, "..", "..", "aurexis_lang", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from aurexis_lang.temporal_payload_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    TemporalMatchVerdict, TemporalMatchResult,
    ExpectedTemporalSignatureBaseline, V1_MATCH_BASELINE,
    match_temporal_signature, match_from_signature_result,
    _get_expected_temporal_signatures,
    MATCH_CASES, MISMATCH_CASES, SIGN_FAIL_CASES,
    UNSUPPORTED_CASES, OOB_CASES,
)
from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION, SignatureVerdict,
    sign_temporal_payload, SIGN_CASES,
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
check(MATCH_VERSION == "V1.0", "MATCH_VERSION == V1.0")
check(MATCH_FROZEN is True, "MATCH_FROZEN is True")
check(isinstance(V1_MATCH_BASELINE, ExpectedTemporalSignatureBaseline), "V1_MATCH_BASELINE type")


# ════════════════════════════════════════════════════════════
# Section 2: Match verdict enum
# ════════════════════════════════════════════════════════════
print("Section 2: Match verdict enum")
expected_verdicts = {"MATCH", "MISMATCH", "UNSUPPORTED", "SIGN_FAILED", "EMPTY_PAYLOAD", "ERROR"}
actual_verdicts = {v.value for v in TemporalMatchVerdict}
check(actual_verdicts == expected_verdicts, "all 6 TemporalMatchVerdict values present")
for v in expected_verdicts:
    check(TemporalMatchVerdict(v).value == v, f"TemporalMatchVerdict.{v} round-trips")


# ════════════════════════════════════════════════════════════
# Section 3: Expected baseline structure
# ════════════════════════════════════════════════════════════
print("Section 3: Expected baseline structure")
check(V1_MATCH_BASELINE.version == "V1.0", "baseline version")
check(len(V1_MATCH_BASELINE.supported_cases) == 6, "baseline has 6 supported cases")
for case in SIGN_CASES:
    check(V1_MATCH_BASELINE.is_supported(case["label"]), f"baseline supports {case['label']}")
check(not V1_MATCH_BASELINE.is_supported("nonexistent"), "baseline rejects nonexistent")
check(not V1_MATCH_BASELINE.is_supported(""), "baseline rejects empty label")


# ════════════════════════════════════════════════════════════
# Section 4: Expected signature generation
# ════════════════════════════════════════════════════════════
print("Section 4: Expected signature generation")
expected_sigs = _get_expected_temporal_signatures()
check(len(expected_sigs) == 6, "exactly 6 expected signatures generated")
for label, sig in expected_sigs.items():
    check(isinstance(sig, str), f"sig for {label} is str")
    check(len(sig) == 64, f"sig for {label} is 64 hex chars")
    check(all(c in "0123456789abcdef" for c in sig), f"sig for {label} is valid hex")


# ════════════════════════════════════════════════════════════
# Section 5: Expected signatures are distinct
# ════════════════════════════════════════════════════════════
print("Section 5: Expected signatures are distinct")
sig_values = list(expected_sigs.values())
check(len(sig_values) == len(set(sig_values)), "all 6 expected signatures are distinct")


# ════════════════════════════════════════════════════════════
# Section 6: Match cases — E2E match
# ════════════════════════════════════════════════════════════
print("Section 6: Match cases — E2E match")
check(len(MATCH_CASES) == 6, "exactly 6 MATCH_CASES")
for case in MATCH_CASES:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    check(mr.verdict == TemporalMatchVerdict.MATCH, f"match case {case['label']} → MATCH")
    check(mr.computed_signature == mr.expected_signature, f"match case {case['label']} sigs equal")
    check(len(mr.computed_signature) == 64, f"match case {case['label']} sig is 64 hex")
    check(mr.case_label == case["label"], f"match case {case['label']} label preserved")
    check(mr.contract_name == case["contract"], f"match case {case['label']} contract preserved")


# ════════════════════════════════════════════════════════════
# Section 7: Mismatch cases — changed payload
# ════════════════════════════════════════════════════════════
print("Section 7: Mismatch cases — changed payload")
check(len(MISMATCH_CASES) == 3, "exactly 3 MISMATCH_CASES")
for case in MISMATCH_CASES:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["case_label"],
        transport_mode=case["mode"],
    )
    check(mr.verdict == TemporalMatchVerdict.MISMATCH, f"mismatch case {case['label']} → MISMATCH")
    check(mr.computed_signature != mr.expected_signature, f"mismatch case {case['label']} sigs differ")
    check(len(mr.computed_signature) == 64, f"mismatch case {case['label']} computed sig exists")
    check(len(mr.expected_signature) == 64, f"mismatch case {case['label']} expected sig exists")


# ════════════════════════════════════════════════════════════
# Section 8: Sign-fail cases — contract validation fails
# ════════════════════════════════════════════════════════════
print("Section 8: Sign-fail cases — contract validation fails")
check(len(SIGN_FAIL_CASES) == 2, "exactly 2 SIGN_FAIL_CASES")
for case in SIGN_FAIL_CASES:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["case_label"],
        transport_mode=case["mode"],
    )
    check(mr.verdict == TemporalMatchVerdict.SIGN_FAILED, f"sign_fail case {case['label']} → SIGN_FAILED")
    check(mr.computed_signature == "", f"sign_fail case {case['label']} no computed sig")


# ════════════════════════════════════════════════════════════
# Section 9: Unsupported cases — label not in baseline
# ════════════════════════════════════════════════════════════
print("Section 9: Unsupported cases — label not in baseline")
check(len(UNSUPPORTED_CASES) == 2, "exactly 2 UNSUPPORTED_CASES")
for case in UNSUPPORTED_CASES:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["case_label"],
        transport_mode=case["mode"],
    )
    check(mr.verdict == TemporalMatchVerdict.UNSUPPORTED, f"unsupported case {case['label']} → UNSUPPORTED")


# ════════════════════════════════════════════════════════════
# Section 10: OOB cases — empty payload
# ════════════════════════════════════════════════════════════
print("Section 10: OOB cases — empty payload")
check(len(OOB_CASES) == 1, "exactly 1 OOB_CASE")
for case in OOB_CASES:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["case_label"],
        transport_mode=case["mode"],
    )
    check(mr.verdict == TemporalMatchVerdict.EMPTY_PAYLOAD, f"oob case {case['label']} → EMPTY_PAYLOAD")


# ════════════════════════════════════════════════════════════
# Section 11: Determinism — repeated match runs
# ════════════════════════════════════════════════════════════
print("Section 11: Determinism — repeated match runs")
for case in MATCH_CASES[:3]:  # test 3 cases x 3 runs
    results = []
    for _ in range(3):
        mr = match_temporal_signature(
            payload=case["payload"],
            contract_name=case["contract"],
            case_label=case["label"],
            transport_mode=case["mode"],
        )
        results.append(mr.computed_signature)
    check(len(set(results)) == 1, f"determinism: {case['label']} same sig over 3 runs")


# ════════════════════════════════════════════════════════════
# Section 12: match_from_signature_result — convenience path
# ════════════════════════════════════════════════════════════
print("Section 12: match_from_signature_result — convenience path")
for case in MATCH_CASES:
    # First sign the payload
    sr = sign_temporal_payload(
        payload=case["payload"],
        contract_name=case["contract"],
        transport_mode=case["mode"],
    )
    check(sr.verdict == SignatureVerdict.SIGNED, f"conv pre-sign {case['label']} SIGNED")
    # Then match via convenience
    mr = match_from_signature_result(sr, case["label"])
    check(mr.verdict == TemporalMatchVerdict.MATCH, f"conv match {case['label']} → MATCH")
    check(mr.computed_signature == mr.expected_signature, f"conv match {case['label']} sigs equal")


# ════════════════════════════════════════════════════════════
# Section 13: Convenience path with failed signing
# ════════════════════════════════════════════════════════════
print("Section 13: Convenience path with failed signing")
# Create a signature result with CONTRACT_NOT_SATISFIED
sr_fail = sign_temporal_payload(
    payload=(0, 0, 1, 0),
    contract_name="rs_4bit_adjacent",
    transport_mode="complementary_color",  # wrong mode
)
check(sr_fail.verdict != SignatureVerdict.SIGNED, "convenience pre-sign fails as expected")
mr_fail = match_from_signature_result(sr_fail, "rs_4bit_adj_sign")
check(mr_fail.verdict == TemporalMatchVerdict.SIGN_FAILED, "convenience with failed sign → SIGN_FAILED")


# ════════════════════════════════════════════════════════════
# Section 14: Convenience path with unsupported label
# ════════════════════════════════════════════════════════════
print("Section 14: Convenience path with unsupported label")
sr_ok = sign_temporal_payload(
    payload=(0, 0, 1, 0),
    contract_name="rs_4bit_adjacent",
    transport_mode="rolling_shutter",
)
check(sr_ok.verdict == SignatureVerdict.SIGNED, "convenience unsupported pre-sign ok")
mr_unsup = match_from_signature_result(sr_ok, "nonexistent_label")
check(mr_unsup.verdict == TemporalMatchVerdict.UNSUPPORTED, "convenience with bad label → UNSUPPORTED")


# ════════════════════════════════════════════════════════════
# Section 15: Result serialization round-trip
# ════════════════════════════════════════════════════════════
print("Section 15: Result serialization round-trip")
for case in MATCH_CASES[:2]:
    mr = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    d = mr.to_dict()
    check(d["verdict"] == "MATCH", f"serialization {case['label']} verdict")
    check(d["computed_signature"] == d["expected_signature"], f"serialization {case['label']} sigs match")
    j = json.dumps(d)
    d2 = json.loads(j)
    check(d2 == d, f"serialization {case['label']} JSON round-trip")


# ════════════════════════════════════════════════════════════
# Section 16: Cross-path consistency
# ════════════════════════════════════════════════════════════
print("Section 16: Cross-path consistency — E2E vs convenience produce same result")
for case in MATCH_CASES:
    # E2E path
    mr_e2e = match_temporal_signature(
        payload=case["payload"],
        contract_name=case["contract"],
        case_label=case["label"],
        transport_mode=case["mode"],
    )
    # Convenience path
    sr = sign_temporal_payload(
        payload=case["payload"],
        contract_name=case["contract"],
        transport_mode=case["mode"],
    )
    mr_conv = match_from_signature_result(sr, case["label"])
    check(mr_e2e.verdict == mr_conv.verdict, f"cross-path {case['label']} verdict")
    check(mr_e2e.computed_signature == mr_conv.computed_signature, f"cross-path {case['label']} sig")


# ════════════════════════════════════════════════════════════
# Section 17: Predefined case counts
# ════════════════════════════════════════════════════════════
print("Section 17: Predefined case counts")
check(len(MATCH_CASES) == 6, "MATCH_CASES count == 6")
check(len(MISMATCH_CASES) == 3, "MISMATCH_CASES count == 3")
check(len(SIGN_FAIL_CASES) == 2, "SIGN_FAIL_CASES count == 2")
check(len(UNSUPPORTED_CASES) == 2, "UNSUPPORTED_CASES count == 2")
check(len(OOB_CASES) == 1, "OOB_CASES count == 1")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
total = passed + failed
print()
print("=" * 60)
print(f"Temporal Payload Signature Match Bridge V1 — {total} assertions: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
