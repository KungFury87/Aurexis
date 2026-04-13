"""
Pytest test suite — Frame-Accurate Transport Bridge V1 (23rd bridge)

Tests the bounded temporal slot-identity preservation proof.

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
    verify_frame_accuracy,
    generate_drifted_sequence,
    SUPPORTED_SEQUENCE_LENGTHS,
    RS_FRAME_CASES,
    CC_FRAME_CASES,
    DRIFT_CASES,
    OOB_CASES,
)

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import V1_DISPATCH_PROFILE


class TestModuleConstants:
    def test_version(self):
        assert FRAME_ACCURATE_VERSION == "V1.0"

    def test_frozen(self):
        assert FRAME_ACCURATE_FROZEN is True


class TestVerdictEnum:
    def test_all_verdicts(self):
        expected = ["FRAME_ACCURATE", "SLOT_MISMATCH", "SLOT_DECODE_FAILED",
                    "SEQUENCE_TOO_SHORT", "SEQUENCE_TOO_LONG", "EMPTY_SEQUENCE",
                    "GENERATION_FAILED", "ERROR"]
        for v in expected:
            assert hasattr(FrameAccurateVerdict, v)

    def test_count(self):
        assert len(FrameAccurateVerdict) == 8


class TestProfile:
    def test_sequence_lengths(self):
        assert V1_FRAME_ACCURATE_PROFILE.supported_sequence_lengths == (2, 3, 4)

    def test_modes(self):
        assert V1_FRAME_ACCURATE_PROFILE.supported_modes == ("rolling_shutter", "complementary_color")

    def test_dispatch(self):
        assert V1_FRAME_ACCURATE_PROFILE.dispatch_profile is V1_DISPATCH_PROFILE

    def test_immutable(self):
        with pytest.raises(Exception):
            V1_FRAME_ACCURATE_PROFILE.version = "other"


class TestSlotRecord:
    def test_defaults(self):
        sr = SlotRecord()
        assert sr.slot_index == 0
        assert sr.succeeded is False

    def test_serialization(self):
        sr = SlotRecord(slot_index=1, intended_payload=(0, 1), recovered_payload=(0, 1),
                        transport_mode="rolling_shutter", slot_match=True, succeeded=True)
        d = sr.to_dict()
        assert d["slot_index"] == 1
        assert isinstance(json.dumps(d), str)


class TestFrameAccurateResult:
    def test_defaults(self):
        r = FrameAccurateResult()
        assert r.verdict == FrameAccurateVerdict.ERROR
        assert r.frame_accurate_signature == ""

    def test_serialization(self):
        r = FrameAccurateResult(verdict=FrameAccurateVerdict.FRAME_ACCURATE,
                                 sequence_length=2, slots_matched=2)
        d = r.to_dict()
        assert d["verdict"] == "FRAME_ACCURATE"
        assert isinstance(json.dumps(d), str)


class TestSignature:
    def test_deterministic(self):
        a = compute_frame_accurate_signature("rs", ((0, 1), (1, 0)), 2)
        b = compute_frame_accurate_signature("rs", ((0, 1), (1, 0)), 2)
        assert a == b
        assert len(a) == 64

    def test_order_matters(self):
        a = compute_frame_accurate_signature("rs", ((0, 1), (1, 0)), 2)
        b = compute_frame_accurate_signature("rs", ((1, 0), (0, 1)), 2)
        assert a != b


class TestGeneration:
    def test_rs(self):
        sigs = generate_sequence_signals(((0, 0, 1, 0), (0, 1, 1, 0)), "rolling_shutter")
        assert sigs is not None
        assert len(sigs) == 2

    def test_cc(self):
        sigs = generate_sequence_signals(((0, 0, 1), (0, 1, 0)), "complementary_color")
        assert sigs is not None
        assert len(sigs) == 2

    def test_drifted(self):
        d = generate_drifted_sequence(((0, 0, 1, 0), (0, 1, 1, 0)), 1, (1, 0, 1, 0, 1))
        assert d[0] == (0, 0, 1, 0)
        assert d[1] == (1, 0, 1, 0, 1)


class TestOOBCases:
    def test_empty(self):
        r = verify_frame_accuracy((), "rolling_shutter")
        assert r.verdict == FrameAccurateVerdict.EMPTY_SEQUENCE

    def test_too_short(self):
        r = verify_frame_accuracy(((0, 0, 1, 0),), "rolling_shutter")
        assert r.verdict == FrameAccurateVerdict.SEQUENCE_TOO_SHORT

    def test_too_long(self):
        r = verify_frame_accuracy(
            ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1), (0, 0, 0, 1), (0, 0, 1, 1)),
            "rolling_shutter")
        assert r.verdict == FrameAccurateVerdict.SEQUENCE_TOO_LONG


class TestRSFrameCases:
    @pytest.mark.parametrize("case", RS_FRAME_CASES, ids=lambda c: c["label"])
    def test_rs_frame_accurate(self, case):
        payloads = tuple(tuple(p) for p in case["payloads"])
        result = verify_frame_accuracy(payloads, case["mode"])
        assert result.verdict == FrameAccurateVerdict.FRAME_ACCURATE
        assert result.slots_matched == len(payloads)
        assert result.recovered_payloads == payloads
        for i, rec in enumerate(result.slot_records):
            assert rec.route_name == case["expected_routes"][i]


class TestCCFrameCases:
    @pytest.mark.parametrize("case", CC_FRAME_CASES, ids=lambda c: c["label"])
    def test_cc_frame_accurate(self, case):
        payloads = tuple(tuple(p) for p in case["payloads"])
        result = verify_frame_accuracy(payloads, case["mode"])
        assert result.verdict == FrameAccurateVerdict.FRAME_ACCURATE
        assert result.slots_matched == len(payloads)
        assert result.recovered_payloads == payloads


class TestDriftCases:
    @pytest.mark.parametrize("case", DRIFT_CASES, ids=lambda c: c["label"])
    def test_drifted_recovery(self, case):
        base = tuple(tuple(p) for p in case["base_payloads"])
        drifted = generate_drifted_sequence(base, case["drift_index"], tuple(case["drifted_payload"]))
        result = verify_frame_accuracy(drifted, case["mode"])
        assert result.verdict == FrameAccurateVerdict.FRAME_ACCURATE
        assert result.recovered_payloads != base


class TestDeterminism:
    def test_rs_deterministic(self):
        for _ in range(3):
            r1 = verify_frame_accuracy(((0, 0, 1, 0), (0, 1, 1, 0)), "rolling_shutter")
            r2 = verify_frame_accuracy(((0, 0, 1, 0), (0, 1, 1, 0)), "rolling_shutter")
            assert r1.frame_accurate_signature == r2.frame_accurate_signature

    def test_cc_deterministic(self):
        for _ in range(3):
            r1 = verify_frame_accuracy(((0, 0, 1), (0, 1, 0)), "complementary_color")
            r2 = verify_frame_accuracy(((0, 0, 1), (0, 1, 0)), "complementary_color")
            assert r1.frame_accurate_signature == r2.frame_accurate_signature


class TestSignatureDistinctness:
    def test_all_sigs_unique(self):
        sigs = set()
        for case in RS_FRAME_CASES + CC_FRAME_CASES:
            payloads = tuple(tuple(p) for p in case["payloads"])
            result = verify_frame_accuracy(payloads, case["mode"])
            assert result.verdict == FrameAccurateVerdict.FRAME_ACCURATE
            sigs.add(result.frame_accurate_signature)
        assert len(sigs) == len(RS_FRAME_CASES) + len(CC_FRAME_CASES)


class TestCrossMode:
    def test_same_payloads_different_modes(self):
        payloads = ((0, 0, 1, 0), (0, 1, 1, 0))
        r_rs = verify_frame_accuracy(payloads, "rolling_shutter")
        r_cc = verify_frame_accuracy(payloads, "complementary_color")
        assert r_rs.verdict == FrameAccurateVerdict.FRAME_ACCURATE
        assert r_cc.verdict == FrameAccurateVerdict.FRAME_ACCURATE
        assert r_rs.frame_accurate_signature != r_cc.frame_accurate_signature


class TestSlotOrder:
    def test_reversed_order_different_sig(self):
        fwd = ((0, 0, 1, 0), (0, 1, 1, 0))
        rev = ((0, 1, 1, 0), (0, 0, 1, 0))
        r_fwd = verify_frame_accuracy(fwd, "rolling_shutter")
        r_rev = verify_frame_accuracy(rev, "rolling_shutter")
        assert r_fwd.frame_accurate_signature != r_rev.frame_accurate_signature


class TestPredefinedCounts:
    def test_rs_count(self):
        assert len(RS_FRAME_CASES) == 4

    def test_cc_count(self):
        assert len(CC_FRAME_CASES) == 3

    def test_drift_count(self):
        assert len(DRIFT_CASES) == 2

    def test_oob_count(self):
        assert len(OOB_CASES) == 3
