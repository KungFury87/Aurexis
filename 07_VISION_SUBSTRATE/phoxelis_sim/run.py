"""Phoxelis Encoding Simulation — round-trip runner.

Generates random payloads, encodes them, decodes them, reports
bit-error rate. v0.1 is the smallest correct test: clean encode ->
decode through the real Phoxelis runtime, no distortion. If
round-trip BER is 0/16 across many trials, the kernel works and
v0.2 (distortion sweeps) is worth building.

Usage:
    python -m phoxelis_sim.run
    python -m phoxelis_sim.run --trials 100 --seed 42
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

from .encoder import encode_bits, encode_bytes, N_CELLS
from .decoder import decode_bits, decode_bytes


def run_trial(bits: list[int]) -> tuple[list[int], int]:
    """Encode -> decode round-trip. Returns (recovered_bits, n_errors)."""
    img = encode_bits(bits)
    recovered = decode_bits(img)
    errors = sum(1 for a, b in zip(bits, recovered) if a != b)
    return recovered, errors


def run_byte_trial(payload: bytes) -> tuple[bytes, int]:
    """Same but for byte payloads."""
    img = encode_bytes(payload)
    recovered = decode_bytes(img)
    errors = sum(1 for a, b in zip(payload, recovered) if a != b)
    return recovered, errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=20,
                      help="number of random payloads to test")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save-images", default="",
                      help="if set, save first 3 encoded images here as PNGs")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    print(f"Phoxelis Encoding Sim v0.1 — round-trip test")
    print(f"  cells: {N_CELLS}  bits/image: {N_CELLS}  trials: {args.trials}")
    print(f"  predicate carrier: has_red_dominant")
    print(f"  distortion: NONE (clean round-trip)")
    print()

    total_bits = 0
    total_errors = 0
    perfect_trials = 0
    for t in range(args.trials):
        bits = [rng.randint(0, 1) for _ in range(N_CELLS)]
        recovered, errors = run_trial(bits)
        total_bits += N_CELLS
        total_errors += errors
        if errors == 0:
            perfect_trials += 1
        if t < 3 or errors > 0:
            mark = "OK" if errors == 0 else f"FAIL({errors})"
            print(f"  trial {t:>3}: bits={''.join(map(str, bits))}  "
                  f"recovered={''.join(map(str, recovered))}  {mark}")
        if args.save_images and t < 3:
            from PIL import Image
            from .encoder import encode_bits as _enc
            outdir = Path(args.save_images)
            outdir.mkdir(parents=True, exist_ok=True)
            Image.fromarray(_enc(bits)).save(outdir / f"trial_{t:03d}.png")

    print()
    print(f"summary:")
    print(f"  trials run:           {args.trials}")
    print(f"  perfect round-trips:  {perfect_trials}/{args.trials}")
    print(f"  total bits exchanged: {total_bits}")
    print(f"  total bit errors:     {total_errors}")
    ber = total_errors / max(total_bits, 1)
    print(f"  bit error rate:       {ber:.4f}")
    print()
    if perfect_trials == args.trials:
        print("VERDICT: v0.1 KERNEL WORKS. Round-trip is byte-exact at zero distortion.")
        print("  Next: v0.2 adds capture distortion sweeps (Gaussian noise, blur, JPEG).")
        return 0
    elif ber < 0.05:
        print(f"VERDICT: v0.1 mostly works (BER {ber:.3f} < 5%). Some cells flipped.")
        print("  Investigate: which cells flipped, and why the predicate misread them.")
        return 0
    else:
        print(f"VERDICT: v0.1 KERNEL DOES NOT WORK (BER {ber:.3f}).")
        print("  Either the encoder isn't producing the predicate signature it claims,")
        print("  or the decoder runtime evaluates the predicate differently than expected.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
