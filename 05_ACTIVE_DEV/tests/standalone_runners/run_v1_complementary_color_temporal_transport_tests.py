#!/usr/bin/env python3
"""
Standalone test runner — Complementary-Color Temporal Transport Bridge V1 (20th bridge)

Runs deterministic assertions against the complementary-color temporal transport
bridge module.  Requires only Python 3.x stdlib + the aurexis_lang package on
sys.path.

Usage:
    cd 05_ACTIVE_DEV
    python -m tests.standalone_runners.run_v1_complementary_color_temporal_transport_tests

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys, os, hashlib, json

# ── path bootstrap ──
_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(os.path.dirname(_here))
_src = os.path.join(_dev, "aurexis_lang", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    CC_TRANSPORT_VERSION,
    CC_TRANSPORT_FROZEN,
    CCTransportVerdict,
    CCTransportResult,
    ComplementaryColorTransportProfile,
    V1_CC_TRANSPORT_PROFILE,
    FROZEN_COLOR_PAIRS,
    COLOR_PAIR_MAP,
    FROZEN_ROUTE_TABLE,
    ROUTE_MAP,
    encode_cc_payload,
    simulate_cc_capture,
    decode_cc_chrominance,
    extract_cc_payload,
    resolve_cc_route,
    compute_perceptual_average,
    compute_cc_payload_signature,
    transport_cc_payload,
    IN_BOUNDS_CASES,
    OOB_CASES,
    EDGE_CASES,
    _color_diff_axis,
    _project_onto_axis,
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
check("version_is_v1", CC_TRANSPORT_VERSION == "V1.0")
check("frozen_true", CC_TRANSPORT_FROZEN is True)
check("version_is_string", isinstance(CC_TRANSPORT_VERSION, str))
check("frozen_is_bool", isinstance(CC_TRANSPORT_FROZEN, bool))

# ════════════════════════════════════════════════════════════
# Section 2: Profile Validation
# ════════════════════════════════════════════════════════════
print("Section 2: Profile validation")
p = V1_CC_TRANSPORT_PROFILE
check("profile_pair_name", p.color_pair_name == "cyan_red")
check("profile_slot_hz", p.temporal_slot_hz == 60)
check("profile_exposure", p.exposure_slots == 1)
check("profile_lengths", p.supported_payload_lengths == (3, 4, 5, 6))
check("profile_sync", p.sync_header == (0, 1, 0))
check("profile_threshold", p.chrominance_threshold == 0.0)
check("profile_version", p.version == "V1.0")
check("profile_frozen", hasattr(p, '__dataclass_fields__'))
# Frozen check: attempt to mutate should raise
try:
    p.color_pair_name = "other"
    check("profile_immutable", False)
except (AttributeError, FrozenInstanceError if 'FrozenInstanceError' in dir() else AttributeError):
    check("profile_immutable", True)

# ════════════════════════════════════════════════════════════
# Section 3: Frozen Color Pairs
# ════════════════════════════════════════════════════════════
print("Section 3: Frozen color pairs")
check("three_color_pairs", len(FROZEN_COLOR_PAIRS) == 3)
check("pair_names", set(COLOR_PAIR_MAP.keys()) == {"cyan_red", "magenta_green", "yellow_blue"})
# Verify complementary property: each pair sums to (255, 255, 255)
for name, primary, complement in FROZEN_COLOR_PAIRS:
    s = (primary[0] + complement[0], primary[1] + complement[1], primary[2] + complement[2])
    check(f"complementary_{name}", s == (255, 255, 255))
# Verify map entries match frozen pairs
for name, primary, complement in FROZEN_COLOR_PAIRS:
    mp, mc = COLOR_PAIR_MAP[name]
    check(f"map_primary_{name}", mp == primary)
    check(f"map_complement_{name}", mc == complement)

# ════════════════════════════════════════════════════════════
# Section 4: Route Table
# ════════════════════════════════════════════════════════════
print("Section 4: Route table")
check("route_table_len", len(FROZEN_ROUTE_TABLE) == 4)
check("route_00", ROUTE_MAP["00"] == "adjacent_pair")
check("route_01", ROUTE_MAP["01"] == "containment")
check("route_10", ROUTE_MAP["10"] == "three_regions")
check("route_11", ROUTE_MAP["11"] == "RESERVED")
check("route_map_size", len(ROUTE_MAP) == 4)

# ════════════════════════════════════════════════════════════
# Section 5: Verdict Enum
# ════════════════════════════════════════════════════════════
print("Section 5: Verdict enum")
expected_verdicts = [
    "DECODED", "SYNC_FAILED", "PAYLOAD_TOO_SHORT", "PAYLOAD_TOO_LONG",
    "UNSUPPORTED_LENGTH", "UNSUPPORTED_PAIR", "ROUTE_FAILED",
    "CHROMINANCE_ERROR", "MISMATCH", "ERROR",
]
for v in expected_verdicts:
    check(f"verdict_{v}", hasattr(CCTransportVerdict, v))
check("verdict_count", len(CCTransportVerdict) == 10)

# ════════════════════════════════════════════════════════════
# Section 6: Color-Difference Axis
# ════════════════════════════════════════════════════════════
print("Section 6: Color-difference axis")
# Cyan (0,255,255) vs Red (255,0,0): diff = (-255, 255, 255)
axis_cr = _color_diff_axis((0, 255, 255), (255, 0, 0))
mag = (axis_cr[0]**2 + axis_cr[1]**2 + axis_cr[2]**2) ** 0.5
check("axis_normalized", abs(mag - 1.0) < 1e-9)
# Axis should point from Red toward Cyan
check("axis_cr_negative_r", axis_cr[0] < 0)
check("axis_cr_positive_g", axis_cr[1] > 0)
check("axis_cr_positive_b", axis_cr[2] > 0)

# Magenta (255,0,255) vs Green (0,255,0)
axis_mg = _color_diff_axis((255, 0, 255), (0, 255, 0))
mag_mg = (axis_mg[0]**2 + axis_mg[1]**2 + axis_mg[2]**2) ** 0.5
check("axis_mg_normalized", abs(mag_mg - 1.0) < 1e-9)

# Yellow (255,255,0) vs Blue (0,0,255)
axis_yb = _color_diff_axis((255, 255, 0), (0, 0, 255))
mag_yb = (axis_yb[0]**2 + axis_yb[1]**2 + axis_yb[2]**2) ** 0.5
check("axis_yb_normalized", abs(mag_yb - 1.0) < 1e-9)

# Degenerate case: identical colors
axis_zero = _color_diff_axis((128, 128, 128), (128, 128, 128))
check("axis_zero", axis_zero == (0.0, 0.0, 0.0))

# Projection: PRIMARY should project positive, COMPLEMENT negative
for name, primary, complement in FROZEN_COLOR_PAIRS:
    axis = _color_diff_axis(primary, complement)
    mid = ((primary[0]+complement[0])/2, (primary[1]+complement[1])/2, (primary[2]+complement[2])/2)
    proj_p = _project_onto_axis((float(primary[0]), float(primary[1]), float(primary[2])), mid, axis)
    proj_c = _project_onto_axis((float(complement[0]), float(complement[1]), float(complement[2])), mid, axis)
    check(f"proj_primary_positive_{name}", proj_p > 0)
    check(f"proj_complement_negative_{name}", proj_c < 0)

# ════════════════════════════════════════════════════════════
# Section 7: Encoding
# ════════════════════════════════════════════════════════════
print("Section 7: Encoding")
# Basic encode
enc = encode_cc_payload((0, 0, 1), V1_CC_TRANSPORT_PROFILE)
check("encode_not_none", enc is not None)
check("encode_length", len(enc) == 6)  # 3 sync + 3 payload
# First 3 frames = sync header mapped to colors
cyan = (0, 255, 255)
red = (255, 0, 0)
check("encode_sync_0", enc[0] == cyan)    # sync bit 0 = PRIMARY
check("encode_sync_1", enc[1] == red)     # sync bit 1 = COMPLEMENT
check("encode_sync_2", enc[2] == cyan)    # sync bit 0 = PRIMARY
# Payload bits: 0, 0, 1
check("encode_payload_0", enc[3] == cyan)  # bit 0 = PRIMARY
check("encode_payload_1", enc[4] == cyan)  # bit 0 = PRIMARY
check("encode_payload_2", enc[5] == red)   # bit 1 = COMPLEMENT

# Unsupported length returns None
check("encode_unsupported", encode_cc_payload((0, 0), V1_CC_TRANSPORT_PROFILE) is None)
# Invalid bits returns None
check("encode_invalid_bits", encode_cc_payload((0, 2, 1), V1_CC_TRANSPORT_PROFILE) is None)
# Unknown pair returns None
bad_profile = ComplementaryColorTransportProfile(color_pair_name="bad_pair")
check("encode_bad_pair", encode_cc_payload((0, 0, 1), bad_profile) is None)

# Encode with different color pairs
for pair_name in ["cyan_red", "magenta_green", "yellow_blue"]:
    prof = ComplementaryColorTransportProfile(color_pair_name=pair_name)
    e = encode_cc_payload((0, 1, 0), prof)
    check(f"encode_{pair_name}_works", e is not None)
    check(f"encode_{pair_name}_len", len(e) == 6)

# ════════════════════════════════════════════════════════════
# Section 8: Capture Simulation
# ════════════════════════════════════════════════════════════
print("Section 8: Capture simulation")
# Snapshot mode (exposure_slots=1)
enc_frames = encode_cc_payload((0, 0, 1), V1_CC_TRANSPORT_PROFILE)
captured = simulate_cc_capture(enc_frames, V1_CC_TRANSPORT_PROFILE)
check("capture_count", len(captured) == len(enc_frames))
# Each capture should match the emitted frame exactly
for i, (cap, frame) in enumerate(zip(captured, enc_frames)):
    check(f"capture_snapshot_{i}", cap == (float(frame[0]), float(frame[1]), float(frame[2])))

# Integration mode (exposure_slots=2)
int_profile = ComplementaryColorTransportProfile(exposure_slots=2)
captured_int = simulate_cc_capture(enc_frames, int_profile)
check("capture_integration_count", len(captured_int) == len(enc_frames) // 2)

# Empty sequence
check("capture_empty", simulate_cc_capture((), V1_CC_TRANSPORT_PROFILE) == ())

# ════════════════════════════════════════════════════════════
# Section 9: Chrominance Decoding
# ════════════════════════════════════════════════════════════
print("Section 9: Chrominance decoding")
# Decode snapshot captures back to bits
decoded_bits = decode_cc_chrominance(captured, V1_CC_TRANSPORT_PROFILE)
check("decode_not_none", decoded_bits is not None)
check("decode_length", len(decoded_bits) == 6)  # 3 sync + 3 payload
# Should recover: sync(0,1,0) + payload(0,0,1)
expected_bits = (0, 1, 0, 0, 0, 1)
check("decode_matches_original", decoded_bits == expected_bits)

# Decode empty
check("decode_empty", decode_cc_chrominance((), V1_CC_TRANSPORT_PROFILE) is None)

# Decode with bad pair
check("decode_bad_pair", decode_cc_chrominance(captured, bad_profile) is None)

# Integration mode: averaged complementary pair → ambiguous (midpoint)
# Two complementary frames averaged: (0+255)/2, (255+0)/2, (255+0)/2 = (127.5, 127.5, 127.5)
# This should project to ~0 on the axis → CHROMINANCE_ERROR
int_samples = ((127.5, 127.5, 127.5),)
decoded_int = decode_cc_chrominance(int_samples, V1_CC_TRANSPORT_PROFILE)
check("decode_integrated_ambiguous", decoded_int is None)

# Decode with all three color pairs
for pair_name in ["cyan_red", "magenta_green", "yellow_blue"]:
    prof = ComplementaryColorTransportProfile(color_pair_name=pair_name)
    enc_p = encode_cc_payload((1, 0, 1), prof)
    cap_p = simulate_cc_capture(enc_p, prof)
    dec_p = decode_cc_chrominance(cap_p, prof)
    check(f"decode_{pair_name}_round_trip", dec_p is not None)
    check(f"decode_{pair_name}_correct", dec_p == (0, 1, 0, 1, 0, 1))

# ════════════════════════════════════════════════════════════
# Section 10: Payload Extraction
# ════════════════════════════════════════════════════════════
print("Section 10: Payload extraction")
# Extract from correctly decoded sequence
extracted = extract_cc_payload(decoded_bits, V1_CC_TRANSPORT_PROFILE)
check("extract_not_none", extracted is not None)
check("extract_payload", extracted == (0, 0, 1))

# Wrong sync header
check("extract_wrong_sync", extract_cc_payload((1, 1, 1, 0, 0, 1), V1_CC_TRANSPORT_PROFILE) is None)

# Too short
check("extract_too_short", extract_cc_payload((0, 1), V1_CC_TRANSPORT_PROFILE) is None)

# Empty
check("extract_empty", extract_cc_payload((), V1_CC_TRANSPORT_PROFILE) is None)

# Just sync header, no payload
just_sync = extract_cc_payload((0, 1, 0), V1_CC_TRANSPORT_PROFILE)
check("extract_just_sync", just_sync is not None)
check("extract_just_sync_empty", just_sync == ())

# ════════════════════════════════════════════════════════════
# Section 11: Route Resolution
# ════════════════════════════════════════════════════════════
print("Section 11: Route resolution")
check("route_00", resolve_cc_route((0, 0, 1)) == "adjacent_pair")
check("route_01", resolve_cc_route((0, 1, 0)) == "containment")
check("route_10", resolve_cc_route((1, 0, 1)) == "three_regions")
check("route_11_reserved", resolve_cc_route((1, 1, 0)) is None)
check("route_too_short", resolve_cc_route((0,)) is None)
check("route_empty", resolve_cc_route(()) is None)

# ════════════════════════════════════════════════════════════
# Section 12: Perceptual Average
# ════════════════════════════════════════════════════════════
print("Section 12: Perceptual average")
for name, primary, complement in FROZEN_COLOR_PAIRS:
    avg = compute_perceptual_average(primary, complement)
    check(f"perceptual_avg_{name}_r", abs(avg[0] - 127.5) < 0.01)
    check(f"perceptual_avg_{name}_g", abs(avg[1] - 127.5) < 0.01)
    check(f"perceptual_avg_{name}_b", abs(avg[2] - 127.5) < 0.01)

# ════════════════════════════════════════════════════════════
# Section 13: In-bounds Transport (E2E)
# ════════════════════════════════════════════════════════════
print("Section 13: In-bounds transport (E2E)")
for case in IN_BOUNDS_CASES:
    label = case["label"]
    prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    result = transport_cc_payload(tuple(case["payload"]), prof)
    check(f"ib_{label}_verdict", result.verdict.value == case["expected_verdict"])
    check(f"ib_{label}_route", result.route_name == case["expected_route"])
    check(f"ib_{label}_decoded_matches", result.decoded_payload == tuple(case["payload"]))
    check(f"ib_{label}_sig_nonempty", len(result.payload_signature) == 64)
    check(f"ib_{label}_frame_count", result.frame_count > 0)
    check(f"ib_{label}_capture_count", result.capture_count > 0)
    check(f"ib_{label}_pair_name", result.color_pair_name == case["color_pair"])

# ════════════════════════════════════════════════════════════
# Section 14: OOB Transport
# ════════════════════════════════════════════════════════════
print("Section 14: OOB transport")
for case in OOB_CASES:
    label = case["label"]
    prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    result = transport_cc_payload(tuple(case["payload"]), prof)
    check(f"oob_{label}_verdict", result.verdict.value == case["expected_verdict"])
    # OOB cases should NOT have DECODED verdict
    check(f"oob_{label}_not_decoded", result.verdict != CCTransportVerdict.DECODED)

# ════════════════════════════════════════════════════════════
# Section 15: Edge Cases
# ════════════════════════════════════════════════════════════
print("Section 15: Edge cases")
for case in EDGE_CASES:
    label = case["label"]
    prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    result = transport_cc_payload(tuple(case["payload"]), prof)
    check(f"edge_{label}_verdict", result.verdict.value == case["expected_verdict"])
    if "expected_route" in case:
        check(f"edge_{label}_route", result.route_name == case["expected_route"])

# ════════════════════════════════════════════════════════════
# Section 16: Determinism / Stability
# ════════════════════════════════════════════════════════════
print("Section 16: Determinism / stability")
for _ in range(3):
    for case in IN_BOUNDS_CASES[:3]:
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        r1 = transport_cc_payload(tuple(case["payload"]), prof)
        r2 = transport_cc_payload(tuple(case["payload"]), prof)
        check(f"determinism_{case['label']}", r1.to_dict() == r2.to_dict())

# ════════════════════════════════════════════════════════════
# Section 17: Payload Signature Distinctness
# ════════════════════════════════════════════════════════════
print("Section 17: Payload signature distinctness")
sigs = set()
for case in IN_BOUNDS_CASES:
    prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    result = transport_cc_payload(tuple(case["payload"]), prof)
    sigs.add(result.payload_signature)
check("all_sigs_distinct", len(sigs) == len(IN_BOUNDS_CASES))
# Each sig is 64 hex chars
for sig in sigs:
    check(f"sig_len_{sig[:8]}", len(sig) == 64)

# Also check that same payload with different color pair gives different sig
sig_cr = compute_cc_payload_signature((0, 0, 1), "cyan_red")
sig_mg = compute_cc_payload_signature((0, 0, 1), "magenta_green")
sig_yb = compute_cc_payload_signature((0, 0, 1), "yellow_blue")
check("sig_pair_distinct_cr_mg", sig_cr != sig_mg)
check("sig_pair_distinct_cr_yb", sig_cr != sig_yb)
check("sig_pair_distinct_mg_yb", sig_mg != sig_yb)

# ════════════════════════════════════════════════════════════
# Section 18: Serialization
# ════════════════════════════════════════════════════════════
print("Section 18: Serialization")
for case in IN_BOUNDS_CASES[:3]:
    prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
    result = transport_cc_payload(tuple(case["payload"]), prof)
    d = result.to_dict()
    check(f"ser_{case['label']}_verdict", d["verdict"] == case["expected_verdict"])
    check(f"ser_{case['label']}_payload", d["original_payload"] == list(case["payload"]))
    check(f"ser_{case['label']}_decoded", d["decoded_payload"] == list(case["payload"]))
    check(f"ser_{case['label']}_route", d["route_name"] == case["expected_route"])
    check(f"ser_{case['label']}_pair", d["color_pair_name"] == case["color_pair"])
    check(f"ser_{case['label']}_version", d["version"] == "V1.0")
    # JSON round-trip
    j = json.dumps(d)
    d2 = json.loads(j)
    check(f"ser_{case['label']}_json_rt", d == d2)

# ════════════════════════════════════════════════════════════
# Section 19: Cross-Pair Round-Trip
# ════════════════════════════════════════════════════════════
print("Section 19: Cross-pair round-trip")
# Prove that each color pair independently supports full E2E transport
for pair_name in ["cyan_red", "magenta_green", "yellow_blue"]:
    for payload in [(0, 0, 1), (0, 1, 0), (1, 0, 1), (0, 0, 1, 0)]:
        prof = ComplementaryColorTransportProfile(color_pair_name=pair_name)
        result = transport_cc_payload(payload, prof)
        expected_route = resolve_cc_route(payload)
        if expected_route is not None:
            check(f"cross_{pair_name}_{payload}_decoded", result.verdict == CCTransportVerdict.DECODED)
            check(f"cross_{pair_name}_{payload}_matches", result.decoded_payload == payload)
        else:
            check(f"cross_{pair_name}_{payload}_route_failed", result.verdict == CCTransportVerdict.ROUTE_FAILED)

# ════════════════════════════════════════════════════════════
# Section 20: Custom Profile
# ════════════════════════════════════════════════════════════
print("Section 20: Custom profile")
# Custom profile with magenta_green, different slot rate
custom = ComplementaryColorTransportProfile(
    color_pair_name="magenta_green",
    temporal_slot_hz=120,
    exposure_slots=1,
    supported_payload_lengths=(3, 4),
    sync_header=(0, 1, 0),
    chrominance_threshold=0.0,
)
r_custom = transport_cc_payload((0, 0, 1), custom)
check("custom_decoded", r_custom.verdict == CCTransportVerdict.DECODED)
check("custom_route", r_custom.route_name == "adjacent_pair")
check("custom_pair", r_custom.color_pair_name == "magenta_green")
# Unsupported length on custom profile
r_custom_oob = transport_cc_payload((0, 0, 1, 0, 1), custom)
check("custom_oob", r_custom_oob.verdict == CCTransportVerdict.UNSUPPORTED_LENGTH)

# ════════════════════════════════════════════════════════════
# Section 21: E2E Round-Trip Pipeline Detail
# ════════════════════════════════════════════════════════════
print("Section 21: E2E round-trip pipeline detail")
# Walk through each pipeline stage manually for one case
test_payload = (0, 1, 0, 1)
test_profile = V1_CC_TRANSPORT_PROFILE

# Encode
frames = encode_cc_payload(test_payload, test_profile)
check("e2e_encode_ok", frames is not None)
check("e2e_encode_len", len(frames) == 7)  # 3 sync + 4 payload

# Capture
caps = simulate_cc_capture(frames, test_profile)
check("e2e_capture_ok", len(caps) == 7)

# Decode chrominance
bits = decode_cc_chrominance(caps, test_profile)
check("e2e_decode_ok", bits is not None)
check("e2e_decode_len", len(bits) == 7)

# Extract payload
payload_out = extract_cc_payload(bits, test_profile)
check("e2e_extract_ok", payload_out is not None)
check("e2e_extract_match", payload_out == test_payload)

# Route
route = resolve_cc_route(payload_out)
check("e2e_route_ok", route == "containment")

# Signature
sig = compute_cc_payload_signature(test_payload, test_profile.color_pair_name)
check("e2e_sig_len", len(sig) == 64)
sig2 = compute_cc_payload_signature(test_payload, test_profile.color_pair_name)
check("e2e_sig_deterministic", sig == sig2)

# ════════════════════════════════════════════════════════════
# Section 22: Integration Mode Behavior
# ════════════════════════════════════════════════════════════
print("Section 22: Integration mode behavior")
# Integration mode with exposure_slots=2 averages consecutive pairs.
# When alternating complementary colors, the average is neutral gray.
int_prof = ComplementaryColorTransportProfile(
    color_pair_name="cyan_red",
    exposure_slots=2,
)
# Encode a payload: sync(0,1,0) + payload(0,0,1) = 6 frames
# Colors: cyan, red, cyan, cyan, cyan, red
enc_int = encode_cc_payload((0, 0, 1), int_prof)
check("int_encode_ok", enc_int is not None)
cap_int = simulate_cc_capture(enc_int, int_prof)
check("int_capture_count", len(cap_int) == 3)  # 6 frames / 2 exposure = 3 samples

# Sample 0: avg(cyan, red) = (127.5, 127.5, 127.5) — neutral
check("int_sample_0_neutral_r", abs(cap_int[0][0] - 127.5) < 0.01)
check("int_sample_0_neutral_g", abs(cap_int[0][1] - 127.5) < 0.01)
check("int_sample_0_neutral_b", abs(cap_int[0][2] - 127.5) < 0.01)

# Sample 1: avg(cyan, cyan) = (0, 255, 255) — pure PRIMARY
check("int_sample_1_cyan", cap_int[1] == (0.0, 255.0, 255.0))

# Sample 2: avg(cyan, red) = (127.5, 127.5, 127.5) — neutral
check("int_sample_2_neutral_r", abs(cap_int[2][0] - 127.5) < 0.01)

# Decoding integrated samples should fail for neutral samples (chrominance ≈ 0)
dec_int = decode_cc_chrominance(cap_int, int_prof)
check("int_decode_fails_neutral", dec_int is None)

# ════════════════════════════════════════════════════════════
# Section 23: Complementary Property Verification
# ════════════════════════════════════════════════════════════
print("Section 23: Complementary property verification")
# For each pair, verify PRIMARY + COMPLEMENT = (255, 255, 255)
for name, primary, complement in FROZEN_COLOR_PAIRS:
    s = tuple(p + c for p, c in zip(primary, complement))
    check(f"comp_sum_{name}", s == (255, 255, 255))

# Verify all primaries are distinct
primaries = [p for _, p, _ in FROZEN_COLOR_PAIRS]
check("primaries_distinct", len(set(primaries)) == 3)

# Verify all complements are distinct
complements = [c for _, _, c in FROZEN_COLOR_PAIRS]
check("complements_distinct", len(set(complements)) == 3)

# Each primary is a complement of some other pair and vice versa
all_colors = set(primaries + complements)
check("six_distinct_colors", len(all_colors) == 6)

# ════════════════════════════════════════════════════════════
# Section 24: Transport Result Fields
# ════════════════════════════════════════════════════════════
print("Section 24: Transport result fields")
r = transport_cc_payload((0, 0, 1), V1_CC_TRANSPORT_PROFILE)
check("result_has_verdict", hasattr(r, 'verdict'))
check("result_has_original", hasattr(r, 'original_payload'))
check("result_has_decoded", hasattr(r, 'decoded_payload'))
check("result_has_route", hasattr(r, 'route_name'))
check("result_has_pair", hasattr(r, 'color_pair_name'))
check("result_has_frame_count", hasattr(r, 'frame_count'))
check("result_has_capture_count", hasattr(r, 'capture_count'))
check("result_has_sig", hasattr(r, 'payload_signature'))
check("result_has_version", hasattr(r, 'version'))

# Default result
dr = CCTransportResult()
check("default_verdict", dr.verdict == CCTransportVerdict.ERROR)
check("default_payload", dr.original_payload == ())
check("default_decoded", dr.decoded_payload == ())
check("default_route", dr.route_name == "")
check("default_pair", dr.color_pair_name == "")
check("default_frame_count", dr.frame_count == 0)
check("default_capture_count", dr.capture_count == 0)
check("default_sig", dr.payload_signature == "")
check("default_version", dr.version == CC_TRANSPORT_VERSION)

# ════════════════════════════════════════════════════════════
# Section 25: All Supported Lengths
# ════════════════════════════════════════════════════════════
print("Section 25: All supported lengths")
# Verify every supported length decodes with a valid route
for length in V1_CC_TRANSPORT_PROFILE.supported_payload_lengths:
    # Build a payload of the given length starting with 00 (adjacent_pair route)
    payload = (0, 0) + (1,) * (length - 2)
    result = transport_cc_payload(payload, V1_CC_TRANSPORT_PROFILE)
    check(f"length_{length}_decoded", result.verdict == CCTransportVerdict.DECODED)
    check(f"length_{length}_route", result.route_name == "adjacent_pair")
    check(f"length_{length}_match", result.decoded_payload == payload)

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
