"""
Aurexis Core — Orientation Normalization Bridge V1

Bounded rotated-artifact recovery for the narrow V1 raster bridge.
Proves that a canonical V1 artifact embedded in a host image with
bounded orientation variation (0, 90, 180, 270 degrees) can be
localized, orientation-normalized back to canonical form, and
decoded through the existing raster bridge into the substrate.

What this proves:
  A canonical V1 raster artifact, rotated by one of the four
  cardinal angles and embedded in a host image, can be recovered
  to canonical orientation and bridged to the V1 substrate
  deterministically.

What this does NOT prove:
  - Arbitrary-angle rotation robustness
  - Full perspective correction
  - Full camera capture robustness
  - General rotation invariance
  - Full print/scan round-trip robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Only four cardinal rotations are supported: 0, 90, 180, 270 degrees
  - Rotation operations are deterministic pixel-level transforms
  - Orientation detection uses exhaustive trial: try all 4 inverse
    rotations, pick the one that produces correct primitive count
  - If no rotation produces a valid parse, fail honestly
  - The normalized artifact flows through the existing tolerant
    parser and substrate bridge — no bypass

This is a narrow orientation recovery proof, not general rotation
invariance or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_COLOR,
    PRIMITIVE_PALETTE, ArtifactSpec, ArtifactPrimitive,
    render_artifact, _render_to_raw_rgb, _encode_png, _decode_png_to_rgb,
    _color_distance_sq,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE, ToleranceProfile,
    degrade_scale,
)
from aurexis_lang.artifact_localization_bridge_v1 import (
    LocalizationProfile, V1_LOCALIZATION_PROFILE,
    ALLOWED_HOST_BACKGROUNDS, HostImageSpec,
    localize_artifact, extract_and_normalize,
    _is_palette_pixel,
)
from aurexis_lang.type_system_v1 import safe_execute_image_as_program


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

ORIENTATION_VERSION = "V1.0"
ORIENTATION_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN ORIENTATION PROFILE
# ════════════════════════════════════════════════════════════

# Supported cardinal rotations (degrees clockwise)
SUPPORTED_ANGLES = (0, 90, 180, 270)


@dataclass(frozen=True)
class OrientationProfile:
    """
    Frozen envelope of allowed orientation variations for V1 artifacts.
    Only the four cardinal rotations are supported. Any other angle
    is out of bounds and must fail honestly.
    """
    # Supported rotation angles (degrees, clockwise)
    supported_angles: Tuple[int, ...] = SUPPORTED_ANGLES

    # Detection method: try all supported rotations, pick the one
    # that produces correct primitive count from tolerant parse
    detection_method: str = "exhaustive_trial"

    # Host image parameters (inherited from localization profile)
    host_width: int = 800
    host_height: int = 800

    # Artifact placement bounds within host
    min_offset_x: int = 10
    max_offset_x: int = 380
    min_offset_y: int = 10
    max_offset_y: int = 380

    # Embedded artifact scale bounds
    min_embed_scale: float = 0.80
    max_embed_scale: float = 1.20

    # Minimum palette pixels to detect artifact
    min_artifact_pixels: int = 200

    # Padding around detected bbox
    extraction_padding: int = 5

    # Color distance threshold for palette detection
    palette_detect_threshold_sq: int = 10000


V1_ORIENTATION_PROFILE = OrientationProfile()


# ════════════════════════════════════════════════════════════
# DETERMINISTIC ROTATION FUNCTIONS
# ════════════════════════════════════════════════════════════

def rotate_90_cw(
    rgb_buf: bytearray, width: int, height: int
) -> Tuple[bytearray, int, int]:
    """
    Rotate image 90 degrees clockwise.
    Input WxH -> Output HxW.
    Pixel at (x, y) moves to (height-1-y, x) in the new image.
    Deterministic: same input -> identical output.
    """
    new_w, new_h = height, width
    new_buf = bytearray(new_w * new_h * 3)

    for y in range(height):
        for x in range(width):
            src_off = (y * width + x) * 3
            # New position: new_x = height-1-y, new_y = x
            new_x = height - 1 - y
            new_y = x
            dst_off = (new_y * new_w + new_x) * 3
            new_buf[dst_off] = rgb_buf[src_off]
            new_buf[dst_off + 1] = rgb_buf[src_off + 1]
            new_buf[dst_off + 2] = rgb_buf[src_off + 2]

    return new_buf, new_w, new_h


def rotate_180(
    rgb_buf: bytearray, width: int, height: int
) -> Tuple[bytearray, int, int]:
    """
    Rotate image 180 degrees.
    Pixel at (x, y) moves to (width-1-x, height-1-y).
    Deterministic: same input -> identical output.
    """
    new_buf = bytearray(width * height * 3)

    for y in range(height):
        for x in range(width):
            src_off = (y * width + x) * 3
            new_x = width - 1 - x
            new_y = height - 1 - y
            dst_off = (new_y * width + new_x) * 3
            new_buf[dst_off] = rgb_buf[src_off]
            new_buf[dst_off + 1] = rgb_buf[src_off + 1]
            new_buf[dst_off + 2] = rgb_buf[src_off + 2]

    return new_buf, width, height


def rotate_270_cw(
    rgb_buf: bytearray, width: int, height: int
) -> Tuple[bytearray, int, int]:
    """
    Rotate image 270 degrees clockwise (= 90 degrees counter-clockwise).
    Input WxH -> Output HxW.
    Pixel at (x, y) moves to (y, width-1-x) in the new image.
    Deterministic: same input -> identical output.
    """
    new_w, new_h = height, width
    new_buf = bytearray(new_w * new_h * 3)

    for y in range(height):
        for x in range(width):
            src_off = (y * width + x) * 3
            # New position: new_x = y, new_y = width-1-x
            new_x = y
            new_y = width - 1 - x
            dst_off = (new_y * new_w + new_x) * 3
            new_buf[dst_off] = rgb_buf[src_off]
            new_buf[dst_off + 1] = rgb_buf[src_off + 1]
            new_buf[dst_off + 2] = rgb_buf[src_off + 2]

    return new_buf, new_w, new_h


def rotate_image(
    rgb_buf: bytearray, width: int, height: int, angle: int
) -> Tuple[bytearray, int, int]:
    """
    Rotate image by the given angle (must be 0, 90, 180, or 270).
    Returns (new_buf, new_width, new_height).
    Deterministic.
    """
    angle = angle % 360
    if angle == 0:
        return bytearray(rgb_buf), width, height
    elif angle == 90:
        return rotate_90_cw(rgb_buf, width, height)
    elif angle == 180:
        return rotate_180(rgb_buf, width, height)
    elif angle == 270:
        return rotate_270_cw(rgb_buf, width, height)
    else:
        raise ValueError(
            f"Unsupported rotation angle: {angle}. "
            f"Only {SUPPORTED_ANGLES} are supported."
        )


def rotate_png(png_bytes: bytes, angle: int) -> bytes:
    """
    Rotate a PNG image by the given cardinal angle.
    Returns new PNG bytes. Deterministic.
    """
    width, height, buf = _decode_png_to_rgb(png_bytes)
    rot_buf, rot_w, rot_h = rotate_image(buf, width, height, angle)
    return _encode_png(rot_w, rot_h, rot_buf)


# ════════════════════════════════════════════════════════════
# ROTATED HOST IMAGE GENERATOR
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RotatedHostSpec:
    """
    Defines how a canonical artifact, rotated by a cardinal angle,
    is embedded in a host image.
    """
    artifact_spec: ArtifactSpec
    rotation_angle: int = 0        # 0, 90, 180, 270 degrees CW
    offset_x: int = 50
    offset_y: int = 50
    embed_scale: float = 1.0
    host_width: int = 800
    host_height: int = 800
    host_background: Tuple[int, int, int] = (220, 220, 220)


def generate_rotated_host_image(spec: RotatedHostSpec) -> bytes:
    """
    Generate a host image with a rotated canonical artifact embedded.

    Steps:
    1. Render canonical artifact to raw RGB
    2. Rotate by the specified angle
    3. Scale if embed_scale != 1.0
    4. Create host canvas with background
    5. Blit rotated artifact onto host at (offset_x, offset_y)
    6. Encode as PNG

    Deterministic: same RotatedHostSpec -> identical PNG bytes.
    """
    # Step 1: Render canonical artifact
    art_rgb = _render_to_raw_rgb(spec.artifact_spec)
    art_w, art_h = CANVAS_WIDTH, CANVAS_HEIGHT

    # Step 2: Rotate
    art_rgb, art_w, art_h = rotate_image(art_rgb, art_w, art_h, spec.rotation_angle)

    # Step 3: Scale if needed
    if spec.embed_scale != 1.0:
        art_rgb, art_w, art_h = degrade_scale(
            art_rgb, art_w, art_h, spec.embed_scale
        )

    # Step 4: Create host canvas
    hw, hh = spec.host_width, spec.host_height
    bg = spec.host_background
    host_buf = bytearray(bg * hw * hh)

    # Step 5: Blit rotated artifact onto host
    ox, oy = spec.offset_x, spec.offset_y
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
            if px != BACKGROUND_COLOR:
                dst_off = (dst_y * hw + dst_x) * 3
                host_buf[dst_off] = px[0]
                host_buf[dst_off + 1] = px[1]
                host_buf[dst_off + 2] = px[2]

    # Step 6: Encode
    return _encode_png(hw, hh, host_buf)


# ════════════════════════════════════════════════════════════
# ORIENTATION DETECTION — exhaustive trial
# ════════════════════════════════════════════════════════════

def _color_signature_matches(
    parsed: List[Dict[str, Any]],
    spec: ArtifactSpec,
    direction_threshold: int = 5,
) -> bool:
    """
    Check whether parsed primitives' relative spatial arrangement
    matches the canonical spec by color.

    Uses pairwise centroid direction (left/right, above/below) of
    color-matched primitives. This is robust to the non-proportional
    scaling introduced by extract_and_normalize because relative
    ordering (left-of, above) is preserved even when aspect ratio changes.

    For single-primitive specs, always returns True (no pairwise checks).
    """
    if len(parsed) != len(spec.primitives):
        return False

    # Build color -> centroid map from parsed
    parsed_map: Dict[Tuple[int, int, int], Tuple[float, float]] = {}
    for p in parsed:
        color = tuple(p["_artifact_color"])
        cx = p["bbox"][0] + p["bbox"][2] / 2.0
        cy = p["bbox"][1] + p["bbox"][3] / 2.0
        parsed_map[color] = (cx, cy)

    # Build color -> centroid map from canonical spec
    spec_map: Dict[Tuple[int, int, int], Tuple[float, float]] = {}
    for p in spec.primitives:
        cx = p.x + p.w / 2.0
        cy = p.y + p.h / 2.0
        spec_map[p.color] = (cx, cy)

    # Check all spec colors are found in parsed
    for color in spec_map:
        if color not in parsed_map:
            return False

    # Pairwise direction check: for each pair of primitives, verify
    # that the canonical spatial relationship is preserved in the parsed
    # image. "Red is LEFT of Blue" must remain true after correct rotation.
    colors = list(spec_map.keys())
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            c1, c2 = colors[i], colors[j]
            # Canonical direction
            sx = spec_map[c1][0] - spec_map[c2][0]
            sy = spec_map[c1][1] - spec_map[c2][1]
            # Parsed direction
            px = parsed_map[c1][0] - parsed_map[c2][0]
            py = parsed_map[c1][1] - parsed_map[c2][1]
            # Check x direction: if canonical has significant x-separation,
            # parsed must also have significant x-separation in same direction
            if abs(sx) > direction_threshold:
                if abs(px) < direction_threshold:
                    return False  # Lost x-separation
                if (sx > 0) != (px > 0):
                    return False  # Wrong x direction
            # Check y direction: same logic
            if abs(sy) > direction_threshold:
                if abs(py) < direction_threshold:
                    return False  # Lost y-separation
                if (sy > 0) != (py > 0):
                    return False  # Wrong y direction

    return True


def detect_orientation(
    artifact_png: bytes,
    spec: ArtifactSpec,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: OrientationProfile = V1_ORIENTATION_PROFILE,
) -> Optional[int]:
    """
    Detect the orientation of an extracted artifact image by
    exhaustive trial of all supported rotations.

    For each candidate angle, rotates the image by the inverse
    angle and attempts tolerant parsing. The angle that produces
    correct primitive count AND matching color-spatial signature
    (pairwise centroid directions match canonical) is returned.

    Uses color-spatial signatures rather than absolute bbox positions.
    This is robust to the non-proportional scaling from extraction.

    Returns the detected rotation angle (the angle the artifact
    was rotated BY), or None if no orientation produces a valid parse.

    Trial order: 0, 90, 180, 270 — deterministic.
    """
    width, height, buf = _decode_png_to_rgb(artifact_png)
    expected_count = len(spec.primitives)

    for angle in profile.supported_angles:
        # Inverse rotation: if artifact was rotated by `angle`,
        # we need to rotate by `-angle` (= 360-angle) to undo it
        inverse_angle = (360 - angle) % 360
        rot_buf, rot_w, rot_h = rotate_image(buf, width, height, inverse_angle)
        candidate_png = _encode_png(rot_w, rot_h, rot_buf)

        parsed = parse_artifact_tolerant(candidate_png, tolerance)
        if len(parsed) != expected_count:
            continue

        if _color_signature_matches(parsed, spec):
            return angle

    return None


def normalize_orientation(
    artifact_png: bytes,
    detected_angle: int,
) -> bytes:
    """
    Rotate an extracted artifact image back to canonical orientation.

    If the artifact was rotated by `detected_angle`, this applies
    the inverse rotation to restore canonical orientation.

    Returns PNG bytes of the normalized artifact.
    Deterministic.
    """
    inverse_angle = (360 - detected_angle) % 360
    return rotate_png(artifact_png, inverse_angle)


# ════════════════════════════════════════════════════════════
# ORIENTATION VERDICT
# ════════════════════════════════════════════════════════════

class OrientationVerdict(str, Enum):
    """Result of orientation normalization bridge."""
    NORMALIZED = "NORMALIZED"       # Orientation recovered, decoded, bridged
    NOT_FOUND = "NOT_FOUND"         # No artifact detected in host
    ORIENTATION_UNKNOWN = "ORIENTATION_UNKNOWN"  # Could not determine orientation
    PARSE_FAILED = "PARSE_FAILED"   # Normalized but parse count wrong
    BRIDGE_FAILED = "BRIDGE_FAILED" # Parsed but substrate bridge failed


@dataclass
class OrientationResult:
    """Complete result of the orientation normalization bridge."""
    verdict: OrientationVerdict = OrientationVerdict.NOT_FOUND
    host_spec: Optional[RotatedHostSpec] = None
    detected_bbox: Optional[Tuple[int, int, int, int]] = None
    detected_angle: Optional[int] = None
    parsed_primitives: int = 0
    expected_primitives: int = 0
    type_check_verdict: str = ""
    execution_verdict: str = ""
    bridge_verdict: str = ""
    profile_version: str = ORIENTATION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "detected_bbox": list(self.detected_bbox) if self.detected_bbox else None,
            "detected_angle": self.detected_angle,
            "parsed_primitives": self.parsed_primitives,
            "expected_primitives": self.expected_primitives,
            "type_check_verdict": self.type_check_verdict,
            "execution_verdict": self.execution_verdict,
            "bridge_verdict": self.bridge_verdict,
            "profile_version": self.profile_version,
        }


# ════════════════════════════════════════════════════════════
# FULL ORIENTATION NORMALIZATION BRIDGE — end to end
# ════════════════════════════════════════════════════════════

def orient_and_bridge(
    host_spec: RotatedHostSpec,
    orientation_profile: OrientationProfile = V1_ORIENTATION_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
) -> OrientationResult:
    """
    Full orientation normalization bridge path:
      host_spec -> generate rotated host image -> localize ->
      extract -> detect orientation -> normalize -> tolerant parse ->
      substrate bridge

    1. Generate host image with rotated embedded artifact
    2. Localize artifact via palette-color scanning
    3. Extract and normalize to canonical canvas size
    4. Detect orientation by exhaustive trial of inverse rotations
    5. Apply inverse rotation to normalize orientation
    6. Parse normalized image with tolerant parser
    7. Bridge to substrate

    If any step fails, returns an honest failure verdict.
    """
    result = OrientationResult(host_spec=host_spec)
    result.expected_primitives = len(host_spec.artifact_spec.primitives)

    # Step 1: Generate rotated host image
    host_png = generate_rotated_host_image(host_spec)

    # Step 2: Localize — use a LocalizationProfile derived from orientation profile
    loc_profile = LocalizationProfile(
        host_width=orientation_profile.host_width,
        host_height=orientation_profile.host_height,
        min_offset_x=orientation_profile.min_offset_x,
        max_offset_x=orientation_profile.max_offset_x,
        min_offset_y=orientation_profile.min_offset_y,
        max_offset_y=orientation_profile.max_offset_y,
        min_embed_scale=orientation_profile.min_embed_scale,
        max_embed_scale=orientation_profile.max_embed_scale,
        min_artifact_pixels=orientation_profile.min_artifact_pixels,
        extraction_padding=orientation_profile.extraction_padding,
        palette_detect_threshold_sq=orientation_profile.palette_detect_threshold_sq,
    )

    bbox = localize_artifact(host_png, loc_profile)
    if bbox is None:
        result.verdict = OrientationVerdict.NOT_FOUND
        return result
    result.detected_bbox = bbox

    # Step 3: Extract and normalize to canonical size
    try:
        extracted_png = extract_and_normalize(host_png, bbox)
    except Exception:
        result.verdict = OrientationVerdict.NOT_FOUND
        return result

    # Step 4: Detect orientation via exhaustive trial with bbox matching
    detected_angle = detect_orientation(
        extracted_png,
        spec=host_spec.artifact_spec,
        tolerance=tolerance,
        profile=orientation_profile,
    )

    if detected_angle is None:
        result.verdict = OrientationVerdict.ORIENTATION_UNKNOWN
        return result
    result.detected_angle = detected_angle

    # Step 5: Normalize orientation
    normalized_png = normalize_orientation(extracted_png, detected_angle)

    # Step 6: Tolerant parse on normalized image
    parsed = parse_artifact_tolerant(normalized_png, tolerance)
    result.parsed_primitives = len(parsed)

    if result.parsed_primitives != result.expected_primitives:
        result.verdict = OrientationVerdict.PARSE_FAILED
        return result

    # Step 7: Bridge to substrate
    spec = host_spec.artifact_spec
    substrate_result = safe_execute_image_as_program(
        parsed,
        bindings=spec.bindings,
        operations=list(spec.operations),
    )

    if not substrate_result["executed"]:
        result.verdict = OrientationVerdict.BRIDGE_FAILED
        result.bridge_verdict = "NOT_EXECUTED"
        return result

    result.type_check_verdict = (
        "WELL_TYPED" if substrate_result["type_check"]["is_well_typed"]
        else "ILL_TYPED"
    )
    result.execution_verdict = substrate_result["execution"]["verdict"]

    # PASS, PARTIAL, EMPTY are valid substrate outcomes
    if result.execution_verdict in ("PASS", "PARTIAL", "EMPTY"):
        result.verdict = OrientationVerdict.NORMALIZED
        result.bridge_verdict = "BRIDGED"
    else:
        result.verdict = OrientationVerdict.BRIDGE_FAILED
        result.bridge_verdict = result.execution_verdict

    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: rotated artifacts within the frozen orientation profile
# Each entry: (rotation_angle, offset_x, offset_y, embed_scale, host_background)
IN_BOUNDS_CASES = [
    # 0 degrees — no rotation (baseline)
    {"angle": 0, "offset_x": 200, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # 90 degrees CW
    {"angle": 90, "offset_x": 200, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # 180 degrees
    {"angle": 180, "offset_x": 200, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # 270 degrees CW
    {"angle": 270, "offset_x": 200, "offset_y": 200, "embed_scale": 1.0,
     "host_background": (220, 220, 220)},

    # 90 degrees with different placement
    {"angle": 90, "offset_x": 50, "offset_y": 50, "embed_scale": 1.0,
     "host_background": (255, 255, 255)},

    # 180 degrees with scale
    {"angle": 180, "offset_x": 100, "offset_y": 100, "embed_scale": 0.90,
     "host_background": (180, 180, 180)},

    # 270 degrees with scale and different background
    {"angle": 270, "offset_x": 150, "offset_y": 150, "embed_scale": 1.10,
     "host_background": (240, 240, 230)},

    # 90 degrees tight to edge
    {"angle": 90, "offset_x": 15, "offset_y": 15, "embed_scale": 1.0,
     "host_background": (200, 210, 220)},
]

# Out-of-bounds: cases that should fail orientation detection or decode
OUT_OF_BOUNDS_CASES = [
    # 45 degrees — not a supported cardinal rotation
    # We can't actually rotate by 45 degrees with our functions,
    # so we simulate this by generating a deliberately scrambled image.
    # Instead: artifact placed mostly off-canvas (too few pixels to detect)
    {"angle": 0, "offset_x": 790, "offset_y": 790, "embed_scale": 1.0,
     "host_background": (220, 220, 220), "expected_failure": "NOT_FOUND"},

    # Extreme miniaturization — too small to detect or normalize
    {"angle": 90, "offset_x": 200, "offset_y": 200, "embed_scale": 0.05,
     "host_background": (220, 220, 220), "expected_failure": "NOT_FOUND"},

    # Off-canvas entirely
    {"angle": 180, "offset_x": -500, "offset_y": -500, "embed_scale": 1.0,
     "host_background": (220, 220, 220), "expected_failure": "NOT_FOUND"},

    # Extreme miniaturization at edge
    {"angle": 270, "offset_x": 700, "offset_y": 700, "embed_scale": 0.08,
     "host_background": (220, 220, 220), "expected_failure": "NOT_FOUND"},
]
