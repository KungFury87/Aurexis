#!/usr/bin/env python3
"""
Standalone test runner — Temporal Payload Signature Bridge V1 (26th bridge)

Tests the bounded temporal fingerprint proof.
No external dependencies required (stdlib only).

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

_here = os.path.dirname(os.path.abspath(__file__))
_tests = os.path.dirname(_here)
_dev = os.path.dirname(_tests)
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION,
    SIGNATURE_FROZEN,
    SignatureVerdict,
    TemporalSignatureProfile,
    V1_SIGNATURE_PROFILE,
    TemporalSignatureResult,
    compute_temporal_signature,
    sign_temporal_payload,
    sign_from_contract_result,
    SIGN_CASES,
    REJECT_CASES,
    OOB_CASES,
    DIFFERENCE_CASES,
)

from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    validate_temporal_contract,
    ContractVerdict,
)

passed = 0
failed = 0

def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {label}")


# ════════════════════════════════════════════════════════════
print("Section 1: Module constants")
check(SIGNATURE_VERSION == "V1.0", "version is V1.0")
check(SIGNATURE_FROZEN is True, "frozen is True")

# ════════════════════════════════════════════════════════════
print("Section 2: Verdict enum")
expected = ["SIGNED", "CONTRACT_NOT_SATISFIED", "EMPTY_PAYLOAD",
            "UNSUPPORTED_CONTRACT", "ERROR"]
for v in expected:
    check(hasattr(SignatureVerdict, v), f"verdict {v} exists")
check(len(SignatureVerdict) == 5, f"verdict count is 5, got {len(SignatureVerdict)}")

# ════════════════════════════════════════════════════════════
print("Section 3: Signature profile")
check(len(V1_SIGNATURE_PROFILE.canonical_fields) == 6, "6 canonical fields")
check(V1_SIGNATURE_PROFILE.hash_algorithm == "sha256", "hash is sha256")
check(V1_SIGNATURE_PROFILE.version == "V1.0", "profile version V1.0")

# ════════════════════════════════════════════════════════════
print("Section 4: Profile immutability")
try:
    V1_SIGNATURE_PROFILE.version = "hacked"
    check(False, "profile should be immutable")
except Exception:
    check(True, "profile is immutable")

# ════════════════════════════════════════════════════════════
print("Section 5: Result defaults")
r = TemporalSignatureResult()
check(r.verdict == SignatureVerdict.ERROR, "default verdict ERROR")
check(r.temporal_signature == "", "default sig empty")
check(r.payload == (), "default payload empty")
check(r.is_fused is False, "default not fused")

# ════════════════════════════════════════════════════════════
print("Section 6: Result serialization")
r = TemporalSignatureResult(
    verdict=SignatureVerdict.SIGNED,
    temporal_signature="abc123",
    contract_name="test",
    payload=(0, 0, 1, 0),
)
d = r.to_dict()
check(d["verdict"] == "SIGNED", "verdict in dict")
check(d["temporal_signature"] == "abc123", "sig in dict")
check(isinstance(json.dumps(d), str), "serializes to JSON")

# ════════════════════════════════════════════════════════════
print("Section 7: Signature determinism (raw function)")
s1 = compute_temporal_signature("test", (0, 0, 1, 0), "adj", "rs", False)
s2 = compute_temporal_signature("test", (0, 0, 1, 0), "adj", "rs", False)
check(s1 == s2, "raw sig deterministic")
check(len(s1) == 64, "raw sig is 64 hex chars")

# Different inputs → different signature
s3 = compute_temporal_signature("test", (0, 1, 1, 0), "adj", "rs", False)
check(s1 != s3, "different payload different sig")
s4 = compute_temporal_signature("test", (0, 0, 1, 0), "cont", "rs", False)
check(s1 != s4, "different family different sig")
s5 = compute_temporal_signature("test", (0, 0, 1, 0), "adj", "cc", False)
check(s1 != s5, "different mode different sig")
s6 = compute_temporal_signature("other", (0, 0, 1, 0), "adj", "rs", False)
check(s1 != s6, "different contract different sig")
s7 = compute_temporal_signature("test", (0, 0, 1, 0), "adj", "rs", True)
check(s1 != s7, "different fused flag different sig")

# ════════════════════════════════════════════════════════════
print("Section 8: Sign cases (E2E)")
for case in SIGN_CASES:
    result = sign_temporal_payload(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == SignatureVerdict.SIGNED,
        f"{case['label']}: verdict={result.verdict.value}"
    )
    check(
        len(result.temporal_signature) == 64,
        f"{case['label']}: has 64-char signature"
    )
    check(
        result.payload_length > 0,
        f"{case['label']}: payload_length > 0"
    )
    check(
        result.payload_family != "",
        f"{case['label']}: has family"
    )
    check(
        result.contract_verdict == "CONTRACT_SATISFIED",
        f"{case['label']}: contract satisfied"
    )

# ════════════════════════════════════════════════════════════
print("Section 9: Reject cases")
for case in REJECT_CASES:
    result = sign_temporal_payload(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED,
        f"{case['label']}: verdict={result.verdict.value}"
    )
    check(
        result.temporal_signature == "",
        f"{case['label']}: no signature"
    )

# ════════════════════════════════════════════════════════════
print("Section 10: OOB cases")
for case in OOB_CASES:
    result = sign_temporal_payload(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == SignatureVerdict[case["expected_verdict"]],
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 11: Difference cases — changed inputs → different sigs")
for case in DIFFERENCE_CASES:
    r_a = sign_temporal_payload(
        tuple(case["payload_a"]), case["contract_a"], case["mode_a"],
    )
    r_b = sign_temporal_payload(
        tuple(case["payload_b"]), case["contract_b"], case["mode_b"],
    )
    check(r_a.verdict == SignatureVerdict.SIGNED, f"{case['label']}: a signed")
    check(r_b.verdict == SignatureVerdict.SIGNED, f"{case['label']}: b signed")
    check(
        r_a.temporal_signature != r_b.temporal_signature,
        f"{case['label']}: sigs differ"
    )

# ════════════════════════════════════════════════════════════
print("Section 12: Determinism — repeated E2E runs")
for _ in range(3):
    r1 = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
    r2 = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
    check(r1.temporal_signature == r2.temporal_signature, "E2E deterministic sig")
    check(r1.verdict == r2.verdict, "E2E deterministic verdict")

# ════════════════════════════════════════════════════════════
print("Section 13: Signature distinctness across sign cases")
sigs = set()
for case in SIGN_CASES:
    result = sign_temporal_payload(
        tuple(case["payload"]), case["contract"], case["mode"],
    )
    sigs.add(result.temporal_signature)
check(len(sigs) == len(SIGN_CASES), f"all {len(SIGN_CASES)} sigs unique, got {len(sigs)}")

# ════════════════════════════════════════════════════════════
print("Section 14: sign_from_contract_result — convenience path")
cr_ok = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
sr_ok = sign_from_contract_result(cr_ok)
check(sr_ok.verdict == SignatureVerdict.SIGNED, "from_result: signed")
check(len(sr_ok.temporal_signature) == 64, "from_result: has sig")

cr_fail = validate_temporal_contract((0, 1, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
sr_fail = sign_from_contract_result(cr_fail)
check(sr_fail.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED, "from_result: rejected")
check(sr_fail.temporal_signature == "", "from_result: no sig")

# Verify E2E and convenience produce same signature
r_e2e = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
check(sr_ok.temporal_signature == r_e2e.temporal_signature, "E2E == convenience sig")

# ════════════════════════════════════════════════════════════
print("Section 15: Full result JSON round-trip")
result = sign_temporal_payload((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
d = result.to_dict()
s = json.dumps(d)
d2 = json.loads(s)
check(d2["verdict"] == "SIGNED", "round-trip verdict")
check(d2["contract_name"] == "rs_4bit_adjacent", "round-trip contract")
check(d2["payload"] == [0, 0, 1, 0], "round-trip payload")
check(len(d2["temporal_signature"]) == 64, "round-trip sig")

# ════════════════════════════════════════════════════════════
print("Section 16: Cross-mode — same payload, different modes, different sigs")
r_rs = sign_temporal_payload((0, 1, 1, 0), "either_containment", "rolling_shutter")
r_cc = sign_temporal_payload((0, 1, 1, 0), "either_containment", "complementary_color")
r_fused = sign_temporal_payload((0, 1, 1, 0), "either_containment", "fused")
check(r_rs.verdict == SignatureVerdict.SIGNED, "cross-mode rs signed")
check(r_cc.verdict == SignatureVerdict.SIGNED, "cross-mode cc signed")
check(r_fused.verdict == SignatureVerdict.SIGNED, "cross-mode fused signed")
check(r_rs.temporal_signature != r_cc.temporal_signature, "rs != cc sig")
check(r_rs.temporal_signature != r_fused.temporal_signature, "rs != fused sig")
check(r_cc.temporal_signature != r_fused.temporal_signature, "cc != fused sig")

# ════════════════════════════════════════════════════════════
print("Section 17: Predefined case counts")
check(len(SIGN_CASES) == 6, f"sign cases: {len(SIGN_CASES)}")
check(len(REJECT_CASES) == 3, f"reject cases: {len(REJECT_CASES)}")
check(len(OOB_CASES) == 2, f"OOB cases: {len(OOB_CASES)}")
check(len(DIFFERENCE_CASES) == 3, f"difference cases: {len(DIFFERENCE_CASES)}")

# ════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
total = passed + failed
print(f"Temporal Payload Signature Bridge V1 — {total} assertions: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL PASS \u2713")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
