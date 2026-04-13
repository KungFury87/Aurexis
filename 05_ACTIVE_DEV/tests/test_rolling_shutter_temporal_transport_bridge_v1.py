"""
Pytest tests for Rolling Shutter Temporal Transport Bridge V1.

Proves that a bounded payload can be encoded into a temporal screen-emission
pattern, captured as rolling-shutter stripe structure on ordinary CMOS,
decoded back into the original payload, and routed into the existing Aurexis
validation path.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
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


# ── Module Constants ───────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert RS_TRANSPORT_VERSION == "V1.0"

    def test_frozen(self):
        assert RS_TRANSPORT_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_TRANSPORT_PROFILE, TemporalTransportProfile)

    def test_profile_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            V1_TRANSPORT_PROFILE.version = "hacked"

    def test_profile_timing(self):
        p = V1_TRANSPORT_PROFILE
        slot_us = 1e6 / p.temporal_rate_hz
        rows_per_slot = slot_us / p.row_readout_us
        assert rows_per_slot == 40.0

    def test_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 8
        assert len(OOB_CASES) == 4
        assert len(EDGE_CASES) == 2


# ── Encoding ───────────────────────────────────────────────

class TestEncoding:
    def test_basic_encode(self):
        encoded = encode_payload((0, 0, 1, 0))
        assert encoded == (1, 0, 1, 0, 0, 1, 0)

    def test_8bit_encode(self):
        encoded = encode_payload((1, 0, 1, 1, 0, 0, 1, 0))
        assert len(encoded) == 11
        assert encoded[:3] == (1, 0, 1)

    def test_unsupported_length(self):
        assert encode_payload((0, 0, 1)) is None

    def test_invalid_bits(self):
        assert encode_payload((0, 2, 1, 0)) is None


# ── Rolling-Shutter Simulation ─────────────────────────────

class TestRollingShutter:
    def test_image_dimensions(self):
        image = simulate_rolling_shutter((1, 0, 1))
        assert len(image) == 480
        assert len(image[0]) == 640

    def test_stripe_brightness(self):
        image = simulate_rolling_shutter((1, 0))
        # Slot 0 center (row 20) should be white
        assert image[20][0] == 240
        # Slot 1 center (row 60) should be black
        assert image[60][0] == 16

    def test_uniform_rows(self):
        image = simulate_rolling_shutter((1, 0, 1))
        assert all(p == image[0][0] for p in image[0])


# ── Stripe Decoding ────────────────────────────────────────

class TestDecoding:
    def test_roundtrip(self):
        seq = (1, 0, 1, 0, 0, 1, 0)
        image = simulate_rolling_shutter(seq)
        decoded = decode_stripes(image, len(seq))
        assert decoded == seq

    def test_empty_image(self):
        assert decode_stripes((), 3) is None


# ── Payload Extraction ─────────────────────────────────────

class TestExtraction:
    def test_basic(self):
        assert extract_payload((1, 0, 1, 0, 0, 1, 0)) == (0, 0, 1, 0)

    def test_no_sync(self):
        assert extract_payload((0, 0, 0, 1, 0)) is None


# ── Route Resolution ───────────────────────────────────────

class TestRouting:
    def test_adjacent_pair(self):
        assert resolve_route((0, 0, 1, 0)) == "adjacent_pair"

    def test_containment(self):
        assert resolve_route((0, 1, 1, 0)) == "containment"

    def test_three_regions(self):
        assert resolve_route((1, 0, 0, 1)) == "three_regions"

    def test_reserved(self):
        assert resolve_route((1, 1, 0, 0)) is None

    def test_too_short(self):
        assert resolve_route((0,)) is None


# ── In-Bounds Transport ───────────────────────────────────

class TestInBounds:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_verdict(self, case):
        r = transport_payload(tuple(case["payload"]))
        assert r.verdict == TransportVerdict.DECODED

    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_roundtrip(self, case):
        payload = tuple(case["payload"])
        r = transport_payload(payload)
        assert r.decoded_payload == payload

    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_route(self, case):
        r = transport_payload(tuple(case["payload"]))
        assert r.route_name == case["expected_route"]


# ── Out-of-Bounds Transport ───────────────────────────────

class TestOOB:
    @pytest.mark.parametrize("case", OOB_CASES, ids=lambda c: c["label"])
    def test_verdict(self, case):
        r = transport_payload(tuple(case["payload"]))
        assert r.verdict == TransportVerdict(case["expected_verdict"])


# ── Edge Cases ─────────────────────────────────────────────

class TestEdge:
    @pytest.mark.parametrize("case", EDGE_CASES, ids=lambda c: c["label"])
    def test_verdict(self, case):
        r = transport_payload(tuple(case["payload"]))
        assert r.verdict == TransportVerdict(case["expected_verdict"])


# ── Determinism ────────────────────────────────────────────

class TestDeterminism:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=lambda c: c["label"])
    def test_stable(self, case):
        payload = tuple(case["payload"])
        r1 = transport_payload(payload)
        r2 = transport_payload(payload)
        assert r1.verdict == r2.verdict
        assert r1.decoded_payload == r2.decoded_payload
        assert r1.payload_signature == r2.payload_signature


# ── Serialization ──────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES[:3], ids=lambda c: c["label"])
    def test_to_dict(self, case):
        r = transport_payload(tuple(case["payload"]))
        d = r.to_dict()
        assert d["verdict"] == "DECODED"
        assert d["route_name"] == case["expected_route"]
        assert d["version"] == "V1.0"


# ── Signature Distinctness ─────────────────────────────────

class TestSignatures:
    def test_all_distinct(self):
        sigs = [compute_payload_signature(tuple(c["payload"]))
                for c in IN_BOUNDS_CASES]
        assert len(set(sigs)) == len(sigs)


# ── E2E Round-Trip ─────────────────────────────────────────

class TestE2E:
    @pytest.mark.parametrize("length",
                             V1_TRANSPORT_PROFILE.supported_payload_lengths)
    def test_all_lengths(self, length):
        payload = tuple([0, 0] + [i % 2 for i in range(length - 2)])
        r = transport_payload(payload)
        assert r.verdict == TransportVerdict.DECODED
        assert r.decoded_payload == payload

    def test_full_chain(self):
        payload = (1, 0, 0, 1, 1, 0)
        frame_seq = encode_payload(payload)
        image = simulate_rolling_shutter(frame_seq)
        decoded_seq = decode_stripes(image, len(frame_seq))
        assert decoded_seq == frame_seq
        extracted = extract_payload(decoded_seq)
        assert extracted == payload
        route = resolve_route(extracted)
        assert route == "three_regions"
