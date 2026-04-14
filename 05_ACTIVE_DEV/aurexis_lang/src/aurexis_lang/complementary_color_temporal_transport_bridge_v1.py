"""
Aurexis Core — Complementary-Color Temporal Transport Bridge V1

Bounded screen-to-camera complementary-color transport proof for the narrow
V1 temporal transport branch.  Proves that a bounded payload can be encoded
into a sequence of complementary-color display frames, captured/integrated
as a color-pair representation, decoded back into the original payload, and
routed into the existing Aurexis validation path.

What this proves:
  Given a tiny bitstring payload (3–6 bits), the system can:
  1. Encode it into a deterministic sequence of complementary-color frame
     pairs.  Each bit maps to one of two complementary-color states: the
     PRIMARY color or its COMPLEMENT.
  2. Simulate display/capture: a camera integrating over a short exposure
     captures the weighted average of the emitted complementary-color frames,
     producing a characteristic chrominance signature per temporal slot.
  3. Decode the chrominance signature sequence back into the original
     temporal bit sequence using a threshold on the color-difference axis.
  4. Map the recovered payload to a route ID that connects into the existing
     Aurexis dispatch/validation path (frozen artifact family names).

  Supported payloads decode correctly.  Out-of-bounds payloads (too long,
  wrong bit depth, corrupted chrominance) fail honestly.

What this does NOT prove:
  - Full invisible transport / imperceptible encoding
  - Full DeepCCB implementation
  - General optical camera communication
  - Noise-tolerant real-world camera capture
  - Multi-frame temporal consistency
  - Arbitrary payload sizes or unknown formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen ComplementaryColorTransportProfile defines the supported
    display/camera configuration: color pairs, temporal slot rate, exposure
    model, supported payload lengths, and route mapping.
  - Complementary-color pairs are chosen from a small frozen set:
    (Cyan, Red), (Magenta, Green), (Yellow, Blue).  Each pair sums to
    white (255, 255, 255) — the defining property of complementary colors.
  - Encoding: each payload bit selects PRIMARY (0) or COMPLEMENT (1) from
    the active color pair.  A sync header (PRIMARY, COMPLEMENT, PRIMARY)
    is prepended.
  - Display simulation: each temporal slot emits its assigned color as a
    uniform full-frame RGB value.
  - Capture simulation: the camera integrates consecutive pairs of frames
    (or single-frame snapshots) and the chrominance is measured along the
    color-difference axis defined by the pair.
  - Decoding: for each slot, compute the signed color-difference projection
    onto the pair axis.  PRIMARY projects positive, COMPLEMENT projects
    negative.  A threshold classifies each slot.
  - Route mapping: identical to rolling-shutter bridge — first 2 bits of
    payload select artifact family.
  - Human-visible integration: the complementary-color pairs are chosen so
    that rapid alternation (≥30 Hz) produces a perceptual average near
    neutral gray/white to a human viewer.  This is a bounded design
    constraint, not a broad imperceptibility claim.
  - All operations are deterministic and use only stdlib.

This is a narrow deterministic complementary-color temporal transport proof,
not general optical camera communication or full DeepCCB.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CC_TRANSPORT_VERSION = "V1.0"
CC_TRANSPORT_FROZEN = True


# ════════════════════════════════════════════════════════════
# TRANSPORT VERDICTS
# ════════════════════════════════════════════════════════════

class CCTransportVerdict(str, Enum):
    """Outcome of a complementary-color temporal transport operation."""
    DECODED = "DECODED"                        # Payload successfully decoded and routed
    SYNC_FAILED = "SYNC_FAILED"                # Sync header not detected
    PAYLOAD_TOO_SHORT = "PAYLOAD_TOO_SHORT"    # Decoded fewer bits than expected
    PAYLOAD_TOO_LONG = "PAYLOAD_TOO_LONG"      # Decoded more bits than supported
    UNSUPPORTED_LENGTH = "UNSUPPORTED_LENGTH"   # Payload bit length not in profile
    UNSUPPORTED_PAIR = "UNSUPPORTED_PAIR"       # Color pair not in frozen set
    ROUTE_FAILED = "ROUTE_FAILED"              # Decoded payload has no valid route
    CHROMINANCE_ERROR = "CHROMINANCE_ERROR"     # Could not classify chrominance
    MISMATCH = "MISMATCH"                      # Decoded payload does not match original
    ERROR = "ERROR"                            # Unexpected error


# ════════════════════════════════════════════════════════════
# FROZEN COMPLEMENTARY COLOR PAIRS
# ════════════════════════════════════════════════════════════
# Each pair (PRIMARY, COMPLEMENT) sums to (255, 255, 255).
# This is the defining property of complementary colors in
# additive RGB color space.

ColorRGB = Tuple[int, int, int]

FROZEN_COLOR_PAIRS: Tuple[Tuple[str, ColorRGB, ColorRGB], ...] = (
    ("cyan_red",    (0, 255, 255), (255, 0, 0)),
    ("magenta_green", (255, 0, 255), (0, 255, 0)),
    ("yellow_blue", (255, 255, 0), (0, 0, 255)),
)

COLOR_PAIR_MAP: Dict[str, Tuple[ColorRGB, ColorRGB]] = {
    name: (primary, complement)
    for name, primary, complement in FROZEN_COLOR_PAIRS
}


# ════════════════════════════════════════════════════════════
# ROUTE MAPPING — IDENTICAL TO ROLLING-SHUTTER BRIDGE
# ════════════════════════════════════════════════════════════

FROZEN_ROUTE_TABLE: Tuple[Tuple[str, str], ...] = (
    ("00", "adjacent_pair"),
    ("01", "containment"),
    ("10", "three_regions"),
    ("11", "RESERVED"),
)

ROUTE_MAP: Dict[str, str] = {prefix: name for prefix, name in FROZEN_ROUTE_TABLE}


# ════════════════════════════════════════════════════════════
# COMPLEMENTARY-COLOR TRANSPORT PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ComplementaryColorTransportProfile:
    """
    Frozen profile defining the supported display/camera configuration
    for complementary-color temporal transport.

    color_pair_name: which complementary-color pair to use (from frozen set).
    temporal_slot_hz: rate at which display switches color states (Hz).
        At ≥30 Hz, rapid alternation produces near-neutral perception
        for human viewers — a bounded design constraint.
    exposure_slots: how many temporal slots the camera integrates per
        captured sample.  1 = snapshot (captures single slot), 2 = integrates
        two consecutive slots.  Snapshot mode (1) is used for decoding;
        integration mode (2) demonstrates the human-perception average.
    supported_payload_lengths: tuple of supported payload bit lengths.
    sync_header: bit pattern prepended for synchronization (0=PRIMARY, 1=COMPLEMENT).
    chrominance_threshold: signed projection threshold for classification.
        Values above this → PRIMARY (0), below -threshold → COMPLEMENT (1).
    version: profile version string.
    """
    color_pair_name: str = "cyan_red"
    temporal_slot_hz: int = 60
    exposure_slots: int = 1
    supported_payload_lengths: Tuple[int, ...] = (3, 4, 5, 6)
    sync_header: Tuple[int, ...] = (0, 1, 0)
    chrominance_threshold: float = 0.0
    version: str = CC_TRANSPORT_VERSION


V1_CC_TRANSPORT_PROFILE = ComplementaryColorTransportProfile()


# ════════════════════════════════════════════════════════════
# COLOR-DIFFERENCE AXIS COMPUTATION
# ════════════════════════════════════════════════════════════

def _color_diff_axis(primary: ColorRGB, complement: ColorRGB) -> Tuple[float, float, float]:
    """
    Compute the normalized color-difference axis between primary and complement.

    The axis points from complement toward primary.
    Projection onto this axis:
      > 0 → closer to PRIMARY
      < 0 → closer to COMPLEMENT
      = 0 → exactly at midpoint (neutral gray)
    """
    diff = (
        primary[0] - complement[0],
        primary[1] - complement[1],
        primary[2] - complement[2],
    )
    magnitude = (diff[0]**2 + diff[1]**2 + diff[2]**2) ** 0.5
    if magnitude == 0:
        return (0.0, 0.0, 0.0)
    return (diff[0] / magnitude, diff[1] / magnitude, diff[2] / magnitude)


def _project_onto_axis(
    color: Tuple[float, float, float],
    midpoint: Tuple[float, float, float],
    axis: Tuple[float, float, float],
) -> float:
    """
    Project a color onto the color-difference axis relative to the midpoint.

    Returns a signed scalar:
      > 0 → toward PRIMARY
      < 0 → toward COMPLEMENT
    """
    centered = (
        color[0] - midpoint[0],
        color[1] - midpoint[1],
        color[2] - midpoint[2],
    )
    return centered[0] * axis[0] + centered[1] * axis[1] + centered[2] * axis[2]


# ════════════════════════════════════════════════════════════
# ENCODING: PAYLOAD → COLOR FRAME SEQUENCE
# ════════════════════════════════════════════════════════════

def encode_cc_payload(
    payload_bits: Tuple[int, ...],
    profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE,
) -> Optional[Tuple[Tuple[int, int, int], ...]]:
    """
    Encode a payload bitstring into a complementary-color frame sequence.

    Each bit maps to a color:
      0 → PRIMARY color of the active pair
      1 → COMPLEMENT color of the active pair

    A sync header is prepended.
    Returns a tuple of RGB triples, one per temporal slot.
    Returns None if payload length is unsupported or color pair unknown.

    Deterministic: same payload + same profile → identical frame sequence.
    """
    if len(payload_bits) not in profile.supported_payload_lengths:
        return None
    if not all(b in (0, 1) for b in payload_bits):
        return None
    if profile.color_pair_name not in COLOR_PAIR_MAP:
        return None

    primary, complement = COLOR_PAIR_MAP[profile.color_pair_name]
    bit_sequence = profile.sync_header + payload_bits

    frames: List[Tuple[int, int, int]] = []
    for bit in bit_sequence:
        if bit == 0:
            frames.append(primary)
        else:
            frames.append(complement)

    return tuple(frames)


# ════════════════════════════════════════════════════════════
# DISPLAY/CAPTURE SIMULATION
# ════════════════════════════════════════════════════════════

def simulate_cc_capture(
    frame_sequence: Tuple[Tuple[int, int, int], ...],
    profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE,
) -> Tuple[Tuple[float, float, float], ...]:
    """
    Simulate camera capture of a complementary-color frame sequence.

    In snapshot mode (exposure_slots=1): each captured sample is exactly
    the emitted color of one temporal slot (ideal single-slot capture).

    In integration mode (exposure_slots=2): each captured sample is the
    average of two consecutive slots (simulates camera integration).

    Returns a tuple of captured RGB float triples, one per sample.

    Deterministic: same frame_sequence + same profile → identical captures.
    """
    if len(frame_sequence) == 0:
        return ()

    exposure = profile.exposure_slots
    if exposure < 1:
        exposure = 1

    captures: List[Tuple[float, float, float]] = []

    if exposure == 1:
        # Snapshot: each frame captured individually
        for frame in frame_sequence:
            captures.append((float(frame[0]), float(frame[1]), float(frame[2])))
    else:
        # Integration: average consecutive groups of 'exposure' frames
        idx = 0
        while idx + exposure <= len(frame_sequence):
            r_sum = 0.0
            g_sum = 0.0
            b_sum = 0.0
            for j in range(exposure):
                f = frame_sequence[idx + j]
                r_sum += f[0]
                g_sum += f[1]
                b_sum += f[2]
            captures.append((r_sum / exposure, g_sum / exposure, b_sum / exposure))
            idx += exposure

    return tuple(captures)


# ════════════════════════════════════════════════════════════
# CHROMINANCE DECODING: CAPTURED SAMPLES → BIT SEQUENCE
# ════════════════════════════════════════════════════════════

def decode_cc_chrominance(
    captured_samples: Tuple[Tuple[float, float, float], ...],
    profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE,
) -> Optional[Tuple[int, ...]]:
    """
    Decode captured color samples back into a bit sequence using
    chrominance projection onto the color-difference axis.

    For each sample:
      1. Project onto the axis defined by (PRIMARY - COMPLEMENT).
      2. If projection > threshold → PRIMARY → bit 0.
      3. If projection < -threshold → COMPLEMENT → bit 1.
      4. If exactly at threshold → error (ambiguous).

    Returns the decoded bit sequence, or None if decoding fails.

    Deterministic: same samples + same profile → identical bit sequence.
    """
    if len(captured_samples) == 0:
        return None
    if profile.color_pair_name not in COLOR_PAIR_MAP:
        return None

    primary, complement = COLOR_PAIR_MAP[profile.color_pair_name]
    axis = _color_diff_axis(primary, complement)

    # Midpoint between primary and complement
    midpoint = (
        (primary[0] + complement[0]) / 2.0,
        (primary[1] + complement[1]) / 2.0,
        (primary[2] + complement[2]) / 2.0,
    )

    bits: List[int] = []
    for sample in captured_samples:
        proj = _project_onto_axis(sample, midpoint, axis)
        if proj > profile.chrominance_threshold:
            bits.append(0)  # PRIMARY
        elif proj < -profile.chrominance_threshold:
            bits.append(1)  # COMPLEMENT
        else:
            # Ambiguous — exactly at threshold (only happens with
            # integrated complementary pairs, which is expected)
            return None

    return tuple(bits)


# ════════════════════════════════════════════════════════════
# PAYLOAD EXTRACTION: BIT SEQUENCE → PAYLOAD
# ════════════════════════════════════════════════════════════

def extract_cc_payload(
    bit_sequence: Tuple[int, ...],
    profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE,
) -> Optional[Tuple[int, ...]]:
    """
    Extract the payload from a decoded bit sequence by detecting
    and stripping the sync header.

    Returns None if the sync header is not found.

    Deterministic: same bit_sequence → identical payload.
    """
    header = profile.sync_header
    header_len = len(header)

    if len(bit_sequence) < header_len:
        return None

    if bit_sequence[:header_len] != header:
        return None

    return bit_sequence[header_len:]


# ════════════════════════════════════════════════════════════
# ROUTE RESOLUTION
# ════════════════════════════════════════════════════════════

def resolve_cc_route(payload_bits: Tuple[int, ...]) -> Optional[str]:
    """
    Resolve a decoded payload to an artifact family route name.

    The first 2 bits select the route (identical to RS bridge).
    Returns None if the route prefix maps to RESERVED or is unknown.

    Deterministic: same payload → identical route.
    """
    if len(payload_bits) < 2:
        return None
    prefix = f"{payload_bits[0]}{payload_bits[1]}"
    route = ROUTE_MAP.get(prefix)
    if route is None or route == "RESERVED":
        return None
    return route


# ════════════════════════════════════════════════════════════
# HUMAN-VISIBLE INTEGRATION CHECK
# ════════════════════════════════════════════════════════════

def compute_perceptual_average(
    primary: ColorRGB,
    complement: ColorRGB,
) -> Tuple[float, float, float]:
    """
    Compute the perceptual average of rapid alternation between
    primary and complement colors.

    For true complementary pairs, this should be close to neutral
    gray (127.5, 127.5, 127.5).  This is a bounded design
    constraint — not a broad imperceptibility claim.

    Returns the average RGB as floats.
    """
    return (
        (primary[0] + complement[0]) / 2.0,
        (primary[1] + complement[1]) / 2.0,
        (primary[2] + complement[2]) / 2.0,
    )


# ════════════════════════════════════════════════════════════
# TRANSPORT RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CCTransportResult:
    """Complete result of a complementary-color temporal transport operation."""
    verdict: CCTransportVerdict = CCTransportVerdict.ERROR
    original_payload: Tuple[int, ...] = ()
    decoded_payload: Tuple[int, ...] = ()
    route_name: str = ""
    color_pair_name: str = ""
    frame_count: int = 0
    capture_count: int = 0
    payload_signature: str = ""
    version: str = CC_TRANSPORT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "original_payload": list(self.original_payload),
            "decoded_payload": list(self.decoded_payload),
            "route_name": self.route_name,
            "color_pair_name": self.color_pair_name,
            "frame_count": self.frame_count,
            "capture_count": self.capture_count,
            "payload_signature": self.payload_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# PAYLOAD SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_cc_payload_signature(
    payload_bits: Tuple[int, ...],
    color_pair_name: str,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a CC transport payload.

    Canonical form: "cc_payload=<bits>\\ncolor_pair=<name>\\nversion=<version>"

    Deterministic: same payload + same pair → identical signature.
    """
    bits_str = ",".join(str(b) for b in payload_bits)
    canonical = f"cc_payload={bits_str}\ncolor_pair={color_pair_name}\nversion={CC_TRANSPORT_VERSION}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# END-TO-END TRANSPORT: PAYLOAD → COLOR FRAMES → CAPTURE → DECODE → ROUTE
# ════════════════════════════════════════════════════════════

def transport_cc_payload(
    payload_bits: Tuple[int, ...],
    profile: ComplementaryColorTransportProfile = V1_CC_TRANSPORT_PROFILE,
) -> CCTransportResult:
    """
    Full end-to-end complementary-color temporal transport.

    Steps:
    1. Validate payload length is supported
    2. Validate color pair is in frozen set
    3. Encode payload into complementary-color frame sequence
    4. Simulate camera capture → color samples
    5. Decode chrominance → recovered bit sequence
    6. Extract payload from recovered bit sequence
    7. Verify decoded payload matches original
    8. Resolve route from decoded payload
    9. Compute payload signature
    10. Return CCTransportResult with verdict

    Deterministic: same payload + same profile → identical result.
    """
    result = CCTransportResult(
        original_payload=payload_bits,
        color_pair_name=profile.color_pair_name,
    )

    try:
        # Step 1: Validate payload length
        if len(payload_bits) not in profile.supported_payload_lengths:
            result.verdict = CCTransportVerdict.UNSUPPORTED_LENGTH
            return result

        if not all(b in (0, 1) for b in payload_bits):
            result.verdict = CCTransportVerdict.ERROR
            return result

        # Step 2: Validate color pair
        if profile.color_pair_name not in COLOR_PAIR_MAP:
            result.verdict = CCTransportVerdict.UNSUPPORTED_PAIR
            return result

        # Step 3: Encode payload
        frame_seq = encode_cc_payload(payload_bits, profile)
        if frame_seq is None:
            result.verdict = CCTransportVerdict.ERROR
            return result
        result.frame_count = len(frame_seq)

        # Step 4: Simulate capture
        captured = simulate_cc_capture(frame_seq, profile)
        result.capture_count = len(captured)

        # Step 5: Decode chrominance
        decoded_bits = decode_cc_chrominance(captured, profile)
        if decoded_bits is None:
            result.verdict = CCTransportVerdict.CHROMINANCE_ERROR
            return result

        # Step 6: Extract payload
        decoded_payload = extract_cc_payload(decoded_bits, profile)
        if decoded_payload is None:
            result.verdict = CCTransportVerdict.SYNC_FAILED
            return result
        result.decoded_payload = decoded_payload

        # Step 7: Verify length
        if len(decoded_payload) < len(payload_bits):
            result.verdict = CCTransportVerdict.PAYLOAD_TOO_SHORT
            return result
        if len(decoded_payload) > max(profile.supported_payload_lengths):
            result.verdict = CCTransportVerdict.PAYLOAD_TOO_LONG
            return result

        # Step 8: Verify content match
        if decoded_payload[:len(payload_bits)] != payload_bits:
            result.verdict = CCTransportVerdict.MISMATCH
            return result

        # Step 9: Resolve route
        route = resolve_cc_route(decoded_payload)
        if route is None:
            result.verdict = CCTransportVerdict.ROUTE_FAILED
            return result
        result.route_name = route

        # Step 10: Compute signature
        result.payload_signature = compute_cc_payload_signature(
            payload_bits, profile.color_pair_name
        )

        result.verdict = CCTransportVerdict.DECODED
        return result

    except Exception:
        result.verdict = CCTransportVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: supported payloads that decode correctly and route
IN_BOUNDS_CASES = (
    {
        "label": "3bit_adjacent_pair_cyan_red",
        "payload": (0, 0, 1),
        "color_pair": "cyan_red",
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "3bit_containment_cyan_red",
        "payload": (0, 1, 0),
        "color_pair": "cyan_red",
        "expected_verdict": "DECODED",
        "expected_route": "containment",
    },
    {
        "label": "3bit_three_regions_magenta_green",
        "payload": (1, 0, 1),
        "color_pair": "magenta_green",
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
    {
        "label": "4bit_adjacent_pair_yellow_blue",
        "payload": (0, 0, 1, 0),
        "color_pair": "yellow_blue",
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "5bit_containment_cyan_red",
        "payload": (0, 1, 0, 1, 1),
        "color_pair": "cyan_red",
        "expected_verdict": "DECODED",
        "expected_route": "containment",
    },
    {
        "label": "6bit_three_regions_magenta_green",
        "payload": (1, 0, 1, 0, 1, 0),
        "color_pair": "magenta_green",
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
    {
        "label": "4bit_containment_magenta_green",
        "payload": (0, 1, 1, 0),
        "color_pair": "magenta_green",
        "expected_verdict": "DECODED",
        "expected_route": "containment",
    },
    {
        "label": "6bit_adjacent_pair_yellow_blue",
        "payload": (0, 0, 0, 1, 1, 0),
        "color_pair": "yellow_blue",
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "5bit_three_regions_yellow_blue",
        "payload": (1, 0, 0, 1, 1),
        "color_pair": "yellow_blue",
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
)

# Out-of-bounds: payloads that fail honestly
OOB_CASES = (
    {
        "label": "too_short_2bit",
        "payload": (0, 0),
        "color_pair": "cyan_red",
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "too_long_7bit",
        "payload": (0, 0, 1, 0, 1, 0, 1),
        "color_pair": "cyan_red",
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "empty_payload",
        "payload": (),
        "color_pair": "cyan_red",
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "reserved_route_11",
        "payload": (1, 1, 0),
        "color_pair": "cyan_red",
        "expected_verdict": "ROUTE_FAILED",
    },
    {
        "label": "unknown_color_pair",
        "payload": (0, 0, 1),
        "color_pair": "orange_teal",
        "expected_verdict": "UNSUPPORTED_PAIR",
    },
)

# Edge cases: boundary conditions
EDGE_CASES = (
    {
        "label": "all_zeros_3bit",
        "payload": (0, 0, 0),
        "color_pair": "cyan_red",
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "all_ones_3bit_reserved",
        "payload": (1, 1, 1),
        "color_pair": "cyan_red",
        "expected_verdict": "ROUTE_FAILED",
    },
    {
        "label": "all_zeros_6bit",
        "payload": (0, 0, 0, 0, 0, 0),
        "color_pair": "magenta_green",
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
)
