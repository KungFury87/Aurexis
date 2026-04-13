"""
Pytest suite — Complementary-Color Temporal Transport Bridge V1 (20th bridge)

Tests the complementary-color temporal transport bridge module with parametrized
cases covering encoding, capture simulation, chrominance decoding, payload
extraction, route resolution, and end-to-end transport.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
import json
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


# ── Fixtures ──

@pytest.fixture(scope="module")
def profile():
    return V1_CC_TRANSPORT_PROFILE


# ── Module Constants ──

class TestModuleConstants:
    def test_version(self):
        assert CC_TRANSPORT_VERSION == "V1.0"

    def test_frozen(self):
        assert CC_TRANSPORT_FROZEN is True

    def test_version_type(self):
        assert isinstance(CC_TRANSPORT_VERSION, str)

    def test_frozen_type(self):
        assert isinstance(CC_TRANSPORT_FROZEN, bool)


# ── Profile ──

class TestProfile:
    def test_default_pair(self, profile):
        assert profile.color_pair_name == "cyan_red"

    def test_default_hz(self, profile):
        assert profile.temporal_slot_hz == 60

    def test_default_exposure(self, profile):
        assert profile.exposure_slots == 1

    def test_supported_lengths(self, profile):
        assert profile.supported_payload_lengths == (3, 4, 5, 6)

    def test_sync_header(self, profile):
        assert profile.sync_header == (0, 1, 0)

    def test_threshold(self, profile):
        assert profile.chrominance_threshold == 0.0

    def test_immutable(self, profile):
        with pytest.raises(AttributeError):
            profile.color_pair_name = "other"


# ── Color Pairs ──

class TestColorPairs:
    def test_three_pairs(self):
        assert len(FROZEN_COLOR_PAIRS) == 3

    @pytest.mark.parametrize("name,primary,complement", FROZEN_COLOR_PAIRS)
    def test_complementary_sum(self, name, primary, complement):
        s = tuple(p + c for p, c in zip(primary, complement))
        assert s == (255, 255, 255)

    @pytest.mark.parametrize("name,primary,complement", FROZEN_COLOR_PAIRS)
    def test_map_matches(self, name, primary, complement):
        assert COLOR_PAIR_MAP[name] == (primary, complement)


# ── Route Table ──

class TestRouteTable:
    def test_table_size(self):
        assert len(FROZEN_ROUTE_TABLE) == 4

    def test_routes(self):
        assert ROUTE_MAP["00"] == "adjacent_pair"
        assert ROUTE_MAP["01"] == "containment"
        assert ROUTE_MAP["10"] == "three_regions"
        assert ROUTE_MAP["11"] == "RESERVED"


# ── Verdicts ──

class TestVerdicts:
    def test_verdict_count(self):
        assert len(CCTransportVerdict) == 10

    @pytest.mark.parametrize("name", [
        "DECODED", "SYNC_FAILED", "PAYLOAD_TOO_SHORT", "PAYLOAD_TOO_LONG",
        "UNSUPPORTED_LENGTH", "UNSUPPORTED_PAIR", "ROUTE_FAILED",
        "CHROMINANCE_ERROR", "MISMATCH", "ERROR",
    ])
    def test_verdict_exists(self, name):
        assert hasattr(CCTransportVerdict, name)


# ── Encoding ──

class TestEncoding:
    def test_basic_encode(self, profile):
        enc = encode_cc_payload((0, 0, 1), profile)
        assert enc is not None
        assert len(enc) == 6

    def test_unsupported_length(self, profile):
        assert encode_cc_payload((0, 0), profile) is None

    def test_invalid_bits(self, profile):
        assert encode_cc_payload((0, 2, 1), profile) is None

    def test_bad_pair(self):
        bad = ComplementaryColorTransportProfile(color_pair_name="bad")
        assert encode_cc_payload((0, 0, 1), bad) is None

    @pytest.mark.parametrize("pair_name", ["cyan_red", "magenta_green", "yellow_blue"])
    def test_all_pairs(self, pair_name):
        prof = ComplementaryColorTransportProfile(color_pair_name=pair_name)
        enc = encode_cc_payload((0, 1, 0), prof)
        assert enc is not None
        assert len(enc) == 6


# ── Capture Simulation ──

class TestCaptureSimulation:
    def test_snapshot_count(self, profile):
        frames = encode_cc_payload((0, 0, 1), profile)
        caps = simulate_cc_capture(frames, profile)
        assert len(caps) == len(frames)

    def test_integration_count(self):
        prof = ComplementaryColorTransportProfile(exposure_slots=2)
        frames = encode_cc_payload((0, 0, 1), prof)
        caps = simulate_cc_capture(frames, prof)
        assert len(caps) == len(frames) // 2

    def test_empty(self, profile):
        assert simulate_cc_capture((), profile) == ()


# ── Chrominance Decoding ──

class TestChrominanceDecoding:
    def test_basic_round_trip(self, profile):
        frames = encode_cc_payload((0, 0, 1), profile)
        caps = simulate_cc_capture(frames, profile)
        bits = decode_cc_chrominance(caps, profile)
        assert bits == (0, 1, 0, 0, 0, 1)

    def test_empty(self, profile):
        assert decode_cc_chrominance((), profile) is None

    def test_bad_pair(self):
        bad = ComplementaryColorTransportProfile(color_pair_name="bad")
        assert decode_cc_chrominance(((0.0, 0.0, 0.0),), bad) is None

    @pytest.mark.parametrize("pair_name", ["cyan_red", "magenta_green", "yellow_blue"])
    def test_all_pairs_round_trip(self, pair_name):
        prof = ComplementaryColorTransportProfile(color_pair_name=pair_name)
        frames = encode_cc_payload((1, 0, 1), prof)
        caps = simulate_cc_capture(frames, prof)
        bits = decode_cc_chrominance(caps, prof)
        assert bits == (0, 1, 0, 1, 0, 1)


# ── Payload Extraction ──

class TestPayloadExtraction:
    def test_basic_extract(self, profile):
        assert extract_cc_payload((0, 1, 0, 0, 0, 1), profile) == (0, 0, 1)

    def test_wrong_sync(self, profile):
        assert extract_cc_payload((1, 1, 1, 0, 0, 1), profile) is None

    def test_too_short(self, profile):
        assert extract_cc_payload((0, 1), profile) is None

    def test_empty(self, profile):
        assert extract_cc_payload((), profile) is None


# ── Route Resolution ──

class TestRouteResolution:
    def test_adjacent_pair(self):
        assert resolve_cc_route((0, 0, 1)) == "adjacent_pair"

    def test_containment(self):
        assert resolve_cc_route((0, 1, 0)) == "containment"

    def test_three_regions(self):
        assert resolve_cc_route((1, 0, 1)) == "three_regions"

    def test_reserved(self):
        assert resolve_cc_route((1, 1, 0)) is None

    def test_too_short(self):
        assert resolve_cc_route((0,)) is None


# ── Perceptual Average ──

class TestPerceptualAverage:
    @pytest.mark.parametrize("name,primary,complement", FROZEN_COLOR_PAIRS)
    def test_neutral_gray(self, name, primary, complement):
        avg = compute_perceptual_average(primary, complement)
        assert abs(avg[0] - 127.5) < 0.01
        assert abs(avg[1] - 127.5) < 0.01
        assert abs(avg[2] - 127.5) < 0.01


# ── In-Bounds Transport ──

class TestInBoundsTransport:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES, ids=[c["label"] for c in IN_BOUNDS_CASES])
    def test_in_bounds(self, case):
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        result = transport_cc_payload(tuple(case["payload"]), prof)
        assert result.verdict.value == case["expected_verdict"]
        assert result.route_name == case["expected_route"]
        assert result.decoded_payload == tuple(case["payload"])
        assert len(result.payload_signature) == 64


# ── OOB Transport ──

class TestOOBTransport:
    @pytest.mark.parametrize("case", OOB_CASES, ids=[c["label"] for c in OOB_CASES])
    def test_oob(self, case):
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        result = transport_cc_payload(tuple(case["payload"]), prof)
        assert result.verdict.value == case["expected_verdict"]
        assert result.verdict != CCTransportVerdict.DECODED


# ── Edge Cases ──

class TestEdgeCases:
    @pytest.mark.parametrize("case", EDGE_CASES, ids=[c["label"] for c in EDGE_CASES])
    def test_edge(self, case):
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        result = transport_cc_payload(tuple(case["payload"]), prof)
        assert result.verdict.value == case["expected_verdict"]


# ── Determinism ──

class TestDeterminism:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES[:3], ids=[c["label"] for c in IN_BOUNDS_CASES[:3]])
    def test_deterministic(self, case):
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        r1 = transport_cc_payload(tuple(case["payload"]), prof)
        r2 = transport_cc_payload(tuple(case["payload"]), prof)
        assert r1.to_dict() == r2.to_dict()


# ── Signature Distinctness ──

class TestSignatureDistinctness:
    def test_all_in_bounds_distinct(self):
        sigs = set()
        for case in IN_BOUNDS_CASES:
            prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
            result = transport_cc_payload(tuple(case["payload"]), prof)
            sigs.add(result.payload_signature)
        assert len(sigs) == len(IN_BOUNDS_CASES)


# ── Serialization ──

class TestSerialization:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES[:3], ids=[c["label"] for c in IN_BOUNDS_CASES[:3]])
    def test_serialization(self, case):
        prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        result = transport_cc_payload(tuple(case["payload"]), prof)
        d = result.to_dict()
        j = json.dumps(d)
        d2 = json.loads(j)
        assert d == d2


# ── Supported Lengths ──

class TestSupportedLengths:
    @pytest.mark.parametrize("length", [3, 4, 5, 6])
    def test_length(self, length):
        payload = (0, 0) + (1,) * (length - 2)
        result = transport_cc_payload(payload, V1_CC_TRANSPORT_PROFILE)
        assert result.verdict == CCTransportVerdict.DECODED
        assert result.route_name == "adjacent_pair"
        assert result.decoded_payload == payload
