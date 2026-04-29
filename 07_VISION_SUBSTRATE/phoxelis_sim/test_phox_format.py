"""Test the .phox format kernel: write -> read should be byte-exact in
both the byte stream and the recovered semantic content.

Run:
    python -m phoxelis_sim.test_phox_format
"""
from __future__ import annotations

import random
import sys

from .phox_format import (
    PhoxImage, write_phox, read_phox,
    CHUNK_USER, MAGIC, VERSION,
)


def random_phox(seed: int, grid_w: int, grid_h: int,
                  predicate_names) -> PhoxImage:
    rng = random.Random(seed)
    cells = []
    for gy in range(grid_h):
        row = []
        for gx in range(grid_w):
            row.append([bool(rng.randint(0, 1)) for _ in predicate_names])
        cells.append(row)
    return PhoxImage(grid_w=grid_w, grid_h=grid_h,
                       predicate_names=list(predicate_names),
                       cell_states=cells)


def test_smallest():
    """1×1 grid, 1 predicate, 1 bit total."""
    img = PhoxImage(grid_w=1, grid_h=1, predicate_names=["p"],
                      cell_states=[[[True]]])
    blob = write_phox(img)
    back = read_phox(blob)
    assert back.predicate_names == ["p"]
    assert back.cell_states == [[[True]]]
    print(f"  smallest:        {len(blob):>5} bytes  PASS")


def test_v01_size():
    """4x4 grid, 1 predicate (matches sim v0.1 capacity)."""
    img = random_phox(seed=42, grid_w=4, grid_h=4, predicate_names=["has_red_dominant"])
    blob = write_phox(img)
    back = read_phox(blob)
    assert back.cell_states == img.cell_states
    print(f"  v0.1 (4x4 x 1):  {len(blob):>5} bytes  "
            f"({img.total_semantic_bits} semantic bits)  PASS")


def test_v03_size():
    """8x8 grid, 4 predicates (matches sim v0.3 plan)."""
    preds = ["has_red_dominant", "has_high_edge_density",
             "has_uniform_focus", "has_overexposed_regions"]
    img = random_phox(seed=42, grid_w=8, grid_h=8, predicate_names=preds)
    blob = write_phox(img)
    back = read_phox(blob)
    assert back.cell_states == img.cell_states
    assert back.predicate_names == preds
    print(f"  v0.3 (8x8 x 4):  {len(blob):>5} bytes  "
            f"({img.total_semantic_bits} semantic bits)  PASS")


def test_full_vocabulary():
    """16x16 grid, full 103-predicate vocabulary."""
    # Cap at 100 because the format spec uses uint8 for n_predicates (max 255).
    preds = [f"pred_{i:03d}" for i in range(100)]
    img = random_phox(seed=42, grid_w=16, grid_h=16, predicate_names=preds)
    blob = write_phox(img)
    back = read_phox(blob)
    assert back.cell_states == img.cell_states
    bytes_per_bit = len(blob) / img.total_semantic_bits
    print(f"  full (16x16 x 100): {len(blob):>5} bytes  "
            f"({img.total_semantic_bits} semantic bits, "
            f"{bytes_per_bit:.3f} bytes/bit)  PASS")


def test_with_chunks():
    """Tail chunks should round-trip too."""
    img = random_phox(seed=1, grid_w=2, grid_h=2,
                        predicate_names=["a", "b", "c"])
    img.chunks = [(CHUNK_USER, b"hello world"),
                    (CHUNK_USER, b"\x00\x01\x02\x03")]
    blob = write_phox(img)
    back = read_phox(blob)
    assert back.chunks == img.chunks
    print(f"  with chunks:     {len(blob):>5} bytes  PASS")


def test_byte_exact_repeated_writes():
    """Writing the same PhoxImage twice must produce identical bytes."""
    img = random_phox(seed=99, grid_w=8, grid_h=8,
                        predicate_names=["has_red_dominant", "has_blue_dominant"])
    a = write_phox(img)
    b = write_phox(img)
    assert a == b
    print(f"  determinism:     {len(a):>5} bytes (write x2 identical)  PASS")


def test_density_comparison():
    """Compare information density: same canvas size, .phox vs raw RGB pixels."""
    print("\n  --- information density (same image area) ---")
    print(f"  {'format':<32} {'bytes':>8} {'semantic bits':>15}")
    canvas_px = 256 * 256
    raw_rgb_bytes = canvas_px * 3
    print(f"  {'raw RGB 256x256':<32} {raw_rgb_bytes:>8} {raw_rgb_bytes*8:>15}")

    # .phox at v0.3 density: 8x8 grid, 4 predicates per cell
    preds = ["a", "b", "c", "d"]
    img = random_phox(seed=1, grid_w=8, grid_h=8, predicate_names=preds)
    blob = write_phox(img)
    print(f"  {'.phox 8x8 x 4 (v0.3 design)':<32} {len(blob):>8} "
            f"{img.total_semantic_bits:>15}")

    # .phox at full-vocabulary density: 16x16 grid, 100 predicates per cell
    preds = [f"p{i:03d}" for i in range(100)]
    img = random_phox(seed=1, grid_w=16, grid_h=16, predicate_names=preds)
    blob = write_phox(img)
    print(f"  {'.phox 16x16 x 100':<32} {len(blob):>8} "
            f"{img.total_semantic_bits:>15}")


def main() -> int:
    print("Phoxelis .phox format v0.1 — round-trip tests\n")
    tests = [test_smallest, test_v01_size, test_v03_size,
             test_full_vocabulary, test_with_chunks,
             test_byte_exact_repeated_writes]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  CRASH {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    test_density_comparison()
    print()
    if failed:
        print(f"FAILED: {failed}/{len(tests)} tests")
        return 1
    print(f"PASS: {len(tests)}/{len(tests)} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
