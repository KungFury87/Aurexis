"""Deterministic generators for the V2 B1 base static screen benchmark family.

Each public ``gen_*`` function returns a complete PNG file as bytes, rendered
at the requested resolution with no randomness, no environmental inputs, and
no external dependencies. Two invocations with the same arguments MUST
produce byte-identical output; this invariant is enforced by
``tests/test_v2_benchmark.py``.

Parameters are kept narrow on purpose. The V2-M2 lock freezes the set; any
parameter change requires a new set_version in ``V2_BENCHMARK_SET_MANIFEST.json``.
"""

from __future__ import annotations

from .png_writer import encode_rgb_png


# ---------------------------------------------------------------------------
# Helpers (local, deterministic, no hidden state).
# ---------------------------------------------------------------------------

def _solid(width: int, height: int, rgb_triplet: tuple[int, int, int]) -> bytes:
    r, g, b = rgb_triplet
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError("rgb values must be in 0..255")
    return bytes((r, g, b)) * (width * height)


# ---------------------------------------------------------------------------
# B1 family generators.
# ---------------------------------------------------------------------------

def gen_clean_solid(width: int, height: int, gray_level: int = 128) -> bytes:
    """``b1-clean-solid`` — solid neutral gray.

    Measurement target: clean-detection baseline / sensor noise floor.
    """
    if not (0 <= gray_level <= 255):
        raise ValueError("gray_level must be in 0..255")
    pixels = _solid(width, height, (gray_level, gray_level, gray_level))
    return encode_rgb_png(width, height, pixels)


def gen_edge_half(width: int, height: int) -> bytes:
    """``b1-edge-half`` — left half black, right half white.

    Measurement target: edge/boundary stability. Sharp vertical transition
    at x = width // 2.
    """
    mid = width // 2
    row = bytes((0, 0, 0)) * mid + bytes((255, 255, 255)) * (width - mid)
    pixels = row * height
    return encode_rgb_png(width, height, pixels)


def gen_grid_64(width: int, height: int, cell: int = 64) -> bytes:
    """``b1-grid-64`` — 64 px checkerboard starting with black at (0, 0).

    Measurement target: routing stability, moire / aliasing observation
    against the capture sensor grid.
    """
    if cell <= 0:
        raise ValueError("cell must be positive")
    black = bytes((0, 0, 0))
    white = bytes((255, 255, 255))
    out = bytearray(width * height * 3)
    stride = width * 3
    for y in range(height):
        row_parity = (y // cell) & 1
        row = bytearray(stride)
        for x in range(width):
            col_parity = (x // cell) & 1
            px = white if (row_parity ^ col_parity) else black
            row[x * 3 : x * 3 + 3] = px
        out[y * stride : (y + 1) * stride] = row
    return encode_rgb_png(width, height, bytes(out))


def gen_gradient_h(width: int, height: int) -> bytes:
    """``b1-gradient-h`` — horizontal linear luminance ramp 0 -> 255.

    Measurement target: gradient / signature stability under display
    non-linearities and sensor response.
    """
    if width < 2:
        raise ValueError("width must be >= 2 for a gradient")
    row = bytearray(width * 3)
    for x in range(width):
        level = (x * 255 + (width - 1) // 2) // (width - 1)  # rounded
        row[x * 3] = level
        row[x * 3 + 1] = level
        row[x * 3 + 2] = level
    pixels = bytes(row) * height
    return encode_rgb_png(width, height, pixels)


def gen_corners_fiducials(
    width: int,
    height: int,
    marker_size: int = 32,
    inset: int = 10,
) -> bytes:
    """``b1-corners-fiducials`` — black field with 4 white corner markers.

    Each marker is a ``marker_size`` x ``marker_size`` white square placed
    ``inset`` pixels from its nearest corner.

    Measurement target: angle / geometry baseline. Detecting the four
    markers and their centroids yields a perspective reference across
    captures.
    """
    if marker_size <= 0 or inset < 0:
        raise ValueError("marker_size must be > 0, inset must be >= 0")
    if marker_size + inset * 2 >= min(width, height):
        raise ValueError("markers would overlap or exceed the frame")

    black = bytes((0, 0, 0))
    white = bytes((255, 255, 255))
    stride = width * 3
    out = bytearray(black * width * height)

    marker_ranges = [
        # (y_start, y_end, x_start, x_end)
        (inset, inset + marker_size, inset, inset + marker_size),
        (inset, inset + marker_size, width - inset - marker_size, width - inset),
        (height - inset - marker_size, height - inset, inset, inset + marker_size),
        (
            height - inset - marker_size,
            height - inset,
            width - inset - marker_size,
            width - inset,
        ),
    ]
    for y0, y1, x0, x1 in marker_ranges:
        row_fill = white * (x1 - x0)
        for y in range(y0, y1):
            start = y * stride + x0 * 3
            end = y * stride + x1 * 3
            out[start:end] = row_fill
    return encode_rgb_png(width, height, bytes(out))


# ---------------------------------------------------------------------------
# Registry — frozen list of B1 artifacts. Order is part of the lock.
# ---------------------------------------------------------------------------

B1_ARTIFACTS = (
    {
        "artifact_id": "b1-clean-solid",
        "family": "B1-base-static-screen",
        "generator": "gen_clean_solid",
        "params": {"gray_level": 128},
        "measurement_target": "clean-detection baseline / sensor noise floor",
        "mandatory": True,
        "notes": "Solid mid-gray fill. Captures the noise floor and the AWB "
                 "baseline before any spatial features are involved.",
    },
    {
        "artifact_id": "b1-edge-half",
        "family": "B1-base-static-screen",
        "generator": "gen_edge_half",
        "params": {},
        "measurement_target": "edge / boundary stability",
        "mandatory": True,
        "notes": "Sharp vertical edge at x = width // 2. Exercises "
                 "edge detectors against a single high-contrast transition.",
    },
    {
        "artifact_id": "b1-grid-64",
        "family": "B1-base-static-screen",
        "generator": "gen_grid_64",
        "params": {"cell": 64},
        "measurement_target": "routing stability / moire observation",
        "mandatory": True,
        "notes": "64 px checkerboard. Reveals moire and aliasing between "
                 "the panel pixel grid and the phone sensor grid.",
    },
    {
        "artifact_id": "b1-gradient-h",
        "family": "B1-base-static-screen",
        "generator": "gen_gradient_h",
        "params": {},
        "measurement_target": "gradient / signature stability",
        "mandatory": True,
        "notes": "Horizontal luminance ramp 0 -> 255. Surfaces display and "
                 "sensor non-linearities and banding.",
    },
    {
        "artifact_id": "b1-corners-fiducials",
        "family": "B1-base-static-screen",
        "generator": "gen_corners_fiducials",
        "params": {"marker_size": 32, "inset": 10},
        "measurement_target": "angle / geometry baseline",
        "mandatory": True,
        "notes": "Four white corner markers on a black field. Marker "
                 "centroids give a perspective / keystone reference.",
    },
)


def render_artifact(entry: dict, width: int, height: int) -> bytes:
    """Render a registry entry to PNG bytes using the named generator."""
    fn_name = entry["generator"]
    fn = globals()[fn_name]
    return fn(width=width, height=height, **entry["params"])
