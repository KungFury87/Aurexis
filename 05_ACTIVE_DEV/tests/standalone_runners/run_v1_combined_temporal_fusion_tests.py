#!/usr/bin/env python3
"""
Standalone test runner — Combined RS+CC Temporal Fusion Bridge V1 (24th bridge)

Runs deterministic assertions against the combined temporal fusion bridge.
Requires only Python 3.x stdlib + the aurexis_lang package on sys.path.

Usage:
    cd 05_ACTIVE_DEV
    python -m tests.standalone_runners.run_v1_combined_temporal_fusion_tests

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, json

_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(os.path.dirname(_here))
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.combined_temporal_fusion_bridge_v1 import (
    FUSION_VERSION,
    FUSION_FROZEN,
    FusionVerdict,
    FusionProfile,
    V1_FUSION_PROFILE,
    V1_FUSION_STRICT_PROFILE,
    FUSED_PAYLOAD_LENGTHS,
    ChannelRecord,
    FusionResult,
    compute_fusion_signature,
    generate_fused_signals,
    fused_decode,
    AGREE_CASES,
    OOB_CASES,
    DISAGREE_CASES,
)

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE,
    generate_rs_signal,
    generate_cc_signal,
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
check("version_is_v1", FUSION_VERSION == "V1.0")
check("frozen_true", FUSION_FROZEN is True)
check("version_type", isinstance(FUSION_VERSION, str))
check("frozen_type", isinstance(FUSION_FROZEN, bool))

# ════════════════════════════════════════════════════════════
# Section 2: Verdict Enum
# ════════════════════════════════════════════════════════════
print("Section 2: Verdict enum")
expected_verdicts = [
    "BOTH_AGREE", "RS_ONLY", "CC_ONLY", "DISAGREE", "BOTH_FAILED",
    "FALLBACK_DENIED", "UNSUPPORTED_LENGTH", "EMPTY_PAYLOAD",
    "GENERATION_FAILED", "ERROR",
]
for v in expected_verdicts:
    check(f"verdict_{v}", hasattr(FusionVerdict, v))
check("verdict_count", len(FusionVerdict) == 10)
check("verdict_str_subclass", isinstance(FusionVerdict.BOTH_AGREE, str))

# ════════════════════════════════════════════════════════════
# Section 3: Profile
# ════════════════════════════════════════════════════════════
print("Section 3: Profile")
p = V1_FUSION_PROFILE
check("profile_lengths", p.supported_payload_lengths == (4, 5, 6))
check("profile_fallback", p.allow_single_channel_fallback is True)
check("profile_dispatch", p.dispatch_profile is V1_DISPATCH_PROFILE)
check("profile_version", p.version == "V1.0")
try:
    p.version = "other"
    check("profile_immutable", False)
except Exception:
    check("profile_immutable", True)

# Strict profile
ps = V1_FUSION_STRICT_PROFILE
check("strict_no_fallback", ps.allow_single_channel_fallback is False)
check("strict_same_lengths", ps.supported_payload_lengths == (4, 5, 6))

# ════════════════════════════════════════════════════════════
# Section 4: Frozen Constants
# ════════════════════════════════════════════════════════════
print("Section 4: Frozen constants")
check("fused_lengths", FUSED_PAYLOAD_LENGTHS == (4, 5, 6))

# ════════════════════════════════════════════════════════════
# Section 5: ChannelRecord Defaults
# ════════════════════════════════════════════════════════════
print("Section 5: ChannelRecord defaults")
cr = ChannelRecord()
check("cr_name", cr.channel_name == "")
check("cr_verdict", cr.dispatch_verdict == "")
check("cr_payload", cr.decoded_payload == ())
check("cr_route", cr.route_name == "")
check("cr_sig", cr.payload_signature == "")
check("cr_ok", cr.succeeded is False)

# ════════════════════════════════════════════════════════════
# Section 6: ChannelRecord Serialization
# ════════════════════════════════════════════════════════════
print("Section 6: ChannelRecord serialization")
cr2 = ChannelRecord(
    channel_name="rolling_shutter", dispatch_verdict="DISPATCHED",
    decoded_payload=(0, 0, 1, 0), route_name="adjacent_pair",
    payload_signature="abc", succeeded=True,
)
d = cr2.to_dict()
check("cr_ser_name", d["channel_name"] == "rolling_shutter")
check("cr_ser_payload", d["decoded_payload"] == [0, 0, 1, 0])
check("cr_ser_ok", d["succeeded"] is True)
j = json.dumps(d)
check("cr_ser_json", isinstance(json.loads(j), dict))

# ════════════════════════════════════════════════════════════
# Section 7: FusionResult Defaults
# ════════════════════════════════════════════════════════════
print("Section 7: FusionResult defaults")
fr = FusionResult()
check("fr_verdict", fr.verdict == FusionVerdict.ERROR)
check("fr_payload", fr.fused_payload == ())
check("fr_route", fr.fused_route == "")
check("fr_source", fr.source_channel == "")
check("fr_rs_name", fr.rs_record.channel_name == "rolling_shutter")
check("fr_cc_name", fr.cc_record.channel_name == "complementary_color")
check("fr_sig", fr.fusion_signature == "")

# ════════════════════════════════════════════════════════════
# Section 8: FusionResult Serialization
# ════════════════════════════════════════════════════════════
print("Section 8: FusionResult serialization")
fr2 = FusionResult(
    verdict=FusionVerdict.BOTH_AGREE, fused_payload=(0, 0, 1, 0),
    fused_route="adjacent_pair", source_channel="both",
    fusion_signature="xyz",
)
d2 = fr2.to_dict()
check("fr_ser_verdict", d2["verdict"] == "BOTH_AGREE")
check("fr_ser_payload", d2["fused_payload"] == [0, 0, 1, 0])
check("fr_ser_route", d2["fused_route"] == "adjacent_pair")
check("fr_ser_source", d2["source_channel"] == "both")
check("fr_ser_sig", d2["fusion_signature"] == "xyz")
check("fr_ser_rs", isinstance(d2["rs_record"], dict))
check("fr_ser_cc", isinstance(d2["cc_record"], dict))
j2 = json.dumps(d2)
check("fr_ser_json", isinstance(json.loads(j2), dict))

# ════════════════════════════════════════════════════════════
# Section 9: Fusion Signature
# ════════════════════════════════════════════════════════════
print("Section 9: Fusion signature")
sig1 = compute_fusion_signature("BOTH_AGREE", (0, 0, 1, 0), "adjacent_pair", "both")
check("sig_is_str", isinstance(sig1, str))
check("sig_len_64", len(sig1) == 64)
check("sig_hex", all(c in "0123456789abcdef" for c in sig1))
sig2 = compute_fusion_signature("BOTH_AGREE", (0, 0, 1, 0), "adjacent_pair", "both")
check("sig_deterministic", sig1 == sig2)
sig3 = compute_fusion_signature("BOTH_AGREE", (0, 1, 1, 0), "containment", "both")
check("sig_diff_payload", sig1 != sig3)
sig4 = compute_fusion_signature("RS_ONLY", (0, 0, 1, 0), "adjacent_pair", "rolling_shutter")
check("sig_diff_verdict", sig1 != sig4)

# ════════════════════════════════════════════════════════════
# Section 10: Signal Generation
# ════════════════════════════════════════════════════════════
print("Section 10: Signal generation")
pair = generate_fused_signals((0, 0, 1, 0))
check("gen_not_none", pair is not None)
check("gen_len", len(pair) == 2)
rs_sig, cc_sig = pair
check("gen_rs_nonempty", len(rs_sig) > 0)
check("gen_cc_nonempty", len(cc_sig) > 0)
# Different types
check("gen_rs_is_int", isinstance(rs_sig[0][0], int))
check("gen_cc_is_float", isinstance(cc_sig[0][0], float))

# ════════════════════════════════════════════════════════════
# Section 11: Agree Cases (E2E)
# ════════════════════════════════════════════════════════════
print("Section 11: Agree cases (E2E)")
for case in AGREE_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    result = fused_decode(payload)
    check(f"agree_{label}_verdict", result.verdict == FusionVerdict.BOTH_AGREE)
    check(f"agree_{label}_payload", result.fused_payload == payload)
    check(f"agree_{label}_route", result.fused_route == case["expected_route"])
    check(f"agree_{label}_source", result.source_channel == "both")
    check(f"agree_{label}_sig_len", len(result.fusion_signature) == 64)
    check(f"agree_{label}_rs_ok", result.rs_record.succeeded is True)
    check(f"agree_{label}_cc_ok", result.cc_record.succeeded is True)
    check(f"agree_{label}_rs_payload", result.rs_record.decoded_payload == payload)
    check(f"agree_{label}_cc_payload", result.cc_record.decoded_payload == payload)
    check(f"agree_{label}_rs_route", result.rs_record.route_name == case["expected_route"])
    check(f"agree_{label}_cc_route", result.cc_record.route_name == case["expected_route"])

# ════════════════════════════════════════════════════════════
# Section 12: OOB Cases
# ════════════════════════════════════════════════════════════
print("Section 12: OOB cases")
for case in OOB_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    result = fused_decode(payload)
    check(f"oob_{label}_verdict", result.verdict.value == case["expected_verdict"])
    check(f"oob_{label}_no_sig", result.fusion_signature == "")

# ════════════════════════════════════════════════════════════
# Section 13: Disagree Cases
# ════════════════════════════════════════════════════════════
print("Section 13: Disagree cases")
for case in DISAGREE_CASES:
    label = case["label"]
    rs_pay = tuple(case["rs_payload"])
    cc_pay = tuple(case["cc_payload"])
    # Generate mismatched signals
    rs_sig = generate_rs_signal(rs_pay)
    cc_sig = generate_cc_signal(cc_pay)
    check(f"disagree_{label}_rs_gen", rs_sig is not None)
    check(f"disagree_{label}_cc_gen", cc_sig is not None)
    # Decode with overrides
    result = fused_decode(rs_pay, rs_signal_override=rs_sig, cc_signal_override=cc_sig)
    check(f"disagree_{label}_verdict", result.verdict == FusionVerdict.DISAGREE)
    check(f"disagree_{label}_source", result.source_channel == "none")
    check(f"disagree_{label}_no_sig", result.fusion_signature == "")
    check(f"disagree_{label}_rs_ok", result.rs_record.succeeded is True)
    check(f"disagree_{label}_cc_ok", result.cc_record.succeeded is True)
    check(f"disagree_{label}_payloads_differ",
          result.rs_record.decoded_payload != result.cc_record.decoded_payload)

# ════════════════════════════════════════════════════════════
# Section 14: RS-Only Fallback (CC fails)
# ════════════════════════════════════════════════════════════
print("Section 14: RS-only fallback")
payload_fb = (0, 0, 1, 0)
rs_sig_fb = generate_rs_signal(payload_fb)
# Provide a broken CC signal (empty tuple = will fail identification)
result_rsonly = fused_decode(payload_fb, rs_signal_override=rs_sig_fb, cc_signal_override=())
check("rsonly_verdict", result_rsonly.verdict == FusionVerdict.RS_ONLY)
check("rsonly_payload", result_rsonly.fused_payload == payload_fb)
check("rsonly_source", result_rsonly.source_channel == "rolling_shutter")
check("rsonly_rs_ok", result_rsonly.rs_record.succeeded is True)
check("rsonly_cc_fail", result_rsonly.cc_record.succeeded is False)
check("rsonly_sig_len", len(result_rsonly.fusion_signature) == 64)

# ════════════════════════════════════════════════════════════
# Section 15: CC-Only Fallback (RS fails)
# ════════════════════════════════════════════════════════════
print("Section 15: CC-only fallback")
cc_sig_fb = generate_cc_signal(payload_fb)
result_cconly = fused_decode(payload_fb, rs_signal_override=(), cc_signal_override=cc_sig_fb)
check("cconly_verdict", result_cconly.verdict == FusionVerdict.CC_ONLY)
check("cconly_payload", result_cconly.fused_payload == payload_fb)
check("cconly_source", result_cconly.source_channel == "complementary_color")
check("cconly_rs_fail", result_cconly.rs_record.succeeded is False)
check("cconly_cc_ok", result_cconly.cc_record.succeeded is True)
check("cconly_sig_len", len(result_cconly.fusion_signature) == 64)

# ════════════════════════════════════════════════════════════
# Section 16: Both Failed
# ════════════════════════════════════════════════════════════
print("Section 16: Both failed")
result_both = fused_decode(payload_fb, rs_signal_override=(), cc_signal_override=())
check("both_failed_verdict", result_both.verdict == FusionVerdict.BOTH_FAILED)
check("both_failed_source", result_both.source_channel == "none")
check("both_failed_no_sig", result_both.fusion_signature == "")

# ════════════════════════════════════════════════════════════
# Section 17: Strict Profile — Fallback Denied
# ════════════════════════════════════════════════════════════
print("Section 17: Strict profile — fallback denied")
# RS only with strict profile
result_strict_rs = fused_decode(
    payload_fb, profile=V1_FUSION_STRICT_PROFILE,
    rs_signal_override=rs_sig_fb, cc_signal_override=(),
)
check("strict_rs_denied", result_strict_rs.verdict == FusionVerdict.FALLBACK_DENIED)
check("strict_rs_source", result_strict_rs.source_channel == "none")

# CC only with strict profile
result_strict_cc = fused_decode(
    payload_fb, profile=V1_FUSION_STRICT_PROFILE,
    rs_signal_override=(), cc_signal_override=cc_sig_fb,
)
check("strict_cc_denied", result_strict_cc.verdict == FusionVerdict.FALLBACK_DENIED)
check("strict_cc_source", result_strict_cc.source_channel == "none")

# Both agree under strict should still work
result_strict_ok = fused_decode(payload_fb, profile=V1_FUSION_STRICT_PROFILE)
check("strict_agree_verdict", result_strict_ok.verdict == FusionVerdict.BOTH_AGREE)
check("strict_agree_payload", result_strict_ok.fused_payload == payload_fb)

# ════════════════════════════════════════════════════════════
# Section 18: Determinism
# ════════════════════════════════════════════════════════════
print("Section 18: Determinism")
for _ in range(3):
    r_a = fused_decode((0, 0, 1, 0))
    r_b = fused_decode((0, 0, 1, 0))
    check("det_verdict", r_a.verdict == r_b.verdict)
    check("det_payload", r_a.fused_payload == r_b.fused_payload)
    check("det_route", r_a.fused_route == r_b.fused_route)
    check("det_sig", r_a.fusion_signature == r_b.fusion_signature)

for _ in range(3):
    r_c = fused_decode((1, 0, 1, 0, 1))
    r_d = fused_decode((1, 0, 1, 0, 1))
    check("det5_verdict", r_c.verdict == r_d.verdict)
    check("det5_sig", r_c.fusion_signature == r_d.fusion_signature)

# ════════════════════════════════════════════════════════════
# Section 19: Signature Distinctness
# ════════════════════════════════════════════════════════════
print("Section 19: Signature distinctness")
all_sigs = set()
for case in AGREE_CASES:
    payload = tuple(case["payload"])
    result = fused_decode(payload)
    check(f"sigdist_{case['label']}_pass", result.verdict == FusionVerdict.BOTH_AGREE)
    all_sigs.add(result.fusion_signature)
check("sigs_all_distinct", len(all_sigs) == len(AGREE_CASES))
for sig in all_sigs:
    check(f"sig_hex_{sig[:8]}", len(sig) == 64)

# ════════════════════════════════════════════════════════════
# Section 20: All Fused Payload Lengths
# ════════════════════════════════════════════════════════════
print("Section 20: All fused payload lengths")
fused_paylens = {
    4: (0, 0, 1, 0),
    5: (0, 0, 1, 0, 1),
    6: (0, 0, 1, 0, 1, 0),
}
for plen, payload in fused_paylens.items():
    result = fused_decode(payload)
    check(f"flen{plen}_verdict", result.verdict == FusionVerdict.BOTH_AGREE)
    check(f"flen{plen}_payload", result.fused_payload == payload)
    check(f"flen{plen}_rs_ok", result.rs_record.succeeded is True)
    check(f"flen{plen}_cc_ok", result.cc_record.succeeded is True)

# ════════════════════════════════════════════════════════════
# Section 21: Route Agreement Between Channels
# ════════════════════════════════════════════════════════════
print("Section 21: Route agreement between channels")
for case in AGREE_CASES:
    payload = tuple(case["payload"])
    result = fused_decode(payload)
    check(f"routeagree_{case['label']}_rs_eq_cc",
          result.rs_record.route_name == result.cc_record.route_name)
    check(f"routeagree_{case['label']}_fused_eq_rs",
          result.fused_route == result.rs_record.route_name)

# ════════════════════════════════════════════════════════════
# Section 22: Full Result JSON Round-Trip
# ════════════════════════════════════════════════════════════
print("Section 22: Full result JSON round-trip")
r_full = fused_decode((0, 1, 1, 0))
d_full = r_full.to_dict()
j_full = json.dumps(d_full, indent=2)
loaded = json.loads(j_full)
check("json_verdict", loaded["verdict"] == "BOTH_AGREE")
check("json_payload", loaded["fused_payload"] == [0, 1, 1, 0])
check("json_route", loaded["fused_route"] == "containment")
check("json_source", loaded["source_channel"] == "both")
check("json_sig", len(loaded["fusion_signature"]) == 64)
check("json_rs", isinstance(loaded["rs_record"], dict))
check("json_cc", isinstance(loaded["cc_record"], dict))
check("json_version", loaded["version"] == "V1.0")

# ════════════════════════════════════════════════════════════
# Section 23: Predefined Case Counts
# ════════════════════════════════════════════════════════════
print("Section 23: Predefined case counts")
check("agree_count", len(AGREE_CASES) == 6)
check("oob_count", len(OOB_CASES) == 4)
check("disagree_count", len(DISAGREE_CASES) == 2)

for case in AGREE_CASES:
    check(f"case_{case['label']}_has_payload", "payload" in case)
    check(f"case_{case['label']}_has_route", "expected_route" in case)

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = _pass + _fail
print(f"Combined Temporal Fusion Bridge V1 — {total} assertions: {_pass} passed, {_fail} failed")
if _fail == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_fail}")
    sys.exit(1)
