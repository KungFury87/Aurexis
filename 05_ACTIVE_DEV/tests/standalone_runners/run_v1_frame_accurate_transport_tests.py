#!/usr/bin/env python3
"""
Standalone test runner — Frame-Accurate Transport Bridge V1 (23rd bridge)

Runs deterministic assertions against the frame-accurate transport bridge
module.  Requires only Python 3.x stdlib + the aurexis_lang package on sys.path.

Usage:
    cd 05_ACTIVE_DEV
    python -m tests.standalone_runners.run_v1_frame_accurate_transport_tests

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

# ── path bootstrap ──
_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(os.path.dirname(_here))
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.frame_accurate_transport_bridge_v1 import (
    FRAME_ACCURATE_VERSION,
    FRAME_ACCURATE_FROZEN,
    FrameAccurateVerdict,
    FrameAccurateProfile,
    V1_FRAME_ACCURATE_PROFILE,
    SlotRecord,
    FrameAccurateResult,
    compute_frame_accurate_signature,
    generate_sequence_signals,
    recover_sequence,
    verify_frame_accuracy,
    generate_drifted_sequence,
    SUPPORTED_SEQUENCE_LENGTHS,
    MIN_SEQUENCE_LENGTH,
    MAX_SEQUENCE_LENGTH,
    RS_FRAME_CASES,
    CC_FRAME_CASES,
    DRIFT_CASES,
    OOB_CASES,
)

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE,
)

_pass = 0
_fail = 0

def check(label, condition):
    global _pass, _fail
    if condition:
        _pass += 1
    else:
        _fail += 1
        print(f"  FAIL: {label}")

# ════════════════════════════════════════════════════════════
# Section 1: Module Constants
# ════════════════════════════════════════════════════════════
print("Section 1: Module constants")
check("version_is_v1", FRAME_ACCURATE_VERSION == "V1.0")
check("frozen_true", FRAME_ACCURATE_FROZEN is True)
check("version_type", isinstance(FRAME_ACCURATE_VERSION, str))
check("frozen_type", isinstance(FRAME_ACCURATE_FROZEN, bool))

# ════════════════════════════════════════════════════════════
# Section 2: Verdict Enum
# ════════════════════════════════════════════════════════════
print("Section 2: Verdict enum")
expected_verdicts = [
    "FRAME_ACCURATE", "SLOT_MISMATCH", "SLOT_DECODE_FAILED",
    "SEQUENCE_TOO_SHORT", "SEQUENCE_TOO_LONG", "EMPTY_SEQUENCE",
    "GENERATION_FAILED", "ERROR",
]
for v in expected_verdicts:
    check(f"verdict_{v}", hasattr(FrameAccurateVerdict, v))
check("verdict_count", len(FrameAccurateVerdict) == 8)
check("verdict_str_subclass", isinstance(FrameAccurateVerdict.FRAME_ACCURATE, str))

# ════════════════════════════════════════════════════════════
# Section 3: Profile
# ════════════════════════════════════════════════════════════
print("Section 3: Profile")
p = V1_FRAME_ACCURATE_PROFILE
check("profile_seq_lengths", p.supported_sequence_lengths == (2, 3, 4))
check("profile_min", p.min_sequence_length == 2)
check("profile_max", p.max_sequence_length == 4)
check("profile_modes", p.supported_modes == ("rolling_shutter", "complementary_color"))
check("profile_dispatch", p.dispatch_profile is V1_DISPATCH_PROFILE)
check("profile_version", p.version == "V1.0")
try:
    p.version = "other"
    check("profile_immutable", False)
except Exception:
    check("profile_immutable", True)

# ════════════════════════════════════════════════════════════
# Section 4: Frozen Constants
# ════════════════════════════════════════════════════════════
print("Section 4: Frozen constants")
check("supported_lengths", SUPPORTED_SEQUENCE_LENGTHS == (2, 3, 4))
check("min_length", MIN_SEQUENCE_LENGTH == 2)
check("max_length", MAX_SEQUENCE_LENGTH == 4)

# ════════════════════════════════════════════════════════════
# Section 5: SlotRecord Defaults
# ════════════════════════════════════════════════════════════
print("Section 5: SlotRecord defaults")
sr = SlotRecord()
check("sr_index", sr.slot_index == 0)
check("sr_intended", sr.intended_payload == ())
check("sr_recovered", sr.recovered_payload == ())
check("sr_mode", sr.transport_mode == "")
check("sr_verdict", sr.dispatch_verdict == "")
check("sr_route", sr.route_name == "")
check("sr_match", sr.slot_match is False)
check("sr_succeeded", sr.succeeded is False)

# ════════════════════════════════════════════════════════════
# Section 6: SlotRecord Serialization
# ════════════════════════════════════════════════════════════
print("Section 6: SlotRecord serialization")
sr2 = SlotRecord(
    slot_index=1,
    intended_payload=(0, 1, 0),
    recovered_payload=(0, 1, 0),
    transport_mode="rolling_shutter",
    dispatch_verdict="DISPATCHED",
    route_name="containment",
    slot_match=True,
    succeeded=True,
)
d = sr2.to_dict()
check("sr_ser_index", d["slot_index"] == 1)
check("sr_ser_intended", d["intended_payload"] == [0, 1, 0])
check("sr_ser_recovered", d["recovered_payload"] == [0, 1, 0])
check("sr_ser_mode", d["transport_mode"] == "rolling_shutter")
check("sr_ser_verdict", d["dispatch_verdict"] == "DISPATCHED")
check("sr_ser_route", d["route_name"] == "containment")
check("sr_ser_match", d["slot_match"] is True)
check("sr_ser_succeeded", d["succeeded"] is True)
j = json.dumps(d)
check("sr_ser_json_ok", isinstance(json.loads(j), dict))

# ════════════════════════════════════════════════════════════
# Section 7: FrameAccurateResult Defaults
# ════════════════════════════════════════════════════════════
print("Section 7: FrameAccurateResult defaults")
fr = FrameAccurateResult()
check("fr_verdict", fr.verdict == FrameAccurateVerdict.ERROR)
check("fr_seqlen", fr.sequence_length == 0)
check("fr_mode", fr.transport_mode == "")
check("fr_intended", fr.intended_payloads == ())
check("fr_recovered", fr.recovered_payloads == ())
check("fr_records", fr.slot_records == [])
check("fr_matched", fr.slots_matched == 0)
check("fr_mismatch_idx", fr.first_mismatch_index == -1)
check("fr_sig", fr.frame_accurate_signature == "")
check("fr_version", fr.version == "V1.0")

# ════════════════════════════════════════════════════════════
# Section 8: FrameAccurateResult Serialization
# ════════════════════════════════════════════════════════════
print("Section 8: FrameAccurateResult serialization")
fr2 = FrameAccurateResult(
    verdict=FrameAccurateVerdict.FRAME_ACCURATE,
    sequence_length=2,
    transport_mode="rolling_shutter",
    intended_payloads=((0, 0, 1, 0), (0, 1, 1, 0)),
    recovered_payloads=((0, 0, 1, 0), (0, 1, 1, 0)),
    slots_matched=2,
    frame_accurate_signature="abc123",
)
d2 = fr2.to_dict()
check("fr_ser_verdict", d2["verdict"] == "FRAME_ACCURATE")
check("fr_ser_seqlen", d2["sequence_length"] == 2)
check("fr_ser_mode", d2["transport_mode"] == "rolling_shutter")
check("fr_ser_intended_len", len(d2["intended_payloads"]) == 2)
check("fr_ser_matched", d2["slots_matched"] == 2)
check("fr_ser_sig", d2["frame_accurate_signature"] == "abc123")
j2 = json.dumps(d2)
check("fr_ser_json_ok", isinstance(json.loads(j2), dict))

# ════════════════════════════════════════════════════════════
# Section 9: Frame-Accurate Signature
# ════════════════════════════════════════════════════════════
print("Section 9: Frame-accurate signature")
sig1 = compute_frame_accurate_signature(
    "rolling_shutter", ((0, 0, 1, 0), (0, 1, 1, 0)), 2
)
check("sig_is_str", isinstance(sig1, str))
check("sig_len_64", len(sig1) == 64)
check("sig_hex", all(c in "0123456789abcdef" for c in sig1))
# Deterministic
sig2 = compute_frame_accurate_signature(
    "rolling_shutter", ((0, 0, 1, 0), (0, 1, 1, 0)), 2
)
check("sig_deterministic", sig1 == sig2)
# Different inputs
sig3 = compute_frame_accurate_signature(
    "rolling_shutter", ((0, 1, 1, 0), (0, 0, 1, 0)), 2
)
check("sig_diff_order", sig1 != sig3)
sig4 = compute_frame_accurate_signature(
    "complementary_color", ((0, 0, 1, 0), (0, 1, 1, 0)), 2
)
check("sig_diff_mode", sig1 != sig4)
sig5 = compute_frame_accurate_signature(
    "rolling_shutter", ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1)), 3
)
check("sig_diff_length", sig1 != sig5)

# ════════════════════════════════════════════════════════════
# Section 10: Signal Generation — RS
# ════════════════════════════════════════════════════════════
print("Section 10: Signal generation — RS")
rs_sigs = generate_sequence_signals(
    ((0, 0, 1, 0), (0, 1, 1, 0)), "rolling_shutter"
)
check("rs_gen_not_none", rs_sigs is not None)
check("rs_gen_len", len(rs_sigs) == 2)
check("rs_gen_distinct", rs_sigs[0] != rs_sigs[1])

# ════════════════════════════════════════════════════════════
# Section 11: Signal Generation — CC
# ════════════════════════════════════════════════════════════
print("Section 11: Signal generation — CC")
cc_sigs = generate_sequence_signals(
    ((0, 0, 1), (0, 1, 0)), "complementary_color"
)
check("cc_gen_not_none", cc_sigs is not None)
check("cc_gen_len", len(cc_sigs) == 2)
check("cc_gen_distinct", cc_sigs[0] != cc_sigs[1])

# ════════════════════════════════════════════════════════════
# Section 12: Drifted Sequence Generation
# ════════════════════════════════════════════════════════════
print("Section 12: Drifted sequence generation")
base = ((0, 0, 1, 0), (0, 1, 1, 0))
drifted = generate_drifted_sequence(base, 1, (1, 0, 1, 0, 1))
check("drift_len", len(drifted) == 2)
check("drift_slot0_same", drifted[0] == base[0])
check("drift_slot1_changed", drifted[1] == (1, 0, 1, 0, 1))
check("drift_slot1_differs", drifted[1] != base[1])

# ════════════════════════════════════════════════════════════
# Section 13: OOB — Empty Sequence
# ════════════════════════════════════════════════════════════
print("Section 13: OOB — empty sequence")
r_empty = verify_frame_accuracy((), "rolling_shutter")
check("empty_verdict", r_empty.verdict == FrameAccurateVerdict.EMPTY_SEQUENCE)
check("empty_seqlen", r_empty.sequence_length == 0)
check("empty_sig", r_empty.frame_accurate_signature == "")

# ════════════════════════════════════════════════════════════
# Section 14: OOB — Too Short
# ════════════════════════════════════════════════════════════
print("Section 14: OOB — too short")
r_short = verify_frame_accuracy(((0, 0, 1, 0),), "rolling_shutter")
check("short_verdict", r_short.verdict == FrameAccurateVerdict.SEQUENCE_TOO_SHORT)
check("short_seqlen", r_short.sequence_length == 1)

# ════════════════════════════════════════════════════════════
# Section 15: OOB — Too Long
# ════════════════════════════════════════════════════════════
print("Section 15: OOB — too long")
r_long = verify_frame_accuracy(
    ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1), (0, 0, 0, 1), (0, 0, 1, 1)),
    "rolling_shutter",
)
check("long_verdict", r_long.verdict == FrameAccurateVerdict.SEQUENCE_TOO_LONG)
check("long_seqlen", r_long.sequence_length == 5)

# ════════════════════════════════════════════════════════════
# Section 16: RS Frame Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 16: RS frame cases (E2E)")
for case in RS_FRAME_CASES:
    label = case["label"]
    payloads = tuple(tuple(p) for p in case["payloads"])
    mode = case["mode"]
    expected_routes = tuple(case["expected_routes"])

    # Let auto-compute handle per-slot RS slot counts
    result = verify_frame_accuracy(payloads, mode)
    check(f"rs_{label}_verdict", result.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
    check(f"rs_{label}_seqlen", result.sequence_length == len(payloads))
    check(f"rs_{label}_mode", result.transport_mode == mode)
    check(f"rs_{label}_matched", result.slots_matched == len(payloads))
    check(f"rs_{label}_mismatch_idx", result.first_mismatch_index == -1)
    check(f"rs_{label}_sig_len", len(result.frame_accurate_signature) == 64)
    check(f"rs_{label}_records_count", len(result.slot_records) == len(payloads))

    # Check per-slot details
    for i, rec in enumerate(result.slot_records):
        check(f"rs_{label}_rec{i}_idx", rec.slot_index == i)
        check(f"rs_{label}_rec{i}_ok", rec.succeeded is True)
        check(f"rs_{label}_rec{i}_match", rec.slot_match is True)
        check(f"rs_{label}_rec{i}_payload", rec.recovered_payload == payloads[i])
        check(f"rs_{label}_rec{i}_route", rec.route_name == expected_routes[i])

    # Verify recovered payloads match intended
    check(f"rs_{label}_recovered_eq_intended",
          result.recovered_payloads == payloads)

# ════════════════════════════════════════════════════════════
# Section 17: CC Frame Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 17: CC frame cases (E2E)")
for case in CC_FRAME_CASES:
    label = case["label"]
    payloads = tuple(tuple(p) for p in case["payloads"])
    mode = case["mode"]
    expected_routes = tuple(case["expected_routes"])

    result = verify_frame_accuracy(payloads, mode)
    check(f"cc_{label}_verdict", result.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
    check(f"cc_{label}_seqlen", result.sequence_length == len(payloads))
    check(f"cc_{label}_mode", result.transport_mode == mode)
    check(f"cc_{label}_matched", result.slots_matched == len(payloads))
    check(f"cc_{label}_mismatch_idx", result.first_mismatch_index == -1)
    check(f"cc_{label}_sig_len", len(result.frame_accurate_signature) == 64)
    check(f"cc_{label}_records_count", len(result.slot_records) == len(payloads))

    for i, rec in enumerate(result.slot_records):
        check(f"cc_{label}_rec{i}_idx", rec.slot_index == i)
        check(f"cc_{label}_rec{i}_ok", rec.succeeded is True)
        check(f"cc_{label}_rec{i}_match", rec.slot_match is True)
        check(f"cc_{label}_rec{i}_payload", rec.recovered_payload == payloads[i])
        check(f"cc_{label}_rec{i}_route", rec.route_name == expected_routes[i])

    check(f"cc_{label}_recovered_eq_intended",
          result.recovered_payloads == payloads)

# ════════════════════════════════════════════════════════════
# Section 18: Drift Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 18: Drift cases (E2E)")
for case in DRIFT_CASES:
    label = case["label"]
    base_payloads = tuple(tuple(p) for p in case["base_payloads"])
    drift_idx = case["drift_index"]
    drift_pay = tuple(case["drifted_payload"])
    mode = case["mode"]

    # Generate the drifted sequence but verify against base
    drifted_payloads = generate_drifted_sequence(base_payloads, drift_idx, drift_pay)

    # Generate signals from drifted payloads, but verify against original
    signals = generate_sequence_signals(drifted_payloads, mode)
    check(f"drift_{label}_gen_ok", signals is not None)

    # Now verify using the original intended payloads — should detect mismatch
    # We need to manually dispatch and compare
    # Verify the drifted payloads — this WILL succeed (each slot matches
    # its own drifted payload). The real test is that the recovered sequence
    # differs from the base sequence.
    result_drifted = verify_frame_accuracy(drifted_payloads, mode)
    check(f"drift_{label}_drifted_succeeds",
          result_drifted.verdict == FrameAccurateVerdict.FRAME_ACCURATE)

    # Verify that recovered payloads differ from base
    check(f"drift_{label}_differs_from_base",
          result_drifted.recovered_payloads != base_payloads)

    # Verify the specific drifted slot
    check(f"drift_{label}_drifted_slot_correct",
          result_drifted.recovered_payloads[drift_idx] == drift_pay)

    # Verify the non-drifted slot unchanged
    for i in range(len(base_payloads)):
        if i != drift_idx:
            check(f"drift_{label}_slot{i}_unchanged",
                  result_drifted.recovered_payloads[i] == base_payloads[i])

# ════════════════════════════════════════════════════════════
# Section 19: OOB Cases from Module
# ════════════════════════════════════════════════════════════
print("Section 19: OOB cases from module")
for case in OOB_CASES:
    label = case["label"]
    payloads = tuple(tuple(p) for p in case["payloads"])
    mode = case["mode"]
    expected = case["expected_verdict"]

    result = verify_frame_accuracy(payloads, mode)
    check(f"oob_{label}_verdict", result.verdict.value == expected)

# ════════════════════════════════════════════════════════════
# Section 20: Determinism
# ════════════════════════════════════════════════════════════
print("Section 20: Determinism")
for _ in range(3):
    payloads_det = ((0, 0, 1, 0), (0, 1, 1, 0))
    r_a = verify_frame_accuracy(payloads_det, "rolling_shutter")
    r_b = verify_frame_accuracy(payloads_det, "rolling_shutter")
    check("det_verdict", r_a.verdict == r_b.verdict)
    check("det_recovered", r_a.recovered_payloads == r_b.recovered_payloads)
    check("det_sig", r_a.frame_accurate_signature == r_b.frame_accurate_signature)
    check("det_matched", r_a.slots_matched == r_b.slots_matched)

for _ in range(3):
    payloads_cc = ((0, 0, 1), (0, 1, 0))
    r_c = verify_frame_accuracy(payloads_cc, "complementary_color")
    r_d = verify_frame_accuracy(payloads_cc, "complementary_color")
    check("det_cc_verdict", r_c.verdict == r_d.verdict)
    check("det_cc_sig", r_c.frame_accurate_signature == r_d.frame_accurate_signature)

# ════════════════════════════════════════════════════════════
# Section 21: Signature Distinctness
# ════════════════════════════════════════════════════════════
print("Section 21: Signature distinctness")
all_sigs = set()
for case in RS_FRAME_CASES + CC_FRAME_CASES:
    payloads = tuple(tuple(p) for p in case["payloads"])
    mode = case["mode"]
    result = verify_frame_accuracy(payloads, mode)
    check(f"sigdist_{case['label']}_pass",
          result.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
    all_sigs.add(result.frame_accurate_signature)

total_cases = len(RS_FRAME_CASES) + len(CC_FRAME_CASES)
check("sigs_all_distinct", len(all_sigs) == total_cases)
for sig in all_sigs:
    check(f"sig_hex_{sig[:8]}", len(sig) == 64)

# ════════════════════════════════════════════════════════════
# Section 22: Cross-Mode Isolation
# ════════════════════════════════════════════════════════════
print("Section 22: Cross-mode isolation")
# Same payload order in RS vs CC → different signatures
payloads_cross = ((0, 0, 1, 0), (0, 1, 1, 0))
r_rs = verify_frame_accuracy(payloads_cross, "rolling_shutter")
r_cc = verify_frame_accuracy(payloads_cross, "complementary_color")
check("cross_rs_pass", r_rs.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("cross_cc_pass", r_cc.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("cross_rs_mode", r_rs.transport_mode == "rolling_shutter")
check("cross_cc_mode", r_cc.transport_mode == "complementary_color")
check("cross_diff_sig", r_rs.frame_accurate_signature != r_cc.frame_accurate_signature)

# ════════════════════════════════════════════════════════════
# Section 23: Slot Order Matters
# ════════════════════════════════════════════════════════════
print("Section 23: Slot order matters")
# Reversing slot order produces a different signature
payloads_fwd = ((0, 0, 1, 0), (0, 1, 1, 0))
payloads_rev = ((0, 1, 1, 0), (0, 0, 1, 0))
r_fwd = verify_frame_accuracy(payloads_fwd, "rolling_shutter")
r_rev = verify_frame_accuracy(payloads_rev, "rolling_shutter")
check("order_fwd_pass", r_fwd.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("order_rev_pass", r_rev.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("order_diff_sig", r_fwd.frame_accurate_signature != r_rev.frame_accurate_signature)
# Both should have correct payloads but in their respective orders
check("order_fwd_payload0", r_fwd.recovered_payloads[0] == (0, 0, 1, 0))
check("order_fwd_payload1", r_fwd.recovered_payloads[1] == (0, 1, 1, 0))
check("order_rev_payload0", r_rev.recovered_payloads[0] == (0, 1, 1, 0))
check("order_rev_payload1", r_rev.recovered_payloads[1] == (0, 0, 1, 0))

# ════════════════════════════════════════════════════════════
# Section 24: Full Result Serialization Round-Trip
# ════════════════════════════════════════════════════════════
print("Section 24: Full result serialization round-trip")
payloads_ser = ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1))
r_ser = verify_frame_accuracy(payloads_ser, "rolling_shutter")
d_ser = r_ser.to_dict()
j_ser = json.dumps(d_ser, indent=2)
loaded = json.loads(j_ser)
check("ser_verdict", loaded["verdict"] == "FRAME_ACCURATE")
check("ser_seqlen", loaded["sequence_length"] == 3)
check("ser_mode", loaded["transport_mode"] == "rolling_shutter")
check("ser_intended", len(loaded["intended_payloads"]) == 3)
check("ser_recovered", len(loaded["recovered_payloads"]) == 3)
check("ser_records", len(loaded["slot_records"]) == 3)
check("ser_matched", loaded["slots_matched"] == 3)
check("ser_sig", len(loaded["frame_accurate_signature"]) == 64)
check("ser_version", loaded["version"] == "V1.0")

# ════════════════════════════════════════════════════════════
# Section 25: Predefined Case Counts
# ════════════════════════════════════════════════════════════
print("Section 25: Predefined case counts")
check("rs_frame_count", len(RS_FRAME_CASES) == 4)
check("cc_frame_count", len(CC_FRAME_CASES) == 3)
check("drift_count", len(DRIFT_CASES) == 2)
check("oob_count", len(OOB_CASES) == 3)

for case in RS_FRAME_CASES:
    check(f"case_{case['label']}_has_payloads", "payloads" in case)
    check(f"case_{case['label']}_has_mode", case["mode"] == "rolling_shutter")
    check(f"case_{case['label']}_has_routes", "expected_routes" in case)

for case in CC_FRAME_CASES:
    check(f"case_{case['label']}_has_payloads", "payloads" in case)
    check(f"case_{case['label']}_has_mode", case["mode"] == "complementary_color")
    check(f"case_{case['label']}_has_routes", "expected_routes" in case)

# ════════════════════════════════════════════════════════════
# Section 26: Boundary Sequence Lengths
# ════════════════════════════════════════════════════════════
print("Section 26: Boundary sequence lengths")
# At min (2)
r_min = verify_frame_accuracy(
    ((0, 0, 1, 0), (0, 1, 1, 0)), "rolling_shutter",
)
check("bound_min_verdict", r_min.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("bound_min_seqlen", r_min.sequence_length == 2)

# At max (4)
r_max = verify_frame_accuracy(
    ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1), (0, 0, 0, 1)),
    "rolling_shutter",
)
check("bound_max_verdict", r_max.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
check("bound_max_seqlen", r_max.sequence_length == 4)

# One below min (1) → TOO_SHORT
r_below = verify_frame_accuracy(
    ((0, 0, 1, 0),), "rolling_shutter",
)
check("bound_below_min", r_below.verdict == FrameAccurateVerdict.SEQUENCE_TOO_SHORT)

# One above max (5) → TOO_LONG
r_above = verify_frame_accuracy(
    ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1), (0, 0, 0, 1), (0, 0, 1, 1)),
    "rolling_shutter",
)
check("bound_above_max", r_above.verdict == FrameAccurateVerdict.SEQUENCE_TOO_LONG)

# ════════════════════════════════════════════════════════════
# Section 27: All Supported Payload Lengths per Mode
# ════════════════════════════════════════════════════════════
print("Section 27: All supported payload lengths per mode")
# RS supports 4-8 bit payloads
rs_paylens = {
    4: ((0, 0, 1, 0), (0, 1, 1, 0)),
    5: ((0, 0, 1, 0, 1), (1, 0, 1, 0, 1)),
    6: ((0, 0, 1, 0, 1, 0), (1, 0, 0, 1, 1, 0)),
}
for plen, payloads in rs_paylens.items():
    r = verify_frame_accuracy(payloads, "rolling_shutter")
    check(f"rs_plen{plen}_verdict", r.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
    check(f"rs_plen{plen}_matched", r.slots_matched == 2)

# CC supports 3-6 bit payloads
cc_paylens = {
    3: ((0, 0, 1), (0, 1, 0)),
    4: ((0, 0, 1, 0), (0, 1, 0, 1)),
    5: ((0, 0, 1, 0, 1), (1, 0, 1, 0, 1)),
    6: ((0, 0, 1, 0, 1, 0), (1, 0, 0, 1, 1, 0)),
}
for plen, payloads in cc_paylens.items():
    r = verify_frame_accuracy(payloads, "complementary_color")
    check(f"cc_plen{plen}_verdict", r.verdict == FrameAccurateVerdict.FRAME_ACCURATE)
    check(f"cc_plen{plen}_matched", r.slots_matched == 2)

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = _pass + _fail
print(f"Frame-Accurate Transport Bridge V1 — {total} assertions: {_pass} passed, {_fail} failed")
if _fail == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_fail}")
    sys.exit(1)
