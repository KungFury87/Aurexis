"""Phoxelis Encoding Simulation v0.2 — saturation × distortion sweep.

Find the cliff. v0.1 had infinite margin because cells were saturated
red/green and the decoder's decision boundary is far from saturated
colors. v0.2 sweeps:

  - saturation: 1.0 (v0.1 baseline) down toward 0.0 (gray, no signal)
  - Gaussian noise sigma: 0 to 100
  - JPEG quality: 100 to 5
  - blur kernel: 1 to 41

For each (saturation × distortion) cell of the matrix, runs N trials
of random 64-bit payloads and reports BER. Output: a 2-D matrix
showing where the signal first dies.
"""
from __future__ import annotations

import argparse
import io
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter

from .encoder import encode_bits, DEFAULT_GRID_W, DEFAULT_GRID_H
from .decoder import decode_bits

N_BITS = DEFAULT_GRID_W * DEFAULT_GRID_H


def add_gaussian(img: np.ndarray, sigma: float, rng) -> np.ndarray:
    if sigma <= 0:
        return img
    arr = img.astype(np.float64) + rng.normal(0, sigma, img.shape)
    return np.clip(arr, 0, 255).astype(np.uint8)


def jpeg_recode(img: np.ndarray, quality: int) -> np.ndarray:
    if quality >= 100:
        return img
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=int(quality))
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("RGB"))


def box_blur(img: np.ndarray, kernel: int) -> np.ndarray:
    if kernel <= 1:
        return img
    out = np.zeros_like(img)
    for c in range(3):
        out[..., c] = uniform_filter(img[..., c], size=int(kernel))
    return out


def trial(saturation: float, distortion_fn, rng, np_rng) -> int:
    """One round-trip; return number of bit errors."""
    bits = [rng.randint(0, 1) for _ in range(N_BITS)]
    img = encode_bits(bits, saturation=saturation)
    if distortion_fn is not None:
        img = distortion_fn(img, np_rng)
    recovered = decode_bits(img)
    return sum(1 for a, b in zip(bits, recovered) if a != b)


def sweep(distortion_label: str, distortion_makers, saturations, n_trials,
            seed):
    """For each (saturation, distortion-amount), run n_trials and report BER.
    distortion_makers: list of (label, callable(img, np_rng)) pairs."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    print(f"\n=== {distortion_label} sweep ({n_trials} trials/cell) ===")
    head = "saturation \\ distortion"
    print(f"{head:<24}  " + "  ".join(f"{lbl:>10}" for lbl, _ in distortion_makers))
    for sat in saturations:
        cells = []
        for _, fn in distortion_makers:
            errs = sum(trial(sat, fn, rng, np_rng) for _ in range(n_trials))
            ber = errs / (n_trials * N_BITS)
            cells.append(f"{ber:.3f}")
        print(f"sat={sat:>4.2f}{'':<14}  " + "  ".join(f"{c:>10}" for c in cells))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10,
                      help="trials per (saturation, distortion) cell")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    np_rng = np.random.default_rng(args.seed)

    print(f"Phoxelis Encoding Sim v0.2 — saturation × distortion sweep")
    print(f"  grid: {DEFAULT_GRID_W}×{DEFAULT_GRID_H} = {N_BITS} bits/image")
    print(f"  cell size: {256 // DEFAULT_GRID_W} × {256 // DEFAULT_GRID_H} px")
    print(f"  predicate carrier: has_red_dominant")
    print(f"  trials per cell: {args.trials}")

    saturations = [1.00, 0.75, 0.50, 0.30, 0.20, 0.15, 0.10, 0.05]

    # Gaussian noise sweep
    g_sigmas = [0, 25, 50, 75, 100]
    sweep("Gaussian noise (sigma)",
          [(f"σ={s}", (lambda i, r, s=s: add_gaussian(i, s, r))) for s in g_sigmas],
          saturations, args.trials, args.seed)

    # JPEG sweep
    jpeg_q = [100, 75, 50, 25, 10, 5]
    sweep("JPEG re-encode (quality)",
          [(f"q={q}", (lambda i, r, q=q: jpeg_recode(i, q))) for q in jpeg_q],
          saturations, args.trials, args.seed + 1)

    # Box blur sweep
    blurs = [1, 5, 11, 21, 41]
    sweep("Box blur (kernel size)",
          [(f"k={k}", (lambda i, r, k=k: box_blur(i, k))) for k in blurs],
          saturations, args.trials, args.seed + 2)

    print()
    print("Read the matrices: row = saturation level (1.0 = pure red/green,")
    print("0.05 = nearly gray); column = distortion magnitude.")
    print("BER 0.500 = signal indistinguishable from noise.")
    print("BER 0.000 = byte-exact.")
    print("The cliff is wherever a row first becomes nonzero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
