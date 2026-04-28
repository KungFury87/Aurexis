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


# ---------- Pure-hue synthetic scenes (v0.6) ----------
# Each scene is a uniform high-saturation patch at a known HSV hue
# angle. Used to verify the named-hue predicates classify correctly.

def _hsv_to_rgb(h_deg, s, v):
    """h in [0,360), s in [0,1], v in [0,1] -> (R,G,B) in [0,1]."""
    h = h_deg / 60.0
    c = v * s
    x = c * (1 - abs((h % 2) - 1))
    m = v - c
    if 0 <= h < 1:    r, g, b = c, x, 0
    elif 1 <= h < 2:  r, g, b = x, c, 0
    elif 2 <= h < 3:  r, g, b = 0, c, x
    elif 3 <= h < 4:  r, g, b = 0, x, c
    elif 4 <= h < 5:  r, g, b = x, 0, c
    else:             r, g, b = c, 0, x
    return r + m, g + m, b + m


def _pure_hue_scene(hue_deg, size=256, sat=0.85, val=0.85, seed=0):
    rng = np.random.default_rng(seed)
    r, g, b = _hsv_to_rgb(hue_deg, sat, val)
    rgb = np.zeros((size, size, 3))
    rgb[..., 0] = r + rng.normal(0, 0.02, size=(size, size))
    rgb[..., 1] = g + rng.normal(0, 0.02, size=(size, size))
    rgb[..., 2] = b + rng.normal(0, 0.02, size=(size, size))
    return np.clip(rgb, 0.0, 1.0)


def pure_orange_scene(size=256, seed=0):  return _pure_hue_scene(30, size, seed=seed)
def pure_yellow_scene(size=256, seed=0):  return _pure_hue_scene(60, size, seed=seed)
def pure_green_scene(size=256, seed=0):   return _pure_hue_scene(120, size, seed=seed)
def pure_cyan_scene(size=256, seed=0):    return _pure_hue_scene(180, size, seed=seed)
def pure_violet_scene(size=256, seed=0):  return _pure_hue_scene(270, size, seed=seed)


PURE_HUE_GENERATORS = {
    "pure_orange_scene": pure_orange_scene,
    "pure_yellow_scene": pure_yellow_scene,
    "pure_green_scene":  pure_green_scene,
    "pure_cyan_scene":   pure_cyan_scene,
    "pure_violet_scene": pure_violet_scene,
}


def write_pure_hue_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in PURE_HUE_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="RGB").save(out / (name + ".png"))


# ---------- Shape primitive synthetic scenes (v0.7) ----------

def circle_scene(size=256, seed=0):
    """Single white filled circle on black background."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    cx, cy = size / 2, size / 2
    r = size / 4
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.where(dist < r, 1.0, 0.0)


def rectangle_scene(size=256, seed=0):
    """White centred rectangle on black background."""
    scene = np.zeros((size, size))
    a = size // 4; b = 3 * size // 4
    scene[a:b, a:b] = 1.0
    return scene


def diagonal_lines_scene(size=256, seed=0):
    """Parallel diagonal lines at 45 deg."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    return 0.5 + 0.4 * np.cos(2 * np.pi * 0.04 * (xx + yy))


def many_circles_scene(size=256, seed=0):
    """Many small circles (dotted/spotted pattern)."""
    rng = np.random.default_rng(seed)
    scene = np.zeros((size, size))
    yy, xx = np.indices((size, size)).astype(np.float64)
    for _ in range(40):
        cx = rng.uniform(15, size - 15)
        cy = rng.uniform(15, size - 15)
        r = rng.uniform(4, 9)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        scene = np.where(dist < r, 1.0, scene)
    return scene


SHAPE_GENERATORS = {
    "circle_scene":         circle_scene,
    "rectangle_scene":      rectangle_scene,
    "diagonal_lines_scene": diagonal_lines_scene,
    "many_circles_scene":   many_circles_scene,
}


def write_shape_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in SHAPE_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="L").save(out / (name + ".png"))


# ---------- Depth-cue synthetic scenes (v0.8) ----------

def perspective_road_scene(size=256, seed=0):
    """Road receding into distance - lines converging to a central
    vanishing point at the horizon (size/3 from top)."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    scene = np.full((size, size), 0.6)  # sky-toned
    vp_x = size / 2.0
    vp_y = size / 3.0
    # ground plane below the horizon
    ground_mask = yy > vp_y
    scene[ground_mask] = 0.35
    # converging lane lines (8 lines from edges to vanishing point)
    n_lines = 9
    for i in range(n_lines):
        edge_x = (i / (n_lines - 1)) * size
        for t in np.linspace(0.0, 1.0, 100):
            x = (1 - t) * edge_x + t * vp_x
            y = (1 - t) * size + t * vp_y
            iy = int(np.clip(y, 0, size - 1))
            ix = int(np.clip(x, 0, size - 1))
            scene[max(0, iy-1):iy+2, max(0, ix-1):ix+2] = 0.95
    return np.clip(scene, 0.0, 1.0)


def hazy_landscape_scene(size=256, seed=0):
    """Top half desaturated + blue-tinted (sky/atmosphere with distant
    hills), bottom half saturated green-brown (foreground)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    rgb = np.zeros((size, size, 3))
    # Top: desaturated sky-blue
    top_factor = (1.0 - yy / size)  # 1 at top, 0 at bottom
    rgb[..., 0] = 0.55 + 0.10 * (1 - top_factor)  # R: low at top, rises
    rgb[..., 1] = 0.65 + 0.05 * (1 - top_factor)  # G: similar
    rgb[..., 2] = 0.80 - 0.30 * (1 - top_factor)  # B: high at top, drops
    # Bottom: saturated foreground texture
    foreground_mask = yy > size * 0.6
    rgb[foreground_mask, 0] = 0.45 + rng.normal(0, 0.10, size=int(foreground_mask.sum()))
    rgb[foreground_mask, 1] = 0.55 + rng.normal(0, 0.10, size=int(foreground_mask.sum()))
    rgb[foreground_mask, 2] = 0.20 + rng.normal(0, 0.05, size=int(foreground_mask.sum()))
    return np.clip(rgb, 0.0, 1.0)


def shallow_dof_scene(size=256, seed=0):
    """Sharp central subject (high frequency) + heavily blurred surround
    (low frequency)."""
    rng = np.random.default_rng(seed)
    # Sharp center: random text-like pattern
    yy, xx = np.indices((size, size)).astype(np.float64)
    cx, cy = size / 2, size / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # Sharp pattern in center disk
    sharp_pattern = 0.5 + 0.4 * np.cos(2 * np.pi * 0.15 * xx) * np.cos(2 * np.pi * 0.15 * yy)
    sharp_pattern = sharp_pattern + rng.normal(0, 0.05, size=(size, size))
    # Blurred surround
    base = 0.5 + rng.normal(0, 0.1, size=(size, size))
    smoothed = base.copy()
    for _ in range(20):
        s = smoothed.copy()
        smoothed[1:-1, 1:-1] = (s[1:-1, 1:-1] + s[:-2, 1:-1] + s[2:, 1:-1]
                                  + s[1:-1, :-2] + s[1:-1, 2:]) / 5.0
    # Combine: sharp inside disk r=size/4, blurred outside
    r_disk = size / 4.0
    inside = dist < r_disk
    scene = np.where(inside, sharp_pattern, smoothed)
    return np.clip(scene, 0.0, 1.0)


DEPTH_GENERATORS = {
    "perspective_road_scene": perspective_road_scene,
    "hazy_landscape_scene":   hazy_landscape_scene,
    "shallow_dof_scene":      shallow_dof_scene,
}


def write_depth_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in DEPTH_GENERATORS.items():
        scene = gen()
        if scene.ndim == 3:
            arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="RGB").save(out / (name + ".png"))
        else:
            arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="L").save(out / (name + ".png"))


# ---------- Composition synthetic scenes (v0.9) ----------

def rule_of_thirds_scene(size=256, seed=0):
    """Single small textured subject placed at the top-right thirds
    intersection. Background is uniform. Tests has_subject_at_thirds_top_right
    and has_significant_negative_space."""
    rng = np.random.default_rng(seed)
    scene = np.full((size, size), 0.6)
    # Subject at top-right third intersection
    cx = int(size * 2 / 3); cy = int(size / 3)
    subject_size = 24
    # Random textured 24x24 patch
    patch = rng.uniform(0.0, 1.0, size=(subject_size, subject_size))
    y0 = cy - subject_size // 2
    x0 = cx - subject_size // 2
    scene[y0:y0 + subject_size, x0:x0 + subject_size] = patch
    return np.clip(scene, 0.0, 1.0)


def balanced_composition_scene(size=256, seed=0):
    """Two subjects of similar visual weight, one left and one right,
    both at vertical centre. Tests has_horizontal_balance + has_vertical_balance."""
    rng = np.random.default_rng(seed)
    scene = np.full((size, size), 0.5)
    # Left subject
    yy, xx = np.indices((size, size)).astype(np.float64)
    cx_l, cy = size * 0.25, size * 0.5
    cx_r, _ = size * 0.75, size * 0.5
    r = size * 0.10
    left_dist = np.sqrt((xx - cx_l) ** 2 + (yy - cy) ** 2)
    right_dist = np.sqrt((xx - cx_r) ** 2 + (yy - cy) ** 2)
    scene = np.where(left_dist < r, 0.9, scene)
    scene = np.where(right_dist < r, 0.1, scene)
    return np.clip(scene, 0.0, 1.0)


def negative_space_subject_scene(size=256, seed=0):
    """Tiny subject in vast empty space - tests has_significant_negative_space."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    scene = np.full((size, size), 0.5)
    # Small high-contrast subject in lower-right
    cx = size * 0.65; cy = size * 0.65
    r = size * 0.04
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    scene = np.where(dist < r, 0.95, scene)
    return scene


COMPOSITION_GENERATORS = {
    "rule_of_thirds_scene":           rule_of_thirds_scene,
    "balanced_composition_scene":     balanced_composition_scene,
    "negative_space_subject_scene":   negative_space_subject_scene,
}


def write_composition_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in COMPOSITION_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="L").save(out / (name + ".png"))


# ---------- Burst synthetic scenes (v0.10) ----------
# These are saved as directories of N frames; visual_intake.bundle_from_path
# auto-stacks any directory of images into an image_stack burst.

def panning_right_burst(size=128, n_frames=5):
    """Camera pans right - content shifts left in successive frames."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    frames = []
    for k in range(n_frames):
        cx = 30 + k * 8  # blob shifts rightward in image (so camera was panning left)
        blob = np.exp(-((xx - cx) ** 2 + (yy - size // 2) ** 2)
                       / (2 * 12 ** 2))
        # add background texture
        bg = 0.1 * np.cos(2 * np.pi * 0.04 * yy)
        frames.append(0.3 + 0.6 * blob + bg)
    return [np.clip(f, 0.0, 1.0) for f in frames]


def panning_down_burst(size=128, n_frames=5):
    """Camera pans down - content shifts up."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    frames = []
    for k in range(n_frames):
        cy = 30 + k * 8
        blob = np.exp(-((xx - size // 2) ** 2 + (yy - cy) ** 2)
                       / (2 * 12 ** 2))
        frames.append(np.clip(0.3 + 0.6 * blob, 0.0, 1.0))
    return frames


def shaking_burst(size=128, n_frames=5, seed=0):
    """Random-direction camera shake - low coherence."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    frames = []
    for k in range(n_frames):
        dx = rng.choice([-6, 6, -3, 3])
        dy = rng.choice([-6, 6, -3, 3])
        cx = size // 2 + dx
        cy = size // 2 + dy
        blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2)
                       / (2 * 12 ** 2))
        frames.append(np.clip(0.3 + 0.6 * blob, 0.0, 1.0))
    return frames


BURST_GENERATORS = {
    "panning_right_burst": panning_right_burst,
    "panning_down_burst":  panning_down_burst,
    "shaking_burst":        shaking_burst,
}


def write_burst_scenes(out_root):
    """Each burst is saved as a sub-directory of N PNGs."""
    out = Path(out_root)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in BURST_GENERATORS.items():
        burst_dir = out / name
        burst_dir.mkdir(exist_ok=True)
        frames = gen()
        for i, f in enumerate(frames):
            arr = (np.clip(f, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="L").save(
                burst_dir / f"{i + 1:04d}.png")


# ---------- Vocabulary-cleanup synthetic scenes (v0.11) ----------
# Each targets one structural equivalence class identified by IR:

def edge_ratio_borderline_scene(size=256, seed=0):
    """Horizontal edges only slightly dominant - h/v ratio about 1.4.
    Should fire has_horizon_line_signature (>1.30) but NOT
    has_horizontal_dominant_edges (>1.50). Achieves this by tuning
    horizontal vs vertical sinusoid amplitudes to give energy ratio ~1.4."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    horizontal = 0.5 + 0.20 * np.cos(2 * np.pi * 0.04 * yy)
    vertical = 0.17 * np.cos(2 * np.pi * 0.04 * xx)
    return np.clip(horizontal + vertical +
                    rng.normal(0, 0.005, size=(size, size)), 0.0, 1.0)


def slow_coherent_burst(size=128, n_frames=5):
    """Camera pans rightward 1.5 px/frame - coherent BUT velocity
    below has_fast_motion threshold (5 px). Should fire
    has_real_motion_validated but NOT has_fast_motion."""
    yy, xx = np.indices((size, size)).astype(np.float64)
    frames = []
    for k in range(n_frames):
        cx = 60 + k * 1.5
        blob = np.exp(-((xx - cx) ** 2 + (yy - 64) ** 2) / (2 * 12 ** 2))
        frames.append(np.clip(0.3 + 0.6 * blob, 0.0, 1.0))
    return frames


def faint_green_tint_scene(size=256, seed=0):
    """RGB green channel slightly dominant in mean, but ALL pixels are
    near-grey (low saturation). Should fire has_green_dominant (mean
    comparison) but NOT has_significant_green_hue (saturation gate
    excludes near-grey pixels from hue counting)."""
    rng = np.random.default_rng(seed)
    grey = 0.50 + rng.normal(0, 0.02, size=(size, size))
    rgb = np.zeros((size, size, 3))
    rgb[..., 0] = grey - 0.005  # R slightly less
    rgb[..., 1] = grey + 0.010  # G slightly more
    rgb[..., 2] = grey - 0.005  # B slightly less
    return np.clip(rgb, 0.0, 1.0)


def rainbow_no_magenta_scene(size=256, seed=0):
    """Vertical bands of red, orange, yellow, green, cyan, blue
    (6 hues, 4+ buckets) but NO magenta. Should fire
    has_polychromatic_palette but NOT has_significant_magenta_hue."""
    rgb = np.zeros((size, size, 3))
    bands = [
        (0.95, 0.10, 0.10),  # red
        (0.95, 0.50, 0.10),  # orange
        (0.95, 0.90, 0.10),  # yellow
        (0.10, 0.85, 0.20),  # green
        (0.10, 0.85, 0.85),  # cyan
        (0.10, 0.30, 0.95),  # blue
    ]
    band_w = size // len(bands)
    for i, (r, g, b) in enumerate(bands):
        rgb[:, i * band_w:(i + 1) * band_w, 0] = r
        rgb[:, i * band_w:(i + 1) * band_w, 1] = g
        rgb[:, i * band_w:(i + 1) * band_w, 2] = b
    # fill any remaining pixels with the last band
    if len(bands) * band_w < size:
        rgb[:, len(bands) * band_w:, 0] = bands[-1][0]
        rgb[:, len(bands) * band_w:, 1] = bands[-1][1]
        rgb[:, len(bands) * band_w:, 2] = bands[-1][2]
    return rgb


CLEANUP_GENERATORS = {
    "edge_ratio_borderline_scene": edge_ratio_borderline_scene,
    "faint_green_tint_scene":       faint_green_tint_scene,
    "rainbow_no_magenta_scene":     rainbow_no_magenta_scene,
}
CLEANUP_BURSTS = {
    "slow_coherent_burst":          slow_coherent_burst,
}


def write_cleanup_scenes(scenes_dir, bursts_dir):
    sd = Path(scenes_dir); bd = Path(bursts_dir)
    sd.mkdir(parents=True, exist_ok=True)
    bd.mkdir(parents=True, exist_ok=True)
    for name, gen in CLEANUP_GENERATORS.items():
        scene = gen()
        if scene.ndim == 3:
            arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="RGB").save(sd / (name + ".png"))
        else:
            arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="L").save(sd / (name + ".png"))
    for name, gen in CLEANUP_BURSTS.items():
        burst_dir = bd / name
        burst_dir.mkdir(exist_ok=True)
        frames = gen()
        for i, f in enumerate(frames):
            arr = (np.clip(f, 0.0, 1.0) * 255).astype(np.uint8)
            Image.fromarray(arr, mode="L").save(burst_dir / f"{i + 1:04d}.png")


# ---------- Lighting / illumination synthetic scenes (v0.11) ----------

def low_light_scene(size=256, seed=0):
    """Mostly very dark with subtle texture."""
    rng = np.random.default_rng(seed)
    base = 0.12 + 0.08 * np.cos(2 * np.pi * 0.02 * np.arange(size))[:, None]
    base = np.broadcast_to(base, (size, size)).copy()
    return np.clip(base + rng.normal(0, 0.03, size=(size, size)), 0.0, 1.0)


def high_key_scene(size=256, seed=0):
    """Mostly very bright with subtle subject."""
    rng = np.random.default_rng(seed)
    base = np.full((size, size), 0.85)
    yy, xx = np.indices((size, size)).astype(np.float64)
    cx, cy = size / 2, size / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # Faint darker subject in centre
    base[dist < size / 8] = 0.65
    return np.clip(base + rng.normal(0, 0.02, size=(size, size)), 0.0, 1.0)


def center_lit_scene(size=256, seed=0):
    """Bright subject at centre, dark surround. Portrait / spotlight."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    cx, cy = size / 2, size / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # Smooth fall-off from 0.85 at centre to 0.12 at edges
    falloff = np.exp(-(dist ** 2) / (2 * (size / 4) ** 2))
    base = 0.12 + 0.73 * falloff
    return np.clip(base + rng.normal(0, 0.02, size=(size, size)), 0.0, 1.0)


def specular_highlight_scene(size=256, seed=0):
    """Mid-grey overall with several tiny very-bright spots
    (specular reflections on a glossy surface)."""
    rng = np.random.default_rng(seed)
    base = np.full((size, size), 0.45) + rng.normal(0, 0.05, size=(size, size))
    # Place 8 tiny bright spots
    for _ in range(8):
        cy = int(rng.integers(10, size - 10))
        cx = int(rng.integers(10, size - 10))
        base[cy - 1:cy + 2, cx - 1:cx + 2] = 0.97
    return np.clip(base, 0.0, 1.0)


LIGHTING_GENERATORS = {
    "low_light_scene":          low_light_scene,
    "high_key_scene":           high_key_scene,
    "center_lit_scene":         center_lit_scene,
    "specular_highlight_scene": specular_highlight_scene,
}


def write_lighting_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in LIGHTING_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="L").save(out / (name + ".png"))


# ---------- Curve synthetic (v0.12) ----------

def curve_scene(size=256, seed=0):
    """A short ~90-degree arc - gradient orientations span a CONTIGUOUS
    SUBSET of bins (not the full range, not a single peak). This is
    the target signal for has_curved_signature."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size)).astype(np.float64)
    # Quarter arc centred at upper-right, radius reaching lower-left
    cx, cy = size * 0.95, size * 0.05
    r = size * 0.85
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    arc = np.exp(-((dist - r) ** 2) / (2 * 3 ** 2))
    # Mask: only show the visible 90 deg arc (within the frame)
    angle = np.arctan2(yy - cy, xx - cx)
    # Quarter arc: angle between 90 and 180 degrees
    angle_mask = (angle > np.pi / 2 - 0.4) & (angle < np.pi + 0.4)
    arc = arc * angle_mask
    return np.clip(0.25 + 0.65 * arc + rng.normal(0, 0.02, size=(size, size)),
                    0.0, 1.0)


CURVE_GENERATORS = {"curve_scene": curve_scene}


def write_curve_scenes(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, gen in CURVE_GENERATORS.items():
        scene = gen()
        arr = (np.clip(scene, 0.0, 1.0) * 255).astype(np.uint8)
        Image.fromarray(arr, mode="L").save(out / (name + ".png"))
