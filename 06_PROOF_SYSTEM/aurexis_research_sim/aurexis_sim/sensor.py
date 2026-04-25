"""Sensor-path primitives: Bayer CFA mosaic, bilinear demosaic, and
per-channel helpers.

Scope claim: this is an approximation useful for research on which
spatial/chromatic relations survive CFA sampling. It is NOT a RAW
pipeline, NOT a production demosaic, and makes no claim of CMOS
fidelity. Specifically:

- No photon-count / shot-noise-by-channel-density modeling.
- No optical low-pass (OLPF) approximation beyond the existing
  per-channel gaussian blur.
- No white-balance, CCM, or gamma-curve-from-raw step.
- Demosaic is bilinear, not gradient/adaptive.

The point is to expose CFA + interpolation as a real degradation
mechanism, not to claim it's fully simulated.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Tuple

import numpy as np

from .color import promote_to_rgb, is_rgb


BAYER_PATTERNS = ("RGGB", "BGGR", "GRBG", "GBRG")


@dataclass
class SensorParams:
    enabled: bool = False
    pattern: str = "RGGB"
    # Per-channel optical blur sigmas (applied BEFORE mosaicking).
    # A small R/B vs G difference models trivial chromatic aberration.
    blur_sigma_r: float = 0.0
    blur_sigma_g: float = 0.0
    blur_sigma_b: float = 0.0
    # Per-channel gaussian read noise std, applied at the mosaic stage.
    noise_r: float = 0.0
    noise_g: float = 0.0
    noise_b: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


# --- CFA masks ------------------------------------------------------------

def _cfa_masks(shape_hw: Tuple[int, int], pattern: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return boolean R/G/B masks for the given Bayer pattern.

    pattern is read row-major top-left: e.g. 'RGGB' means
        (0,0)=R  (0,1)=G
        (1,0)=G  (1,1)=B
    """
    if pattern not in BAYER_PATTERNS:
        raise ValueError(f"Unknown Bayer pattern {pattern!r}. Known: {BAYER_PATTERNS}")
    h, w = shape_hw
    mR = np.zeros((h, w), dtype=bool)
    mG = np.zeros((h, w), dtype=bool)
    mB = np.zeros((h, w), dtype=bool)

    if pattern == "RGGB":
        mR[0::2, 0::2] = True
        mG[0::2, 1::2] = True
        mG[1::2, 0::2] = True
        mB[1::2, 1::2] = True
    elif pattern == "BGGR":
        mB[0::2, 0::2] = True
        mG[0::2, 1::2] = True
        mG[1::2, 0::2] = True
        mR[1::2, 1::2] = True
    elif pattern == "GRBG":
        mG[0::2, 0::2] = True
        mR[0::2, 1::2] = True
        mB[1::2, 0::2] = True
        mG[1::2, 1::2] = True
    elif pattern == "GBRG":
        mG[0::2, 0::2] = True
        mB[0::2, 1::2] = True
        mR[1::2, 0::2] = True
        mG[1::2, 1::2] = True
    return mR, mG, mB


# --- mosaic / demosaic ----------------------------------------------------

def bayer_mosaic(rgb: np.ndarray, pattern: str = "RGGB") -> np.ndarray:
    """RGB (HxWx3) -> 2D mosaic (HxW). One channel sampled per pixel."""
    if not is_rgb(rgb):
        raise ValueError("bayer_mosaic expects an HxWx3 RGB image")
    h, w, _ = rgb.shape
    mR, mG, mB = _cfa_masks((h, w), pattern)
    out = np.zeros((h, w), dtype=np.float32)
    out[mR] = rgb[..., 0][mR]
    out[mG] = rgb[..., 1][mG]
    out[mB] = rgb[..., 2][mB]
    return out


def demosaic_bilinear(mosaic: np.ndarray, pattern: str = "RGGB") -> np.ndarray:
    """Bilinear demosaic: fill missing channels by averaging nearest same-color
    samples. Not production quality — but research-honest.

    Implementation: for each channel, create a sparse same-color plane and
    do a separable bilinear fill via the known CFA density pattern.
    """
    h, w = mosaic.shape
    mR, mG, mB = _cfa_masks((h, w), pattern)

    # Populate sparse channel planes where samples exist, zero elsewhere.
    R = np.where(mR, mosaic, 0.0).astype(np.float32)
    G = np.where(mG, mosaic, 0.0).astype(np.float32)
    B = np.where(mB, mosaic, 0.0).astype(np.float32)

    # Bilinear-ish interpolation via small convolutions.
    # For G (half-density, quincunx): 4-neighbor average works well.
    kG = np.array([[0, 1, 0],
                   [1, 4, 1],
                   [0, 1, 0]], dtype=np.float32) / 4.0
    # For R and B (quarter-density, square grid): full 3x3 neighbor avg
    # with correct weights: corners get contribution from 4 known samples,
    # the edges from 2, center from itself.
    kRB = np.array([[1, 2, 1],
                    [2, 4, 2],
                    [1, 2, 1]], dtype=np.float32) / 4.0

    G_full = _conv2d_same(G, kG)
    R_full = _conv2d_same(R, kRB)
    B_full = _conv2d_same(B, kRB)

    out = np.stack([R_full, G_full, B_full], axis=-1)
    return np.clip(out, 0.0, 1.0)


def _conv2d_same(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Small 2D convolution with edge-replicate padding. Same size out."""
    from numpy.lib.stride_tricks import sliding_window_view

    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(img, ((ph, ph), (pw, pw)), mode="edge").astype(np.float32)
    windows = sliding_window_view(padded, (kh, kw))
    return np.einsum("ijkl,kl->ij", windows, k.astype(np.float32))


# --- per-channel primitives ----------------------------------------------

def per_channel_blur(rgb: np.ndarray, sigmas: Tuple[float, float, float]) -> np.ndarray:
    """Gaussian blur each channel independently."""
    from .simulate import _gaussian_kernel_1d, _conv1d  # reuse
    out = np.empty_like(rgb)
    for c, s in enumerate(sigmas):
        if s <= 0:
            out[..., c] = rgb[..., c]
            continue
        k = _gaussian_kernel_1d(s)
        ch = _conv1d(rgb[..., c], k, axis=1)
        ch = _conv1d(ch, k, axis=0)
        out[..., c] = ch
    return out


def mosaic_noise(mosaic: np.ndarray, pattern: str,
                 stds: Tuple[float, float, float],
                 rng: np.random.Generator) -> np.ndarray:
    """Add per-channel gaussian noise at the mosaic stage.

    A given pixel gets only one channel's noise, depending on its CFA role.
    """
    h, w = mosaic.shape
    mR, mG, mB = _cfa_masks((h, w), pattern)
    out = mosaic.astype(np.float32).copy()
    if stds[0] > 0:
        out[mR] += rng.normal(0.0, stds[0], size=int(mR.sum())).astype(np.float32)
    if stds[1] > 0:
        out[mG] += rng.normal(0.0, stds[1], size=int(mG.sum())).astype(np.float32)
    if stds[2] > 0:
        out[mB] += rng.normal(0.0, stds[2], size=int(mB.sum())).astype(np.float32)
    return np.clip(out, 0.0, 1.0)


# --- end-to-end sensor stage ----------------------------------------------

def run_sensor_stage(rgb: np.ndarray, sp: SensorParams,
                     rng: np.random.Generator) -> dict:
    """Full sensor sub-chain: per-channel blur -> mosaic -> mosaic noise -> demosaic.

    Returns intermediates for inspection.
    """
    if not is_rgb(rgb):
        rgb = promote_to_rgb(rgb)

    pre_cfa = per_channel_blur(
        rgb, (sp.blur_sigma_r, sp.blur_sigma_g, sp.blur_sigma_b)
    )
    mosaic = bayer_mosaic(pre_cfa, pattern=sp.pattern)
    noisy_mosaic = mosaic_noise(
        mosaic, sp.pattern, (sp.noise_r, sp.noise_g, sp.noise_b), rng
    )
    demosaiced = demosaic_bilinear(noisy_mosaic, pattern=sp.pattern)
    return {
        "pre_cfa_rgb": pre_cfa,
        "mosaic": mosaic,
        "mosaic_noisy": noisy_mosaic,
        "demosaiced_rgb": demosaiced,
    }
