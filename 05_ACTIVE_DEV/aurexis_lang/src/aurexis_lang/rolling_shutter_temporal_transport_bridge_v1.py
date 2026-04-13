"""
Aurexis Core — Rolling Shutter Temporal Transport Bridge V1

Bounded screen-to-camera stripe transport proof for the narrow V1 raster bridge.
Proves that a bounded payload can be encoded into a temporal screen-emission
pattern, captured as rolling-shutter stripe structure on ordinary CMOS, decoded
back into the original payload, and routed into the existing Aurexis validation
path.

What this proves:
  Given a tiny bitstring payload (4–8 bits), the system can:
  1. Encode it into a deterministic sequence of binary screen-emission frames
     (black/white at a known refresh rate).
  2. Simulate rolling-shutter capture: an ordinary CMOS sensor exposes rows
     sequentially, so a screen that changes during exposure creates horizontal
     stripes.  The stripe pattern is a spatial encoding of the temporal
     frame sequence.
  3. Decode the stripe structure back into the original temporal sequence,
     then extract the bitstring payload.
  4. Map the recovered payload to a route ID that connects into the existing
     Aurexis dispatch/validation path (frozen artifact family names).

  Supported payloads decode correctly.  Out-of-bounds payloads (too long,
  wrong bit depth, corrupted stripes) fail honestly.

What this does NOT prove:
  - Full RS-OFDM or multi-carrier modulation
  - Imperceptible complementary-color transport
  - Noise-tolerant real-world camera capture
  - Multi-frame temporal consistency
  - Arbitrary payload sizes or unknown formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen TemporalTransportProfile defines the supported display/camera
    configuration: display refresh rate (Hz), sensor row readout time (µs),
    frame height (rows), supported payload bit lengths, and the route
    mapping from payload prefixes to artifact family names.
  - Temporal encoding: each payload bit maps to one temporal slot
    (1 = white band, 0 = black band).  A start-of-frame marker
    (white-black-white triple) is prepended for synchronization.
  - The display modulates at a temporal rate (e.g. 1000 Hz via
    backlight PWM or high-refresh switching) faster than the camera's
    row readout time, so different rows capture different temporal
    slots.
  - Rolling-shutter simulation: rows are assigned to temporal slots
    based on the ratio of row readout time to temporal slot duration.
    Each row's brightness reflects the display state at that row's
    exposure instant.
  - Stripe decoding: the simulated capture image is segmented into
    horizontal bands by brightness threshold.  Band transitions mark
    bit boundaries.  The synchronization header is detected and stripped.
  - Route mapping: the decoded bitstring's first 2 bits select a route ID,
    which maps to one of the frozen artifact family names from the existing
    dispatch bridge.
  - All operations are deterministic and use only stdlib.

This is a narrow deterministic rolling-shutter stripe transport proof,
not general optical camera communication or full RS-OFDM.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

RS_TRANSPORT_VERSION = "V1.0"
RS_TRANSPORT_FROZEN = True


# ════════════════════════════════════════════════════════════
# TRANSPORT VERDICTS
# ════════════════════════════════════════════════════════════

class TransportVerdict(str, Enum):
    """Outcome of a rolling-shutter temporal transport operation."""
    DECODED = "DECODED"                    # Payload successfully decoded and routed
    SYNC_FAILED = "SYNC_FAILED"            # Synchronization header not found
    PAYLOAD_TOO_SHORT = "PAYLOAD_TOO_SHORT"  # Decoded fewer bits than expected
    PAYLOAD_TOO_LONG = "PAYLOAD_TOO_LONG"  # Decoded more bits than supported
    UNSUPPORTED_LENGTH = "UNSUPPORTED_LENGTH"  # Payload bit length not in profile
    ROUTE_FAILED = "ROUTE_FAILED"          # Decoded payload has no valid route
    STRIPE_ERROR = "STRIPE_ERROR"          # Could not segment stripes
    ERROR = "ERROR"                        # Unexpected error


# ════════════════════════════════════════════════════════════
# ROUTE MAPPING — CONNECT TO EXISTING DISPATCH PATH
# ════════════════════════════════════════════════════════════
# The first 2 bits of the decoded payload select a route ID.
# Route IDs map to frozen artifact family names from the
# existing artifact dispatch bridge.

FROZEN_ROUTE_TABLE: Tuple[Tuple[str, str], ...] = (
    ("00", "adjacent_pair"),
    ("01", "containment"),
    ("10", "three_regions"),
    ("11", "RESERVED"),
)

ROUTE_MAP: Dict[str, str] = {prefix: name for prefix, name in FROZEN_ROUTE_TABLE}


# ════════════════════════════════════════════════════════════
# TEMPORAL TRANSPORT PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalTransportProfile:
    """
    Frozen profile defining the supported display/camera configuration
    for rolling-shutter temporal transport.

    temporal_rate_hz: display temporal modulation rate in Hz.  This is
        the rate at which the screen switches between states, achievable
        via backlight PWM or high-refresh displays (e.g. 1000 Hz).
        This is NOT the visual refresh rate — it is the underlying
        modulation rate that the rolling-shutter sensor can resolve.
    row_readout_us: time to read out one sensor row in microseconds.
        Typical CMOS: 15–30 µs/row.
    frame_height: number of rows in the simulated capture.
    frame_width: number of columns in the simulated capture.
    supported_payload_lengths: tuple of supported payload bit lengths.
    sync_header: the synchronization bit pattern prepended to payloads.
    brightness_white: pixel value for "white" (0–255).
    brightness_black: pixel value for "black" (0–255).
    stripe_threshold: brightness threshold to classify a row as white/black.
    version: profile version.

    With the default parameters:
    - temporal_rate_hz=1000 → slot duration = 1000 µs
    - row_readout_us=25 → rows per slot = 1000/25 = 40 rows
    - frame_height=480 → total readout = 12000 µs → 12 slots
    - max sequence = 3 (sync) + 8 (payload) = 11 ≤ 12 ✓
    """
    temporal_rate_hz: int = 1000
    row_readout_us: float = 25.0
    frame_height: int = 480
    frame_width: int = 640
    supported_payload_lengths: Tuple[int, ...] = (4, 5, 6, 7, 8)
    sync_header: Tuple[int, ...] = (1, 0, 1)
    brightness_white: int = 240
    brightness_black: int = 16
    stripe_threshold: int = 128
    version: str = RS_TRANSPORT_VERSION


V1_TRANSPORT_PROFILE = TemporalTransportProfile()


# ════════════════════════════════════════════════════════════
# TEMPORAL ENCODING: PAYLOAD → FRAME SEQUENCE
# ════════════════════════════════════════════════════════════

def encode_payload(
    payload_bits: Tuple[int, ...],
    profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE,
) -> Optional[Tuple[int, ...]]:
    """
    Encode a payload bitstring into a temporal frame sequence.

    The frame sequence is:
      sync_header + payload_bits

    Each element is 0 (black frame) or 1 (white frame).
    Returns None if the payload length is not supported.

    Deterministic: same payload → identical frame sequence.
    """
    if len(payload_bits) not in profile.supported_payload_lengths:
        return None
    if not all(b in (0, 1) for b in payload_bits):
        return None
    return profile.sync_header + payload_bits


# ════════════════════════════════════════════════════════════
# ROLLING-SHUTTER SIMULATION: FRAME SEQUENCE → STRIPE IMAGE
# ════════════════════════════════════════════════════════════

def simulate_rolling_shutter(
    frame_sequence: Tuple[int, ...],
    profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE,
) -> Tuple[Tuple[int, ...], ...]:
    """
    Simulate rolling-shutter capture of a temporal frame sequence.

    Physics model:
    - The display modulates at temporal_rate_hz, switching state once
      per temporal slot (1/temporal_rate_hz seconds).
    - The CMOS sensor reads rows sequentially from top to bottom.
    - Each row's exposure instant is offset by row_readout_us from
      the previous row.
    - The brightness of each row is determined by which temporal slot
      (and thus which frame in the sequence) was active at that row's
      exposure instant.

    Returns a 2D image as a tuple of rows, where each row is a tuple
    of identical pixel values (uniform horizontal brightness per row).

    The image height is profile.frame_height, width is profile.frame_width.

    Deterministic: same frame_sequence + same profile → identical image.
    """
    # Time per temporal slot in microseconds
    frame_duration_us = 1_000_000.0 / profile.temporal_rate_hz

    # Total time covered by the frame sequence
    total_sequence_time_us = len(frame_sequence) * frame_duration_us

    # Total sensor readout time
    total_readout_us = profile.frame_height * profile.row_readout_us

    rows = []
    for row_idx in range(profile.frame_height):
        # Time at which this row is exposed (µs from start)
        row_time_us = row_idx * profile.row_readout_us

        # Which frame index is active at this time?
        frame_idx = int(row_time_us / frame_duration_us)

        # Clamp to valid range
        if frame_idx < 0:
            frame_idx = 0
        elif frame_idx >= len(frame_sequence):
            frame_idx = len(frame_sequence) - 1

        # Determine brightness
        if frame_sequence[frame_idx] == 1:
            brightness = profile.brightness_white
        else:
            brightness = profile.brightness_black

        # All pixels in the row have the same brightness
        row_pixels = tuple(brightness for _ in range(profile.frame_width))
        rows.append(row_pixels)

    return tuple(rows)


# ════════════════════════════════════════════════════════════
# STRIPE DECODING: STRIPE IMAGE → FRAME SEQUENCE
# ════════════════════════════════════════════════════════════

def decode_stripes(
    image: Tuple[Tuple[int, ...], ...],
    expected_slot_count: int,
    profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE,
) -> Optional[Tuple[int, ...]]:
    """
    Decode a rolling-shutter stripe image back into the temporal
    frame sequence using timing-based slot sampling.

    Unlike transition-based decoding (which fails on consecutive
    same-value bits), this decoder uses the known temporal rate and
    row readout time to compute exactly which rows correspond to
    each temporal slot, then samples the center of each slot.

    This matches how real OCC receivers work: the receiver knows
    the clock rate and samples at the correct positions.

    Steps:
    1. Compute rows_per_slot = slot_duration_us / row_readout_us.
    2. For each expected slot, find the center row.
    3. Compute mean brightness of that row.
    4. Classify as white (1) or black (0) using threshold.

    Returns the decoded frame sequence (tuple of 0s and 1s),
    or None if decoding fails.

    Deterministic: same image + same profile → identical frame sequence.
    """
    if len(image) == 0:
        return None

    # Compute timing parameters
    slot_duration_us = 1_000_000.0 / profile.temporal_rate_hz
    rows_per_slot = slot_duration_us / profile.row_readout_us

    if rows_per_slot < 1.0:
        return None  # Can't resolve individual slots

    frame_bits: List[int] = []
    for slot_idx in range(expected_slot_count):
        # Center row of this slot
        center_row = int((slot_idx + 0.5) * rows_per_slot)

        if center_row < 0 or center_row >= len(image):
            # Slot extends beyond image — can't decode
            return None

        row = image[center_row]
        if len(row) == 0:
            return None

        mean_brightness = sum(row) / len(row)
        frame_bits.append(
            1 if mean_brightness >= profile.stripe_threshold else 0
        )

    return tuple(frame_bits)


# ════════════════════════════════════════════════════════════
# PAYLOAD EXTRACTION: FRAME SEQUENCE → BITSTRING
# ════════════════════════════════════════════════════════════

def extract_payload(
    frame_sequence: Tuple[int, ...],
    profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE,
) -> Optional[Tuple[int, ...]]:
    """
    Extract the payload bitstring from a decoded frame sequence.

    Steps:
    1. Detect the synchronization header at the start.
    2. Strip the header.
    3. Return the remaining bits as the payload.

    Returns None if the sync header is not found.

    Deterministic: same frame_sequence → identical payload.
    """
    header = profile.sync_header
    header_len = len(header)

    if len(frame_sequence) < header_len:
        return None

    # Check for sync header
    if frame_sequence[:header_len] != header:
        return None

    payload = frame_sequence[header_len:]
    return payload


# ════════════════════════════════════════════════════════════
# ROUTE RESOLUTION: PAYLOAD → ARTIFACT FAMILY ROUTE
# ════════════════════════════════════════════════════════════

def resolve_route(
    payload_bits: Tuple[int, ...],
) -> Optional[str]:
    """
    Resolve a decoded payload to an artifact family route name.

    The first 2 bits of the payload select the route.
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
# TRANSPORT RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TransportResult:
    """Complete result of a rolling-shutter temporal transport operation."""
    verdict: TransportVerdict = TransportVerdict.ERROR
    original_payload: Tuple[int, ...] = ()
    decoded_payload: Tuple[int, ...] = ()
    route_name: str = ""
    frame_sequence_length: int = 0
    stripe_count: int = 0
    image_height: int = 0
    image_width: int = 0
    payload_signature: str = ""
    version: str = RS_TRANSPORT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "original_payload": list(self.original_payload),
            "decoded_payload": list(self.decoded_payload),
            "route_name": self.route_name,
            "frame_sequence_length": self.frame_sequence_length,
            "stripe_count": self.stripe_count,
            "image_height": self.image_height,
            "image_width": self.image_width,
            "payload_signature": self.payload_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# PAYLOAD SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_payload_signature(
    payload_bits: Tuple[int, ...],
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a payload bitstring.

    Canonical form: "payload=<bits>\nversion=<version>"
    where <bits> is the comma-separated bit values.

    Deterministic: same payload → identical signature.
    """
    bits_str = ",".join(str(b) for b in payload_bits)
    canonical = f"payload={bits_str}\nversion={RS_TRANSPORT_VERSION}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# END-TO-END TRANSPORT: PAYLOAD → STRIPE → DECODE → ROUTE
# ════════════════════════════════════════════════════════════

def transport_payload(
    payload_bits: Tuple[int, ...],
    profile: TemporalTransportProfile = V1_TRANSPORT_PROFILE,
) -> TransportResult:
    """
    Full end-to-end rolling-shutter temporal transport.

    Steps:
    1. Validate payload length is supported
    2. Encode payload into temporal frame sequence
    3. Simulate rolling-shutter capture → stripe image
    4. Decode stripe image → recovered frame sequence
    5. Extract payload from recovered frame sequence
    6. Verify decoded payload matches original
    7. Resolve route from decoded payload
    8. Return TransportResult with verdict

    Deterministic: same payload + same profile → identical result.
    """
    result = TransportResult(
        original_payload=payload_bits,
        image_height=profile.frame_height,
        image_width=profile.frame_width,
    )

    try:
        # Step 1: Validate payload length
        if len(payload_bits) not in profile.supported_payload_lengths:
            result.verdict = TransportVerdict.UNSUPPORTED_LENGTH
            return result

        if not all(b in (0, 1) for b in payload_bits):
            result.verdict = TransportVerdict.ERROR
            return result

        # Step 2: Encode payload
        frame_seq = encode_payload(payload_bits, profile)
        if frame_seq is None:
            result.verdict = TransportVerdict.ERROR
            return result
        result.frame_sequence_length = len(frame_seq)

        # Step 3: Simulate rolling-shutter capture
        image = simulate_rolling_shutter(frame_seq, profile)
        result.image_height = len(image)
        result.image_width = len(image[0]) if image else 0

        # Step 4: Decode stripes (we know the expected slot count)
        expected_slots = len(frame_seq)
        decoded_seq = decode_stripes(image, expected_slots, profile)
        if decoded_seq is None:
            result.verdict = TransportVerdict.STRIPE_ERROR
            return result
        result.stripe_count = len(decoded_seq)

        # Step 5: Extract payload
        decoded_payload = extract_payload(decoded_seq, profile)
        if decoded_payload is None:
            result.verdict = TransportVerdict.SYNC_FAILED
            return result
        result.decoded_payload = decoded_payload

        # Step 6: Verify length
        if len(decoded_payload) < len(payload_bits):
            result.verdict = TransportVerdict.PAYLOAD_TOO_SHORT
            return result
        if len(decoded_payload) > max(profile.supported_payload_lengths):
            result.verdict = TransportVerdict.PAYLOAD_TOO_LONG
            return result

        # Step 7: Verify content match
        if decoded_payload[:len(payload_bits)] != payload_bits:
            # This should not happen in deterministic synthetic transport
            result.verdict = TransportVerdict.ERROR
            return result

        # Step 8: Resolve route
        route = resolve_route(decoded_payload)
        if route is None:
            result.verdict = TransportVerdict.ROUTE_FAILED
            return result
        result.route_name = route

        # Step 9: Compute payload signature
        result.payload_signature = compute_payload_signature(payload_bits)

        result.verdict = TransportVerdict.DECODED
        return result

    except Exception:
        result.verdict = TransportVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: supported payloads that decode correctly and route
IN_BOUNDS_CASES = (
    {
        "label": "4bit_adjacent_pair",
        "payload": (0, 0, 1, 0),
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "4bit_containment",
        "payload": (0, 1, 1, 0),
        "expected_verdict": "DECODED",
        "expected_route": "containment",
    },
    {
        "label": "4bit_three_regions",
        "payload": (1, 0, 0, 1),
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
    {
        "label": "5bit_adjacent_pair",
        "payload": (0, 0, 1, 1, 0),
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "6bit_containment",
        "payload": (0, 1, 0, 1, 1, 0),
        "expected_verdict": "DECODED",
        "expected_route": "containment",
    },
    {
        "label": "7bit_three_regions",
        "payload": (1, 0, 1, 0, 1, 0, 1),
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
    {
        "label": "8bit_adjacent_pair",
        "payload": (0, 0, 0, 0, 1, 1, 1, 1),
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "8bit_three_regions",
        "payload": (1, 0, 1, 1, 0, 0, 1, 0),
        "expected_verdict": "DECODED",
        "expected_route": "three_regions",
    },
)

# Out-of-bounds: payloads that fail honestly
OOB_CASES = (
    {
        "label": "too_short_3bit",
        "payload": (0, 0, 1),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "too_long_9bit",
        "payload": (0, 0, 1, 0, 1, 0, 1, 0, 1),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "empty_payload",
        "payload": (),
        "expected_verdict": "UNSUPPORTED_LENGTH",
    },
    {
        "label": "reserved_route_11",
        "payload": (1, 1, 0, 0),
        "expected_verdict": "ROUTE_FAILED",
    },
)

# All-zeros and all-ones edge cases
EDGE_CASES = (
    {
        "label": "all_zeros_4bit",
        "payload": (0, 0, 0, 0),
        "expected_verdict": "DECODED",
        "expected_route": "adjacent_pair",
    },
    {
        "label": "all_ones_4bit_reserved",
        "payload": (1, 1, 1, 1),
        "expected_verdict": "ROUTE_FAILED",
    },
)
