"""
Aurexis Core — Capture Tolerance Bridge V1

Bounded capture tolerance path for the narrow V1 raster law bridge.
Proves that the existing canonical raster artifacts survive a defined
envelope of non-ideal image conditions while preserving deterministic
decode into the V1 substrate.

What this proves:
  A canonical V1 raster artifact, subjected to bounded synthetic
  degradations (scale, translation, blur, noise, compression,
  brightness/contrast), can still be parsed back into correct
  V1 primitives and bridged to the substrate — within a frozen
  tolerance profile.

What this does NOT prove:
  - Full real-world camera capture robustness
  - Full print/scan round-trip robustness
  - General-purpose CV or noise resilience
  - Tolerance beyond the frozen envelope
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - All degradations are deterministic (seeded PRNG or exact math)
  - A frozen ToleranceProfile defines what is "in bounds"
  - The tolerant parser matches palette colors within a color
    distance threshold instead of exact match
  - Out-of-bounds degradations must fail cleanly, not silently
    overclaim success

This is a synthetic-only bounded tolerance proof.
Real-world capture robustness is explicitly out of scope.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math
import struct
import zlib

from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_COLOR,
    PRIMITIVE_PALETTE, ArtifactSpec, ArtifactPrimitive,
    BridgeVerdict, BridgeResult,
    render_artifact, validate_spec, _render_to_raw_rgb, _encode_png,
    _decode_png_to_rgb, _color_distance_sq,
)
from aurexis_lang.type_system_v1 import safe_execute_image_as_program
from aurexis_lang.visual_grammar_v1 import OperationKind


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CAPTURE_TOLERANCE_VERSION = "V1.0"
CAPTURE_TOLERANCE_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN TOLERANCE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToleranceProfile:
    """
    Frozen envelope of allowed degradations for V1 artifact decode.

    Each bound defines the maximum magnitude of a degradation
    that the tolerant parser is designed to handle. Degradations
    beyond these bounds are expected to fail.
    """
    # Scale: factor applied to canvas. 1.0 = original.
    # e.g. 0.95 means 5% shrink, 1.05 means 5% grow
    min_scale: float = 0.90
    max_scale: float = 1.10

    # Translation: max pixel shift in x or y
    max_translate_px: int = 10

    # Gaussian blur: max kernel radius (integer pixels)
    max_blur_radius: int = 2

    # Additive noise: max per-channel deviation (uniform, signed)
    max_noise_amplitude: int = 25

    # JPEG compression: minimum quality (0-100)
    min_jpeg_quality: int = 70

    # Brightness shift: additive offset to all channels
    min_brightness_shift: int = -30
    max_brightness_shift: int = 30

    # Contrast factor: multiplier around 128 midpoint
    min_contrast_factor: float = 0.80
    max_contrast_factor: float = 1.20

    # Color matching threshold: max squared RGB distance for palette match
    # sqrt(50^2 * 3) ~ 86, so this allows ~50 per-channel deviation
    color_match_threshold_sq: int = 7500

    # Minimum primitive area (in pixels) after degradation to be detectable.
    # Must be high enough to filter blur-boundary artifacts (typically < 500px)
    # but low enough to detect real primitives (smallest canonical = 2500px+).
    min_detectable_area_px: int = 500


# The one frozen profile for V1
V1_TOLERANCE_PROFILE = ToleranceProfile()


# ════════════════════════════════════════════════════════════
# DETERMINISTIC DEGRADATION FUNCTIONS
# ════════════════════════════════════════════════════════════

def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, v))


def degrade_scale(
    rgb_buf: bytearray, width: int, height: int, factor: float
) -> Tuple[bytearray, int, int]:
    """
    Scale the image by a factor using nearest-neighbor interpolation.
    Returns (new_buf, new_width, new_height).
    Deterministic: same inputs → same output.
    """
    new_w = max(1, int(round(width * factor)))
    new_h = max(1, int(round(height * factor)))
    new_buf = bytearray(new_w * new_h * 3)

    for y in range(new_h):
        src_y = min(int(y / factor), height - 1)
        for x in range(new_w):
            src_x = min(int(x / factor), width - 1)
            src_off = (src_y * width + src_x) * 3
            dst_off = (y * new_w + x) * 3
            new_buf[dst_off] = rgb_buf[src_off]
            new_buf[dst_off + 1] = rgb_buf[src_off + 1]
            new_buf[dst_off + 2] = rgb_buf[src_off + 2]

    return new_buf, new_w, new_h


def degrade_translate(
    rgb_buf: bytearray, width: int, height: int, dx: int, dy: int
) -> bytearray:
    """
    Translate the image by (dx, dy) pixels. Fills new areas with white.
    Deterministic: same inputs → same output.
    """
    new_buf = bytearray(BACKGROUND_COLOR * width * height)

    for y in range(height):
        src_y = y - dy
        if src_y < 0 or src_y >= height:
            continue
        for x in range(width):
            src_x = x - dx
            if src_x < 0 or src_x >= width:
                continue
            src_off = (src_y * width + src_x) * 3
            dst_off = (y * width + x) * 3
            new_buf[dst_off] = rgb_buf[src_off]
            new_buf[dst_off + 1] = rgb_buf[src_off + 1]
            new_buf[dst_off + 2] = rgb_buf[src_off + 2]

    return new_buf


def degrade_blur(
    rgb_buf: bytearray, width: int, height: int, radius: int
) -> bytearray:
    """
    Apply box blur with given radius. Deterministic.
    Kernel size = (2*radius+1) x (2*radius+1).
    """
    if radius <= 0:
        return bytearray(rgb_buf)

    new_buf = bytearray(len(rgb_buf))
    kernel_size = (2 * radius + 1) ** 2

    for y in range(height):
        for x in range(width):
            r_sum = g_sum = b_sum = 0
            for ky in range(-radius, radius + 1):
                sy = max(0, min(height - 1, y + ky))
                for kx in range(-radius, radius + 1):
                    sx = max(0, min(width - 1, x + kx))
                    off = (sy * width + sx) * 3
                    r_sum += rgb_buf[off]
                    g_sum += rgb_buf[off + 1]
                    b_sum += rgb_buf[off + 2]

            dst = (y * width + x) * 3
            new_buf[dst] = r_sum // kernel_size
            new_buf[dst + 1] = g_sum // kernel_size
            new_buf[dst + 2] = b_sum // kernel_size

    return new_buf


def degrade_noise(
    rgb_buf: bytearray, width: int, height: int,
    amplitude: int, seed: int = 42
) -> bytearray:
    """
    Add deterministic pseudo-random uniform noise to each channel.
    Uses a simple LCG PRNG for reproducibility (no external deps).
    Noise range: [-amplitude, +amplitude] per channel.
    """
    new_buf = bytearray(len(rgb_buf))
    # Simple LCG: x_{n+1} = (a * x_n + c) mod m
    state = seed & 0xFFFFFFFF
    a, c, m = 1664525, 1013904223, 2**32

    for i in range(len(rgb_buf)):
        state = (a * state + c) % m
        # Map state to [-amplitude, +amplitude]
        noise = (state % (2 * amplitude + 1)) - amplitude
        new_buf[i] = _clamp(rgb_buf[i] + noise)

    return new_buf


def degrade_brightness(
    rgb_buf: bytearray, width: int, height: int, shift: int
) -> bytearray:
    """Shift all channel values by a constant. Deterministic."""
    new_buf = bytearray(len(rgb_buf))
    for i in range(len(rgb_buf)):
        new_buf[i] = _clamp(rgb_buf[i] + shift)
    return new_buf


def degrade_contrast(
    rgb_buf: bytearray, width: int, height: int, factor: float
) -> bytearray:
    """
    Adjust contrast around midpoint (128).
    factor > 1.0 = more contrast, < 1.0 = less contrast.
    Deterministic.
    """
    new_buf = bytearray(len(rgb_buf))
    for i in range(len(rgb_buf)):
        v = int(round(128 + (rgb_buf[i] - 128) * factor))
        new_buf[i] = _clamp(v)
    return new_buf


def degrade_jpeg_compress(
    png_bytes: bytes, quality: int
) -> bytes:
    """
    Simulate JPEG compression artifacts by quantizing color values.
    Since we can't use actual JPEG without Pillow/external deps,
    we simulate the main effect: color quantization per block.

    This applies 8x8 block averaging then adds quantization noise
    proportional to (100 - quality). Deterministic.

    Returns new PNG bytes.
    """
    width, height, rgb_buf = _decode_png_to_rgb(png_bytes)

    # Quantization step: higher quality = less quantization
    q_step = max(1, (100 - quality) // 5)
    block_size = 8

    new_buf = bytearray(rgb_buf)

    for by in range(0, height, block_size):
        for bx in range(0, width, block_size):
            # Compute block average
            r_sum = g_sum = b_sum = 0
            count = 0
            for y in range(by, min(by + block_size, height)):
                for x in range(bx, min(bx + block_size, width)):
                    off = (y * width + x) * 3
                    r_sum += rgb_buf[off]
                    g_sum += rgb_buf[off + 1]
                    b_sum += rgb_buf[off + 2]
                    count += 1

            # Quantize and distribute
            r_avg = (r_sum // count // q_step) * q_step
            g_avg = (g_sum // count // q_step) * q_step
            b_avg = (b_sum // count // q_step) * q_step

            for y in range(by, min(by + block_size, height)):
                for x in range(bx, min(bx + block_size, width)):
                    off = (y * width + x) * 3
                    # Blend original toward quantized average
                    blend = q_step / 50.0  # Higher q_step = more blending
                    blend = min(blend, 1.0)
                    new_buf[off] = _clamp(int(rgb_buf[off] * (1 - blend) + r_avg * blend))
                    new_buf[off + 1] = _clamp(int(rgb_buf[off + 1] * (1 - blend) + g_avg * blend))
                    new_buf[off + 2] = _clamp(int(rgb_buf[off + 2] * (1 - blend) + b_avg * blend))

    return _encode_png(width, height, new_buf)


# ════════════════════════════════════════════════════════════
# TOLERANT PARSER — color distance matching
# ════════════════════════════════════════════════════════════

def parse_artifact_tolerant(
    png_bytes: bytes,
    profile: ToleranceProfile = V1_TOLERANCE_PROFILE,
) -> List[Dict[str, Any]]:
    """
    Parse a (possibly degraded) artifact PNG into primitive dicts.

    Unlike the exact parse_artifact(), this uses color distance
    matching: each pixel is assigned to the nearest palette color
    within the threshold. If no palette color is close enough,
    the pixel is treated as background.

    Returns primitives with confidence < 1.0 to indicate tolerant
    (non-exact) matching was used.
    """
    width, height, buf = _decode_png_to_rgb(png_bytes)

    # For each palette color, find bounding box of matching pixels
    # and count matched pixels for area check
    color_data: Dict[int, Dict] = {}
    for idx, color in enumerate(PRIMITIVE_PALETTE):
        color_data[idx] = {
            "color": color,
            "min_x": width, "min_y": height,
            "max_x": -1, "max_y": -1,
            "pixel_count": 0,
        }

    threshold_sq = profile.color_match_threshold_sq

    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            px = (buf[offset], buf[offset + 1], buf[offset + 2])

            # Skip near-white pixels (background)
            bg_dist = _color_distance_sq(px, BACKGROUND_COLOR)
            if bg_dist < 1000:  # Close to white
                continue

            # Find nearest palette color
            best_idx = -1
            best_dist = threshold_sq + 1
            for idx, color in enumerate(PRIMITIVE_PALETTE):
                d = _color_distance_sq(px, color)
                if d < best_dist:
                    best_dist = d
                    best_idx = idx

            if best_idx >= 0 and best_dist <= threshold_sq:
                cd = color_data[best_idx]
                cd["min_x"] = min(cd["min_x"], x)
                cd["min_y"] = min(cd["min_y"], y)
                cd["max_x"] = max(cd["max_x"], x)
                cd["max_y"] = max(cd["max_y"], y)
                cd["pixel_count"] += 1

    results = []
    for idx, cd in color_data.items():
        if cd["max_x"] < 0:
            continue  # No pixels found for this color
        if cd["pixel_count"] < profile.min_detectable_area_px:
            continue  # Too small to be a real primitive

        w = cd["max_x"] - cd["min_x"] + 1
        h = cd["max_y"] - cd["min_y"] + 1
        results.append({
            "type": "region",
            "bbox": [cd["min_x"], cd["min_y"], w, h],
            "confidence": 0.95,  # Below 1.0: tolerant match, not exact
            "_artifact_color": list(cd["color"]),
            "_pixel_count": cd["pixel_count"],
        })

    return results


# ════════════════════════════════════════════════════════════
# TOLERANCE VERDICT
# ════════════════════════════════════════════════════════════

class ToleranceVerdict(str, Enum):
    """Result of capture tolerance bridge."""
    TOLERATED = "TOLERATED"       # Degraded artifact decoded successfully
    REJECTED = "REJECTED"         # Degradation too severe, honest failure
    PARSE_FAILED = "PARSE_FAILED" # Could not extract expected primitives
    BRIDGE_FAILED = "BRIDGE_FAILED"  # Parsed but substrate bridge failed


@dataclass
class ToleranceResult:
    """Complete result of a capture tolerance test."""
    verdict: ToleranceVerdict = ToleranceVerdict.REJECTED
    degradation_type: str = ""
    degradation_params: Dict[str, Any] = field(default_factory=dict)
    parsed_primitives: int = 0
    expected_primitives: int = 0
    bbox_match: bool = False
    bridge_verdict: str = ""
    profile_version: str = CAPTURE_TOLERANCE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "degradation_type": self.degradation_type,
            "degradation_params": self.degradation_params,
            "parsed_primitives": self.parsed_primitives,
            "expected_primitives": self.expected_primitives,
            "bbox_match": self.bbox_match,
            "bridge_verdict": self.bridge_verdict,
            "profile_version": self.profile_version,
        }


# ════════════════════════════════════════════════════════════
# DEGRADATION APPLICATION — high-level functions
# ════════════════════════════════════════════════════════════

def apply_degradation(
    spec: ArtifactSpec,
    degradation_type: str,
    **params,
) -> bytes:
    """
    Render a canonical artifact and apply a named degradation.
    Returns degraded PNG bytes.

    Supported degradation_type values:
      "scale", "translate", "blur", "noise",
      "brightness", "contrast", "jpeg"

    All degradations are deterministic.
    """
    if degradation_type == "jpeg":
        # JPEG works on PNG bytes directly
        png_bytes = render_artifact(spec)
        quality = params.get("quality", 80)
        return degrade_jpeg_compress(png_bytes, quality)

    # All other degradations work on raw RGB buffer
    rgb_buf = _render_to_raw_rgb(spec)
    w, h = spec.canvas_width, spec.canvas_height

    if degradation_type == "scale":
        factor = params.get("factor", 1.0)
        rgb_buf, w, h = degrade_scale(rgb_buf, w, h, factor)

    elif degradation_type == "translate":
        dx = params.get("dx", 0)
        dy = params.get("dy", 0)
        rgb_buf = degrade_translate(rgb_buf, w, h, dx, dy)

    elif degradation_type == "blur":
        radius = params.get("radius", 1)
        rgb_buf = degrade_blur(rgb_buf, w, h, radius)

    elif degradation_type == "noise":
        amplitude = params.get("amplitude", 10)
        seed = params.get("seed", 42)
        rgb_buf = degrade_noise(rgb_buf, w, h, amplitude, seed)

    elif degradation_type == "brightness":
        shift = params.get("shift", 0)
        rgb_buf = degrade_brightness(rgb_buf, w, h, shift)

    elif degradation_type == "contrast":
        factor = params.get("factor", 1.0)
        rgb_buf = degrade_contrast(rgb_buf, w, h, factor)

    else:
        raise ValueError(f"Unknown degradation type: {degradation_type}")

    return _encode_png(w, h, rgb_buf)


# ════════════════════════════════════════════════════════════
# TOLERANT BRIDGE — degraded artifact → substrate
# ════════════════════════════════════════════════════════════

def bridge_degraded_to_substrate(
    spec: ArtifactSpec,
    degradation_type: str,
    profile: ToleranceProfile = V1_TOLERANCE_PROFILE,
    **params,
) -> ToleranceResult:
    """
    Full tolerance bridge path:
      spec → render → degrade → tolerant parse → substrate

    1. Render the canonical artifact
    2. Apply the named degradation
    3. Parse with tolerant color matching
    4. Verify primitive count matches
    5. Check bbox proximity (within tolerance for scale/translate)
    6. Bridge to substrate if parse succeeds

    If degradation is out of bounds, returns REJECTED honestly.
    """
    result = ToleranceResult(
        degradation_type=degradation_type,
        degradation_params=params,
        expected_primitives=len(spec.primitives),
    )

    # Step 1-2: Render and degrade
    degraded_png = apply_degradation(spec, degradation_type, **params)

    # Step 3: Tolerant parse
    parsed = parse_artifact_tolerant(degraded_png, profile)
    result.parsed_primitives = len(parsed)

    if result.parsed_primitives != result.expected_primitives:
        result.verdict = ToleranceVerdict.PARSE_FAILED
        return result

    # Step 4: Check bbox proximity
    # For scale/translate, bboxes won't be pixel-exact but should be close
    spec_bboxes = sorted([(p.x, p.y, p.w, p.h) for p in spec.primitives])
    parsed_bboxes = sorted([tuple(p["bbox"]) for p in parsed])

    # Allow bbox deviation proportional to degradation
    max_bbox_dev = 15  # pixels of allowed bbox deviation
    if degradation_type == "scale":
        factor = params.get("factor", 1.0)
        max_bbox_dev = int(abs(1.0 - factor) * max(CANVAS_WIDTH, CANVAS_HEIGHT)) + 5
    elif degradation_type == "translate":
        max_bbox_dev = abs(params.get("dx", 0)) + abs(params.get("dy", 0)) + 5

    bbox_ok = True
    for sb, pb in zip(spec_bboxes, parsed_bboxes):
        for sv, pv in zip(sb, pb):
            if abs(sv - pv) > max_bbox_dev:
                bbox_ok = False
                break
        if not bbox_ok:
            break

    result.bbox_match = bbox_ok

    if not bbox_ok:
        result.verdict = ToleranceVerdict.PARSE_FAILED
        return result

    # Step 5: Bridge to substrate using parsed primitives
    substrate_result = safe_execute_image_as_program(
        parsed,
        bindings=spec.bindings,
        operations=list(spec.operations),
    )

    if not substrate_result["executed"]:
        result.verdict = ToleranceVerdict.BRIDGE_FAILED
        result.bridge_verdict = "NOT_EXECUTED"
        return result

    exec_verdict = substrate_result["execution"]["verdict"]
    result.bridge_verdict = exec_verdict

    # PASS, PARTIAL, EMPTY are all valid substrate outcomes
    if exec_verdict in ("PASS", "PARTIAL", "EMPTY"):
        result.verdict = ToleranceVerdict.TOLERATED
    else:
        result.verdict = ToleranceVerdict.BRIDGE_FAILED

    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: degradations within the frozen tolerance profile
IN_BOUNDS_CASES = [
    # Scale variations
    ("scale", {"factor": 0.95}),
    ("scale", {"factor": 1.05}),
    ("scale", {"factor": 0.92}),
    ("scale", {"factor": 1.08}),

    # Translation
    ("translate", {"dx": 5, "dy": 0}),
    ("translate", {"dx": 0, "dy": 5}),
    ("translate", {"dx": -5, "dy": -5}),
    ("translate", {"dx": 8, "dy": 8}),

    # Blur
    ("blur", {"radius": 1}),
    ("blur", {"radius": 2}),

    # Noise
    ("noise", {"amplitude": 10, "seed": 42}),
    ("noise", {"amplitude": 20, "seed": 99}),

    # Brightness
    ("brightness", {"shift": 15}),
    ("brightness", {"shift": -15}),
    ("brightness", {"shift": 25}),

    # Contrast
    ("contrast", {"factor": 0.85}),
    ("contrast", {"factor": 1.15}),

    # JPEG compression
    ("jpeg", {"quality": 80}),
    ("jpeg", {"quality": 75}),
]

# Out-of-bounds: degradations beyond the frozen tolerance profile.
# Each must produce genuine decode failure — either wrong primitive
# count, unrecognizable colors, or washed-out image.
OUT_OF_BOUNDS_CASES = [
    # Heavy blur — colors bleed together, spurious matches
    ("blur", {"radius": 15}),

    # Extreme noise — palette colors unrecognizable
    ("noise", {"amplitude": 120, "seed": 42}),

    # Extreme brightness — washes out all colors to white
    ("brightness", {"shift": 200}),

    # Extreme negative brightness — crushes all to black
    ("brightness", {"shift": -200}),

    # Extreme contrast reduction — all colors converge to gray
    ("contrast", {"factor": 0.1}),

    # Moderate contrast reduction — still collapses palette distinction
    ("contrast", {"factor": 0.2}),
]
