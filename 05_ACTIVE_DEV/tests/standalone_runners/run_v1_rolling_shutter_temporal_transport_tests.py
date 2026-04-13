#!/usr/bin/env python3
"""
Standalone test runner for Rolling Shutter Temporal Transport Bridge V1.
No external dependencies — pure Python 3.

Proves that a bounded payload can be encoded into a temporal screen-emission
pattern, captured as rolling-shutter stripe structure on ordinary CMOS,
decoded back into the original payload, and routed into the existing Aurexis
validation path.

This is a narrow deterministic rolling-shutter stripe transport proof,
not general optical camera communication or full RS-OFDM.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

# ── Path setup ─────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'aurexis_lang', 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    RS_TRANSPORT_VERSION, RS_TRANSPORT_FROZEN,
    TransportVerdict, TransportResult,
    TemporalTransportProfile, V1_TRANSPORT_PROFILE,
    FROZEN_ROUTE_TABLE, ROUTE_MAP,
    encode_payload, simulate_rolling_shutter, decode_stripes,
    extract_payload, resolve_route, compute_payload_signature,
    transport_payload,
    IN_BOUNDS_CASES, OOB_CASES, EDGE_CASES,
)


passed = 0
failed = 0


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


# ════════════════════════════════════════════════════════════
# SECTION 1: Module Constants
# ════════════════════════════════════════════════════════════

print("=== Section 1: Module Constants ===")

check(RS_TRANSPORT_VERSION == "V1.0", "version_is_v1")
check(RS_TRANSPORT_FROZEN is True, "frozen_is_true")
check(isinstance(V1_TRANSPORT_PROFILE, TemporalTransportProfile), "profile_type")
check(V1_TRANSPORT_PROFILE.version == "V1.0", "profile_version")
check(V1_TRANSPORT_PROFILE.temporal_rate_hz == 1000, "profile_rate_1000hz")
check(V1_TRANSPORT_PROFILE.row_readout_us == 25.0, "profile_row_readout_25us")
check(V1_TRANSPORT_PROFILE.frame_height == 480, "profile_height_480")
check(V1_TRANSPORT_PROFILE.frame_width == 640, "profile_width_640")
check(len(V1_TRANSPORT_PROFILE.supported_payload_lengths) == 5, "profile_5_lengths")
check(V1_TRANSPORT_PROFILE.sync_header == (1, 0, 1), "profile_sync_101")
check(len(IN_BOUNDS_CASES) == 8, "in_bounds_count_8")
check(len(OOB_CASES) == 4, "oob_count_4")
check(len(EDGE_CASES) == 2, "edge_count_2")


# ════════════════════════════════════════════════════════════
# SECTION 2: Profile Validation
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Profile Validation ===")

# Profile is frozen (immutable)
immutable = True
try:
    V1_TRANSPORT_PROFILE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "profile_frozen_immutable")

# Timing math: 40 rows per slot, 12 max slots
slot_us = 1_000_000.0 / V1_TRANSPORT_PROFILE.temporal_rate_hz
rows_per_slot = slot_us / V1_TRANSPORT_PROFILE.row_readout_us
total_readout_us = V1_TRANSPORT_PROFILE.frame_height * V1_TRANSPORT_PROFILE.row_readout_us
max_slots = total_readout_us / slot_us

check(rows_per_slot == 40.0, "rows_per_slot_40")
check(max_slots == 12.0, "max_slots_12")

# Max sequence: 3 (sync) + 8 (max payload) = 11 <= 12
max_seq = len(V1_TRANSPORT_PROFILE.sync_header) + max(V1_TRANSPORT_PROFILE.supported_payload_lengths)
check(max_seq <= max_slots, "max_sequence_fits_in_readout")
check(max_seq == 11, "max_sequence_is_11")

# Route table
check(len(FROZEN_ROUTE_TABLE) == 4, "route_table_has_4_entries")
check(ROUTE_MAP["00"] == "adjacent_pair", "route_00_adj")
check(ROUTE_MAP["01"] == "containment", "route_01_cont")
check(ROUTE_MAP["10"] == "three_regions", "route_10_three")
check(ROUTE_MAP["11"] == "RESERVED", "route_11_reserved")


# ════════════════════════════════════════════════════════════
# SECTION 3: Encoding
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Encoding ===")

# Basic encoding
encoded = encode_payload((0, 0, 1, 0))
check(encoded is not None, "encode_4bit_ok")
check(encoded == (1, 0, 1, 0, 0, 1, 0), "encode_4bit_correct")
check(len(encoded) == 7, "encode_4bit_len_7")

# 8-bit encoding
encoded8 = encode_payload((1, 0, 1, 1, 0, 0, 1, 0))
check(encoded8 is not None, "encode_8bit_ok")
check(len(encoded8) == 11, "encode_8bit_len_11")
check(encoded8[:3] == (1, 0, 1), "encode_8bit_sync_header")

# Unsupported length
check(encode_payload((0, 0, 1)) is None, "encode_3bit_none")
check(encode_payload(()) is None, "encode_empty_none")

# Invalid bits
check(encode_payload((0, 2, 1, 0)) is None, "encode_invalid_bits_none")


# ════════════════════════════════════════════════════════════
# SECTION 4: Rolling-Shutter Simulation
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: Rolling-Shutter Simulation ===")

frame_seq = (1, 0, 1, 0, 0, 1, 0)
image = simulate_rolling_shutter(frame_seq)

check(len(image) == 480, "rs_height_480")
check(len(image[0]) == 640, "rs_width_640")

# Row 0 should be in slot 0 (white)
check(image[0][0] == 240, "rs_row0_white")
# Row 20 (center of slot 0) should be white
check(image[20][0] == 240, "rs_row20_white")
# Row 60 (center of slot 1) should be black
check(image[60][0] == 16, "rs_row60_black")
# Row 100 (center of slot 2) should be white
check(image[100][0] == 240, "rs_row100_white")
# Row 140 (center of slot 3) should be black
check(image[140][0] == 16, "rs_row140_black")
# Row 180 (center of slot 4) should be black
check(image[180][0] == 16, "rs_row180_black")
# Row 220 (center of slot 5) should be white
check(image[220][0] == 240, "rs_row220_white")
# Row 260 (center of slot 6) should be black
check(image[260][0] == 16, "rs_row260_black")

# All pixels in a row are identical (uniform horizontal brightness)
check(all(p == image[0][0] for p in image[0]), "rs_uniform_row")
check(all(p == image[60][0] for p in image[60]), "rs_uniform_row_60")


# ════════════════════════════════════════════════════════════
# SECTION 5: Stripe Decoding
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Stripe Decoding ===")

decoded = decode_stripes(image, 7)
check(decoded is not None, "decode_not_none")
check(decoded == (1, 0, 1, 0, 0, 1, 0), "decode_matches_original")
check(len(decoded) == 7, "decode_len_7")

# Decode with different slot count
decoded_short = decode_stripes(image, 5)
check(decoded_short is not None, "decode_short_not_none")
check(decoded_short == (1, 0, 1, 0, 0), "decode_short_first_5")

# Empty image
check(decode_stripes((), 7) is None, "decode_empty_none")


# ════════════════════════════════════════════════════════════
# SECTION 6: Payload Extraction
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: Payload Extraction ===")

extracted = extract_payload((1, 0, 1, 0, 0, 1, 0))
check(extracted is not None, "extract_not_none")
check(extracted == (0, 0, 1, 0), "extract_4bit_correct")

# No sync header
check(extract_payload((0, 0, 0, 1, 0)) is None, "extract_no_sync_none")

# Too short for header
check(extract_payload((1, 0)) is None, "extract_too_short_none")


# ════════════════════════════════════════════════════════════
# SECTION 7: Route Resolution
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Route Resolution ===")

check(resolve_route((0, 0, 1, 0)) == "adjacent_pair", "route_00_adj_pair")
check(resolve_route((0, 1, 1, 0)) == "containment", "route_01_containment")
check(resolve_route((1, 0, 0, 1)) == "three_regions", "route_10_three_reg")
check(resolve_route((1, 1, 0, 0)) is None, "route_11_reserved_none")
check(resolve_route((0,)) is None, "route_too_short_none")
check(resolve_route(()) is None, "route_empty_none")


# ════════════════════════════════════════════════════════════
# SECTION 8: In-Bounds Transport (Supported Cases → DECODED)
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: In-Bounds Transport ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    r = transport_payload(payload)

    check(r.verdict == TransportVerdict.DECODED,
          f"ib_{label}_verdict")
    check(r.decoded_payload == payload,
          f"ib_{label}_roundtrip")
    check(r.route_name == case["expected_route"],
          f"ib_{label}_route")
    check(len(r.payload_signature) == 64,
          f"ib_{label}_sig_len")
    check(r.frame_sequence_length == len(V1_TRANSPORT_PROFILE.sync_header) + len(payload),
          f"ib_{label}_frame_seq_len")
    check(r.image_height == 480,
          f"ib_{label}_img_height")
    check(r.image_width == 640,
          f"ib_{label}_img_width")


# ════════════════════════════════════════════════════════════
# SECTION 9: Out-of-Bounds Transport (Honest Failure)
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Out-of-Bounds Transport ===")

for case in OOB_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    r = transport_payload(payload)

    expected = TransportVerdict(case["expected_verdict"])
    check(r.verdict == expected,
          f"oob_{label}_verdict")
    check(r.route_name == "",
          f"oob_{label}_no_route")


# ════════════════════════════════════════════════════════════
# SECTION 10: Edge Cases
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Edge Cases ===")

for case in EDGE_CASES:
    label = case["label"]
    payload = tuple(case["payload"])
    r = transport_payload(payload)

    expected = TransportVerdict(case["expected_verdict"])
    check(r.verdict == expected,
          f"edge_{label}_verdict")
    if "expected_route" in case:
        check(r.route_name == case["expected_route"],
              f"edge_{label}_route")


# ════════════════════════════════════════════════════════════
# SECTION 11: Determinism / Stability
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Determinism / Stability ===")

for case in IN_BOUNDS_CASES:
    payload = tuple(case["payload"])
    r1 = transport_payload(payload)
    r2 = transport_payload(payload)
    check(r1.verdict == r2.verdict,
          f"stable_{case['label']}_verdict")
    check(r1.decoded_payload == r2.decoded_payload,
          f"stable_{case['label']}_payload")
    check(r1.payload_signature == r2.payload_signature,
          f"stable_{case['label']}_sig")
    check(r1.route_name == r2.route_name,
          f"stable_{case['label']}_route")


# ════════════════════════════════════════════════════════════
# SECTION 12: Payload Signature Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: Payload Signature Distinctness ===")

all_sigs = []
for case in IN_BOUNDS_CASES:
    payload = tuple(case["payload"])
    sig = compute_payload_signature(payload)
    all_sigs.append(sig)
    check(len(sig) == 64, f"sig_len_{case['label']}")

check(len(set(all_sigs)) == len(all_sigs), "all_sigs_distinct")


# ════════════════════════════════════════════════════════════
# SECTION 13: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 13: Serialization ===")

for case in IN_BOUNDS_CASES[:3]:
    payload = tuple(case["payload"])
    r = transport_payload(payload)
    d = r.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{case['label']}")
    check(d["verdict"] == "DECODED", f"to_dict_verdict_{case['label']}")
    check(d["route_name"] == case["expected_route"], f"to_dict_route_{case['label']}")
    check(d["version"] == "V1.0", f"to_dict_version_{case['label']}")
    check(isinstance(d["original_payload"], list), f"to_dict_orig_list_{case['label']}")
    check(isinstance(d["decoded_payload"], list), f"to_dict_dec_list_{case['label']}")
    check(d["payload_signature"] == r.payload_signature, f"to_dict_sig_{case['label']}")


# ════════════════════════════════════════════════════════════
# SECTION 14: E2E Round-Trip for All Supported Lengths
# ════════════════════════════════════════════════════════════

print("\n=== Section 14: E2E Round-Trip ===")

# For each supported length, test a payload with route "adjacent_pair"
for length in V1_TRANSPORT_PROFILE.supported_payload_lengths:
    # Build a payload: 00 prefix (adjacent_pair) + alternating 1,0
    payload_list = [0, 0]
    for i in range(length - 2):
        payload_list.append(i % 2)
    payload = tuple(payload_list)

    r = transport_payload(payload)
    check(r.verdict == TransportVerdict.DECODED,
          f"e2e_{length}bit_decoded")
    check(r.decoded_payload == payload,
          f"e2e_{length}bit_roundtrip")
    check(r.route_name == "adjacent_pair",
          f"e2e_{length}bit_route")

# Full round-trip: encode → RS → decode → extract → route
payload = (1, 0, 0, 1, 1, 0)
frame_seq = encode_payload(payload)
check(frame_seq is not None, "e2e_full_encode")
image = simulate_rolling_shutter(frame_seq)
decoded_seq = decode_stripes(image, len(frame_seq))
check(decoded_seq == frame_seq, "e2e_full_decode_match")
extracted = extract_payload(decoded_seq)
check(extracted == payload, "e2e_full_extract_match")
route = resolve_route(extracted)
check(route == "three_regions", "e2e_full_route_match")


# ════════════════════════════════════════════════════════════
# SECTION 15: RS Image Physical Properties
# ════════════════════════════════════════════════════════════

print("\n=== Section 15: RS Image Physical Properties ===")

# Verify stripe widths match expected timing
payload = (0, 1, 0, 1)  # containment route, alternating
frame_seq = encode_payload(payload)
image = simulate_rolling_shutter(frame_seq)

# Each slot should be exactly 40 rows
# Slot 0 (bit=1): rows 0-39 → white
# Slot 1 (bit=0): rows 40-79 → black
for row in range(0, 40):
    check(image[row][0] == 240, f"stripe_slot0_row{row}")
for row in range(40, 80):
    check(image[row][0] == 16, f"stripe_slot1_row{row}")

# Verify all pixels are either white or black
all_valid = True
for row in image:
    for px in row:
        if px not in (240, 16):
            all_valid = False
            break
check(all_valid, "all_pixels_binary")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
total = passed + failed
print(f"TOTAL: {total} assertions — {passed} passed, {failed} failed")
if failed:
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: ALL PASS")
    sys.exit(0)
