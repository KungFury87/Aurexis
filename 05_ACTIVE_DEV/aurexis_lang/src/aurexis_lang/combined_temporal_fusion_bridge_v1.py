"""
Aurexis Core — Combined RS + Complementary-Color Temporal Fusion Bridge V1

Bounded stripe-and-color fusion transport proof for the narrow V1 temporal
transport branch.  Proves that encoding the same bounded payload through both
rolling-shutter stripe transport AND complementary-color temporal transport,
then decoding both channels and checking agreement, produces a deterministic
fused payload recovery.

What this proves:
  Given a bounded payload and a frozen fusion profile, the system can:
  1. Encode the payload through the rolling-shutter transport encoder.
  2. Encode the same payload through the complementary-color transport encoder.
  3. Simulate capture of both transport signals independently.
  4. Dispatch each signal through the existing temporal dispatch bridge.
  5. Compare the two decoded payloads under a frozen fusion policy:
     - BOTH_AGREE: both channels decoded successfully and recovered
       identical payloads → fused payload accepted.
     - RS_ONLY: RS decoded but CC failed → bounded fallback to RS
       (if profile allows single-channel fallback).
     - CC_ONLY: CC decoded but RS failed → bounded fallback to CC
       (if profile allows single-channel fallback).
     - DISAGREE: both decoded but payloads differ → honest rejection.
     - BOTH_FAILED: neither channel decoded → honest rejection.
  6. Route the fused payload through the existing Aurexis artifact
     dispatch path.

  Supported fused payloads are those whose bit lengths lie in the
  intersection of RS and CC supported lengths: (4, 5, 6).

What this does NOT prove:
  - Full multimodal OCC
  - General optical fusion stack
  - Full invisible transport
  - Noise-tolerant real-world fusion
  - Adaptive channel weighting
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen FusionProfile defines: the supported payload lengths
    (intersection of RS and CC), the fusion policy (agree/fallback/reject),
    whether single-channel fallback is allowed, and references to both
    underlying transport profiles.
  - Generation produces a FusedSignalPair: one RS signal + one CC signal
    for the same payload.
  - Decode dispatches both signals independently through the existing
    temporal dispatch bridge.
  - Agreement checking compares decoded payloads and routes under the
    frozen policy.
  - A FusionResult records: verdict, per-channel details, fused payload,
    fused route, and a deterministic fusion signature.
  - All operations are deterministic and use only stdlib + existing bridges.

This is a narrow deterministic fused payload proof, not general optical
fusion or full multimodal OCC.

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
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

FUSION_VERSION = "V1.0"
FUSION_FROZEN = True


# ════════════════════════════════════════════════════════════
# FUSION VERDICTS
# ════════════════════════════════════════════════════════════

class FusionVerdict(str, Enum):
    """Outcome of a fused temporal transport decode."""
    BOTH_AGREE = "BOTH_AGREE"                  # Both channels agree on payload
    RS_ONLY = "RS_ONLY"                        # Only RS decoded (CC failed), fallback accepted
    CC_ONLY = "CC_ONLY"                        # Only CC decoded (RS failed), fallback accepted
    DISAGREE = "DISAGREE"                      # Both decoded but payloads differ
    BOTH_FAILED = "BOTH_FAILED"                # Neither channel decoded
    FALLBACK_DENIED = "FALLBACK_DENIED"        # Single channel ok but fallback not allowed
    UNSUPPORTED_LENGTH = "UNSUPPORTED_LENGTH"  # Payload length not in fused profile
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"            # No payload provided
    GENERATION_FAILED = "GENERATION_FAILED"    # Signal generation failed
    ERROR = "ERROR"                            # Unexpected error


# ════════════════════════════════════════════════════════════
# FROZEN FUSION PROFILE
# ════════════════════════════════════════════════════════════

# Supported fused payload lengths = intersection of RS (4-8) and CC (3-6)
FUSED_PAYLOAD_LENGTHS: Tuple[int, ...] = (4, 5, 6)

@dataclass(frozen=True)
class FusionProfile:
    """
    Frozen profile defining the bounded fused temporal transport family.

    supported_payload_lengths: payload bit lengths supported by both channels.
    allow_single_channel_fallback: if True, RS_ONLY or CC_ONLY accepted;
        if False, both channels must succeed.
    dispatch_profile: the dispatch profile used for per-channel decode.
    version: profile version string.
    """
    supported_payload_lengths: Tuple[int, ...] = FUSED_PAYLOAD_LENGTHS
    allow_single_channel_fallback: bool = True
    dispatch_profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE
    version: str = FUSION_VERSION


V1_FUSION_PROFILE = FusionProfile()

# Strict profile: no fallback allowed
V1_FUSION_STRICT_PROFILE = FusionProfile(allow_single_channel_fallback=False)


# ════════════════════════════════════════════════════════════
# CHANNEL RECORD — PER-CHANNEL DETAIL
# ════════════════════════════════════════════════════════════

@dataclass
class ChannelRecord:
    """Detail record for a single transport channel in a fused decode."""
    channel_name: str = ""              # "rolling_shutter" or "complementary_color"
    dispatch_verdict: str = ""
    decoded_payload: Tuple[int, ...] = ()
    route_name: str = ""
    payload_signature: str = ""
    succeeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_name": self.channel_name,
            "dispatch_verdict": self.dispatch_verdict,
            "decoded_payload": list(self.decoded_payload),
            "route_name": self.route_name,
            "payload_signature": self.payload_signature,
            "succeeded": self.succeeded,
        }


# ════════════════════════════════════════════════════════════
# FUSION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class FusionResult:
    """Complete result of a fused temporal transport decode."""
    verdict: FusionVerdict = FusionVerdict.ERROR
    fused_payload: Tuple[int, ...] = ()
    fused_route: str = ""
    source_channel: str = ""            # which channel(s) provided the payload
    rs_record: ChannelRecord = field(default_factory=lambda: ChannelRecord(channel_name="rolling_shutter"))
    cc_record: ChannelRecord = field(default_factory=lambda: ChannelRecord(channel_name="complementary_color"))
    fusion_signature: str = ""
    version: str = FUSION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "fused_payload": list(self.fused_payload),
            "fused_route": self.fused_route,
            "source_channel": self.source_channel,
            "rs_record": self.rs_record.to_dict(),
            "cc_record": self.cc_record.to_dict(),
            "fusion_signature": self.fusion_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FUSION SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_fusion_signature(
    verdict: str,
    payload: Tuple[int, ...],
    route: str,
    source: str,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a fusion result.

    Canonical form:
        fusion_verdict=<verdict>
        payload=<bits>
        route=<route>
        source=<source>
        version=<version>
    """
    bits_str = ",".join(str(b) for b in payload)
    canonical = (
        f"fusion_verdict={verdict}\n"
        f"payload={bits_str}\n"
        f"route={route}\n"
        f"source={source}\n"
        f"version={FUSION_VERSION}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# GENERATION: FUSED SIGNAL PAIR
# ════════════════════════════════════════════════════════════

def generate_fused_signals(
    payload: Tuple[int, ...],
    profile: FusionProfile = V1_FUSION_PROFILE,
) -> Optional[Tuple]:
    """
    Generate a fused signal pair: (rs_signal, cc_signal) for the same payload.

    Returns (rs_signal, cc_signal) or None if generation fails.
    """
    rs_signal = generate_rs_signal(payload, profile.dispatch_profile)
    cc_signal = generate_cc_signal(payload, profile.dispatch_profile)
    if rs_signal is None or cc_signal is None:
        return None
    return (rs_signal, cc_signal)


# ════════════════════════════════════════════════════════════
# FUSED DECODE: DISPATCH BOTH CHANNELS AND CHECK AGREEMENT
# ════════════════════════════════════════════════════════════

def fused_decode(
    payload: Tuple[int, ...],
    profile: FusionProfile = V1_FUSION_PROFILE,
    rs_signal_override: Any = None,
    cc_signal_override: Any = None,
) -> FusionResult:
    """
    Full end-to-end fused temporal transport decode.

    Steps:
    1. Validate payload length against fused profile.
    2. Generate fused signal pair (or use overrides for testing).
    3. Dispatch RS signal through dispatch bridge.
    4. Dispatch CC signal through dispatch bridge.
    5. Apply frozen fusion policy:
       - Both succeed + agree → BOTH_AGREE
       - Both succeed + disagree → DISAGREE
       - One succeeds, other fails:
         → RS_ONLY or CC_ONLY if fallback allowed
         → FALLBACK_DENIED if fallback not allowed
       - Both fail → BOTH_FAILED
    6. Compute fusion signature.

    rs_signal_override / cc_signal_override: optional pre-generated signals
    for testing disagreement or failure scenarios.

    Deterministic: same inputs → identical result.
    """
    result = FusionResult()

    try:
        # Step 1: Validate
        if len(payload) == 0:
            result.verdict = FusionVerdict.EMPTY_PAYLOAD
            return result

        if len(payload) not in profile.supported_payload_lengths:
            result.verdict = FusionVerdict.UNSUPPORTED_LENGTH
            return result

        # Step 2: Generate signals
        if rs_signal_override is not None and cc_signal_override is not None:
            rs_signal = rs_signal_override
            cc_signal = cc_signal_override
        else:
            pair = generate_fused_signals(payload, profile)
            if pair is None:
                result.verdict = FusionVerdict.GENERATION_FAILED
                return result
            rs_signal, cc_signal = pair

        # Step 3: Dispatch RS
        sync_len = len(profile.dispatch_profile.rs_profile.sync_header)
        rs_slot_count = sync_len + len(payload)
        rs_dispatch = dispatch_temporal_signal(
            rs_signal,
            expected_rs_slot_count=rs_slot_count,
            profile=profile.dispatch_profile,
        )
        rs_rec = ChannelRecord(
            channel_name="rolling_shutter",
            dispatch_verdict=rs_dispatch.verdict.value,
            decoded_payload=rs_dispatch.decoded_payload if rs_dispatch.verdict == DispatchVerdict.DISPATCHED else (),
            route_name=rs_dispatch.route_name if rs_dispatch.verdict == DispatchVerdict.DISPATCHED else "",
            payload_signature=rs_dispatch.payload_signature if rs_dispatch.verdict == DispatchVerdict.DISPATCHED else "",
            succeeded=(rs_dispatch.verdict == DispatchVerdict.DISPATCHED),
        )
        result.rs_record = rs_rec

        # Step 4: Dispatch CC
        cc_dispatch = dispatch_temporal_signal(
            cc_signal,
            profile=profile.dispatch_profile,
        )
        cc_rec = ChannelRecord(
            channel_name="complementary_color",
            dispatch_verdict=cc_dispatch.verdict.value,
            decoded_payload=cc_dispatch.decoded_payload if cc_dispatch.verdict == DispatchVerdict.DISPATCHED else (),
            route_name=cc_dispatch.route_name if cc_dispatch.verdict == DispatchVerdict.DISPATCHED else "",
            payload_signature=cc_dispatch.payload_signature if cc_dispatch.verdict == DispatchVerdict.DISPATCHED else "",
            succeeded=(cc_dispatch.verdict == DispatchVerdict.DISPATCHED),
        )
        result.cc_record = cc_rec

        # Step 5: Apply fusion policy
        rs_ok = rs_rec.succeeded
        cc_ok = cc_rec.succeeded

        if rs_ok and cc_ok:
            if rs_rec.decoded_payload == cc_rec.decoded_payload:
                # Both agree
                result.verdict = FusionVerdict.BOTH_AGREE
                result.fused_payload = rs_rec.decoded_payload
                result.fused_route = rs_rec.route_name
                result.source_channel = "both"
            else:
                # Disagree
                result.verdict = FusionVerdict.DISAGREE
                result.source_channel = "none"
                return result

        elif rs_ok and not cc_ok:
            if profile.allow_single_channel_fallback:
                result.verdict = FusionVerdict.RS_ONLY
                result.fused_payload = rs_rec.decoded_payload
                result.fused_route = rs_rec.route_name
                result.source_channel = "rolling_shutter"
            else:
                result.verdict = FusionVerdict.FALLBACK_DENIED
                result.source_channel = "none"
                return result

        elif cc_ok and not rs_ok:
            if profile.allow_single_channel_fallback:
                result.verdict = FusionVerdict.CC_ONLY
                result.fused_payload = cc_rec.decoded_payload
                result.fused_route = cc_rec.route_name
                result.source_channel = "complementary_color"
            else:
                result.verdict = FusionVerdict.FALLBACK_DENIED
                result.source_channel = "none"
                return result

        else:
            # Both failed
            result.verdict = FusionVerdict.BOTH_FAILED
            result.source_channel = "none"
            return result

        # Step 6: Compute signature
        result.fusion_signature = compute_fusion_signature(
            result.verdict.value,
            result.fused_payload,
            result.fused_route,
            result.source_channel,
        )
        return result

    except Exception:
        result.verdict = FusionVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: payloads where both channels should agree
AGREE_CASES = (
    {
        "label": "4bit_adjacent_pair",
        "payload": (0, 0, 1, 0),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "4bit_containment",
        "payload": (0, 1, 1, 0),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "containment",
    },
    {
        "label": "5bit_three_regions",
        "payload": (1, 0, 1, 0, 1),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "three_regions",
    },
    {
        "label": "6bit_adjacent_pair",
        "payload": (0, 0, 0, 1, 1, 0),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "4bit_all_zeros_adj",
        "payload": (0, 0, 0, 0),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "5bit_containment",
        "payload": (0, 1, 0, 1, 0),
        "expected_verdict": "BOTH_AGREE",
        "expected_route": "containment",
    },
)

# OOB / failure cases
OOB_CASES = (
    {
        "label": "empty_payload",
        "payload": (),
        "expected_verdict": "EMPTY_PAYLOAD",
    },
    {
        "label": "3bit_unsupported",
        "payload": (0, 0, 1),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "7bit_unsupported",
        "payload": (0, 0, 1, 0, 1, 0, 1),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "8bit_unsupported",
        "payload": (0, 0, 1, 0, 1, 0, 1, 0),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
)

# Disagreement test descriptors (signals must be generated externally)
DISAGREE_CASES = (
    {
        "label": "rs_adj_cc_cont",
        "rs_payload": (0, 0, 1, 0),       # adjacent_pair
        "cc_payload": (0, 1, 1, 0),        # containment
        "expected_verdict": "DISAGREE",
        "description": "RS encodes adjacent_pair, CC encodes containment",
    },
    {
        "label": "rs_cont_cc_three",
        "rs_payload": (0, 1, 0, 1, 0),     # containment
        "cc_payload": (1, 0, 1, 0, 1),     # three_regions
        "expected_verdict": "DISAGREE",
        "description": "RS encodes containment, CC encodes three_regions",
    },
)
