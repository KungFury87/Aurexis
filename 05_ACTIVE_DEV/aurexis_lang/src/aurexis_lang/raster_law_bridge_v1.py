"""
Aurexis Core — Raster Law Bridge V1 (FROZEN)

First narrow deterministic bridge from an actual raster image artifact
into the existing V1 substrate. Synthetic canonical artifacts only.

What this proves:
  A canonical raster image artifact can be defined, rendered, parsed
  back into V1 primitives, and passed through the existing substrate
  with deterministic results.

What this does NOT prove:
  - Full camera capture robustness
  - Full print/scan round-trip from real-world conditions
  - General-purpose CV or OCR
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Fixed canvas: 400x400 pixels, white background, RGB
  - Primitives encoded as filled rectangles with known colors
  - REGION = solid colored rectangle (any hue)
  - Color convention: each primitive gets a distinct color from a
    frozen palette so the parser can identify them deterministically
  - The artifact IS the program: spatial arrangement of colored
    rectangles on a white canvas → V1 primitives → substrate

Artifact format:
  An ArtifactSpec defines primitives as (color, x, y, w, h) tuples.
  render_artifact() produces a PIL Image from the spec.
  parse_artifact() reads a PIL Image and extracts primitives by color.
  bridge_to_substrate() runs parse → substrate end-to-end.

The renderer and parser are exact inverses for canonical artifacts:
  parse_artifact(render_artifact(spec)) == spec.primitives (up to order)

This is a synthetic-only bridge. Real-world artifacts with noise,
compression, or non-exact colors are explicitly out of scope for V1.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import struct
import zlib

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, BoundingBox, VisualPrimitive,
)
from aurexis_lang.type_system_v1 import safe_execute_image_as_program


# ════════════════════════════════════════════════════════════
# BRIDGE VERSION
# ════════════════════════════════════════════════════════════

BRIDGE_VERSION = "V1.0"
BRIDGE_FROZEN = True


# ════════════════════════════════════════════════════════════
# CANVAS CONSTANTS
# ════════════════════════════════════════════════════════════

CANVAS_WIDTH = 400
CANVAS_HEIGHT = 400
BACKGROUND_COLOR = (255, 255, 255)  # White

# Frozen color palette for primitives.
# Each primitive in an artifact gets a color from this palette.
# Colors are chosen to be maximally distinguishable and far from white.
PRIMITIVE_PALETTE = [
    (255, 0, 0),       # Red
    (0, 0, 255),       # Blue
    (0, 180, 0),       # Green
    (255, 165, 0),     # Orange
    (128, 0, 128),     # Purple
    (0, 128, 128),     # Teal
    (180, 0, 0),       # Dark Red
    (0, 0, 180),       # Dark Blue
    (100, 100, 0),     # Olive
    (180, 0, 180),     # Magenta
]

MAX_PRIMITIVES_IN_ARTIFACT = len(PRIMITIVE_PALETTE)


# ════════════════════════════════════════════════════════════
# ARTIFACT PRIMITIVE — one shape in the artifact
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ArtifactPrimitive:
    """One rectangle in a canonical artifact."""
    color: Tuple[int, int, int]
    x: int
    y: int
    w: int
    h: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "color": list(self.color),
            "x": self.x, "y": self.y,
            "w": self.w, "h": self.h,
        }


# ════════════════════════════════════════════════════════════
# ARTIFACT SPEC — defines a complete artifact
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ArtifactSpec:
    """
    Defines a canonical raster artifact.

    primitives: list of ArtifactPrimitive (max 10, one per palette color)
    operations: list of operations to evaluate (same format as substrate)
    bindings: optional name→index mapping
    """
    primitives: Tuple[ArtifactPrimitive, ...]
    operations: Tuple[Dict[str, Any], ...] = ()
    bindings: Optional[Dict[str, int]] = None
    canvas_width: int = CANVAS_WIDTH
    canvas_height: int = CANVAS_HEIGHT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primitives": [p.to_dict() for p in self.primitives],
            "operations": list(self.operations),
            "bindings": self.bindings,
            "canvas_size": [self.canvas_width, self.canvas_height],
            "bridge_version": BRIDGE_VERSION,
        }


# ════════════════════════════════════════════════════════════
# MINIMAL PNG RENDERER — no Pillow dependency
# ════════════════════════════════════════════════════════════

def _render_to_raw_rgb(spec: ArtifactSpec) -> bytearray:
    """Render artifact to raw RGB pixel buffer (row-major)."""
    w, h = spec.canvas_width, spec.canvas_height
    # Initialize white canvas
    buf = bytearray(BACKGROUND_COLOR * w * h)

    for prim in spec.primitives:
        # Draw filled rectangle
        x0 = max(0, prim.x)
        y0 = max(0, prim.y)
        x1 = min(w, prim.x + prim.w)
        y1 = min(h, prim.y + prim.h)
        r, g, b = prim.color
        for row in range(y0, y1):
            offset = (row * w + x0) * 3
            for col in range(x0, x1):
                buf[offset] = r
                buf[offset + 1] = g
                buf[offset + 2] = b
                offset += 3

    return buf


def _encode_png(width: int, height: int, rgb_buf: bytearray) -> bytes:
    """Encode raw RGB buffer as a minimal PNG file."""
    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = _make_chunk(b'IHDR', ihdr_data)

    # IDAT chunk — raw pixel data with filter bytes
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)  # No filter
        offset = y * width * 3
        raw_rows.extend(rgb_buf[offset:offset + width * 3])
    compressed = zlib.compress(bytes(raw_rows), 9)
    idat = _make_chunk(b'IDAT', compressed)

    # IEND chunk
    iend = _make_chunk(b'IEND', b'')

    return sig + ihdr + idat + iend


def _make_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Build a PNG chunk: length + type + data + CRC."""
    length = struct.pack('>I', len(data))
    crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
    return length + chunk_type + data + crc


# ════════════════════════════════════════════════════════════
# RENDER ARTIFACT
# ════════════════════════════════════════════════════════════

def render_artifact(spec: ArtifactSpec) -> bytes:
    """
    Render a canonical artifact spec to a PNG image (as bytes).

    Returns raw PNG bytes. No Pillow dependency.
    Deterministic: same spec → identical bytes.
    """
    rgb_buf = _render_to_raw_rgb(spec)
    return _encode_png(spec.canvas_width, spec.canvas_height, rgb_buf)


def render_artifact_to_file(spec: ArtifactSpec, path: str) -> str:
    """Render and save to file. Returns the path."""
    data = render_artifact(spec)
    with open(path, 'wb') as f:
        f.write(data)
    return path


# ════════════════════════════════════════════════════════════
# PARSE ARTIFACT — extract primitives from image bytes
# ════════════════════════════════════════════════════════════

def _decode_png_to_rgb(png_bytes: bytes) -> Tuple[int, int, bytearray]:
    """Decode a PNG file to (width, height, rgb_buffer). Minimal decoder."""
    # Use Pillow if available, fall back to manual decode
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes)).convert('RGB')
        w, h = img.size
        buf = bytearray()
        for y in range(h):
            for x in range(w):
                r, g, b = img.getpixel((x, y))
                buf.extend([r, g, b])
        return w, h, buf
    except ImportError:
        pass

    # Manual PNG decode (handles our simple PNGs)
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n', "Not a PNG"
    pos = 8
    width = height = 0
    idat_chunks = []

    while pos < len(png_bytes):
        length = struct.unpack('>I', png_bytes[pos:pos+4])[0]
        chunk_type = png_bytes[pos+4:pos+8]
        data = png_bytes[pos+8:pos+8+length]
        pos += 12 + length  # 4 len + 4 type + data + 4 crc

        if chunk_type == b'IHDR':
            width, height = struct.unpack('>II', data[:8])
        elif chunk_type == b'IDAT':
            idat_chunks.append(data)
        elif chunk_type == b'IEND':
            break

    raw = zlib.decompress(b''.join(idat_chunks))
    buf = bytearray()
    stride = width * 3 + 1  # +1 for filter byte
    for y in range(height):
        row_start = y * stride + 1  # skip filter byte
        buf.extend(raw[row_start:row_start + width * 3])

    return width, height, buf


def _color_distance_sq(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> int:
    """Squared Euclidean distance in RGB space."""
    return (c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2


def parse_artifact(png_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse a canonical artifact PNG back into primitive dicts.

    For each palette color, finds the bounding box of all pixels
    matching that color (exact match for synthetic artifacts).

    Returns a list of dicts compatible with the V1 substrate input
    format: [{"type": "region", "bbox": [x, y, w, h], "confidence": 1.0}, ...]

    Confidence is always 1.0 because these are synthetic artifacts
    with exact pixel colors — no heuristic extraction involved.
    """
    width, height, buf = _decode_png_to_rgb(png_bytes)

    # For each palette color, find bounding box
    results = []
    for color in PRIMITIVE_PALETTE:
        min_x, min_y = width, height
        max_x, max_y = -1, -1

        for y in range(height):
            for x in range(width):
                offset = (y * width + x) * 3
                px = (buf[offset], buf[offset+1], buf[offset+2])
                if px == color:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x >= 0:
            # Found pixels of this color
            w = max_x - min_x + 1
            h = max_y - min_y + 1
            results.append({
                "type": "region",
                "bbox": [min_x, min_y, w, h],
                "confidence": 1.0,
                "_artifact_color": list(color),
            })

    return results


# ════════════════════════════════════════════════════════════
# BRIDGE TO SUBSTRATE — end-to-end path
# ════════════════════════════════════════════════════════════

class BridgeVerdict(str, Enum):
    """Result of the raster law bridge."""
    BRIDGED = "BRIDGED"             # Artifact → substrate succeeded
    PARSE_FAILED = "PARSE_FAILED"   # Could not extract primitives
    TYPE_ERROR = "TYPE_ERROR"       # Parsed but ill-typed
    EXEC_FAILED = "EXEC_FAILED"    # Typed but execution failed
    INVALID_SPEC = "INVALID_SPEC"  # Artifact spec is invalid


@dataclass
class BridgeResult:
    """Complete result of bridging an artifact to the substrate."""
    verdict: BridgeVerdict = BridgeVerdict.INVALID_SPEC
    spec: Optional[ArtifactSpec] = None
    parsed_primitives: int = 0
    expected_primitives: int = 0
    type_check_verdict: str = ""
    execution_verdict: str = ""
    parse_roundtrip_exact: bool = False
    substrate_result: Optional[Dict[str, Any]] = None
    bridge_version: str = BRIDGE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "parsed_primitives": self.parsed_primitives,
            "expected_primitives": self.expected_primitives,
            "type_check_verdict": self.type_check_verdict,
            "execution_verdict": self.execution_verdict,
            "parse_roundtrip_exact": self.parse_roundtrip_exact,
            "bridge_version": self.bridge_version,
        }


def validate_spec(spec: ArtifactSpec) -> List[str]:
    """Validate an artifact spec. Returns list of errors (empty = valid)."""
    errors = []
    if len(spec.primitives) == 0:
        errors.append("No primitives in spec")
    if len(spec.primitives) > MAX_PRIMITIVES_IN_ARTIFACT:
        errors.append(f"Too many primitives: {len(spec.primitives)} > {MAX_PRIMITIVES_IN_ARTIFACT}")

    colors_used = set()
    for i, p in enumerate(spec.primitives):
        if p.color not in PRIMITIVE_PALETTE:
            errors.append(f"Primitive {i}: color {p.color} not in palette")
        if p.color in colors_used:
            errors.append(f"Primitive {i}: duplicate color {p.color}")
        colors_used.add(p.color)

        if p.w <= 0 or p.h <= 0:
            errors.append(f"Primitive {i}: invalid size {p.w}x{p.h}")
        if p.x < 0 or p.y < 0:
            errors.append(f"Primitive {i}: negative position ({p.x}, {p.y})")
        if p.x + p.w > spec.canvas_width or p.y + p.h > spec.canvas_height:
            errors.append(f"Primitive {i}: extends beyond canvas")

    return errors


def bridge_to_substrate(
    spec: ArtifactSpec,
) -> BridgeResult:
    """
    Full end-to-end bridge: artifact spec → render → parse → substrate.

    Steps:
    1. Validate the artifact spec
    2. Render to PNG bytes
    3. Parse PNG back to primitive dicts
    4. Verify parse roundtrip (count and bbox match)
    5. Pass through substrate (type-check + execute)
    6. Return BridgeResult

    This is the proof that an image artifact can carry a V1 law-bearing
    program into the substrate deterministically.
    """
    result = BridgeResult(spec=spec)
    result.expected_primitives = len(spec.primitives)

    # Step 1: Validate
    validation_errors = validate_spec(spec)
    if validation_errors:
        result.verdict = BridgeVerdict.INVALID_SPEC
        return result

    # Step 2: Render
    png_bytes = render_artifact(spec)

    # Step 3: Parse
    parsed = parse_artifact(png_bytes)
    result.parsed_primitives = len(parsed)

    if result.parsed_primitives != result.expected_primitives:
        result.verdict = BridgeVerdict.PARSE_FAILED
        return result

    # Step 4: Verify roundtrip
    # Check that each spec primitive's bbox matches a parsed primitive
    spec_bboxes = sorted(
        [(p.x, p.y, p.w, p.h) for p in spec.primitives]
    )
    parsed_bboxes = sorted(
        [tuple(p["bbox"]) for p in parsed]
    )
    result.parse_roundtrip_exact = (spec_bboxes == parsed_bboxes)

    if not result.parse_roundtrip_exact:
        result.verdict = BridgeVerdict.PARSE_FAILED
        return result

    # Step 5: Substrate execution
    substrate_input = safe_execute_image_as_program(
        parsed,
        bindings=spec.bindings,
        operations=list(spec.operations),
    )

    result.substrate_result = substrate_input
    result.type_check_verdict = (
        "WELL_TYPED" if substrate_input["type_check"]["is_well_typed"]
        else "ILL_TYPED"
    )

    if not substrate_input["executed"]:
        result.verdict = BridgeVerdict.TYPE_ERROR
        return result

    result.execution_verdict = substrate_input["execution"]["verdict"]

    # EMPTY is valid for binding-only programs (no assertions to evaluate)
    if result.execution_verdict in ("PASS", "PARTIAL", "EMPTY"):
        result.verdict = BridgeVerdict.BRIDGED
    else:
        result.verdict = BridgeVerdict.EXEC_FAILED

    return result


# ════════════════════════════════════════════════════════════
# CANONICAL FIXTURES
# ════════════════════════════════════════════════════════════

def fixture_adjacent_pair() -> ArtifactSpec:
    """Two REGIONs side by side — should be ADJACENT under V1 law."""
    return ArtifactSpec(
        primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 50, 150, 100, 100),
            ArtifactPrimitive(PRIMITIVE_PALETTE[1], 150, 150, 100, 100),
        ),
        operations=(
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
        ),
        bindings={"left": 0, "right": 1},
    )


def fixture_containment() -> ArtifactSpec:
    """Large REGION containing a smaller one."""
    return ArtifactSpec(
        primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 50, 50, 300, 300),
            ArtifactPrimitive(PRIMITIVE_PALETTE[1], 100, 100, 100, 100),
        ),
        operations=(
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1},
        ),
        bindings={"outer": 0, "inner": 1},
    )


def fixture_three_regions() -> ArtifactSpec:
    """Three REGIONs in a row — tests multiple primitives and relations."""
    return ArtifactSpec(
        primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 20, 150, 80, 80),
            ArtifactPrimitive(PRIMITIVE_PALETTE[1], 100, 150, 80, 80),
            ArtifactPrimitive(PRIMITIVE_PALETTE[2], 180, 150, 80, 80),
        ),
        operations=(
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
            {"op": OperationKind.ADJACENT, "a_index": 1, "b_index": 2},
        ),
        bindings={"left": 0, "center": 1, "right": 2},
    )


def fixture_single_region() -> ArtifactSpec:
    """One REGION with a binding — minimal valid artifact."""
    return ArtifactSpec(
        primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 100, 100, 200, 200),
        ),
        bindings={"sole": 0},
    )


def fixture_non_adjacent() -> ArtifactSpec:
    """Two REGIONs far apart — ADJACENT should be FALSE."""
    return ArtifactSpec(
        primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 10, 10, 50, 50),
            ArtifactPrimitive(PRIMITIVE_PALETTE[1], 300, 300, 50, 50),
        ),
        operations=(
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
        ),
        bindings={"a": 0, "b": 1},
    )


ALL_FIXTURES = {
    "adjacent_pair": fixture_adjacent_pair,
    "containment": fixture_containment,
    "three_regions": fixture_three_regions,
    "single_region": fixture_single_region,
    "non_adjacent": fixture_non_adjacent,
}
