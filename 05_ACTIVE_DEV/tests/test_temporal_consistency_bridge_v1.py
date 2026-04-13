"""
Pytest test suite — Temporal Consistency Bridge V1 (22nd bridge)

Tests the bounded repeated-capture agreement proof for temporal transport.

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
)

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
)


# ── Module Constants ──

class TestModuleConstants:
    def test_version(self):
        assert CONSISTENCY_VERSION == "V1.0"

    def test_frozen(self):
        assert CONSISTENCY_FROZEN is True

    def test_version_type(self):
        assert isinstance(CONSISTENCY_VERSION, str)


# ── Verdict Enum ──

class TestVerdictEnum:
    def test_all_verdicts_exist(self):
        expected = ["CONSISTENT", "INCONSISTENT", "CAPTURE_FAILED",
                    "TOO_FEW_CAPTURES", "TOO_MANY_CAPTURES", "EMPTY_SET", "ERROR"]
        for v in expected:
            assert hasattr(ConsistencyVerdict, v)

    def test_verdict_count(self):
        assert len(ConsistencyVerdict) == 7

    def test_verdict_is_str(self):
        assert isinstance(ConsistencyVerdict.CONSISTENT, str)


# ── Profile ──

class TestProfile:
    def test_min_captures(self):
        assert V1_CONSISTENCY_PROFILE.min_captures == 2

    def test_max_captures(self):
        assert V1_CONSISTENCY_PROFILE.max_captures == 10

    def test_agreement_threshold(self):
        assert V1_CONSISTENCY_PROFILE.agreement_threshold == 1.0

    def test_supported_modes(self):
        assert V1_CONSISTENCY_PROFILE.supported_modes == ("rolling_shutter", "complementary_color")

    def test_dispatch_profile(self):
        assert V1_CONSISTENCY_PROFILE.dispatch_profile is V1_DISPATCH_PROFILE

    def test_immutable(self):
        with pytest.raises(Exception):
            V1_CONSISTENCY_PROFILE.version = "other"


# ── CaptureRecord ──

class TestCaptureRecord:
    def test_defaults(self):
        rec = CaptureRecord()
        assert rec.capture_index == 0
        assert rec.succeeded is False
        assert rec.decoded_payload == ()

    def test_serialization(self):
        rec = CaptureRecord(capture_index=1, dispatch_verdict="DISPATCHED",
                            identified_mode="rolling_shutter",
                            decoded_payload=(0, 1, 0), route_name="adjacent_pair",
                            succeeded=True)
        d = rec.to_dict()
        assert d["capture_index"] == 1
        assert d["succeeded"] is True
        j = json.dumps(d)
        assert isinstance(json.loads(j), dict)


# ── ConsistencyResult ──

class TestConsistencyResult:
    def test_defaults(self):
        cr = TemporalConsistencyResult()
        assert cr.verdict == ConsistencyVerdict.ERROR
        assert cr.common_payload == ()
        assert cr.consistency_signature == ""

    def test_serialization(self):
        cr = TemporalConsistencyResult(
            verdict=ConsistencyVerdict.CONSISTENT,
            common_payload=(0, 1),
            capture_count=2,
            agree_count=2,
        )
        d = cr.to_dict()
        assert d["verdict"] == "CONSISTENT"
        j = json.dumps(d)
        assert isinstance(json.loads(j), dict)


# ── Consistency Signature ──

class TestConsistencySignature:
    def test_is_sha256(self):
        sig = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adj", 3)
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_deterministic(self):
        a = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adj", 3)
        b = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adj", 3)
        assert a == b

    def test_different_inputs(self):
        a = compute_consistency_signature("rolling_shutter", (0, 1, 0), "adj", 3)
        b = compute_consistency_signature("rolling_shutter", (1, 1, 0), "adj", 3)
        assert a != b


# ── Generation Helpers ──

class TestGenerateCaptures:
    def test_rs_repeated(self):
        caps = generate_repeated_rs_captures((0, 0, 1, 0), 3)
        assert len(caps) == 3
        assert all(c == caps[0] for c in caps)

    def test_cc_repeated(self):
        caps = generate_repeated_cc_captures((1, 0, 1), 4)
        assert len(caps) == 4
        assert all(c == caps[0] for c in caps)

    def test_drifted_rs(self):
        d = generate_drifted_capture_set((0, 0, 1, 0), (0, 1, 1, 0),
                                         "rolling_shutter", 2, 1)
        assert len(d) == 3
        assert d[0] == d[1]
        assert d[0] != d[2]

    def test_drifted_cc(self):
        d = generate_drifted_capture_set((0, 0, 1), (1, 0, 1),
                                         "complementary_color", 1, 2)
        assert len(d) == 3
        assert d[1] == d[2]
        assert d[0] != d[1]


# ── OOB Cases ──

class TestOOBCases:
    def test_empty_set(self):
        r = check_temporal_consistency([])
        assert r.verdict == ConsistencyVerdict.EMPTY_SET

    def test_too_few(self):
        caps = generate_repeated_rs_captures((0, 0, 1, 0), 1)
        r = check_temporal_consistency(caps)
        assert r.verdict == ConsistencyVerdict.TOO_FEW_CAPTURES

    def test_too_many(self):
        caps = generate_repeated_rs_captures((0, 0, 1, 0), 11)
        r = check_temporal_consistency(caps)
        assert r.verdict == ConsistencyVerdict.TOO_MANY_CAPTURES


# ── Consistent Cases ──

class TestConsistentCases:
    @pytest.mark.parametrize("case", [c for c in CONSISTENT_CASES if c["mode"] == "rolling_shutter"],
                             ids=lambda c: c["label"])
    def test_rs_consistent(self, case):
        payload = tuple(case["payload"])
        count = case["count"]
        signals = generate_repeated_rs_captures(payload, count)
        slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
        result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)
        assert result.verdict == ConsistencyVerdict.CONSISTENT
        assert result.common_payload == payload
        assert result.common_route == case["expected_route"]
        assert result.agree_count == count

    @pytest.mark.parametrize("case", [c for c in CONSISTENT_CASES if c["mode"] == "complementary_color"],
                             ids=lambda c: c["label"])
    def test_cc_consistent(self, case):
        payload = tuple(case["payload"])
        count = case["count"]
        signals = generate_repeated_cc_captures(payload, count)
        result = check_temporal_consistency(signals)
        assert result.verdict == ConsistencyVerdict.CONSISTENT
        assert result.common_payload == payload
        assert result.common_route == case["expected_route"]
        assert result.agree_count == count


# ── Inconsistent Cases ──

class TestInconsistentCases:
    @pytest.mark.parametrize("case", INCONSISTENT_CASES, ids=lambda c: c["label"])
    def test_drifted(self, case):
        signals = generate_drifted_capture_set(
            tuple(case["payload_a"]), tuple(case["payload_b"]),
            case["mode"], case["count_a"], case["count_b"])
        if case["mode"] == "rolling_shutter":
            slot_count = len(V1_TRANSPORT_PROFILE.sync_header) + len(case["payload_a"])
            result = check_temporal_consistency(signals, expected_rs_slot_count=slot_count)
        else:
            result = check_temporal_consistency(signals)
        assert result.verdict == ConsistencyVerdict.INCONSISTENT
        assert result.disagree_index >= 0


# ── Determinism ──

class TestDeterminism:
    def test_rs_deterministic(self):
        for _ in range(3):
            s1 = generate_repeated_rs_captures((0, 0, 1, 0), 3)
            s2 = generate_repeated_rs_captures((0, 0, 1, 0), 3)
            slot = len(V1_TRANSPORT_PROFILE.sync_header) + 4
            r1 = check_temporal_consistency(s1, expected_rs_slot_count=slot)
            r2 = check_temporal_consistency(s2, expected_rs_slot_count=slot)
            assert r1.consistency_signature == r2.consistency_signature

    def test_cc_deterministic(self):
        for _ in range(3):
            s1 = generate_repeated_cc_captures((1, 0, 1), 3)
            s2 = generate_repeated_cc_captures((1, 0, 1), 3)
            r1 = check_temporal_consistency(s1)
            r2 = check_temporal_consistency(s2)
            assert r1.consistency_signature == r2.consistency_signature


# ── Signature Distinctness ──

class TestSignatureDistinctness:
    def test_all_consistent_sigs_unique(self):
        sigs = set()
        for case in CONSISTENT_CASES:
            payload = tuple(case["payload"])
            count = case["count"]
            if case["mode"] == "rolling_shutter":
                signals = generate_repeated_rs_captures(payload, count)
                slot = len(V1_TRANSPORT_PROFILE.sync_header) + len(payload)
                result = check_temporal_consistency(signals, expected_rs_slot_count=slot)
            else:
                signals = generate_repeated_cc_captures(payload, count)
                result = check_temporal_consistency(signals)
            assert result.verdict == ConsistencyVerdict.CONSISTENT
            sigs.add(result.consistency_signature)
        assert len(sigs) == len(CONSISTENT_CASES)


# ── Predefined Case Counts ──

class TestPredefinedCases:
    def test_consistent_count(self):
        assert len(CONSISTENT_CASES) == 6

    def test_inconsistent_count(self):
        assert len(INCONSISTENT_CASES) == 2

    def test_oob_count(self):
        assert len(OOB_CASES) == 3
