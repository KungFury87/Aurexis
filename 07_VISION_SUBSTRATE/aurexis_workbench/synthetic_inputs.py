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
    """Smooth gradient sky over textured ground with a horizontal
    boundary at y = size/2. Should fire has_horizon_line_signature
    (horizontal mirror near the boundary + horizontal edge dominance)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    # Sky: smooth top-down gradient
    sky = 0.85 - 0.3 * (yy / size)
    # Ground: textured (random but smoother in y than x for horizontal-edge bias)
    ground_noise = rng.normal(0.0, 0.10, size=(size, size))
    # smooth in y direction to bias horizontal edges
    smoothed = ground_noise.copy()
    for k in range(3):
        smoothed[1:-1, :] = (smoothed[1:-1, :]
                              + smoothed[:-2, :]
                              + smoothed[2:, :]) / 3.0
    ground = 0.35 + smoothed * 1.5
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
    """Many random oriented strokes at high spatial frequency. Should
    fire has_high_edge_density."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    scene = np.full((size, size), 0.5)
    # 50 oriented sinusoidal strokes at random angles + frequencies
    for _ in range(50):
        angle = rng.uniform(0, np.pi)
        freq = rng.uniform(0.2, 0.5)
        amp = rng.uniform(0.05, 0.20)
        phase = rng.uniform(0, 2 * np.pi)
        scene = scene + amp * np.cos(2 * np.pi * freq
                                       * (xx * np.cos(angle) + yy * np.sin(angle))
                                       + phase)
    # add noise to break perfect periodicity
    scene = scene + rng.normal(0, 0.02, size=(size, size))
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
