#!/usr/bin/env python3
"""
Standalone test runner — Temporal Consistency Bridge V1 (22nd bridge)

Runs deterministic assertions against the temporal consistency bridge module.
Requires only Python 3.x stdlib + the aurexis_lang package on sys.path.

Usage:
    cd 05_ACTIVE_DEV
    python -m tests.standalone_runners.run_v1_temporal_consistency_tests

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

# ── path bootstrap ──
_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(os.path.dirname(_here))
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.temporal_consistency_bridge_v1 import (
    CONSISTENCY_VERSION,
    CONSISTENCY_FROZEN,
    ConsistencyVerdict,
    TemporalConsistencyProfile,
    V1_CONSISTENCY_PROFILE,
    CaptureRecord,
    TemporalConsistencyResult,
    compute_consistency_signature,
    check_temporal_consistency,
    generate_repeated_rs_captures,
    generate_repeated_cc_captures,
    generate_drifted_capture_set,
    CONSISTENT_CASES,
    INCONSISTENT_CASES,
    OOB_CASES,
)

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE,
    TemporalDispatchProfile,
    DispatchVerdict,
    generate_rs_signal,
    generate_cc_signal,
)

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
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
check("version_is_v1", CONSISTENCY_VERSION == "V1.0")
check("frozen_true", CONSISTENCY_FROZEN is True)
check("version_type", isinstance(CONSISTENCY_VERSION, str))
check("frozen_type", isinstance(CONSISTENCY_FROZEN, bool))

# ════════════════════════════════════════════════════════════
# Section 2: Consistency Verdict Enum
# ════════════════════════════════════════════════════════════
print("Section 2: Consistency verdict enum")
expected_verdicts = [
    "CONSISTENT", "INCONSISTENT", "CAPTURE_FAILED",
    "TOO_FEW_CAPTURES", "TOO_MANY_CAPTURES", "EMPTY_SET", "ERROR",
]
for v in expected_verdicts:
    check(f"verdict_{v}", hasattr(ConsistencyVerdict, v))
check("verdict_count", len(ConsistencyVerdict) == 7)
check("verdict_str_subclass", isinstance(ConsistencyVerdict.CONSISTENT, str))
check("verdict_value_match", ConsistencyVerdict.CONSISTENT.value == "CONSISTENT")

# ════════════════════════════════════════════════════════════
# Section 3: Consistency Profile
# ════════════════════════════════════════════════════════════
print("Section 3: Consistency profile")
p = V1_CONSISTENCY_PROFILE
check("profile_min_captures", p.min_captures == 2)
check("profile_max_captures", p.max_captures == 10)
check("profile_threshold", p.agreement_threshold == 1.0)
check("profile_modes", p.supported_modes == ("rolling_shutter", "complementary_color"))
check("profile_dispatch", p.dispatch_profile is V1_DISPATCH_PROFILE)
check("profile_version", p.version == "V1.0")
# Frozen
try:
    p.version = "other"
    check("profile_immutable", False)
except Exception:
    check("profile_immutable", True)

# ════════════════════════════════════════════════════════════
# Section 4: CaptureRecord Defaults
# ════════════════════════════════════════════════════════════
print("Section 4: CaptureRecord defaults")
rec = CaptureRecord()
check("rec_index_default", rec.capture_index == 0)
check("rec_verdict_default", rec.dispatch_verdict == "")
check("rec_mode_default", rec.identified_mode == "")
check("rec_payload_default", rec.decoded_payload == ())
check("rec_route_default", rec.route_name == "")
check("rec_succeeded_default", rec.succeeded is False)

# ════════════════════════════════════════════════════════════
# Section 5: CaptureRecord Serialization
# ════════════════════════════════════════════════════════════
print("Section 5: CaptureRecord serialization")
rec2 = CaptureRecord(
    capture_index=1,
    dispatch_verdict="DISPATCHED",
    identified_mode="rolling_shutter",
    decoded_payload=(0, 1, 0),
    route_name="adjacent_pair",
    succeeded=True,
)
d = rec2.to_dict()
check("rec_ser_index", d["capture_index"] == 1)
check("rec_ser_verdict", d["dispatch_verdict"] == "DISPATCHED")
check("rec_ser_mode", d["identified_mode"] == "rolling_shutter")
check("rec_ser_payload", d["decoded_payload"] == [0, 1, 0])
check("rec_ser_route", d["route_name"] == "adjacent_pair")
check("rec_ser_succeeded", d["succeeded"] is True)
# JSON round-trip
j = json.dumps(d)
check("rec_ser_json_ok", isinstance(json.loads(j), dict))

# ════════════════════════════════════════════════════════════
# Section 6: ConsistencyResult Defaults
# ════════════════════════════════════════════════════════════
print("Section 6: ConsistencyResult defaults")
cr = TemporalConsistencyResult()
check("cr_verdict_default", cr.verdict == ConsistencyVerdict.ERROR)
check("cr_payload_default", cr.common_payload == ())
check("cr_route_default", cr.common_route == "")
check("cr_mode_default", cr.common_mode == "")
check("cr_count_default", cr.capture_count == 0)
check("cr_agree_default", cr.agree_count == 0)
check("cr_disagree_default", cr.disagree_index == -1)
check("cr_records_default", cr.capture_records == [])
check("cr_sig_default", cr.consistency_signature == "")
check("cr_version_default", cr.version == "V1.0")

# ════════════════════════════════════════════════════════════
# Section 7: ConsistencyResult Serialization
# ════════════════════════════════════════════════════════════
print("Section 7: ConsistencyResult serialization")
cr2 = TemporalConsistencyResult(
    verdict=ConsistencyVerdict.CONSISTENT,
    common_payload=(0, 1, 0),
    common_route="adjacent_pair",
    common_mode="rolling_shutter",
    capture_count=3,
    agree_count=3,
    capture_records=[rec2],
    consistency_signature="abc123",
)
d2 = cr2.to_dict()
check("cr_ser_verdict", d2["verdict"] == "CONSISTENT")
check("cr_ser_payload", d2["common_payload"] == [0, 1, 0])
check("cr_ser_route", d2["common_route"] == "adjacent_pair")
check("cr_ser_mode", d2["common_mode"] == "rolling_shutter")
check("cr_ser_count", d2["capture_count"] == 3)
check("cr_ser_agree", d2["agree_count"] == 3)
check("cr_ser_disagree", d2["disagree_index"] == -1)
check("cr_ser_records_len", len(d2["capture_records"]) == 1)
check("cr_ser_sig", d2["consistency_signature"] == "abc123")
check("cr_ser_version", d2["version"] == "V1.0")
# JSON round-trip
j2 = json.dumps(d2)
check("cr_ser_json_ok", isinstance(json.loads(j2), dict))

# ════════════════════════════════════════════════════════════
# Section 8: Consistency Signature
# ════════════════════════════════════════════════════════════
print("Section 8: Consistency signature")
sig1 = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adjacent_pair", 3)
check("sig_is_str", isinstance(sig1, str))
check("sig_len_64", len(sig1) == 64)
check("sig_hex", all(c in "0123456789abcdef" for c in sig1))
# Deterministic
sig2 = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adjacent_pair", 3)
check("sig_deterministic", sig1 == sig2)
# Different inputs → different sigs
sig3 = compute_consistency_signature("rolling_shutter", (1, 1, 0), "adjacent_pair", 3)
check("sig_diff_payload", sig1 != sig3)
sig4 = compute_consistency_signature("complementary_color", (0, 1, 0), "adjacent_pair", 3)
check("sig_diff_mode", sig1 != sig4)
sig5 = compute_consistency_signature("rolling_shutter", (0, 1, 0), "containment", 3)
check("sig_diff_route", sig1 != sig5)
sig6 = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adjacent_pair", 5)
check("sig_diff_count", sig1 != sig6)

# ════════════════════════════════════════════════════════════
# Section 9: Generate Repeated RS Captures
# ════════════════════════════════════════════════════════════
print("Section 9: Generate repeated RS captures")
rs_caps = generate_repeated_rs_captures((0, 0, 1, 0), 3)
check("rs_caps_len", len(rs_caps) == 3)
check("rs_caps_identical", all(c == rs_caps[0] for c in rs_caps))
check("rs_caps_nonempty", rs_caps[0] is not None)
# Edge: count=0
rs_caps0 = generate_repeated_rs_captures((0, 0, 1, 0), 0)
check("rs_caps_zero", len(rs_caps0) == 0)

# ════════════════════════════════════════════════════════════
# Section 10: Generate Repeated CC Captures
# ════════════════════════════════════════════════════════════
print("Section 10: Generate repeated CC captures")
cc_caps = generate_repeated_cc_captures((1, 0, 1), 4)
check("cc_caps_len", len(cc_caps) == 4)
check("cc_caps_identical", all(c == cc_caps[0] for c in cc_caps))
check("cc_caps_nonempty", cc_caps[0] is not None)
# Edge: count=0
cc_caps0 = generate_repeated_cc_captures((1, 0, 1), 0)
check("cc_caps_zero", len(cc_caps0) == 0)

# ════════════════════════════════════════════════════════════
# Section 11: Generate Drifted Capture Set — RS
# ════════════════════════════════════════════════════════════
print("Section 11: Generate drifted capture set — RS")
drift_rs = generate_drifted_capture_set(
    payload_a=(0, 0, 1, 0),
    payload_b=(0, 1, 1, 0),
    mode="rolling_shutter",
    count_a=2,
    count_b=1,
)
check("drift_rs_len", len(drift_rs) == 3)
check("drift_rs_first_two_same", drift_rs[0] == drift_rs[1])
check("drift_rs_last_differs", drift_rs[0] != drift_rs[2])

# ════════════════════════════════════════════════════════════
# Section 12: Generate Drifted Capture Set — CC
# ════════════════════════════════════════════════════════════
print("Section 12: Generate drifted capture set — CC")
drift_cc = generate_drifted_capture_set(
    payload_a=(0, 0, 1),
    payload_b=(1, 0, 1),
    mode="complementary_color",
    count_a=1,
    count_b=2,
)
check("drift_cc_len", len(drift_cc) == 3)
check("drift_cc_last_two_same", drift_cc[1] == drift_cc[2])
check("drift_cc_first_differs", drift_cc[0] != drift_cc[1])

# ════════════════════════════════════════════════════════════
# Section 13: OOB — Empty Set
# ════════════════════════════════════════════════════════════
print("Section 13: OOB — empty set")
r_empty = check_temporal_consistency([])
check("empty_verdict", r_empty.verdict == ConsistencyVerdict.EMPTY_SET)
check("empty_count", r_empty.capture_count == 0)
check("empty_agree", r_empty.agree_count == 0)
check("empty_sig", r_empty.consistency_signature == "")

# ════════════════════════════════════════════════════════════
# Section 14: OOB — Too Few Captures
# ════════════════════════════════════════════════════════════
print("Section 14: OOB — too few captures")
single_rs = generate_repeated_rs_captures((0, 0, 1, 0), 1)
r_few = check_temporal_consistency(single_rs)
check("few_verdict", r_few.verdict == ConsistencyVerdict.TOO_FEW_CAPTURES)
check("few_count", r_few.capture_count == 1)
check("few_sig", r_few.consistency_signature == "")

# ════════════════════════════════════════════════════════════
# Section 15: OOB — Too Many Captures
# ════════════════════════════════════════════════════════════
print("Section 15: OOB — too many captures")
many_rs = generate_repeated_rs_captures((0, 0, 1, 0), 11)
r_many = check_temporal_consistency(many_rs)
check("many_verdict", r_many.verdict == ConsistencyVerdict.TOO_MANY_CAPTURES)
check("many_count", r_many.capture_count == 11)
check("many_sig", r_many.consistency_signature == "")

# ════════════════════════════════════════════════════════════
# Section 16: Consistent RS Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 16: Consistent RS cases (E2E)")
for case in CONSISTENT_CASES:
    if case["mode"] != "rolling_shutter":
        continue
    label = case["label"]
    payload = tuple(case["payload"])
    count = case["count"]
    expected_route = case["expected_route"]

    signals = generate_repeated_rs_captures(payload, count)
    check(f"rs_{label}_gen_count", len(signals) == count)

    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
    result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)
    check(f"rs_{label}_verdict", result.verdict == ConsistencyVerdict.CONSISTENT)
    check(f"rs_{label}_payload", result.common_payload == payload)
    check(f"rs_{label}_route", result.common_route == expected_route)
    check(f"rs_{label}_mode", result.common_mode == "rolling_shutter")
    check(f"rs_{label}_agree", result.agree_count == count)
    check(f"rs_{label}_disagree_idx", result.disagree_index == -1)
    check(f"rs_{label}_sig_len", len(result.consistency_signature) == 64)
    check(f"rs_{label}_records_count", len(result.capture_records) == count)
    # All capture records succeeded
    for i, rec in enumerate(result.capture_records):
        check(f"rs_{label}_rec{i}_ok", rec.succeeded is True)
        check(f"rs_{label}_rec{i}_idx", rec.capture_index == i)
        check(f"rs_{label}_rec{i}_payload", rec.decoded_payload == payload)
        check(f"rs_{label}_rec{i}_route", rec.route_name == expected_route)

# ════════════════════════════════════════════════════════════
# Section 17: Consistent CC Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 17: Consistent CC cases (E2E)")
for case in CONSISTENT_CASES:
    if case["mode"] != "complementary_color":
        continue
    label = case["label"]
    payload = tuple(case["payload"])
    count = case["count"]
    expected_route = case["expected_route"]

    signals = generate_repeated_cc_captures(payload, count)
    check(f"cc_{label}_gen_count", len(signals) == count)

    result = check_temporal_consistency(signals)
    check(f"cc_{label}_verdict", result.verdict == ConsistencyVerdict.CONSISTENT)
    check(f"cc_{label}_payload", result.common_payload == payload)
    check(f"cc_{label}_route", result.common_route == expected_route)
    check(f"cc_{label}_mode", result.common_mode == "complementary_color")
    check(f"cc_{label}_agree", result.agree_count == count)
    check(f"cc_{label}_disagree_idx", result.disagree_index == -1)
    check(f"cc_{label}_sig_len", len(result.consistency_signature) == 64)
    check(f"cc_{label}_records_count", len(result.capture_records) == count)
    for i, rec in enumerate(result.capture_records):
        check(f"cc_{label}_rec{i}_ok", rec.succeeded is True)
        check(f"cc_{label}_rec{i}_idx", rec.capture_index == i)
        check(f"cc_{label}_rec{i}_payload", rec.decoded_payload == payload)
        check(f"cc_{label}_rec{i}_route", rec.route_name == expected_route)

# ════════════════════════════════════════════════════════════
# Section 18: Inconsistent / Drifted Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 18: Inconsistent / drifted cases (E2E)")
for case in INCONSISTENT_CASES:
    label = case["label"]
    payload_a = tuple(case["payload_a"])
    payload_b = tuple(case["payload_b"])
    mode = case["mode"]
    count_a = case["count_a"]
    count_b = case["count_b"]

    signals = generate_drifted_capture_set(payload_a, payload_b, mode, count_a, count_b)
    total = count_a + count_b
    check(f"drift_{label}_gen_count", len(signals) == total)

    if mode == "rolling_shutter":
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload_a)
        result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)
    else:
        result = check_temporal_consistency(signals)

    check(f"drift_{label}_verdict", result.verdict == ConsistencyVerdict.INCONSISTENT)
    check(f"drift_{label}_disagree_idx_valid", result.disagree_index >= 0)
    check(f"drift_{label}_sig_empty", result.consistency_signature == "")
    check(f"drift_{label}_records_count", len(result.capture_records) == total)

# ════════════════════════════════════════════════════════════
# Section 19: OOB Cases from Module
# ════════════════════════════════════════════════════════════
print("Section 19: OOB cases from module")
for case in OOB_CASES:
    label = case["label"]
    expected = case["expected_verdict"]

    if label == "empty_set":
        result = check_temporal_consistency(case["signals"])
    else:
        payload = tuple(case["payload"])
        count = case["count"]
        mode = case["mode"]
        if mode == "rolling_shutter":
            signals = generate_repeated_rs_captures(payload, count)
        else:
            signals = generate_repeated_cc_captures(payload, count)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)

    check(f"oob_{label}_verdict", result.verdict.value == expected)

# ════════════════════════════════════════════════════════════
# Section 20: Determinism — Same Input → Same Result
# ════════════════════════════════════════════════════════════
print("Section 20: Determinism")
for _ in range(3):
    sigs_a = generate_repeated_rs_captures((0, 0, 1, 0), 3)
    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + 4
    r_a = check_temporal_consistency(sigs_a, expected_rs_slot_count=slot_count)
    sigs_b = generate_repeated_rs_captures((0, 0, 1, 0), 3)
    r_b = check_temporal_consistency(sigs_b, expected_rs_slot_count=slot_count)
    check("det_verdict", r_a.verdict == r_b.verdict)
    check("det_payload", r_a.common_payload == r_b.common_payload)
    check("det_route", r_a.common_route == r_b.common_route)
    check("det_mode", r_a.common_mode == r_b.common_mode)
    check("det_sig", r_a.consistency_signature == r_b.consistency_signature)

# CC determinism
for _ in range(3):
    sigs_c = generate_repeated_cc_captures((1, 0, 1), 3)
    r_c = check_temporal_consistency(sigs_c)
    sigs_d = generate_repeated_cc_captures((1, 0, 1), 3)
    r_d = check_temporal_consistency(sigs_d)
    check("det_cc_verdict", r_c.verdict == r_d.verdict)
    check("det_cc_payload", r_c.common_payload == r_d.common_payload)
    check("det_cc_sig", r_c.consistency_signature == r_d.consistency_signature)

# ════════════════════════════════════════════════════════════
# Section 21: Signature Distinctness Across Cases
# ════════════════════════════════════════════════════════════
print("Section 21: Signature distinctness")
all_sigs = set()
for case in CONSISTENT_CASES:
    payload = tuple(case["payload"])
    count = case["count"]
    mode = case["mode"]
    if mode == "rolling_shutter":
        signals = generate_repeated_rs_captures(payload, count)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)
    else:
        signals = generate_repeated_cc_captures(payload, count)
        result = check_temporal_consistency(signals)
    if result.verdict == ConsistencyVerdict.CONSISTENT:
        all_sigs.add(result.consistency_signature)

check("sigs_all_distinct", len(all_sigs) == len(CONSISTENT_CASES))
for sig in all_sigs:
    check(f"sig_hex_{sig[:8]}", len(sig) == 64)

# ════════════════════════════════════════════════════════════
# Section 22: Cross-Mode Consistency
# ════════════════════════════════════════════════════════════
print("Section 22: Cross-mode consistency")
# RS and CC with matching payload length (4 — supported by both) produce different modes
rs_cross = generate_repeated_rs_captures((0, 0, 1, 0), 3)
cc_cross = generate_repeated_cc_captures((0, 0, 1, 0), 3)
slot_count_cross = len(V1_TRANSPORT_PROFILE.sync_header) + 4
r_rs_cross = check_temporal_consistency(rs_cross, expected_rs_slot_count=slot_count_cross)
r_cc_cross = check_temporal_consistency(cc_cross)

# Both should be consistent within their mode
check("cross_rs_consistent", r_rs_cross.verdict == ConsistencyVerdict.CONSISTENT)
check("cross_cc_consistent", r_cc_cross.verdict == ConsistencyVerdict.CONSISTENT)
check("cross_rs_mode", r_rs_cross.common_mode == "rolling_shutter")
check("cross_cc_mode", r_cc_cross.common_mode == "complementary_color")
# Different sigs because different modes
check("cross_diff_sig", r_rs_cross.consistency_signature != r_cc_cross.consistency_signature)

# Mixed mode signals should produce INCONSISTENT or CAPTURE_FAILED
mixed = [rs_cross[0], cc_cross[0], rs_cross[0]]
r_mixed = check_temporal_consistency(mixed, expected_rs_slot_count=slot_count_cross)
check("cross_mixed_not_consistent",
      r_mixed.verdict in (ConsistencyVerdict.INCONSISTENT, ConsistencyVerdict.CAPTURE_FAILED))

# ════════════════════════════════════════════════════════════
# Section 23: Capture Record Detail Validation
# ════════════════════════════════════════════════════════════
print("Section 23: Capture record detail validation")
rs_detail = generate_repeated_rs_captures((0, 1, 1, 0), 4)
slot_detail = len(V1_TRANSPORT_PROFILE.sync_header) + 4
r_detail = check_temporal_consistency(rs_detail, expected_rs_slot_count=slot_detail)
check("detail_verdict", r_detail.verdict == ConsistencyVerdict.CONSISTENT)
check("detail_records_len", len(r_detail.capture_records) == 4)
for i, rec in enumerate(r_detail.capture_records):
    check(f"detail_rec{i}_index", rec.capture_index == i)
    check(f"detail_rec{i}_succeeded", rec.succeeded is True)
    check(f"detail_rec{i}_dispatch_verdict", rec.dispatch_verdict == "DISPATCHED")
    check(f"detail_rec{i}_mode", rec.identified_mode == "rolling_shutter")
    check(f"detail_rec{i}_payload", rec.decoded_payload == (0, 1, 1, 0))
    check(f"detail_rec{i}_route", rec.route_name == "containment")
    # Serialization round-trip
    d = rec.to_dict()
    check(f"detail_rec{i}_ser_ok", isinstance(json.dumps(d), str))

# ════════════════════════════════════════════════════════════
# Section 24: Boundary Capture Counts
# ════════════════════════════════════════════════════════════
print("Section 24: Boundary capture counts")
# Exactly at min (2)
rs_min = generate_repeated_rs_captures((1, 0, 0, 1), 2)
slot_min = len(V1_TRANSPORT_PROFILE.sync_header) + 4
r_min = check_temporal_consistency(rs_min, expected_rs_slot_count=slot_min)
check("boundary_min_verdict", r_min.verdict == ConsistencyVerdict.CONSISTENT)
check("boundary_min_count", r_min.capture_count == 2)
check("boundary_min_agree", r_min.agree_count == 2)

# Exactly at max (10)
rs_max = generate_repeated_rs_captures((0, 0, 1, 0, 1), 10)
slot_max = len(V1_TRANSPORT_PROFILE.sync_header) + 5
r_max = check_temporal_consistency(rs_max, expected_rs_slot_count=slot_max)
check("boundary_max_verdict", r_max.verdict == ConsistencyVerdict.CONSISTENT)
check("boundary_max_count", r_max.capture_count == 10)
check("boundary_max_agree", r_max.agree_count == 10)

# One below min (1) — should be TOO_FEW
rs_1 = generate_repeated_rs_captures((0, 0, 1, 0), 1)
r_1 = check_temporal_consistency(rs_1)
check("boundary_below_min", r_1.verdict == ConsistencyVerdict.TOO_FEW_CAPTURES)

# One above max (11) — should be TOO_MANY
rs_11 = generate_repeated_rs_captures((0, 0, 1, 0), 11)
r_11 = check_temporal_consistency(rs_11)
check("boundary_above_max", r_11.verdict == ConsistencyVerdict.TOO_MANY_CAPTURES)

# ════════════════════════════════════════════════════════════
# Section 25: All Supported Payload Lengths — RS
# ════════════════════════════════════════════════════════════
print("Section 25: All supported payload lengths — RS")
rs_payload_lengths = {
    4: (0, 0, 1, 0),
    5: (0, 0, 1, 0, 1),
    6: (0, 0, 1, 0, 1, 0),
    7: (0, 0, 1, 0, 1, 0, 1),
    8: (0, 0, 1, 0, 1, 0, 1, 0),
}
for plen, payload in rs_payload_lengths.items():
    signals = generate_repeated_rs_captures(payload, 3)
    slot_ct = len(V1_TRANSPORT_PROFILE.sync_header) + plen
    result = check_temporal_consistency(signals, expected_rs_slot_count=slot_ct)
    check(f"rs_plen{plen}_gen", len(signals) == 3)
    check(f"rs_plen{plen}_verdict", result.verdict == ConsistencyVerdict.CONSISTENT)
    check(f"rs_plen{plen}_payload", result.common_payload == payload)

# ════════════════════════════════════════════════════════════
# Section 26: All Supported Payload Lengths — CC
# ════════════════════════════════════════════════════════════
print("Section 26: All supported payload lengths — CC")
cc_payload_lengths = {
    3: (1, 0, 1),
    4: (1, 0, 1, 0),
    5: (1, 0, 1, 0, 1),
    6: (1, 0, 1, 0, 1, 0),
}
for plen, payload in cc_payload_lengths.items():
    signals = generate_repeated_cc_captures(payload, 3)
    result = check_temporal_consistency(signals)
    check(f"cc_plen{plen}_gen", len(signals) == 3)
    check(f"cc_plen{plen}_verdict", result.verdict == ConsistencyVerdict.CONSISTENT)
    check(f"cc_plen{plen}_payload", result.common_payload == payload)

# ════════════════════════════════════════════════════════════
# Section 27: Full Result Serialization Round-Trip
# ════════════════════════════════════════════════════════════
print("Section 27: Full result serialization round-trip")
rs_full = generate_repeated_rs_captures((0, 0, 1, 0), 3)
slot_full = len(V1_TRANSPORT_PROFILE.sync_header) + 4
r_full = check_temporal_consistency(rs_full, expected_rs_slot_count=slot_full)
d_full = r_full.to_dict()
j_full = json.dumps(d_full, indent=2)
loaded = json.loads(j_full)
check("full_ser_verdict", loaded["verdict"] == "CONSISTENT")
check("full_ser_payload", loaded["common_payload"] == [0, 0, 1, 0])
check("full_ser_route", isinstance(loaded["common_route"], str) and len(loaded["common_route"]) > 0)
check("full_ser_mode", loaded["common_mode"] == "rolling_shutter")
check("full_ser_count", loaded["capture_count"] == 3)
check("full_ser_agree", loaded["agree_count"] == 3)
check("full_ser_records", len(loaded["capture_records"]) == 3)
check("full_ser_sig", len(loaded["consistency_signature"]) == 64)
check("full_ser_version", loaded["version"] == "V1.0")

# ════════════════════════════════════════════════════════════
# Section 28: Predefined Test Case Counts
# ════════════════════════════════════════════════════════════
print("Section 28: Predefined test case counts")
check("consistent_count", len(CONSISTENT_CASES) == 6)
check("inconsistent_count", len(INCONSISTENT_CASES) == 2)
check("oob_count", len(OOB_CASES) == 3)

# Validate consistent case structure
for case in CONSISTENT_CASES:
    check(f"case_{case['label']}_has_payload", "payload" in case)
    check(f"case_{case['label']}_has_mode", "mode" in case)
    check(f"case_{case['label']}_has_count", "count" in case)
    check(f"case_{case['label']}_has_verdict", case["expected_verdict"] == "CONSISTENT")
    check(f"case_{case['label']}_has_route", "expected_route" in case)

# Validate inconsistent case structure
for case in INCONSISTENT_CASES:
    check(f"case_{case['label']}_has_a", "payload_a" in case)
    check(f"case_{case['label']}_has_b", "payload_b" in case)
    check(f"case_{case['label']}_has_verdict", case["expected_verdict"] == "INCONSISTENT")

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = _pass + _fail
print(f"Temporal Consistency Bridge V1 — {total} assertions: {_pass} passed, {_fail} failed")
if _fail == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_fail}")
    sys.exit(1)
