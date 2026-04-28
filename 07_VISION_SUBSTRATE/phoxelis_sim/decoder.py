"""Phoxelis Encoding Simulation — decoder side (v0.2).

Same architecture as v0.1 — the decoder splits the image into a grid
matching the encoder's, wraps each cell as a typed FieldBundle, and
evaluates the bit-carrier predicate via the actual Phoxelis runtime.

v0.2 generalises grid dimensions and ROI cropping: the decoder takes
explicit grid_w / grid_h parameters so it can match whatever the
encoder produced, including non-square grids and non-default image
sizes.
"""
from __future__ import annotations

import numpy as np

from .encoder import DEFAULT_GRID_W, DEFAULT_GRID_H

BIT_CARRIER = "has_red_dominant"


def _bundle_from_cell(cell_rgb: np.ndarray, name: str):
    from aurexis_workbench.fields import FieldBundle
    arr = cell_rgb.astype(np.float64) / 255.0
    color = arr[..., :3]
    luma = 0.299 * color[..., 0] + 0.587 * color[..., 1] + 0.114 * color[..., 2]
    burst = luma[None, ...]
    b = FieldBundle(name=name)
    b.add_value("scene", "image", luma, description="luma")
    b.add_value("color_scene", "color_image", color, description="rgb")
    b.add_value("burst", "image_stack", burst, description="single-frame")
    b.add_value("patch_size", "int", max(8, min(luma.shape) // 4),
                  description="ROI side")
    b.add_value("row_y", "int", luma.shape[0] // 2, description="autocorr row")
    return b


_RUNTIME = None


def _runtime():
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    from aurexis_workbench import dsl, vision_ops, predicates as P, runtime as RT
    from pathlib import Path
    vision_ops.register_all()
    vocab_path = (Path(__file__).resolve().parent.parent / "data" / "vision"
                    / "vocab.aurex")
    text = vocab_path.read_text(encoding="utf-8")
    parsed = dsl.parse_source(text)
    rt = RT.Runtime()
    installed = []
    for pp in parsed:
        if not pp.ok:
            continue
        try:
            P.type_check(pp.pred)
            rt.install(pp.pred)
            installed.append(pp.pred.name)
        except Exception:
            continue
    if BIT_CARRIER not in installed:
        raise RuntimeError(f"bit carrier {BIT_CARRIER!r} not installed; "
                             f"vocab.aurex may be missing this predicate")
    _RUNTIME = rt
    return rt


def decode_bits(img: np.ndarray, *, grid_w: int = DEFAULT_GRID_W,
                  grid_h: int = DEFAULT_GRID_H) -> list[int]:
    """Reverse of encoder.encode_bits. Splits image into grid_w × grid_h
    cells and evaluates the bit-carrier predicate on each."""
    rt = _runtime()
    H, W = img.shape[:2]
    cell_h = H // grid_h
    cell_w = W // grid_w
    bits: list[int] = []
    for i in range(grid_w * grid_h):
        gy = i // grid_w
        gx = i %  grid_w
        cell = img[gy * cell_h:(gy + 1) * cell_h,
                     gx * cell_w:(gx + 1) * cell_w]
        bundle = _bundle_from_cell(cell, name=f"cell_{gy}_{gx}")
        rec = rt.evaluate(BIT_CARRIER, bundle)
        if rec.error:
            # On runtime error, treat as 0; future versions may treat as erasure
            bits.append(0)
            continue
        bits.append(1 if bool(rec.value) else 0)
    return bits


def decode_bytes(img: np.ndarray, **kwargs) -> bytes:
    grid_w = kwargs.get("grid_w", DEFAULT_GRID_W)
    grid_h = kwargs.get("grid_h", DEFAULT_GRID_H)
    n_cells = grid_w * grid_h
    bits = decode_bits(img, **kwargs)
    out = bytearray()
    for byte_idx in range(n_cells // 8):
        b = 0
        for i in range(8):
            b = (b << 1) | bits[byte_idx * 8 + i]
        out.append(b)
    return bytes(out)
