"""
Pytest test suite — Combined RS+CC Temporal Fusion Bridge V1 (24th bridge)

Tests the bounded stripe-and-color fusion transport proof.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import json
import pytest
import sys, os

_here = os.path.dirname(os.path.abspath(__file__))
_dev = os.path.dirname(_here)
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


class TestModuleConstants:
    def test_version(self):
        assert FUSION_VERSION == "V1.0"

    def test_frozen(self):
        assert FUSION_FROZEN is True


class TestVerdictEnum:
    def test_all_verdicts(self):
        expected = ["BOTH_AGREE", "RS_ONLY", "CC_ONLY", "DISAGREE",
                    "BOTH_FAILED", "FALLBACK_DENIED", "UNSUPPORTED_LENGTH",
                    "EMPTY_PAYLOAD", "GENERATION_FAILED", "ERROR"]
        for v in expected:
            assert hasattr(FusionVerdict, v)

    def test_count(self):
        assert len(FusionVerdict) == 10


class TestProfile:
    def test_payload_lengths(self):
        assert V1_FUSION_PROFILE.supported_payload_lengths == (4, 5, 6)

    def test_fallback_allowed(self):
        assert V1_FUSION_PROFILE.allow_single_channel_fallback is True

    def test_dispatch_profile(self):
        assert V1_FUSION_PROFILE.dispatch_profile is V1_DISPATCH_PROFILE

    def test_strict_no_fallback(self):
        assert V1_FUSION_STRICT_PROFILE.allow_single_channel_fallback is False

    def test_immutable(self):
        with pytest.raises(Exception):
            V1_FUSION_PROFILE.version = "other"


class TestFrozenConstants:
    def test_fused_payload_lengths(self):
        assert FUSED_PAYLOAD_LENGTHS == (4, 5, 6)

    def test_intersection_rs_cc(self):
        # RS supports 4-8, CC supports 3-6, intersection = 4,5,6
        for length in FUSED_PAYLOAD_LENGTHS:
            assert 4 <= length <= 8  # RS range
            assert 3 <= length <= 6  # CC range


class TestChannelRecord:
    def test_defaults(self):
        cr = ChannelRecord()
        assert cr.channel_name == ""
        assert cr.succeeded is False
        assert cr.decoded_payload == ()

    def test_serialization(self):
        cr = ChannelRecord(
            channel_name="rolling_shutter",
            dispatch_verdict="DISPATCHED",
            decoded_payload=(0, 0, 1, 0),
            route_name="adjacent_pair",
            payload_signature="abc",
            succeeded=True,
        )
        d = cr.to_dict()
        assert d["channel_name"] == "rolling_shutter"
        assert d["decoded_payload"] == [0, 0, 1, 0]
        assert isinstance(json.dumps(d), str)


class TestFusionResult:
    def test_defaults(self):
        r = FusionResult()
        assert r.verdict == FusionVerdict.ERROR
        assert r.fused_payload == ()
        assert r.fusion_signature == ""

    def test_serialization(self):
        r = FusionResult(
            verdict=FusionVerdict.BOTH_AGREE,
            fused_payload=(0, 0, 1, 0),
            fused_route="adjacent_pair",
            source_channel="both",
        )
        d = r.to_dict()
        assert d["verdict"] == "BOTH_AGREE"
        assert d["fused_payload"] == [0, 0, 1, 0]
        assert isinstance(json.dumps(d), str)


class TestSignature:
    def test_deterministic(self):
        a = compute_fusion_signature("BOTH_AGREE", (0, 0, 1, 0), "adjacent_pair", "both")
        b = compute_fusion_signature("BOTH_AGREE", (0, 0, 1, 0), "adjacent_pair", "both")
        assert a == b
        assert len(a) == 64

    def test_different_verdicts(self):
        a = compute_fusion_signature("BOTH_AGREE", (0, 0, 1, 0), "adjacent_pair", "both")
        b = compute_fusion_signature("RS_ONLY", (0, 0, 1, 0), "adjacent_pair", "rolling_shutter")
        assert a != b


class TestSignalGeneration:
    def test_generates_pair(self):
        pair = generate_fused_signals((0, 0, 1, 0))
        assert pair is not None
        rs_sig, cc_sig = pair
        assert rs_sig is not None
        assert cc_sig is not None

    def test_all_lengths(self):
        for length in FUSED_PAYLOAD_LENGTHS:
            payload = tuple(0 for _ in range(length))
            pair = generate_fused_signals(payload)
            assert pair is not None


class TestAgreeCases:
    @pytest.mark.parametrize("case", AGREE_CASES, ids=lambda c: c["label"])
    def test_both_agree(self, case):
        payload = tuple(case["payload"])
        result = fused_decode(payload)
        assert result.verdict == FusionVerdict.BOTH_AGREE
        assert result.fused_payload == payload
        assert result.fused_route == case["expected_route"]
        assert result.source_channel == "both"
        assert result.rs_record.succeeded is True
        assert result.cc_record.succeeded is True
        assert len(result.fusion_signature) == 64


class TestOOBCases:
    @pytest.mark.parametrize("case", OOB_CASES, ids=lambda c: c["label"])
    def test_oob(self, case):
        payload = tuple(case["payload"])
        result = fused_decode(payload)
        assert result.verdict == FusionVerdict[case["expected_verdict"]]


class TestDisagreeCases:
    @pytest.mark.parametrize("case", DISAGREE_CASES, ids=lambda c: c["label"])
    def test_disagree(self, case):
        rs_payload = tuple(case["rs_payload"])
        cc_payload = tuple(case["cc_payload"])
        rs_sig = generate_rs_signal(rs_payload, V1_DISPATCH_PROFILE)
        cc_sig = generate_cc_signal(cc_payload, V1_DISPATCH_PROFILE)
        assert rs_sig is not None
        assert cc_sig is not None
        result = fused_decode(
            rs_payload,  # primary payload for length validation
            rs_signal_override=rs_sig,
            cc_signal_override=cc_sig,
        )
        assert result.verdict == FusionVerdict.DISAGREE


class TestRSOnlyFallback:
    def test_broken_cc(self):
        payload = (0, 0, 1, 0)
        rs_sig = generate_rs_signal(payload, V1_DISPATCH_PROFILE)
        assert rs_sig is not None
        result = fused_decode(
            payload,
            rs_signal_override=rs_sig,
            cc_signal_override={"broken": True},
        )
        assert result.verdict == FusionVerdict.RS_ONLY
        assert result.fused_payload == payload
        assert result.source_channel == "rolling_shutter"


class TestCCOnlyFallback:
    def test_broken_rs(self):
        payload = (0, 0, 1, 0)
        cc_sig = generate_cc_signal(payload, V1_DISPATCH_PROFILE)
        assert cc_sig is not None
        result = fused_decode(
            payload,
            rs_signal_override={"broken": True},
            cc_signal_override=cc_sig,
        )
        assert result.verdict == FusionVerdict.CC_ONLY
        assert result.fused_payload == payload
        assert result.source_channel == "complementary_color"


class TestBothFailed:
    def test_both_broken(self):
        payload = (0, 0, 1, 0)
        result = fused_decode(
            payload,
            rs_signal_override={"broken": True},
            cc_signal_override={"broken": True},
        )
        assert result.verdict == FusionVerdict.BOTH_FAILED
        assert result.fused_payload == ()


class TestStrictProfile:
    def test_fallback_denied_rs_only(self):
        payload = (0, 0, 1, 0)
        rs_sig = generate_rs_signal(payload, V1_DISPATCH_PROFILE)
        result = fused_decode(
            payload,
            profile=V1_FUSION_STRICT_PROFILE,
            rs_signal_override=rs_sig,
            cc_signal_override={"broken": True},
        )
        assert result.verdict == FusionVerdict.FALLBACK_DENIED

    def test_fallback_denied_cc_only(self):
        payload = (0, 0, 1, 0)
        cc_sig = generate_cc_signal(payload, V1_DISPATCH_PROFILE)
        result = fused_decode(
            payload,
            profile=V1_FUSION_STRICT_PROFILE,
            rs_signal_override={"broken": True},
            cc_signal_override=cc_sig,
        )
        assert result.verdict == FusionVerdict.FALLBACK_DENIED

    def test_strict_both_agree_ok(self):
        payload = (0, 0, 1, 0)
        result = fused_decode(payload, profile=V1_FUSION_STRICT_PROFILE)
        assert result.verdict == FusionVerdict.BOTH_AGREE


class TestDeterminism:
    def test_same_result_repeated(self):
        for _ in range(3):
            r1 = fused_decode((0, 0, 1, 0))
            r2 = fused_decode((0, 0, 1, 0))
            assert r1.fusion_signature == r2.fusion_signature
            assert r1.verdict == r2.verdict


class TestSignatureDistinctness:
    def test_all_agree_sigs_unique(self):
        sigs = set()
        for case in AGREE_CASES:
            result = fused_decode(tuple(case["payload"]))
            assert result.verdict == FusionVerdict.BOTH_AGREE
            sigs.add(result.fusion_signature)
        assert len(sigs) == len(AGREE_CASES)


class TestAllFusedPayloadLengths:
    @pytest.mark.parametrize("length", FUSED_PAYLOAD_LENGTHS)
    def test_length_agree(self, length):
        payload = tuple(0 for _ in range(length))
        result = fused_decode(payload)
        assert result.verdict == FusionVerdict.BOTH_AGREE
        assert len(result.fused_payload) == length


class TestRouteAgreement:
    def test_channels_same_route(self):
        for case in AGREE_CASES:
            result = fused_decode(tuple(case["payload"]))
            assert result.rs_record.route_name == result.cc_record.route_name


class TestJSONRoundTrip:
    def test_full_result(self):
        result = fused_decode((0, 0, 1, 0))
        d = result.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["verdict"] == "BOTH_AGREE"
        assert d2["fused_payload"] == [0, 0, 1, 0]
        assert d2["rs_record"]["succeeded"] is True
        assert d2["cc_record"]["succeeded"] is True


class TestPredefinedCaseCounts:
    def test_agree_count(self):
        assert len(AGREE_CASES) == 6

    def test_oob_count(self):
        assert len(OOB_CASES) == 4

    def test_disagree_count(self):
        assert len(DISAGREE_CASES) == 2
