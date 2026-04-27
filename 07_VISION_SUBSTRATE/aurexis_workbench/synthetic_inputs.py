"""Synthetic corpus pumps for IR vocabulary auditing.

Each generator produces a scene whose ground truth is designed to
trigger one of the always-False predicates the IR identified in
Round 6. The point is not realism - it is targeted exercise of
specific predicates.

Saved to data/vision/synthetic/ as PNGs so the same cli_visual
runner can evaluate them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image


def horizon_scene(size: int = 512, seed: int = 0) -> np.ndarray:
    """Smooth sky over horizontally-banded ground with a strong
    horizontal boundary. Should fire has_horizontal_dominant_edges,
    has_mirror_symmetry_horizontal_axis, has_horizon_line_signature.

    Design: ALL gradients should be in y-direction (horizontal edges).
    No x-direction gradient. Sky is gradient top-to-bottom (gy only).
    Ground is parallel horizontal bands (gy only). Horizon line at
    y=size/2 is a sharp transition (gy only)."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    # Sky: smooth top-down gradient (only gy)
    sky = 0.90 - 0.25 * (yy / size)
    # Ground: parallel horizontal bands at fine pitch (only gy)
    ground = 0.30 + 0.15 * np.cos(2 * np.pi * 0.04 * yy)
    scene = np.where(yy < size / 2, sky, ground)
    return np.clip(scene, 0.0, 1.0)


def uniform_field(size: int = 512, intensity: float = 0.5,
                    noise_sigma: float = 0.005, seed: int = 0) -> np.ndarray:
    """Near-flat field with tiny sensor-noise-level jitter. Should
    fire is_uniform_field and has_low_edge_density."""
    rng = np.random.default_rng(seed)
    return np.clip(intensity + rng.normal(0.0, noise_sigma, size=(size, size)),
                    0.0, 1.0)


def vertically_symmetric_scene(size: int = 512, seed: int = 0) -> np.ndarray:
    """Random texture mirrored about the vertical axis (left = right
    flipped). Should fire has_mirror_symmetry_vertical_axis."""
    rng = np.random.default_rng(seed)
    half = rng.normal(0.5, 0.15, size=(size, size // 2))
    scene = np.zeros((size, size))
    scene[:, :size // 2] = half
    scene[:, size // 2:] = half[:, ::-1]
    return np.clip(scene, 0.0, 1.0)


def high_edge_density_scene(size: int = 512, seed: int = 0) -> np.ndarray:
    """High edge density: pseudo-halftone of fine binary cells. Each
    2-pixel cell is randomly black or white, creating an edge between
    nearly every pair of cells. Gradient magnitude is bimodal (~0
    inside cells, very high at cell boundaries), and roughly half of
    all pixels are at boundaries, which trips has_high_edge_density
    (fraction > 0.20)."""
    rng = np.random.default_rng(seed)
    cell = 2
    cells_y = size // cell
    cells_x = size // cell
    grid = rng.integers(0, 2, size=(cells_y, cells_x)).astype(np.float64)
    # Upsample by replication
    scene = np.repeat(np.repeat(grid, cell, axis=0), cell, axis=1)
    # Pad/crop to exact size
    scene = scene[:size, :size]
    return np.clip(scene, 0.0, 1.0)


def low_edge_density_scene(size: int = 512, seed: int = 0) -> np.ndarray:
    """Heavily smoothed image - low gradient magnitude everywhere.
    Should fire has_low_edge_density and has_low complexity."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.5, 0.15, size=(size, size))
    # heavy box blur (~15 iterations)
    smoothed = base.copy()
    for _ in range(15):
        s = smoothed.copy()
        smoothed[1:-1, 1:-1] = (s[1:-1, 1:-1] + s[:-2, 1:-1] + s[2:, 1:-1]
                                  + s[1:-1, :-2] + s[1:-1, 2:]) / 5.0
    return np.clip(smoothed, 0.0, 1.0)


def vertical_edge_dominant_scene(size: int = 512, seed: int = 0) -> np.ndarray:
    """Strong vertical edges only - should fire has_vertical_dominant_edges
    without firing the horizontal counterpart."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    # vertical bars at fine pitch
    scene = 0.5 + 0.3 * np.cos(2 * np.pi * 0.05 * xx)
    scene = scene + rng.normal(0, 0.03, size=(size, size))
    return np.clip(scene, 0.0, 1.0)


GENERATORS: Dict[str, callable] = {
    "horizon_scene":               horizon_scene,
    "uniform_field":               uniform_field,
    "vertically_symmetric_scene":  vertically_symmetric_scene,
    "high_edge_density_scene":     high_edge_density_scene,
    "low_edge_density_scene":      low_edge_density_scene,
    "vertical_edge_dominant":      vertical_edge_dominant_scene,
}


def write_all(out_dir: str | Path) -> None:
    """Generate all scenes and save as PNGs to out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="L").save(out / f"{name}.png")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "data/vision/synthetic"
    write_all(out)
    print(f"wrote {len(GENERATORS)} synthetic scenes to {out}")


# ---------- Color-targeted synthetic scenes (v0.5) ----------
# Saved as .png so they go through normal visual_intake (with color).

def red_dominant_scene(size: int = 256, seed: int = 0) -> np.ndarray:
    """High-saturation red-dominant scene. R channel ~0.8, G~0.2, B~0.2."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    base_r = 0.80 + rng.normal(0, 0.05, size=(size, size))
    base_g = 0.20 + rng.normal(0, 0.05, size=(size, size))
    base_b = 0.20 + rng.normal(0, 0.05, size=(size, size))
    rgb = np.stack([base_r, base_g, base_b], axis=-1)
    return np.clip(rgb, 0.0, 1.0)


def cool_palette_scene(size: int = 256, seed: int = 0) -> np.ndarray:
    """Blue/cyan dominant scene like sky or ocean."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    base_r = 0.20 + rng.normal(0, 0.04, size=(size, size))
    base_g = 0.45 + 0.10 * (yy / size) + rng.normal(0, 0.04, size=(size, size))
    base_b = 0.75 + rng.normal(0, 0.05, size=(size, size))
    rgb = np.stack([base_r, base_g, base_b], axis=-1)
    return np.clip(rgb, 0.0, 1.0)


def monochrome_color_scene(size: int = 256, seed: int = 0) -> np.ndarray:
    """Pure greyscale - R = G = B at every pixel."""
    rng = np.random.default_rng(seed)
    base = 0.5 + rng.normal(0, 0.15, size=(size, size))
    base = np.clip(base, 0.0, 1.0)
    rgb = np.stack([base, base, base], axis=-1)
    return rgb


def high_diversity_color_scene(size: int = 256, seed: int = 0) -> np.ndarray:
    """Many random colored patches - high palette diversity."""
    rng = np.random.default_rng(seed)
    rgb = np.zeros((size, size, 3))
    cell = 16
    for cy in range(0, size, cell):
        for cx in range(0, size, cell):
            color = rng.uniform(0.0, 1.0, size=3)
            rgb[cy:cy + cell, cx:cx + cell] = color
    return np.clip(rgb, 0.0, 1.0)


# Override write_all to handle the color scenes too (RGB save mode)
COLOR_GENERATORS = {
    "red_dominant_scene":          red_dominant_scene,
    "cool_palette_scene":          cool_palette_scene,
    "monochrome_color_scene":      monochrome_color_scene,
    "high_diversity_color_scene":  high_diversity_color_scene,
}


def write_color_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in COLOR_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="RGB").save(out / (name + ".png"))
