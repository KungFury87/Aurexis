"""
Aurexis Core — Temporal Consistency Bridge V1

Bounded repeated-capture agreement proof for the narrow V1 temporal transport
branch.  Proves that repeated captures of the same bounded temporal payload
produce a stable recovered identity across time under the frozen temporal
transport profile, and that inconsistent or drifted capture sets are honestly
rejected.

What this proves:
  Given a bounded payload and a frozen transport mode (rolling-shutter or
  complementary-color), the system can:
  1. Generate N repeated synthetic captures of the same payload.
  2. Dispatch each capture through the existing temporal transport dispatch
     bridge to recover a payload + route per capture.
  3. Check that all N recovered payloads agree (unanimous agreement policy).
  4. If all agree, produce a CONSISTENT verdict with the common identity.
  5. If any capture disagrees (payload mismatch, route mismatch, decode
     failure), produce an INCONSISTENT verdict identifying the first
     disagreement.

  Supported repeated-capture sets pass correctly.  Drifted, inconsistent,
  or unsupported sets fail honestly.

What this does NOT prove:
  - Full video robustness
  - General motion invariance
  - Unconstrained temporal denoising
  - Full OCC stability system
  - Noise-tolerant real-world repeated capture
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen TemporalConsistencyProfile defines: the minimum and maximum
    number of repeated captures, the required agreement threshold (1.0 =
    unanimous), and the supported transport modes.
  - For each capture in the set, the signal is dispatched through the
    existing temporal transport dispatch bridge.
  - Agreement is checked across: decoded payload identity, route name,
    and transport mode.
  - A ConsistencyResult records: verdict, common payload, common route,
    per-capture details, and a deterministic consistency signature.
  - All operations are deterministic and use only stdlib + existing bridges.

This is a narrow deterministic temporal identity proof, not general video
robustness or full OCC stability.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE,
    TemporalDispatchProfile,
    TemporalDispatchResult,
    DispatchVerdict,
    dispatch_temporal_signal,
    generate_rs_signal,
    generate_cc_signal,
)

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
    ComplementaryColorTransportProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CONSISTENCY_VERSION = "V1.0"
CONSISTENCY_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONSISTENCY VERDICTS
# ════════════════════════════════════════════════════════════

class ConsistencyVerdict(str, Enum):
    """Outcome of a temporal consistency check."""
    CONSISTENT = "CONSISTENT"                    # All captures agree
    INCONSISTENT = "INCONSISTENT"                # Captures disagree
    CAPTURE_FAILED = "CAPTURE_FAILED"            # One or more captures failed to decode
    TOO_FEW_CAPTURES = "TOO_FEW_CAPTURES"        # Below minimum capture count
    TOO_MANY_CAPTURES = "TOO_MANY_CAPTURES"      # Above maximum capture count
    EMPTY_SET = "EMPTY_SET"                      # No captures provided
    ERROR = "ERROR"                              # Unexpected error


# ════════════════════════════════════════════════════════════
# TEMPORAL CONSISTENCY PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalConsistencyProfile:
    """
    Frozen profile defining the supported repeated-capture consistency
    configuration.

    min_captures: minimum number of repeated captures required.
    max_captures: maximum number of repeated captures allowed.
    agreement_threshold: fraction of captures that must agree (1.0 = unanimous).
        V1 uses unanimous agreement only.
    supported_modes: which transport modes are supported for consistency checks.
    dispatch_profile: the dispatch profile to use for per-capture decoding.
    version: profile version string.
    """
    min_captures: int = 2
    max_captures: int = 10
    agreement_threshold: float = 1.0
    supported_modes: Tuple[str, ...] = ("rolling_shutter", "complementary_color")
    dispatch_profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE
    version: str = CONSISTENCY_VERSION


V1_CONSISTENCY_PROFILE = TemporalConsistencyProfile()


# ════════════════════════════════════════════════════════════
# PER-CAPTURE RECORD
# ════════════════════════════════════════════════════════════

@dataclass
class CaptureRecord:
    """Record of a single capture's dispatch result."""
    capture_index: int = 0
    dispatch_verdict: str = ""
    identified_mode: str = ""
    decoded_payload: Tuple[int, ...] = ()
    route_name: str = ""
    succeeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capture_index": self.capture_index,
            "dispatch_verdict": self.dispatch_verdict,
            "identified_mode": self.identified_mode,
            "decoded_payload": list(self.decoded_payload),
            "route_name": self.route_name,
            "succeeded": self.succeeded,
        }


# ════════════════════════════════════════════════════════════
# CONSISTENCY RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalConsistencyResult:
    """Complete result of a temporal consistency check."""
    verdict: ConsistencyVerdict = ConsistencyVerdict.ERROR
    common_payload: Tuple[int, ...] = ()
    common_route: str = ""
    common_mode: str = ""
    capture_count: int = 0
    agree_count: int = 0
    disagree_index: int = -1
    capture_records: List[CaptureRecord] = field(default_factory=list)
    consistency_signature: str = ""
    version: str = CONSISTENCY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "common_payload": list(self.common_payload),
            "common_route": self.common_route,
            "common_mode": self.common_mode,
            "capture_count": self.capture_count,
            "agree_count": self.agree_count,
            "disagree_index": self.disagree_index,
            "capture_records": [r.to_dict() for r in self.capture_records],
            "consistency_signature": self.consistency_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CONSISTENCY SIGNATURE
# ════════════════════════════════════════════════════════════

def compute_consistency_signature(
    mode: str,
    payload: Tuple[int, ...],
    route: str,
    capture_count: int,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a consistency result.

    Canonical form includes mode, payload, route, and capture count.
    """
    bits_str = ",".join(str(b) for b in payload)
    canonical = (
        f"consistency_mode={mode}\n"
        f"payload={bits_str}\n"
        f"route={route}\n"
        f"capture_count={capture_count}\n"
        f"version={CONSISTENCY_VERSION}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# DISPATCH A SINGLE CAPTURE
# ════════════════════════════════════════════════════════════

def _dispatch_capture(
    signal: Any,
    index: int,
    expected_rs_slot_count: int,
    profile: TemporalConsistencyProfile,
) -> CaptureRecord:
    """Dispatch a single capture signal and return a CaptureRecord."""
    record = CaptureRecord(capture_index=index)
    try:
        result = dispatch_temporal_signal(
            signal,
            expected_rs_slot_count=expected_rs_slot_count,
            profile=profile.dispatch_profile,
        )
        record.dispatch_verdict = result.verdict.value
        record.identified_mode = result.identified_mode
        record.decoded_payload = result.decoded_payload
        record.route_name = result.route_name
        record.succeeded = (result.verdict == DispatchVerdict.DISPATCHED)
    except Exception:
        record.dispatch_verdict = "ERROR"
        record.succeeded = False
    return record


# ════════════════════════════════════════════════════════════
# CHECK CONSISTENCY ACROSS CAPTURE SET
# ════════════════════════════════════════════════════════════

def check_temporal_consistency(
    signals: List[Any],
    expected_rs_slot_count: int = 0,
    profile: TemporalConsistencyProfile = V1_CONSISTENCY_PROFILE,
) -> TemporalConsistencyResult:
    """
    Check temporal consistency across a set of repeated captures.

    Steps:
    1. Validate capture count is within profile bounds.
    2. Dispatch each capture through the temporal transport dispatch bridge.
    3. Check that all captures decoded successfully.
    4. Check unanimous agreement on: payload, route, and mode.
    5. If all agree, produce CONSISTENT verdict.
    6. If any disagree, produce INCONSISTENT verdict with first disagreement index.

    Deterministic: same signals + same profile → identical result.
    """
    result = TemporalConsistencyResult()

    try:
        # Step 1: Validate count
        n = len(signals)
        result.capture_count = n

        if n == 0:
            result.verdict = ConsistencyVerdict.EMPTY_SET
            return result
        if n < profile.min_captures:
            result.verdict = ConsistencyVerdict.TOO_FEW_CAPTURES
            return result
        if n > profile.max_captures:
            result.verdict = ConsistencyVerdict.TOO_MANY_CAPTURES
            return result

        # Step 2: Dispatch all captures
        records: List[CaptureRecord] = []
        for i, signal in enumerate(signals):
            rec = _dispatch_capture(signal, i, expected_rs_slot_count, profile)
            records.append(rec)
        result.capture_records = records

        # Step 3: Check all decoded successfully
        for rec in records:
            if not rec.succeeded:
                result.verdict = ConsistencyVerdict.CAPTURE_FAILED
                result.disagree_index = rec.capture_index
                return result

        # Step 4: Check unanimous agreement
        ref = records[0]
        agree = 1
        for i in range(1, len(records)):
            rec = records[i]
            if (rec.decoded_payload != ref.decoded_payload
                    or rec.route_name != ref.route_name
                    or rec.identified_mode != ref.identified_mode):
                result.verdict = ConsistencyVerdict.INCONSISTENT
                result.disagree_index = i
                result.agree_count = agree
                result.common_payload = ref.decoded_payload
                result.common_route = ref.route_name
                result.common_mode = ref.identified_mode
                return result
            agree += 1

        # Step 5: All agree → CONSISTENT
        result.verdict = ConsistencyVerdict.CONSISTENT
        result.common_payload = ref.decoded_payload
        result.common_route = ref.route_name
        result.common_mode = ref.identified_mode
        result.agree_count = agree
        result.consistency_signature = compute_consistency_signature(
            ref.identified_mode, ref.decoded_payload, ref.route_name, n
        )
        return result

    except Exception:
        result.verdict = ConsistencyVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# CONVENIENCE: GENERATE REPEATED CAPTURE SET
# ════════════════════════════════════════════════════════════

def generate_repeated_rs_captures(
    payload: Tuple[int, ...],
    count: int,
    profile: TemporalConsistencyProfile = V1_CONSISTENCY_PROFILE,
) -> List[Any]:
    """Generate `count` identical RS capture signals for a payload."""
    signal = generate_rs_signal(payload, profile.dispatch_profile)
    if signal is None:
        return []
    return [signal] * count


def generate_repeated_cc_captures(
    payload: Tuple[int, ...],
    count: int,
    profile: TemporalConsistencyProfile = V1_CONSISTENCY_PROFILE,
) -> List[Any]:
    """Generate `count` identical CC capture signals for a payload."""
    signal = generate_cc_signal(payload, profile.dispatch_profile)
    if signal is None:
        return []
    return [signal] * count


def generate_drifted_capture_set(
    payload_a: Tuple[int, ...],
    payload_b: Tuple[int, ...],
    mode: str,
    count_a: int,
    count_b: int,
    profile: TemporalConsistencyProfile = V1_CONSISTENCY_PROFILE,
) -> List[Any]:
    """
    Generate a mixed capture set where some captures are of payload_a
    and some are of payload_b — simulating temporal drift.
    """
    signals: List[Any] = []
    if mode == "rolling_shutter":
        sig_a = generate_rs_signal(payload_a, profile.dispatch_profile)
        sig_b = generate_rs_signal(payload_b, profile.dispatch_profile)
    else:
        sig_a = generate_cc_signal(payload_a, profile.dispatch_profile)
        sig_b = generate_cc_signal(payload_b, profile.dispatch_profile)

    if sig_a is None or sig_b is None:
        return []

    signals.extend([sig_a] * count_a)
    signals.extend([sig_b] * count_b)
    return signals


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# Consistent cases: repeated captures of same payload agree
CONSISTENT_CASES = (
    {
        "label": "rs_3x_adjacent_pair",
        "payload": (0, 0, 1, 0),
        "mode": "rolling_shutter",
        "count": 3,
        "expected_verdict": "CONSISTENT",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "rs_5x_containment",
        "payload": (0, 1, 1, 0),
        "mode": "rolling_shutter",
        "count": 5,
        "expected_verdict": "CONSISTENT",
        "expected_route": "containment",
    },
    {
        "label": "cc_3x_three_regions",
        "payload": (1, 0, 1),
        "mode": "complementary_color",
        "count": 3,
        "expected_verdict": "CONSISTENT",
        "expected_route": "three_regions",
    },
    {
        "label": "cc_4x_adjacent_pair",
        "payload": (0, 0, 1),
        "mode": "complementary_color",
        "count": 4,
        "expected_verdict": "CONSISTENT",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "rs_2x_minimum",
        "payload": (1, 0, 0, 1),
        "mode": "rolling_shutter",
        "count": 2,
        "expected_verdict": "CONSISTENT",
        "expected_route": "three_regions",
    },
    {
        "label": "rs_10x_maximum",
        "payload": (0, 0, 1, 0, 1),
        "mode": "rolling_shutter",
        "count": 10,
        "expected_verdict": "CONSISTENT",
        "expected_route": "adjacent_pair",
    },
)

# Inconsistent / drifted cases
INCONSISTENT_CASES = (
    {
        "label": "rs_drift_payload",
        "payload_a": (0, 0, 1, 0),
        "payload_b": (0, 1, 1, 0),
        "mode": "rolling_shutter",
        "count_a": 2,
        "count_b": 1,
        "expected_verdict": "INCONSISTENT",
    },
    {
        "label": "cc_drift_payload",
        "payload_a": (0, 0, 1),
        "payload_b": (1, 0, 1),
        "mode": "complementary_color",
        "count_a": 1,
        "count_b": 2,
        "expected_verdict": "INCONSISTENT",
    },
)

# OOB / failure cases
OOB_CASES = (
    {
        "label": "empty_set",
        "signals": [],
        "expected_verdict": "EMPTY_SET",
    },
    {
        "label": "single_capture",
        "mode": "rolling_shutter",
        "payload": (0, 0, 1, 0),
        "count": 1,
        "expected_verdict": "TOO_FEW_CAPTURES",
    },
    {
        "label": "too_many_captures",
        "mode": "rolling_shutter",
        "payload": (0, 0, 1, 0),
        "count": 11,
        "expected_verdict": "TOO_MANY_CAPTURES",
    },
)
