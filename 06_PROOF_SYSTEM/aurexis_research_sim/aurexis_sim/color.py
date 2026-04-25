"""RGB / color helpers and RGB-aware truth patterns.

Internal image convention:
    - grayscale:  float32 HxW in [0,1]
    - RGB:        float32 HxWx3 in [0,1]  (R,G,B order)

Everything here stays on that contract. No claims about color spaces
beyond 'linear-ish normalized RGB in [0,1]'.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


# --- shape helpers --------------------------------------------------------

def is_rgb(img: np.ndarray) -> bool:
    return img.ndim == 3 and img.shape[2] == 3


def promote_to_rgb(img: np.ndarray) -> np.ndarray:
    """grayscale HxW -> HxWx3 by channel replication. RGB passthrough."""
    if is_rgb(img):
        return img.astype(np.float32)
    if img.ndim == 2:
        return np.repeat(img[:, :, None], 3, axis=2).astype(np.float32)
    if img.ndim == 3 and img.shape[2] == 1:
        return np.repeat(img, 3, axis=2).astype(np.float32)
    raise ValueError(f"Unsupported shape {img.shape}")


def luma(img: np.ndarray) -> np.ndarray:
    """Rec.709 luma. RGB -> HxW. Grayscale passthrough."""
    if not is_rgb(img):
        return img.astype(np.float32)
    a = img.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


# --- RGB truth patterns ---------------------------------------------------

def rgb_blocks(size: int = 256, n: int = 8, seed: int = 0) -> dict:
    """Grid of blocks with random RGB colors. Label map = block ID.

    Useful for testing whether distinguishable color regions survive
    the Bayer sampling + demosaic pipeline.
    """
    rng = np.random.default_rng(seed)
    side = size // n
    img = np.zeros((size, size, 3), dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    colors = rng.uniform(0.1, 0.95, size=(n, n, 3)).astype(np.float32)
    k = 0
    for i in range(n):
        for j in range(n):
            y0, y1 = i * side, (i + 1) * side
            x0, x1 = j * side, (j + 1) * side
            img[y0:y1, x0:x1, :] = colors[i, j]
            lab[y0:y1, x0:x1] = k
            k += 1
    return {
        "image": img,
        "labels": lab,
        "meta": {"kind": "rgb_blocks", "size": size, "n": n, "seed": seed},
    }


def color_relation_probe(size: int = 256, seed: int = 0) -> dict:
    """Four small colored markers at known spatial relations.

    Each marker carries a distinct chromatic identity (approximately
    primary R/G/B and cyan) so adjacency + chroma can be tested through
    Bayer sampling. Labels 1..4 per marker, 0 background.
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size, 3), 0.2, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(4, size // 30)
    markers = [
        (int(size * 0.25), int(size * 0.5), 1, np.array([0.95, 0.1, 0.1])),   # R
        (int(size * 0.45), int(size * 0.5), 2, np.array([0.1, 0.95, 0.1])),   # G
        (int(size * 0.75), int(size * 0.3), 3, np.array([0.1, 0.1, 0.95])),   # B
        (int(size * 0.75), int(size * 0.7), 4, np.array([0.1, 0.85, 0.9])),   # C
    ]
    yy, xx = np.mgrid[0:size, 0:size]
    for (cx, cy, idx, rgb) in markers:
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = rgb.astype(np.float32)
        lab[m] = idx
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {"kind": "color_relation_probe", "size": size, "seed": seed},
    }


def color_bars(size: int = 256) -> dict:
    """Classic vertical color bars. Tests chroma survival + edge alignment."""
    bars = np.array([
        [1.0, 1.0, 1.0],   # white
        [1.0, 1.0, 0.0],   # yellow
        [0.0, 1.0, 1.0],   # cyan
        [0.0, 1.0, 0.0],   # green
        [1.0, 0.0, 1.0],   # magenta
        [1.0, 0.0, 0.0],   # red
        [0.0, 0.0, 1.0],   # blue
        [0.0, 0.0, 0.0],   # black
    ], dtype=np.float32)
    img = np.zeros((size, size, 3), dtype=np.float32)
    w = size // len(bars)
    for i, c in enumerate(bars):
        img[:, i * w:(i + 1) * w, :] = c
    return {
        "image": img,
        "labels": None,
        "meta": {"kind": "color_bars", "size": size},
    }
