#!/usr/bin/env python3
"""
Standalone test runner — Temporal Payload Contract Bridge V1 (25th bridge)

Tests the bounded temporal structure validation proof.
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

from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    CONTRACT_VERSION,
    CONTRACT_FROZEN,
    ContractVerdict,
    TemporalContract,
    TemporalContractProfile,
    V1_CONTRACT_PROFILE,
    TemporalContractResult,
    compute_contract_signature,
    validate_temporal_contract,
    FROZEN_CONTRACTS,
    CONTRACT_MAP,
    RS_4BIT_ADJACENT,
    CC_ANY_FAMILY,
    EITHER_CONTAINMENT,
    FUSED_ANY_FAMILY,
    RS_LARGE_THREE_REGIONS,
    SATISFY_CASES,
    WRONG_LENGTH_CASES,
    WRONG_FAMILY_CASES,
    WRONG_MODE_CASES,
    FUSED_REQUIRED_CASES,
    OOB_CASES,
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
check(CONTRACT_VERSION == "V1.0", "version is V1.0")
check(CONTRACT_FROZEN is True, "frozen is True")

# ════════════════════════════════════════════════════════════
print("Section 2: Verdict enum")
expected_verdicts = [
    "CONTRACT_SATISFIED", "WRONG_PAYLOAD_LENGTH", "WRONG_PAYLOAD_FAMILY",
    "WRONG_TRANSPORT_MODE", "FUSED_REQUIRED", "DECODE_FAILED",
    "EMPTY_PAYLOAD", "UNSUPPORTED_CONTRACT", "ERROR",
]
for v in expected_verdicts:
    check(hasattr(ContractVerdict, v), f"verdict {v} exists")
check(len(ContractVerdict) == 9, f"verdict count is 9, got {len(ContractVerdict)}")

# ════════════════════════════════════════════════════════════
print("Section 3: Contract profile")
check(len(V1_CONTRACT_PROFILE.supported_contracts) == 5, "5 supported contracts")
check(V1_CONTRACT_PROFILE.version == "V1.0", "profile version V1.0")

# ════════════════════════════════════════════════════════════
print("Section 4: Frozen contracts")
check(len(FROZEN_CONTRACTS) == 5, "5 frozen contracts")
check(len(CONTRACT_MAP) == 5, "5 contracts in map")
for c in FROZEN_CONTRACTS:
    check(c.name in CONTRACT_MAP, f"contract {c.name} in map")
    check(len(c.allowed_payload_lengths) > 0, f"{c.name} has payload lengths")
    check(len(c.allowed_payload_families) > 0, f"{c.name} has families")
    check(len(c.allowed_transport_modes) > 0, f"{c.name} has modes")

# ════════════════════════════════════════════════════════════
print("Section 5: Contract immutability")
try:
    RS_4BIT_ADJACENT.name = "hacked"
    check(False, "contract should be immutable")
except Exception:
    check(True, "contract is immutable")

try:
    V1_CONTRACT_PROFILE.version = "hacked"
    check(False, "profile should be immutable")
except Exception:
    check(True, "profile is immutable")

# ════════════════════════════════════════════════════════════
print("Section 6: Individual contract details")
check(RS_4BIT_ADJACENT.allowed_payload_lengths == (4,), "rs_4bit: lengths=(4,)")
check(RS_4BIT_ADJACENT.allowed_payload_families == ("adjacent_pair",), "rs_4bit: families=(adj,)")
check(RS_4BIT_ADJACENT.allowed_transport_modes == ("rolling_shutter",), "rs_4bit: modes=(rs,)")
check(RS_4BIT_ADJACENT.require_fused is False, "rs_4bit: not fused")

check(CC_ANY_FAMILY.allowed_payload_lengths == (3, 4, 5, 6), "cc_any: lengths=(3-6)")
check(len(CC_ANY_FAMILY.allowed_payload_families) == 3, "cc_any: 3 families")
check(CC_ANY_FAMILY.allowed_transport_modes == ("complementary_color",), "cc_any: modes=(cc,)")

check(EITHER_CONTAINMENT.allowed_payload_families == ("containment",), "either_cont: family=(containment,)")
check(len(EITHER_CONTAINMENT.allowed_transport_modes) == 3, "either_cont: 3 modes")

check(FUSED_ANY_FAMILY.require_fused is True, "fused_any: require_fused=True")
check(FUSED_ANY_FAMILY.allowed_transport_modes == ("fused",), "fused_any: modes=(fused,)")

check(RS_LARGE_THREE_REGIONS.allowed_payload_lengths == (5, 6, 7, 8), "rs_large: lengths=(5-8)")
check(RS_LARGE_THREE_REGIONS.allowed_payload_families == ("three_regions",), "rs_large: family=(three_regions,)")

# ════════════════════════════════════════════════════════════
print("Section 7: Contract serialization")
for c in FROZEN_CONTRACTS:
    d = c.to_dict()
    check(isinstance(json.dumps(d), str), f"{c.name} serializes to JSON")

# ════════════════════════════════════════════════════════════
print("Section 8: Result defaults")
r = TemporalContractResult()
check(r.verdict == ContractVerdict.ERROR, "default verdict is ERROR")
check(r.contract_name == "", "default contract_name is empty")
check(r.payload == (), "default payload is empty")
check(r.payload_length == 0, "default payload_length is 0")
check(r.is_fused is False, "default is_fused is False")

# ════════════════════════════════════════════════════════════
print("Section 9: Result serialization")
r = TemporalContractResult(
    verdict=ContractVerdict.CONTRACT_SATISFIED,
    contract_name="test",
    payload=(0, 0, 1, 0),
    payload_length=4,
    payload_family="adjacent_pair",
    transport_mode="rolling_shutter",
)
d = r.to_dict()
check(d["verdict"] == "CONTRACT_SATISFIED", "result verdict in dict")
check(d["payload"] == [0, 0, 1, 0], "result payload in dict")
check(isinstance(json.dumps(d), str), "result serializes to JSON")

# ════════════════════════════════════════════════════════════
print("Section 10: Signature determinism")
s1 = compute_contract_signature("CONTRACT_SATISFIED", "test", (0, 0, 1, 0), "adj", "rs")
s2 = compute_contract_signature("CONTRACT_SATISFIED", "test", (0, 0, 1, 0), "adj", "rs")
check(s1 == s2, "signature deterministic")
check(len(s1) == 64, "signature is 64 hex chars")

s3 = compute_contract_signature("WRONG_PAYLOAD_LENGTH", "test", (0, 0, 1, 0), "adj", "rs")
check(s1 != s3, "different verdict different signature")

# ════════════════════════════════════════════════════════════
print("Section 11: Satisfy cases (E2E)")
for case in SATISFY_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == ContractVerdict.CONTRACT_SATISFIED,
        f"{case['label']}: verdict={result.verdict.value}"
    )
    check(
        len(result.contract_signature) == 64,
        f"{case['label']}: has signature"
    )
    check(
        result.payload_length > 0,
        f"{case['label']}: payload_length > 0"
    )
    check(
        result.payload_family != "",
        f"{case['label']}: has family"
    )

# ════════════════════════════════════════════════════════════
print("Section 12: Wrong length cases")
for case in WRONG_LENGTH_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == ContractVerdict.WRONG_PAYLOAD_LENGTH,
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 13: Wrong family cases")
for case in WRONG_FAMILY_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == ContractVerdict.WRONG_PAYLOAD_FAMILY,
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 14: Wrong mode cases")
for case in WRONG_MODE_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == ContractVerdict.WRONG_TRANSPORT_MODE,
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 15: Fused required cases")
for case in FUSED_REQUIRED_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    # These fail because mode is not in allowed_transport_modes
    check(
        result.verdict == ContractVerdict[case["expected_verdict"]],
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 16: OOB cases")
for case in OOB_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    check(
        result.verdict == ContractVerdict[case["expected_verdict"]],
        f"{case['label']}: verdict={result.verdict.value}"
    )

# ════════════════════════════════════════════════════════════
print("Section 17: Determinism")
for _ in range(3):
    r1 = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
    r2 = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
    check(r1.contract_signature == r2.contract_signature, "deterministic signature")
    check(r1.verdict == r2.verdict, "deterministic verdict")

# ════════════════════════════════════════════════════════════
print("Section 18: Signature distinctness across satisfy cases")
sigs = set()
for case in SATISFY_CASES:
    result = validate_temporal_contract(
        tuple(case["payload"]),
        case["contract"],
        case["mode"],
    )
    sigs.add(result.contract_signature)
check(len(sigs) == len(SATISFY_CASES), f"all {len(SATISFY_CASES)} satisfy sigs unique, got {len(sigs)}")

# ════════════════════════════════════════════════════════════
print("Section 19: Full result JSON round-trip")
result = validate_temporal_contract((0, 0, 1, 0), "rs_4bit_adjacent", "rolling_shutter")
d = result.to_dict()
s = json.dumps(d)
d2 = json.loads(s)
check(d2["verdict"] == "CONTRACT_SATISFIED", "round-trip verdict")
check(d2["contract_name"] == "rs_4bit_adjacent", "round-trip contract name")
check(d2["payload"] == [0, 0, 1, 0], "round-trip payload")
check(d2["payload_family"] == "adjacent_pair", "round-trip family")
check(d2["transport_mode"] == "rolling_shutter", "round-trip mode")

# ════════════════════════════════════════════════════════════
print("Section 20: Cross-mode contract — same payload, different modes")
r_rs = validate_temporal_contract((0, 1, 1, 0), "either_containment", "rolling_shutter")
r_cc = validate_temporal_contract((0, 1, 1, 0), "either_containment", "complementary_color")
r_fused = validate_temporal_contract((0, 1, 1, 0), "either_containment", "fused")
check(r_rs.verdict == ContractVerdict.CONTRACT_SATISFIED, "cross-mode rs satisfied")
check(r_cc.verdict == ContractVerdict.CONTRACT_SATISFIED, "cross-mode cc satisfied")
check(r_fused.verdict == ContractVerdict.CONTRACT_SATISFIED, "cross-mode fused satisfied")
check(r_rs.transport_mode != r_cc.transport_mode, "different modes")
check(r_fused.is_fused is True, "fused flag set")

# ════════════════════════════════════════════════════════════
print("Section 21: Predefined case counts")
check(len(SATISFY_CASES) == 8, f"satisfy cases: {len(SATISFY_CASES)}")
check(len(WRONG_LENGTH_CASES) == 2, f"wrong length cases: {len(WRONG_LENGTH_CASES)}")
check(len(WRONG_FAMILY_CASES) == 2, f"wrong family cases: {len(WRONG_FAMILY_CASES)}")
check(len(WRONG_MODE_CASES) == 2, f"wrong mode cases: {len(WRONG_MODE_CASES)}")
check(len(FUSED_REQUIRED_CASES) == 2, f"fused required cases: {len(FUSED_REQUIRED_CASES)}")
check(len(OOB_CASES) == 3, f"OOB cases: {len(OOB_CASES)}")

# ════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
total = passed + failed
print(f"Temporal Payload Contract Bridge V1 — {total} assertions: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL PASS \u2713")
else:
    print(f"FAILURES: {failed}")
    sys.exit(1)
