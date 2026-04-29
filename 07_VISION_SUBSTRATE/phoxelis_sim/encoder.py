"""Phoxelis Encoding Simulation — encoder side (v0.2).

v0.1 was a 4×4 grid of pure-red / pure-green 64×64 cells. v0.2 keeps
the same architecture but generalises:

  * grid_w × grid_h is configurable (default 8×8 = 64 bits)
  * cell pixel size is computed from total image size
  * `saturation` parameter blends the cell color toward neutral gray,
    pushing the predicate's decision closer to its threshold

At saturation=1.0, cells are the v0.1 colors (saturated red / saturated
green) and the decoder sees a huge margin. At saturation=0.0, every
cell is mid-gray, the predicate cannot distinguish 0 from 1, and BER
should pin at 0.5. The curve between those endpoints is what v0.2
measures.
"""
from __future__ import annotations

import numpy as np

DEFAULT_GRID_W = 8
DEFAULT_GRID_H = 8
DEFAULT_IMG_SIZE = 256

# v0.1 saturated endpoints (kept for reference / saturation=1.0 case)
COLOR_RED   = np.array([200,  50,  50], dtype=np.float64)
COLOR_GREEN = np.array([ 50, 200,  50], dtype=np.float64)
COLOR_GRAY  = np.array([128, 128, 128], dtype=np.float64)


def cell_color(bit: int, saturation: float) -> np.ndarray:
    """Linear blend between gray (saturation=0) and the v0.1 endpoints.

    saturation=1.0 -> [200,50,50] for bit=1, [50,200,50] for bit=0
    saturation=0.0 -> mid-gray for both
    saturation=0.5 -> halfway
    """
    saturation = max(0.0, min(1.0, float(saturation)))
    target = COLOR_RED if bit == 1 else COLOR_GREEN
    out = COLOR_GRAY + saturation * (target - COLOR_GRAY)
    return np.clip(out, 0, 255).astype(np.uint8)


def encode_bits(bits, *, grid_w: int = DEFAULT_GRID_W,
                grid_h: int = DEFAULT_GRID_H,
                img_size: int = DEFAULT_IMG_SIZE,
                saturation: float = 1.0) -> np.ndarray:
    """Encode grid_w*grid_h bits into a square uint8 RGB image."""
    n_cells = grid_w * grid_h
    if len(bits) != n_cells:
        raise ValueError(f"need {n_cells} bits, got {len(bits)}")
    cell_h = img_size // grid_h
    cell_w = img_size // grid_w
    H = cell_h * grid_h
    W = cell_w * grid_w
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for i, bit in enumerate(bits):
        if bit not in (0, 1):
            raise ValueError(f"bit {i} must be 0 or 1, got {bit!r}")
        gy = i // grid_w
        gx = i %  grid_w
        y0 = gy * cell_h
        x0 = gx * cell_w
        img[y0:y0 + cell_h, x0:x0 + cell_w] = cell_color(bit, saturation)
    return img


def encode_bytes(payload: bytes, **kwargs) -> np.ndarray:
    grid_w = kwargs.get("grid_w", DEFAULT_GRID_W)
    grid_h = kwargs.get("grid_h", DEFAULT_GRID_H)
    n_cells = grid_w * grid_h
    max_bytes = n_cells // 8
    if len(payload) > max_bytes:
        raise ValueError(f"payload exceeds {max_bytes} bytes (got {len(payload)})")
    bits = []
    for byte in payload:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    while len(bits) < n_cells:
        bits.append(0)
    return encode_bits(bits, **kwargs)


# Backwards-compat aliases for v0.1 callers
CELL_PX = DEFAULT_IMG_SIZE // DEFAULT_GRID_W
GRID_W  = DEFAULT_GRID_W
GRID_H  = DEFAULT_GRID_H
N_CELLS = DEFAULT_GRID_W * DEFAULT_GRID_H
COLOR_FOR_BIT = {0: tuple(COLOR_GREEN.astype(int)),
                   1: tuple(COLOR_RED.astype(int))}
