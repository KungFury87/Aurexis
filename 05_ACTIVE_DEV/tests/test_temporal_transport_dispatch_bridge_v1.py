"""
Pytest suite — Temporal Transport Dispatch Bridge V1 (21st bridge)

Tests the temporal transport dispatch bridge module with parametrized cases
covering signal identification, RS dispatch, CC dispatch, OOB handling,
determinism, and cross-mode consistency.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
import json
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
from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import V1_TRANSPORT_PROFILE
from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
    ComplementaryColorTransportProfile,
)


# ── Module Constants ──

class TestModuleConstants:
    def test_version(self):
        assert DISPATCH_VERSION == "V1.0"

    def test_frozen(self):
        assert DISPATCH_FROZEN is True


# ── Transport Modes ──

class TestTransportModes:
    def test_mode_count(self):
        assert len(TransportMode) == 2

    def test_frozen_modes(self):
        assert len(FROZEN_TRANSPORT_MODES) == 2


# ── Profile ──

class TestProfile:
    def test_supported_modes(self):
        assert V1_DISPATCH_PROFILE.supported_modes == ("rolling_shutter", "complementary_color")

    def test_immutable(self):
        with pytest.raises(AttributeError):
            V1_DISPATCH_PROFILE.version = "other"


# ── Verdicts ──

class TestVerdicts:
    def test_verdict_count(self):
        assert len(DispatchVerdict) == 6

    @pytest.mark.parametrize("name", [
        "DISPATCHED", "UNKNOWN_MODE", "DECODE_FAILED", "ROUTE_FAILED",
        "EMPTY_SIGNAL", "ERROR",
    ])
    def test_verdict_exists(self, name):
        assert hasattr(DispatchVerdict, name)


# ── Signal Identification ──

class TestSignalIdentification:
    def test_rs_identified(self):
        signal = generate_rs_signal((0, 0, 1, 0))
        assert identify_transport_mode(signal) == TransportMode.ROLLING_SHUTTER

    def test_cc_identified(self):
        signal = generate_cc_signal((0, 0, 1))
        assert identify_transport_mode(signal) == TransportMode.COMPLEMENTARY_COLOR

    @pytest.mark.parametrize("signal", [None, (), (1, 2, 3), (("hello",),)])
    def test_unknown(self, signal):
        assert identify_transport_mode(signal) is None


# ── RS Dispatch ──

class TestRSDispatch:
    @pytest.mark.parametrize("case", RS_DISPATCH_CASES, ids=[c["label"] for c in RS_DISPATCH_CASES])
    def test_rs_dispatch(self, case):
        payload = tuple(case["payload"])
        signal = generate_rs_signal(payload)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        assert result.verdict.value == case["expected_verdict"]
        assert result.identified_mode == case["expected_mode"]
        assert result.route_name == case["expected_route"]
        assert result.decoded_payload == payload


# ── CC Dispatch ──

class TestCCDispatch:
    @pytest.mark.parametrize("case", CC_DISPATCH_CASES, ids=[c["label"] for c in CC_DISPATCH_CASES])
    def test_cc_dispatch(self, case):
        payload = tuple(case["payload"])
        cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
        signal = generate_cc_signal(payload, disp_prof)
        result = dispatch_temporal_signal(signal, profile=disp_prof)
        assert result.verdict.value == case["expected_verdict"]
        assert result.identified_mode == case["expected_mode"]
        assert result.route_name == case["expected_route"]
        assert result.decoded_payload == payload


# ── OOB Cases ──

class TestOOBCases:
    @pytest.mark.parametrize("case", OOB_CASES, ids=[c["label"] for c in OOB_CASES])
    def test_oob(self, case):
        result = dispatch_temporal_signal(case["signal"])
        assert result.verdict.value == case["expected_verdict"]
        assert result.verdict != DispatchVerdict.DISPATCHED


# ── Edge Cases ──

class TestEdgeCases:
    @pytest.mark.parametrize("case", EDGE_CASES, ids=[c["label"] for c in EDGE_CASES])
    def test_edge(self, case):
        payload = tuple(case["payload"])
        if case["mode"] == "rolling_shutter":
            signal = generate_rs_signal(payload)
            slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
            result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        else:
            signal = generate_cc_signal(payload)
            result = dispatch_temporal_signal(signal)
        assert result.verdict.value == case["expected_verdict"]


# ── Determinism ──

class TestDeterminism:
    @pytest.mark.parametrize("case", RS_DISPATCH_CASES[:2], ids=[c["label"] for c in RS_DISPATCH_CASES[:2]])
    def test_rs_deterministic(self, case):
        payload = tuple(case["payload"])
        signal = generate_rs_signal(payload)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        r1 = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        r2 = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        assert r1.to_dict() == r2.to_dict()

    @pytest.mark.parametrize("case", CC_DISPATCH_CASES[:2], ids=[c["label"] for c in CC_DISPATCH_CASES[:2]])
    def test_cc_deterministic(self, case):
        payload = tuple(case["payload"])
        cc_prof = ComplementaryColorTransportProfile(color_pair_name=case["color_pair"])
        disp_prof = TemporalDispatchProfile(cc_profile=cc_prof)
        signal = generate_cc_signal(payload, disp_prof)
        r1 = dispatch_temporal_signal(signal, profile=disp_prof)
        r2 = dispatch_temporal_signal(signal, profile=disp_prof)
        assert r1.to_dict() == r2.to_dict()


# ── Signature Distinctness ──

class TestSignatureDistinctness:
    def test_cross_mode_distinct(self):
        sig_rs = compute_dispatch_signature("rolling_shutter", (0, 0, 1, 0))
        sig_cc = compute_dispatch_signature("complementary_color", (0, 0, 1, 0))
        assert sig_rs != sig_cc


# ── Serialization ──

class TestSerialization:
    def test_json_round_trip(self):
        signal = generate_rs_signal((0, 0, 1, 0))
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + 4
        result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        d = result.to_dict()
        j = json.dumps(d)
        d2 = json.loads(j)
        assert d == d2


# ── Cross-Mode Consistency ──

class TestCrossModeConsistency:
    def test_same_route_different_modes(self):
        rs_result = dispatch_temporal_signal(
            generate_rs_signal((0, 0, 1, 0)),
            expected_rs_slot_count=len(V1_TRANSPORT_PROFILE.sync_header) + 4,
        )
        cc_result = dispatch_temporal_signal(generate_cc_signal((0, 0, 1)))
        assert rs_result.verdict == DispatchVerdict.DISPATCHED
        assert cc_result.verdict == DispatchVerdict.DISPATCHED
        assert rs_result.route_name == cc_result.route_name == "adjacent_pair"
        assert rs_result.identified_mode != cc_result.identified_mode


# ── Disabled Mode Profile ──

class TestDisabledModes:
    def test_cc_disabled(self):
        rs_only = TemporalDispatchProfile(supported_modes=("rolling_shutter",))
        signal = generate_cc_signal((0, 0, 1))
        result = dispatch_temporal_signal(signal, profile=rs_only)
        assert result.verdict == DispatchVerdict.UNKNOWN_MODE

    def test_rs_disabled(self):
        cc_only = TemporalDispatchProfile(supported_modes=("complementary_color",))
        signal = generate_rs_signal((0, 0, 1, 0))
        result = dispatch_temporal_signal(signal, profile=cc_only)
        assert result.verdict == DispatchVerdict.UNKNOWN_MODE


# ── All Payload Lengths ──

class TestAllPayloadLengths:
    @pytest.mark.parametrize("length", [4, 5, 6, 7, 8])
    def test_rs_lengths(self, length):
        payload = (0, 0) + (1,) * (length - 2)
        signal = generate_rs_signal(payload)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + length
        result = dispatch_temporal_signal(signal, expected_rs_slot_count=slot_count)
        assert result.verdict == DispatchVerdict.DISPATCHED

    @pytest.mark.parametrize("length", [3, 4, 5, 6])
    def test_cc_lengths(self, length):
        payload = (0, 0) + (1,) * (length - 2)
        signal = generate_cc_signal(payload)
        result = dispatch_temporal_signal(signal)
        assert result.verdict == DispatchVerdict.DISPATCHED
