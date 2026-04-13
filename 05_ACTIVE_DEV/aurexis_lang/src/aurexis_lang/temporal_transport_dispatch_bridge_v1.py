"""
Aurexis Core — Temporal Transport Dispatch Bridge V1

Bounded temporal-mode routing proof for the narrow V1 temporal transport branch.
Proves that a recovered temporal signal representation can be deterministically
identified as belonging to one of the existing frozen transport modes and routed
to the correct decoder path, with the resulting payload flowing into the existing
Aurexis validation/dispatch path.

What this proves:
  Given a temporal signal representation (either a rolling-shutter stripe image
  or a complementary-color chrominance sample sequence), the system can:
  1. Identify which transport mode produced the signal by inspecting its
     structural properties (dimensionality, value types, shape).
  2. Route the signal to the correct decoder (RS stripe decoder or CC
     chrominance decoder).
  3. Recover the bounded payload from the selected decoder.
  4. Pass the recovered payload into the existing Aurexis route resolution
     (artifact family dispatch).
  5. Report the full dispatch chain: mode → decoder → payload → route.

  Supported transport modes dispatch correctly.  Unknown or malformed signal
  representations fail honestly.

What this does NOT prove:
  - General modulation recognition
  - Full OCC stack
  - Full temporal fusion system
  - Noise-tolerant real-world classification
  - Arbitrary transport family enumeration
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen TemporalDispatchProfile lists exactly which transport modes are
    supported: "rolling_shutter" and "complementary_color".
  - Signal identification uses structural fingerprinting:
      * Rolling-shutter signals are 2D tuple-of-tuples (image rows of int pixels).
      * Complementary-color signals are 1D tuples of RGB float triples.
    This is a deterministic structural check, not a learned classifier.
  - Each mode has a frozen decode function reference and a frozen profile.
  - Dispatch produces a TemporalDispatchResult containing: identified mode,
    decoded payload, artifact family route, and full audit trail.
  - All operations are deterministic and use only stdlib + existing bridge modules.

This is a narrow deterministic temporal dispatch proof, not general modulation
recognition or full temporal fusion.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List, Union
from enum import Enum

# Import the two existing transport bridges
from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
    TemporalTransportProfile,
    TransportVerdict,
    TransportResult,
    encode_payload as rs_encode_payload,
    simulate_rolling_shutter,
    decode_stripes,
    extract_payload as rs_extract_payload,
    resolve_route as rs_resolve_route,
    compute_payload_signature as rs_compute_signature,
    transport_payload as rs_transport_payload,
)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
    ComplementaryColorTransportProfile,
    CCTransportVerdict,
    CCTransportResult,
    encode_cc_payload,
    simulate_cc_capture,
    decode_cc_chrominance,
    extract_cc_payload,
    resolve_cc_route,
    compute_cc_payload_signature,
    transport_cc_payload,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

DISPATCH_VERSION = "V1.0"
DISPATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# DISPATCH VERDICTS
# ════════════════════════════════════════════════════════════

class DispatchVerdict(str, Enum):
    """Outcome of a temporal transport dispatch operation."""
    DISPATCHED = "DISPATCHED"              # Signal identified, decoded, and routed
    UNKNOWN_MODE = "UNKNOWN_MODE"          # Signal does not match any frozen mode
    DECODE_FAILED = "DECODE_FAILED"        # Mode identified but decoding failed
    ROUTE_FAILED = "ROUTE_FAILED"          # Decoded but no valid route
    EMPTY_SIGNAL = "EMPTY_SIGNAL"          # Signal is empty or None
    ERROR = "ERROR"                        # Unexpected error


# ════════════════════════════════════════════════════════════
# FROZEN TRANSPORT MODE FAMILY
# ════════════════════════════════════════════════════════════

class TransportMode(str, Enum):
    """Frozen set of supported temporal transport modes."""
    ROLLING_SHUTTER = "rolling_shutter"
    COMPLEMENTARY_COLOR = "complementary_color"


FROZEN_TRANSPORT_MODES: Tuple[TransportMode, ...] = (
    TransportMode.ROLLING_SHUTTER,
    TransportMode.COMPLEMENTARY_COLOR,
)


# ════════════════════════════════════════════════════════════
# TEMPORAL DISPATCH PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalDispatchProfile:
    """
    Frozen profile defining the supported temporal transport dispatch
    configuration.

    supported_modes: the frozen set of transport mode identifiers.
    rs_profile: the rolling-shutter transport profile to use.
    cc_profile: the complementary-color transport profile to use.
    version: profile version string.
    """
    supported_modes: Tuple[str, ...] = ("rolling_shutter", "complementary_color")
    rs_profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE
    cc_profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE
    version: str = DISPATCH_VERSION


V1_DISPATCH_PROFILE = TemporalDispatchProfile()


# ════════════════════════════════════════════════════════════
# SIGNAL TYPE — UNION OF SUPPORTED SIGNAL REPRESENTATIONS
# ════════════════════════════════════════════════════════════

# Rolling-shutter signal: 2D image as tuple of rows of int pixel values
# Tuple[Tuple[int, ...], ...]
#
# Complementary-color signal: 1D sequence of RGB float triples
# Tuple[Tuple[float, float, float], ...]
#
# The dispatch logic identifies which type a given signal is by
# structural inspection.

TemporalSignal = Union[
    Tuple[Tuple[int, ...], ...],            # RS stripe image
    Tuple[Tuple[float, float, float], ...],  # CC chrominance samples
]


# ════════════════════════════════════════════════════════════
# SIGNAL IDENTIFICATION — STRUCTURAL FINGERPRINTING
# ════════════════════════════════════════════════════════════

def identify_transport_mode(
    signal: Any,
    profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE,
) -> Optional[TransportMode]:
    """
    Identify which temporal transport mode produced a given signal
    by inspecting its structural properties.

    Rules:
    - Signal must be a non-empty tuple of tuples.
    - Rolling-shutter: inner tuples are int-valued with length > 3
      (image rows with many pixel columns).
    - Complementary-color: inner tuples are float-valued with length == 3
      (RGB triples).
    - If the signal matches neither pattern, returns None.

    This is a deterministic structural check, not a learned classifier.
    """
    if not isinstance(signal, tuple) or len(signal) == 0:
        return None

    first = signal[0]
    if not isinstance(first, tuple) or len(first) == 0:
        return None

    # Check first element type to distinguish modes
    first_val = first[0]

    if isinstance(first_val, float):
        # Candidate: complementary-color (RGB float triples)
        # Verify: all inner tuples are length 3 with float values
        if all(
            isinstance(row, tuple) and len(row) == 3
            and all(isinstance(v, float) for v in row)
            for row in signal
        ):
            if "complementary_color" in profile.supported_modes:
                return TransportMode.COMPLEMENTARY_COLOR
        return None

    if isinstance(first_val, int):
        # Candidate: rolling-shutter (2D image with int rows)
        # Verify: inner tuples have length > 3 and all int values
        # (RS images have frame_width columns, typically 640)
        if len(first) > 3 and all(
            isinstance(row, tuple) and len(row) == len(first)
            and all(isinstance(v, int) for v in row)
            for row in signal
        ):
            if "rolling_shutter" in profile.supported_modes:
                return TransportMode.ROLLING_SHUTTER
        return None

    return None


# ════════════════════════════════════════════════════════════
# DISPATCH RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalDispatchResult:
    """Complete result of a temporal transport dispatch operation."""
    verdict: DispatchVerdict = DispatchVerdict.ERROR
    identified_mode: str = ""
    decoded_payload: Tuple[int, ...] = ()
    route_name: str = ""
    payload_signature: str = ""
    inner_verdict: str = ""
    signal_element_count: int = 0
    version: str = DISPATCH_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "identified_mode": self.identified_mode,
            "decoded_payload": list(self.decoded_payload),
            "route_name": self.route_name,
            "payload_signature": self.payload_signature,
            "inner_verdict": self.inner_verdict,
            "signal_element_count": self.signal_element_count,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# DISPATCH SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_dispatch_signature(
    mode: str,
    payload_bits: Tuple[int, ...],
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a dispatch result.

    Canonical form: "dispatch_mode=<mode>\\npayload=<bits>\\nversion=<version>"

    Deterministic: same mode + same payload → identical signature.
    """
    bits_str = ",".join(str(b) for b in payload_bits)
    canonical = f"dispatch_mode={mode}\npayload={bits_str}\nversion={DISPATCH_VERSION}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# RS DECODE PATH — ROUTE RS SIGNAL TO RS DECODER
# ════════════════════════════════════════════════════════════

def _dispatch_rs(
    signal: Tuple[Tuple[int, ...], ...],
    expected_slot_count: int,
    profile: TemporalDispatchProfile,
) -> TemporalDispatchResult:
    """
    Dispatch a rolling-shutter stripe image through the RS decoder.

    Steps:
    1. Decode stripes using timing-based slot sampling.
    2. Extract payload (strip sync header).
    3. Resolve route.
    4. Build dispatch result.
    """
    result = TemporalDispatchResult(
        identified_mode=TransportMode.ROLLING_SHUTTER.value,
        signal_element_count=len(signal),
    )

    try:
        # Decode
        decoded_seq = decode_stripes(signal, expected_slot_count, profile.rs_profile)
        if decoded_seq is None:
            result.verdict = DispatchVerdict.DECODE_FAILED
            result.inner_verdict = "STRIPE_ERROR"
            return result

        # Extract payload
        payload = rs_extract_payload(decoded_seq, profile.rs_profile)
        if payload is None:
            result.verdict = DispatchVerdict.DECODE_FAILED
            result.inner_verdict = "SYNC_FAILED"
            return result
        result.decoded_payload = payload

        # Resolve route
        route = rs_resolve_route(payload)
        if route is None:
            result.verdict = DispatchVerdict.ROUTE_FAILED
            result.inner_verdict = "ROUTE_FAILED"
            return result
        result.route_name = route

        # Signature
        result.payload_signature = compute_dispatch_signature(
            TransportMode.ROLLING_SHUTTER.value, payload
        )
        result.inner_verdict = "DECODED"
        result.verdict = DispatchVerdict.DISPATCHED
        return result

    except Exception:
        result.verdict = DispatchVerdict.ERROR
        result.inner_verdict = "ERROR"
        return result


# ════════════════════════════════════════════════════════════
# CC DECODE PATH — ROUTE CC SIGNAL TO CC DECODER
# ════════════════════════════════════════════════════════════

def _dispatch_cc(
    signal: Tuple[Tuple[float, float, float], ...],
    profile: TemporalDispatchProfile,
) -> TemporalDispatchResult:
    """
    Dispatch a complementary-color chrominance sample sequence through
    the CC decoder.

    Steps:
    1. Decode chrominance projections.
    2. Extract payload (strip sync header).
    3. Resolve route.
    4. Build dispatch result.
    """
    result = TemporalDispatchResult(
        identified_mode=TransportMode.COMPLEMENTARY_COLOR.value,
        signal_element_count=len(signal),
    )

    try:
        # Decode
        decoded_bits = decode_cc_chrominance(signal, profile.cc_profile)
        if decoded_bits is None:
            result.verdict = DispatchVerdict.DECODE_FAILED
            result.inner_verdict = "CHROMINANCE_ERROR"
            return result

        # Extract payload
        payload = extract_cc_payload(decoded_bits, profile.cc_profile)
        if payload is None:
            result.verdict = DispatchVerdict.DECODE_FAILED
            result.inner_verdict = "SYNC_FAILED"
            return result
        result.decoded_payload = payload

        # Resolve route
        route = resolve_cc_route(payload)
        if route is None:
            result.verdict = DispatchVerdict.ROUTE_FAILED
            result.inner_verdict = "ROUTE_FAILED"
            return result
        result.route_name = route

        # Signature
        result.payload_signature = compute_dispatch_signature(
            TransportMode.COMPLEMENTARY_COLOR.value, payload
        )
        result.inner_verdict = "DECODED"
        result.verdict = DispatchVerdict.DISPATCHED
        return result

    except Exception:
        result.verdict = DispatchVerdict.ERROR
        result.inner_verdict = "ERROR"
        return result


# ════════════════════════════════════════════════════════════
# END-TO-END DISPATCH: SIGNAL → IDENTIFY → DECODE → ROUTE
# ════════════════════════════════════════════════════════════

def dispatch_temporal_signal(
    signal: Any,
    expected_rs_slot_count: int = 0,
    profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE,
) -> TemporalDispatchResult:
    """
    Full end-to-end temporal transport dispatch.

    Steps:
    1. Check for empty/None signal.
    2. Identify transport mode by structural fingerprinting.
    3. Route to the correct decoder.
    4. Return TemporalDispatchResult with full audit trail.

    For rolling-shutter signals, expected_rs_slot_count must be provided
    (the decoder needs to know how many temporal slots to sample).
    If not provided (0), it defaults to the RS profile's sync header
    length + max supported payload length.

    Deterministic: same signal + same profile → identical result.
    """
    result = TemporalDispatchResult()

    try:
        # Step 1: Empty check
        if signal is None:
            result.verdict = DispatchVerdict.EMPTY_SIGNAL
            return result
        if isinstance(signal, tuple) and len(signal) == 0:
            result.verdict = DispatchVerdict.EMPTY_SIGNAL
            return result

        # Step 2: Identify mode
        mode = identify_transport_mode(signal, profile)
        if mode is None:
            result.verdict = DispatchVerdict.UNKNOWN_MODE
            return result

        # Step 3: Route to decoder
        if mode == TransportMode.ROLLING_SHUTTER:
            # Default slot count if not provided
            slot_count = expected_rs_slot_count
            if slot_count <= 0:
                slot_count = (
                    len(profile.rs_profile.sync_header)
                    + max(profile.rs_profile.supported_payload_lengths)
                )
            return _dispatch_rs(signal, slot_count, profile)

        elif mode == TransportMode.COMPLEMENTARY_COLOR:
            return _dispatch_cc(signal, profile)

        else:
            result.verdict = DispatchVerdict.UNKNOWN_MODE
            return result

    except Exception:
        result.verdict = DispatchVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# CONVENIENCE: GENERATE SIGNAL FROM PAYLOAD FOR TESTING
# ════════════════════════════════════════════════════════════

def generate_rs_signal(
    payload_bits: Tuple[int, ...],
    profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE,
) -> Optional[Tuple[Tuple[int, ...], ...]]:
    """
    Generate a rolling-shutter stripe image from a payload,
    for use in dispatch testing.

    Returns the 2D stripe image, or None if encoding fails.
    """
    frame_seq = rs_encode_payload(payload_bits, profile.rs_profile)
    if frame_seq is None:
        return None
    return simulate_rolling_shutter(frame_seq, profile.rs_profile)


def generate_cc_signal(
    payload_bits: Tuple[int, ...],
    profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE,
) -> Optional[Tuple[Tuple[float, float, float], ...]]:
    """
    Generate a complementary-color chrominance sample sequence from a payload,
    for use in dispatch testing.

    Returns the captured sample sequence, or None if encoding fails.
    """
    frame_seq = encode_cc_payload(payload_bits, profile.cc_profile)
    if frame_seq is None:
        return None
    return simulate_cc_capture(frame_seq, profile.cc_profile)


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: RS signals that dispatch correctly
RS_DISPATCH_CASES = (
    {
        "label": "rs_4bit_adjacent_pair",
        "payload": (0, 0, 1, 0),
        "expected_mode": "rolling_shutter",
        "expected_route": "adjacent_pair",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "rs_4bit_containment",
        "payload": (0, 1, 1, 0),
        "expected_mode": "rolling_shutter",
        "expected_route": "containment",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "rs_5bit_three_regions",
        "payload": (1, 0, 1, 0, 1),
        "expected_mode": "rolling_shutter",
        "expected_route": "three_regions",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "rs_8bit_adjacent_pair",
        "payload": (0, 0, 0, 0, 1, 1, 1, 1),
        "expected_mode": "rolling_shutter",
        "expected_route": "adjacent_pair",
        "expected_verdict": "DISPATCHED",
    },
)

# In-bounds: CC signals that dispatch correctly
CC_DISPATCH_CASES = (
    {
        "label": "cc_3bit_adjacent_pair",
        "payload": (0, 0, 1),
        "color_pair": "cyan_red",
        "expected_mode": "complementary_color",
        "expected_route": "adjacent_pair",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "cc_3bit_containment",
        "payload": (0, 1, 0),
        "color_pair": "cyan_red",
        "expected_mode": "complementary_color",
        "expected_route": "containment",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "cc_4bit_three_regions",
        "payload": (1, 0, 0, 1),
        "color_pair": "magenta_green",
        "expected_mode": "complementary_color",
        "expected_route": "three_regions",
        "expected_verdict": "DISPATCHED",
    },
    {
        "label": "cc_6bit_adjacent_pair",
        "payload": (0, 0, 0, 1, 1, 0),
        "color_pair": "yellow_blue",
        "expected_mode": "complementary_color",
        "expected_route": "adjacent_pair",
        "expected_verdict": "DISPATCHED",
    },
)

# OOB / failure cases
OOB_CASES = (
    {
        "label": "none_signal",
        "signal": None,
        "expected_verdict": "EMPTY_SIGNAL",
    },
    {
        "label": "empty_tuple",
        "signal": (),
        "expected_verdict": "EMPTY_SIGNAL",
    },
    {
        "label": "flat_ints",
        "signal": (1, 2, 3, 4),
        "expected_verdict": "UNKNOWN_MODE",
    },
    {
        "label": "nested_strings",
        "signal": (("hello",), ("world",)),
        "expected_verdict": "UNKNOWN_MODE",
    },
    {
        "label": "mixed_types",
        "signal": ((1, 2.0, 3),),
        "expected_verdict": "UNKNOWN_MODE",
    },
    {
        "label": "short_int_rows",
        "signal": ((1, 2), (3, 4)),
        "expected_verdict": "UNKNOWN_MODE",
    },
)

# Edge: reserved route through dispatch
EDGE_CASES = (
    {
        "label": "rs_reserved_route",
        "payload": (1, 1, 0, 0),
        "mode": "rolling_shutter",
        "expected_verdict": "ROUTE_FAILED",
    },
    {
        "label": "cc_reserved_route",
        "payload": (1, 1, 0),
        "mode": "complementary_color",
        "expected_verdict": "ROUTE_FAILED",
    },
)
