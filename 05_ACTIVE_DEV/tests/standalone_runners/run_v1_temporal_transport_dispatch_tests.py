#!/usr/bin/env python3
"""
Standalone test runner — Temporal Transport Dispatch Bridge V1 (21st bridge)

Runs deterministic assertions against the temporal transport dispatch bridge
module.  Requires only Python 3.x stdlib + the aurexis_lang package on sys.path.

Usage:
    cd 05_ACTIVE_DEV
    python -m tests.standalone_runners.run_v1_temporal_transport_dispatch_tests

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

# ── path bootstrap ──
_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(os.path.dirname(_here))
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    DISPATCH_VERSION,
    DISPATCH_FROZEN,
    DispatchVerdict,
    TransportMode,
    FROZEN_TRANSPORT_MODES,
    TemporalDispatchProfile,
    V1_DISPATCH_PROFILE,
    TemporalDispatchResult,
    identify_transport_mode,
    dispatch_temporal_signal,
    generate_rs_signal,
    generate_cc_signal,
    compute_dispatch_signature,
    RS_DISPATCH_CASES,
    CC_DISPATCH_CASES,
    OOB_CASES,
    EDGE_CASES,
)

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
    encode_payload as rs_encode_payload,
    simulate_rolling_shutter,
    transport_payload as rs_transport_payload,
)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
    ComplementaryColorTransportProfile,
    encode_cc_payload,
    simulate_cc_capture,
    transport_cc_payload,
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
check("version_is_v1", DISPATCH_VERSION == "V1.0")
check("frozen_true", DISPATCH_FROZEN is True)
check("version_type", isinstance(DISPATCH_VERSION, str))
check("frozen_type", isinstance(DISPATCH_FROZEN, bool))

# ════════════════════════════════════════════════════════════
# Section 2: Transport Mode Enum
# ════════════════════════════════════════════════════════════
print("Section 2: Transport mode enum")
check("mode_rs", TransportMode.ROLLING_SHUTTER.value == "rolling_shutter")
check("mode_cc", TransportMode.COMPLEMENTARY_COLOR.value == "complementary_color")
check("mode_count", len(TransportMode) == 2)
check("frozen_modes_count", len(FROZEN_TRANSPORT_MODES) == 2)
check("frozen_modes_rs", TransportMode.ROLLING_SHUTTER in FROZEN_TRANSPORT_MODES)
check("frozen_modes_cc", TransportMode.COMPLEMENTARY_COLOR in FROZEN_TRANSPORT_MODES)

# ════════════════════════════════════════════════════════════
# Section 3: Dispatch Profile
# ════════════════════════════════════════════════════════════
print("Section 3: Dispatch profile")
p = V1_DISPATCH_PROFILE
check("profile_modes", p.supported_modes == ("rolling_shutter", "complementary_color"))
check("profile_rs", p.rs_profile is V1_TRANSPORT_PROFILE)
check("profile_cc", p.cc_profile is V1_CC_TRANSPORT_PROFILE)
check("profile_version", p.version == "V1.0")
# Frozen
try:
    p.version = "other"
    check("profile_immutable", False)
except (AttributeError, Exception):
    check("profile_immutable", True)

# ════════════════════════════════════════════════════════════
# Section 4: Verdict Enum
# ════════════════════════════════════════════════════════════
print("Section 4: Verdict enum")
expected_verdicts = ["DISPATCHED", "UNKNOWN_MODE", "DECODE_FAILED", "ROUTE_FAILED", "EMPTY_SIGNAL", "ERROR"]
for v in expected_verdicts:
    check(f"verdict_{v}", hasattr(DispatchVerdict, v))
check("verdict_count", len(DispatchVerdict) == 6)

# ════════════════════════════════════════════════════════════
# Section 5: Signal Identification — RS
# ════════════════════════════════════════════════════════════
print("Section 5: Signal identification — RS")
# Generate a real RS signal
rs_signal = generate_rs_signal((0, 0, 1, 0))
check("rs_signal_generated", rs_signal is not None)
check("rs_signal_is_2d_tuple", isinstance(rs_signal, tuple) and len(rs_signal) > 0)
mode = identify_transport_mode(rs_signal)
check("rs_identified", mode == TransportMode.ROLLING_SHUTTER)

# ════════════════════════════════════════════════════════════
# Section 6: Signal Identification — CC
# ════════════════════════════════════════════════════════════
print("Section 6: Signal identification — CC")
cc_signal = generate_cc_signal((0, 0, 1))
check("cc_signal_generated", cc_signal is not None)
check("cc_signal_is_tuple", isinstance(cc_signal, tuple) and len(cc_signal) > 0)
mode_cc = identify_transport_mode(cc_signal)
check("cc_identified", mode_cc == TransportMode.COMPLEMENTARY_COLOR)

# ════════════════════════════════════════════════════════════
# Section 7: Signal Identification — Unknown/Invalid
# ════════════════════════════════════════════════════════════
print("Section 7: Signal identification — unknown/invalid")
check("id_none", identify_transport_mode(None) is None)
check("id_empty", identify_transport_mode(()) is None)
check("id_flat_ints", identify_transport_mode((1, 2, 3)) is None)
check("id_strings", identify_transport_mode((("hello",),)) is None)
check("id_short_rows", identify_transport_mode(((1, 2), (3, 4))) is None)
# Float triples with wrong length
check("id_wrong_float_len", identify_transport_mode(((1.0, 2.0),)) is None)
check("id_mixed", identify_transport_mode(((1, 2.0, 3),)) is None)

# ════════════════════════════════════════════════════════════
# Section 8: RS Dispatch Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 8: RS dispatch cases (E2E)")
for case in RS_DISPATCH_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    signal = generate_rs_signal(payload)
    check(f"rs_gen_{label}", signal is not None)
    # Compute expected slot count
    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
    result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
    check(f"rs_{label}_verdict", result.verdict.value == case["expected_verdict"])
    check(f"rs_{label}_mode", result.identified_mode == case["expected_mode"])
    check(f"rs_{label}_route", result.route_name == case["expected_route"])
    check(f"rs_{label}_payload_match", result.decoded_payload == payload)
    check(f"rs_{label}_sig_len", len(result.payload_signature) == 64)
    check(f"rs_{label}_inner", result.inner_verdict == "DECODED")

# ════════════════════════════════════════════════════════════
# Section 9: CC Dispatch Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 9: CC dispatch cases (E2E)")
for case in CC_DISPATCH_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
    signal = generate_cc_signal(payload, disp_prof)
    check(f"cc_gen_{label}", signal is not None)
    result = dispatch_temporal_signal(signal, profile=disp_prof)
    check(f"cc_{label}_verdict", result.verdict.value == case["expected_verdict"])
    check(f"cc_{label}_mode", result.identified_mode == case["expected_mode"])
    check(f"cc_{label}_route", result.route_name == case["expected_route"])
    check(f"cc_{label}_payload_match", result.decoded_payload == payload)
    check(f"cc_{label}_sig_len", len(result.payload_signature) == 64)
    check(f"cc_{label}_inner", result.inner_verdict == "DECODED")

# ════════════════════════════════════════════════════════════
# Section 10: OOB Cases
# ════════════════════════════════════════════════════════════
print("Section 10: OOB cases")
for case in OOB_CASES:
    label = case["label"]
    result = dispatch_temporal_signal(case["signal"])
    check(f"oob_{label}_verdict", result.verdict.value == case["expected_verdict"])
    check(f"oob_{label}_not_dispatched", result.verdict != DispatchVerdict.DISPATCHED)

# ════════════════════════════════════════════════════════════
# Section 11: Edge Cases — Reserved Routes
# ════════════════════════════════════════════════════════════
print("Section 11: Edge cases — reserved routes")
for case in EDGE_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    if case["mode"] == "rolling_shutter":
        signal = generate_rs_signal(payload)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
    else:
        signal = generate_cc_signal(payload)
        result = dispatch_temporal_signal(signal)
    check(f"edge_{label}_verdict", result.verdict.value == case["expected_verdict"])

# ════════════════════════════════════════════════════════════
# Section 12: Determinism / Stability
# ════════════════════════════════════════════════════════════
print("Section 12: Determinism / stability")
for _ in range(3):
    for case in RS_DISPATCH_CASES[:2]:
        payload = tuple(case["payload"])
        signal = generate_rs_signal(payload)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        r1 = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        r2 = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        check(f"det_rs_{case['label']}", r1.to_dict() == r2.to_dict())
    for case in CC_DISPATCH_CASES[:2]:
        payload = tuple(case["payload"])
        cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
        signal = generate_cc_signal(payload, disp_prof)
        r1 = dispatch_temporal_signal(signal, profile=disp_prof)
        r2 = dispatch_temporal_signal(signal, profile=disp_prof)
        check(f"det_cc_{case['label']}", r1.to_dict() == r2.to_dict())

# ════════════════════════════════════════════════════════════
# Section 13: Dispatch Signature Distinctness
# ════════════════════════════════════════════════════════════
print("Section 13: Dispatch signature distinctness")
sigs = set()
# RS cases
for case in RS_DISPATCH_CASES:
    payload = tuple(case["payload"])
    signal = generate_rs_signal(payload)
    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
    result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
    sigs.add(result.payload_signature)
# CC cases
for case in CC_DISPATCH_CASES:
    payload = tuple(case["payload"])
    cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
    signal = generate_cc_signal(payload, disp_prof)
    result = dispatch_temporal_signal(signal, profile=disp_prof)
    sigs.add(result.payload_signature)
total_cases = len(RS_DISPATCH_CASES) + len(CC_DISPATCH_CASES)
check("all_dispatch_sigs_distinct", len(sigs) == total_cases)

# Same payload, different mode → different signature
sig_rs = compute_dispatch_signature("rolling_shutter", (0, 0, 1, 0))
sig_cc = compute_dispatch_signature("complementary_color", (0, 0, 1, 0))
check("cross_mode_sig_distinct", sig_rs != sig_cc)

# ════════════════════════════════════════════════════════════
# Section 14: Serialization
# ════════════════════════════════════════════════════════════
print("Section 14: Serialization")
for case in RS_DISPATCH_CASES[:2]:
    payload = tuple(case["payload"])
    signal = generate_rs_signal(payload)
    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
    result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
    d = result.to_dict()
    check(f"ser_rs_{case['label']}_verdict", d["verdict"] == case["expected_verdict"])
    check(f"ser_rs_{case['label']}_mode", d["identified_mode"] == case["expected_mode"])
    check(f"ser_rs_{case['label']}_route", d["route_name"] == case["expected_route"])
    check(f"ser_rs_{case['label']}_version", d["version"] == "V1.0")
    j = json.dumps(d)
    d2 = json.loads(j)
    check(f"ser_rs_{case['label']}_json_rt", d == d2)

for case in CC_DISPATCH_CASES[:2]:
    payload = tuple(case["payload"])
    cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
    signal = generate_cc_signal(payload, disp_prof)
    result = dispatch_temporal_signal(signal, profile=disp_prof)
    d = result.to_dict()
    check(f"ser_cc_{case['label']}_verdict", d["verdict"] == case["expected_verdict"])
    check(f"ser_cc_{case['label']}_mode", d["identified_mode"] == case["expected_mode"])
    j = json.dumps(d)
    d2 = json.loads(j)
    check(f"ser_cc_{case['label']}_json_rt", d == d2)

# ════════════════════════════════════════════════════════════
# Section 15: Cross-Mode Dispatch Consistency
# ════════════════════════════════════════════════════════════
print("Section 15: Cross-mode dispatch consistency")
# For the same route prefix (00 = adjacent_pair), verify both modes route correctly
rs_result = dispatch_temporal_signal(
    generate_rs_signal((0, 0, 1, 0)),
    expected_rs_slot_count=len(V1_TRANSPORT_PROFILE.sync_header) + 4,
)
cc_result = dispatch_temporal_signal(generate_cc_signal((0, 0, 1)))
check("cross_both_dispatched", rs_result.verdict == DispatchVerdict.DISPATCHED and cc_result.verdict == DispatchVerdict.DISPATCHED)
check("cross_same_route", rs_result.route_name == cc_result.route_name == "adjacent_pair")
check("cross_different_modes", rs_result.identified_mode != cc_result.identified_mode)
check("cross_different_sigs", rs_result.payload_signature != cc_result.payload_signature)

# ════════════════════════════════════════════════════════════
# Section 16: Dispatch Result Fields
# ════════════════════════════════════════════════════════════
print("Section 16: Dispatch result fields")
r = dispatch_temporal_signal(generate_rs_signal((0, 0, 1, 0)),
    expected_rs_slot_count=len(V1_TRANSPORT_PROFILE.sync_header) + 4)
check("result_has_verdict", hasattr(r, 'verdict'))
check("result_has_mode", hasattr(r, 'identified_mode'))
check("result_has_decoded", hasattr(r, 'decoded_payload'))
check("result_has_route", hasattr(r, 'route_name'))
check("result_has_sig", hasattr(r, 'payload_signature'))
check("result_has_inner", hasattr(r, 'inner_verdict'))
check("result_has_count", hasattr(r, 'signal_element_count'))
check("result_has_version", hasattr(r, 'version'))

# Default result
dr = TemporalDispatchResult()
check("default_verdict", dr.verdict == DispatchVerdict.ERROR)
check("default_mode", dr.identified_mode == "")
check("default_payload", dr.decoded_payload == ())
check("default_route", dr.route_name == "")
check("default_sig", dr.payload_signature == "")
check("default_inner", dr.inner_verdict == "")
check("default_count", dr.signal_element_count == 0)
check("default_version", dr.version == DISPATCH_VERSION)

# ════════════════════════════════════════════════════════════
# Section 17: Disabled Mode Profile
# ════════════════════════════════════════════════════════════
print("Section 17: Disabled mode profile")
# Profile with only RS enabled
rs_only = TemporalDispatchProfile(supported_modes=("rolling_shutter",))
cc_signal_test = generate_cc_signal((0, 0, 1))
r_disabled = dispatch_temporal_signal(cc_signal_test, profile=rs_only)
check("disabled_cc_unknown", r_disabled.verdict == DispatchVerdict.UNKNOWN_MODE)

# Profile with only CC enabled
cc_only = TemporalDispatchProfile(supported_modes=("complementary_color",))
rs_signal_test = generate_rs_signal((0, 0, 1, 0))
r_disabled_rs = dispatch_temporal_signal(rs_signal_test, profile=cc_only,
    expected_rs_slot_count=len(V1_TRANSPORT_PROFILE.sync_header) + 4)
check("disabled_rs_unknown", r_disabled_rs.verdict == DispatchVerdict.UNKNOWN_MODE)

# Empty modes profile
empty_modes = TemporalDispatchProfile(supported_modes=())
r_empty_modes = dispatch_temporal_signal(rs_signal_test, profile=empty_modes)
check("empty_modes_unknown", r_empty_modes.verdict == DispatchVerdict.UNKNOWN_MODE)

# ════════════════════════════════════════════════════════════
# Section 18: Signal Element Count
# ════════════════════════════════════════════════════════════
print("Section 18: Signal element count")
# RS signal has frame_height rows
rs_sig = generate_rs_signal((0, 0, 1, 0))
rs_res = dispatch_temporal_signal(rs_sig,
    expected_rs_slot_count=len(V1_TRANSPORT_PROFILE.sync_header) + 4)
check("rs_element_count", rs_res.signal_element_count == V1_TRANSPORT_PROFILE.frame_height)

# CC signal has sync_header + payload_length samples
cc_sig = generate_cc_signal((0, 0, 1))
cc_res = dispatch_temporal_signal(cc_sig)
check("cc_element_count", cc_res.signal_element_count == len(V1_CC_TRANSPORT_PROFILE.sync_header) + 3)

# ════════════════════════════════════════════════════════════
# Section 19: All RS Payload Lengths via Dispatch
# ════════════════════════════════════════════════════════════
print("Section 19: All RS payload lengths via dispatch")
for length in V1_TRANSPORT_PROFILE.supported_payload_lengths:
    payload = (0, 0) + (1,) * (length - 2)
    signal = generate_rs_signal(payload)
    slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + length
    result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
    check(f"rs_len_{length}_dispatched", result.verdict == DispatchVerdict.DISPATCHED)
    check(f"rs_len_{length}_payload", result.decoded_payload == payload)

# ════════════════════════════════════════════════════════════
# Section 20: All CC Payload Lengths via Dispatch
# ════════════════════════════════════════════════════════════
print("Section 20: All CC payload lengths via dispatch")
for length in V1_CC_TRANSPORT_PROFILE.supported_payload_lengths:
    payload = (0, 0) + (1,) * (length - 2)
    signal = generate_cc_signal(payload)
    result = dispatch_temporal_signal(signal)
    check(f"cc_len_{length}_dispatched", result.verdict == DispatchVerdict.DISPATCHED)
    check(f"cc_len_{length}_payload", result.decoded_payload == payload)

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print()
print(f"TOTAL: {_pass + _fail} assertions — {_pass} passed, {_fail} failed")
if _fail == 0:
    print("RESULT: ALL PASS")
else:
    print("RESULT: FAILURES DETECTED")
    sys.exit(1)
