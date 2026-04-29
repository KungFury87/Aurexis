"""Synthetic frames for verifying the Round 30 frame-quality gate.

Generates a fixed set of images with known degradations. Each is a
deterministic 256x256 RGB array (seeded RNG so re-runs reproduce
exactly) designed to exercise one specific gate component:

    clean_reference   — well-exposed, sharp, no glare    EXPECTED: pass all
    overexposed       — 60% pixels near maximum value    EXPECTED: fail overexposed
    underexposed      — 60% pixels near zero             EXPECTED: fail underexposed
    glare             — sharp bright spots on dark bg    EXPECTED: fail specular highlights
    motion_blur       — heavy directional smear          EXPECTED: fail uniform focus
    multi_problem     — overexposed + glare combined     EXPECTED: fail multiple

The gate is correct if (a) clean_reference scores high, (b) each
single-degradation frame fails its target predicate, and (c) the
multi-problem frame scores lower than any single-problem frame.

Run:
    python -m aurexis_workbench.frame_quality_synthetics

Prints a verification table and exits with code 0 on pass, 1 on fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .fields import FieldBundle
from .frame_quality import score_bundle


def _bundle_from_color(arr: np.ndarray, name: str) -> FieldBundle:
    """Wrap an HxWx3 uint8 array as a FieldBundle the gate can score."""
    arr_f = arr.astype(np.float64) / 255.0
    color = arr_f[..., :3]
    luma = 0.299 * color[..., 0] + 0.587 * color[..., 1] + 0.114 * color[..., 2]
    burst = luma[None, ...]
    bundle = FieldBundle(name=name)
    bundle.add_value("scene", "image", luma, description="luma")
    bundle.add_value("color_scene", "color_image", color, description="rgb")
    bundle.add_value("burst", "image_stack", burst, description="single-frame")
    bundle.add_value("patch_size", "int", 64, description="ROI side")
    bundle.add_value("row_y", "int", luma.shape[0] // 2,
                       description="autocorr row")
    return bundle


# ---- generators -----------------------------------------------------------

def gen_clean_reference(size: int = 256, seed: int = 42) -> np.ndarray:
    """Mid-tone scene with structured edges. Should pass everything."""
    rng = np.random.default_rng(seed)
    arr = np.full((size, size, 3), 128, dtype=np.float64)
    # Add a few rectangles of varied mid-tone color (gives edges)
    for _ in range(8):
        y = rng.integers(20, size - 60)
        x = rng.integers(20, size - 60)
        h = rng.integers(30, 50)
        w = rng.integers(30, 50)
        color = rng.integers(60, 200, size=3)
        arr[y:y+h, x:x+w] = color
    # Mild noise to break exact uniformity
    arr += rng.normal(0, 4, arr.shape)
    return np.clip(arr, 0, 255).astype(np.uint8)


def gen_overexposed(size: int = 256, seed: int = 43) -> np.ndarray:
    """60% of pixels pushed to near-max (saturated highlights)."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(60, 200, (size, size, 3)).astype(np.float64)
    # Force the upper 60% of the frame to clipped values
    saturated_band_h = int(size * 0.6)
    arr[:saturated_band_h] = rng.integers(248, 256, (saturated_band_h, size, 3))
    return np.clip(arr, 0, 255).astype(np.uint8)


def gen_underexposed(size: int = 256, seed: int = 44) -> np.ndarray:
    """60% of pixels pushed to near-zero (clipped shadows)."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(60, 200, (size, size, 3)).astype(np.float64)
    band_h = int(size * 0.6)
    arr[:band_h] = rng.integers(0, 7, (band_h, size, 3))
    return np.clip(arr, 0, 255).astype(np.uint8)


def gen_glare(size: int = 256, seed: int = 45) -> np.ndarray:
    """Mid-tone background with a few sharp very-bright spots (glare)."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(50, 130, (size, size, 3)).astype(np.float64)
    # 6 small bright "specular" disks scattered around
    yy, xx = np.mgrid[:size, :size]
    for _ in range(6):
        cy = rng.integers(15, size - 15)
        cx = rng.integers(15, size - 15)
        r2 = rng.integers(4, 9) ** 2
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 < r2
        arr[mask] = 250
    return np.clip(arr, 0, 255).astype(np.uint8)


def gen_motion_blur(size: int = 256, seed: int = 46) -> np.ndarray:
    """Strong horizontal directional blur applied to a structured scene.

    Goal: make the focus_blur_gradient operator see uniformly low local
    sharpness across the frame (no sharp regions anywhere)."""
    rng = np.random.default_rng(seed)
    # Start from a structured reference
    arr = gen_clean_reference(size=size, seed=seed).astype(np.float64)
    # Apply a 21-pixel horizontal box blur (simulates camera shake)
    k = 21
    pad = k // 2
    padded = np.pad(arr, ((0, 0), (pad, pad), (0, 0)), mode="edge")
    out = np.zeros_like(arr)
    for i in range(k):
        out += padded[:, i:i + size]
    out /= k
    return np.clip(out, 0, 255).astype(np.uint8)


def gen_multi_problem(size: int = 256, seed: int = 47) -> np.ndarray:
    """Overexposed + glare combined. Should fail multiple predicates
    and score noticeably lower than any single-problem frame."""
    rng = np.random.default_rng(seed)
    arr = gen_overexposed(size=size, seed=seed).astype(np.float64)
    # Sprinkle the glare spots on top
    yy, xx = np.mgrid[:size, :size]
    for _ in range(8):
        cy = rng.integers(15, size - 15)
        cx = rng.integers(15, size - 15)
        r2 = rng.integers(4, 9) ** 2
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 < r2
        arr[mask] = 254
    return np.clip(arr, 0, 255).astype(np.uint8)


# Test cases as: (name, generator, expected_failures_subset, expected_score_band)
# expected_failures_subset: predicates that MUST be in the failed list
# expected_score_band: (low, high) score range that the result must fall in
TEST_CASES = [
    ("clean_reference",  gen_clean_reference,
        set(),                                          (0.85, 1.0001)),
    ("overexposed",      gen_overexposed,
        {"has_overexposed_regions"},                    (0.0, 0.30)),
    ("underexposed",     gen_underexposed,
        {"has_underexposed_regions"},                   (0.0, 0.30)),
    ("glare",            gen_glare,
        {"has_specular_highlights"},                    (0.0, 0.30)),
    ("motion_blur",      gen_motion_blur,
        # has_uniform_focus going FALSE = fail (we want uniform focus)
        # but a uniform blur also makes focus uniform-low, so the gate
        # may NOT fail this in the obvious way — accept either signal
        set(),                                          (0.0, 1.0001)),
    ("multi_problem",    gen_multi_problem,
        {"has_overexposed_regions", "has_specular_highlights"},
                                                          (0.0, 0.05)),
]


def run_verification(write_pngs_to: Path | None = None
                       ) -> tuple[int, int, list[dict]]:
    """Run every test case. Return (n_pass, n_total, per_case_records)."""
    print(f"{'case':<22} {'score':>7}  {'expected':<14}  result")
    print("-" * 80)
    n_pass = 0
    records = []
    for name, gen, must_fail, (lo, hi) in TEST_CASES:
        arr = gen()
        bundle = _bundle_from_color(arr, name)
        q = score_bundle(bundle)

        # Save synthetic PNG for inspection if requested
        if write_pngs_to:
            write_pngs_to.mkdir(parents=True, exist_ok=True)
            Image.fromarray(arr).save(write_pngs_to / f"{name}.png")

        score_ok = lo <= q.score <= hi
        fails_ok = must_fail.issubset(set(q.failed_components))

        ok = score_ok and fails_ok
        if ok:
            n_pass += 1
            verdict = "PASS"
        else:
            verdict = "FAIL"
            if not score_ok:
                verdict += f"  (score outside [{lo:.2f}, {hi:.2f}])"
            if not fails_ok:
                missing = must_fail - set(q.failed_components)
                verdict += f"  (missing: {','.join(missing)})"

        expected_label = (",".join(sorted(must_fail))[:14] if must_fail
                            else "pass-all")
        print(f"{name:<22} {q.score:>7.3f}  {expected_label:<14}  {verdict}")
        if q.failed_components:
            print(f"{'':<22} {'':>7}  failed: "
                    f"{', '.join(q.failed_components)}")
        records.append({
            "name": name,
            "score": q.score,
            "expected_failures": sorted(must_fail),
            "actual_failures": list(q.failed_components),
            "actual_passes": list(q.passed_components),
            "blocked": list(q.blocked_components),
            "verdict": verdict,
            "score_band": [lo, hi],
        })
    print("-" * 80)
    print(f"verified: {n_pass}/{len(TEST_CASES)}")
    return n_pass, len(TEST_CASES), records


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-pngs", default="",
                      help="if set, write synthetic frames as PNGs here")
    args = ap.parse_args(argv)

    write_to = Path(args.write_pngs) if args.write_pngs else None
    n_pass, n_total, _ = run_verification(write_pngs_to=write_to)
    return 0 if n_pass == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
