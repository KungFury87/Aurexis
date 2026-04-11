"""
Aurexis Core — Artifact Localization Bridge V1

Bounded embedded-artifact recovery for the narrow V1 raster bridge.
Proves that a canonical V1 artifact embedded inside a larger host image
can be localized, extracted, normalized, and decoded through the existing
raster/substrate path.

What this proves:
  A canonical V1 raster artifact placed at a bounded position within a
  larger host image, with bounded scale and allowed background colors,
  can be found via palette-color scanning, cropped, normalized back to
  canonical canvas size, and bridged into the V1 substrate.

What this does NOT prove:
  - Full real-world camera capture robustness
  - General visual localization or object detection
  - Full scene understanding
  - Multiple artifacts per host image
  - Print/scan round-trip robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Host image: larger canvas (configurable, default 800x800) with a
    uniform background color from an allowed set
  - One canonical artifact embedded at a bounded (x, y) offset with
    optional bounded scaling
  - Localization: scan for palette-color pixels to find the bounding
    box of the artifact region within the host image
  - Extraction: crop the host image to the located bounding box
  - Normalization: scale the cropped region back to 400x400 canonical size
  - Decode: feed normalized image through parse_artifact_tolerant() then
    bridge to substrate via the existing tolerance path
  - All operations are deterministic

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_COLOR,
    PRIMITIVE_PALETTE, ArtifactSpec, ArtifactPrimitive,
    BridgeVerdict, render_artifact, validate_spec,
    _render_to_raw_rgb, _encode_png, _decode_png_to_rgb,
    _color_distance_sq,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE, ToleranceProfile,
    degrade_scale,
)
from aurexis_lang.type_system_v1 import safe_execute_image_as_program


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

LOCALIZATION_VERSION = "V1.0"
LOCALIZATION_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN LOCALIZATION PROFILE
# ════════════════════════════════════════════════════════════

# Allowed host background colors — must be far from any palette color
ALLOWED_HOST_BACKGROUNDS = [
    (255, 255, 255),   # White (same as artifact canvas)
    (220, 220, 220),   # Light gray
    (180, 180, 180),   # Medium gray
    (240, 240, 230),   # Off-white / cream
    (200, 210, 220),   # Light blue-gray
]


@dataclass(frozen=True)
class LocalizationProfile:
    """
    Frozen envelope of allowed host-image configurations for V1 artifact
    localization. Placements beyond these bounds are expected to fail.
    """
    # Host canvas size
    host_width: int = 800
    host_height: int = 800

    # Artifact placement: offset from top-left of host canvas
    # The artifact (at its embedded scale) must fit entirely within host
    min_offset_x: int = 10
    max_offset_x: int = 380  # host_width - CANVAS_WIDTH - margin
    min_offset_y: int = 10
    max_offset_y: int = 380

    # Bounded scaling of the embedded artifact within the host
    min_embed_scale: float = 0.80
    max_embed_scale: float = 1.20

    # Minimum pixels of artifact palette color to consider a valid detection
    min_artifact_pixels: int = 200

    # Padding added around the detected bounding box before extraction
    extraction_padding: int = 5

    # Color distance threshold for palette-vs-background discrimination
    # Pixels must be closer to a palette color than this to count as artifact
    palette_detect_threshold_sq: int = 10000


V1_LOCALIZATION_PROFILE = LocalizationProfile()


# ════════════════════════════════════════════════════════════
# HOST IMAGE GENERATOR
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class HostImageSpec:
    """Defines how a canonical artifact is embedded in a host image."""
    artifact_spec: ArtifactSpec
    offset_x: int = 50
    offset_y: int = 50
    embed_scale: float = 1.0
    host_width: int = 800
    host_height: int = 800
    host_background: Tuple[int, int, int] = (220, 220, 220)


def generate_host_image(host_spec: HostImageSpec) -> bytes:
    """
    Generate a host image with a canonical artifact embedded at the
    specified offset and scale. Returns PNG bytes.

    Steps:
    1. Render the canonical artifact to raw RGB at canonical size
    2. Scale artifact if embed_scale != 1.0
    3. Create host canvas with uniform background
    4. Blit artifact pixels onto host at (offset_x, offset_y)
    5. Encode as PNG

    Deterministic: same HostImageSpec → identical PNG bytes.
    """
    # Step 1: Render canonical artifact
    art_rgb = _render_to_raw_rgb(host_spec.artifact_spec)
    art_w, art_h = CANVAS_WIDTH, CANVAS_HEIGHT

    # Step 2: Scale if needed
    if host_spec.embed_scale != 1.0:
        art_rgb, art_w, art_h = degrade_scale(
            art_rgb, art_w, art_h, host_spec.embed_scale
        )

    # Step 3: Create host canvas
    hw, hh = host_spec.host_width, host_spec.host_height
    bg = host_spec.host_background
    host_buf = bytearray(bg * hw * hh)

    # Step 4: Blit artifact onto host
    ox, oy = host_spec.offset_x, host_spec.offset_y
    for y in range(art_h):
        dst_y = oy + y
        if dst_y < 0 or dst_y >= hh:
            continue
        for x in range(art_w):
            dst_x = ox + x
            if dst_x < 0 or dst_x >= hw:
                continue
            src_off = (y * art_w + x) * 3
            px = (art_rgb[src_off], art_rgb[src_off + 1], art_rgb[src_off + 2])
            # Only blit non-white pixels (artifact content)
            # White pixels are artifact background — let host background show
            if px != BACKGROUND_COLOR:
                dst_off = (dst_y * hw + dst_x) * 3
                host_buf[dst_off] = px[0]
                host_buf[dst_off + 1] = px[1]
                host_buf[dst_off + 2] = px[2]

    # Step 5: Encode
    return _encode_png(hw, hh, host_buf)


# ════════════════════════════════════════════════════════════
# LOCALIZATION — find artifact bounding box in host image
# ════════════════════════════════════════════════════════════

def _is_palette_pixel(
    px: Tuple[int, int, int],
    threshold_sq: int,
) -> bool:
    """Check if a pixel is close to any palette color."""
    for color in PRIMITIVE_PALETTE:
        if _color_distance_sq(px, color) <= threshold_sq:
            return True
    return False


def localize_artifact(
    host_png: bytes,
    profile: LocalizationProfile = V1_LOCALIZATION_PROFILE,
) -> Optional[Tuple[int, int, int, int]]:
    """
    Find the bounding box of a V1 artifact within a host image.

    Scans all pixels for palette-color matches and computes the
    bounding box. Returns (x, y, w, h) or None if no artifact found.

    This is palette-color scanning, not general object detection.
    It works because V1 artifacts use a known frozen palette that
    is far from any allowed host background color.
    """
    width, height, buf = _decode_png_to_rgb(host_png)

    min_x, min_y = width, height
    max_x, max_y = -1, -1
    pixel_count = 0

    threshold_sq = profile.palette_detect_threshold_sq

    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            px = (buf[offset], buf[offset + 1], buf[offset + 2])
            if _is_palette_pixel(px, threshold_sq):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
                pixel_count += 1

    if pixel_count < profile.min_artifact_pixels:
        return None

    if max_x < 0:
        return None

    # Add padding (clamped to image bounds)
    pad = profile.extraction_padding
    x0 = max(0, min_x - pad)
    y0 = max(0, min_y - pad)
    x1 = min(width, max_x + 1 + pad)
    y1 = min(height, max_y + 1 + pad)

    return (x0, y0, x1 - x0, y1 - y0)


# ════════════════════════════════════════════════════════════
# EXTRACTION + NORMALIZATION
# ════════════════════════════════════════════════════════════

def extract_and_normalize(
    host_png: bytes,
    bbox: Tuple[int, int, int, int],
    target_width: int = CANVAS_WIDTH,
    target_height: int = CANVAS_HEIGHT,
) -> bytes:
    """
    Crop the host image to the given bounding box, then scale
    the cropped region to the canonical artifact size (400x400).

    Returns PNG bytes of the normalized artifact image.
    """
    width, height, buf = _decode_png_to_rgb(host_png)

    bx, by, bw, bh = bbox

    # Crop to bounding box
    cropped = bytearray(bw * bh * 3)
    for y in range(bh):
        src_y = by + y
        if src_y < 0 or src_y >= height:
            continue
        for x in range(bw):
            src_x = bx + x
            if src_x < 0 or src_x >= width:
                continue
            src_off = (src_y * width + src_x) * 3
            dst_off = (y * bw + x) * 3
            cropped[dst_off] = buf[src_off]
            cropped[dst_off + 1] = buf[src_off + 1]
            cropped[dst_off + 2] = buf[src_off + 2]

    # Scale to canonical size using nearest-neighbor
    norm_buf = bytearray(target_width * target_height * 3)
    x_ratio = bw / target_width
    y_ratio = bh / target_height

    for y in range(target_height):
        src_y = min(int(y * y_ratio), bh - 1)
        for x in range(target_width):
            src_x = min(int(x * x_ratio), bw - 1)
            src_off = (src_y * bw + src_x) * 3
            dst_off = (y * target_width + x) * 3
            norm_buf[dst_off] = cropped[src_off]
            norm_buf[dst_off + 1] = cropped[src_off + 1]
            norm_buf[dst_off + 2] = cropped[src_off + 2]

    return _encode_png(target_width, target_height, norm_buf)


# ════════════════════════════════════════════════════════════
# LOCALIZATION VERDICT
# ════════════════════════════════════════════════════════════

class LocalizationVerdict(str, Enum):
    """Result of artifact localization bridge."""
    LOCALIZED = "LOCALIZED"             # Found, extracted, decoded, bridged
    NOT_FOUND = "NOT_FOUND"             # No artifact detected in host
    EXTRACTION_FAILED = "EXTRACTION_FAILED"  # Found but extraction/normalization failed
    PARSE_FAILED = "PARSE_FAILED"       # Extracted but could not parse primitives
    BRIDGE_FAILED = "BRIDGE_FAILED"     # Parsed but substrate bridge failed


@dataclass
class LocalizationResult:
    """Complete result of the artifact localization bridge."""
    verdict: LocalizationVerdict = LocalizationVerdict.NOT_FOUND
    host_spec: Optional[HostImageSpec] = None
    detected_bbox: Optional[Tuple[int, int, int, int]] = None
    parsed_primitives: int = 0
    expected_primitives: int = 0
    type_check_verdict: str = ""
    execution_verdict: str = ""
    bridge_verdict: str = ""
    profile_version: str = LOCALIZATION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "detected_bbox": list(self.detected_bbox) if self.detected_bbox else None,
            "parsed_primitives": self.parsed_primitives,
            "expected_primitives": self.expected_primitives,
            "type_check_verdict": self.type_check_verdict,
            "execution_verdict": self.execution_verdict,
            "bridge_verdict": self.bridge_verdict,
            "profile_version": self.profile_version,
        }


# ════════════════════════════════════════════════════════════
# FULL LOCALIZATION BRIDGE — end to end
# ════════════════════════════════════════════════════════════

def localize_and_bridge(
    host_spec: HostImageSpec,
    profile: LocalizationProfile = V1_LOCALIZATION_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
) -> LocalizationResult:
    """
    Full artifact localization bridge path:
      host_spec → generate host image → localize → extract →
      normalize → tolerant parse → substrate bridge

    1. Generate host image with embedded artifact
    2. Localize artifact via palette-color scanning
    3. Extract and normalize to canonical 400x400
    4. Parse with tolerant parser
    5. Bridge to substrate

    If any step fails, returns an honest failure verdict.
    """
    result = LocalizationResult(host_spec=host_spec)
    result.expected_primitives = len(host_spec.artifact_spec.primitives)

    # Step 1: Generate host image
    host_png = generate_host_image(host_spec)

    # Step 2: Localize
    bbox = localize_artifact(host_png, profile)
    if bbox is None:
        result.verdict = LocalizationVerdict.NOT_FOUND
        return result
    result.detected_bbox = bbox

    # Step 3: Extract and normalize
    try:
        normalized_png = extract_and_normalize(host_png, bbox)
    except Exception:
        result.verdict = LocalizationVerdict.EXTRACTION_FAILED
        return result

    # Step 4: Tolerant parse
    parsed = parse_artifact_tolerant(normalized_png, tolerance)
    result.parsed_primitives = len(parsed)

    if result.parsed_primitives != result.expected_primitives:
        result.verdict = LocalizationVerdict.PARSE_FAILED
        return result

    # Step 5: Bridge to substrate
    spec = host_spec.artifact_spec
    substrate_result = safe_execute_image_as_program(
        parsed,
        bindings=spec.bindings,
        operations=list(spec.operations),
    )

    if not substrate_result["executed"]:
        result.verdict = LocalizationVerdict.BRIDGE_FAILED
        result.bridge_verdict = "NOT_EXECUTED"
        return result

    result.type_check_verdict = (
        "WELL_TYPED" if substrate_result["type_check"]["is_well_typed"]
        else "ILL_TYPED"
    )
    result.execution_verdict = substrate_result["execution"]["verdict"]

    # PASS, PARTIAL, EMPTY are valid substrate outcomes
    if result.execution_verdict in ("PASS", "PARTIAL", "EMPTY"):
        result.verdict = LocalizationVerdict.LOCALIZED
        result.bridge_verdict = "BRIDGED"
    else:
        result.verdict = LocalizationVerdict.BRIDGE_FAILED
        result.bridge_verdict = result.execution_verdict

    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: artifact placed within the localization profile envelope
IN_BOUNDS_PLACEMENTS = [
    # Center placement, default scale, various backgrounds
    {"offset_x": 200, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # Top-left, tight to edge
    {"offset_x": 15, "offset_y": 15, "embed_scale": 1.0,
     "host_background": (255, 255, 255)},

    # Bottom-right area
    {"offset_x": 350, "offset_y": 350, "embed_scale": 1.0,
     "host_background": (180, 180, 180)},

    # Off-white background
    {"offset_x": 100, "offset_y": 100, "embed_scale": 1.0,
     "host_background": (240, 240, 230)},

    # Blue-gray background
    {"offset_x": 150, "offset_y": 80, "embed_scale": 1.0,
     "host_background": (200, 210, 220)},

    # Scaled down (0.85)
    {"offset_x": 100, "offset_y": 100, "embed_scale": 0.85,
     "host_background": (220, 220, 220)},

    # Scaled up (1.15)
    {"offset_x": 50, "offset_y": 50, "embed_scale": 1.15,
     "host_background": (220, 220, 220)},

    # Different position, scaled down
    {"offset_x": 250, "offset_y": 250, "embed_scale": 0.90,
     "host_background": (180, 180, 180)},
]

# Out-of-bounds: artifact placement that should fail localization or decode
OUT_OF_BOUNDS_PLACEMENTS = [
    # Artifact placed mostly off-canvas (only tiny sliver visible)
    {"offset_x": 790, "offset_y": 790, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # Extreme scale down — artifact too small to survive normalization
    # At 0.05 scale, a 100x100 primitive becomes 5x5 pixels
    {"offset_x": 200, "offset_y": 200, "embed_scale": 0.05,
     "host_background": (220, 220, 220)},

    # Extreme scale down combined with off-center — too few pixels
    {"offset_x": 700, "offset_y": 700, "embed_scale": 0.08,
     "host_background": (220, 220, 220)},

    # Artifact entirely off-canvas to the left
    {"offset_x": -500, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},
]
