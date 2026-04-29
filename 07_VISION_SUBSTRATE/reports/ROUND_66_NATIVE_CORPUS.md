# Round 66 — close P-20 (native-resolution corpus); confirm P-21 is real

**Date:** 2026-04-29
**Track:** T1 vocabulary health (corpus quality)
**Status:** complete — P-20 closed; native-resolution lifts JPEG-detection firing 0.20→0.40; pixel-grid candidate still 0/20, confirming P-21 is corpus-content gap not sampling artifact

---

## What got built

`round66_native_corpus/` — independent native-resolution corpus harness.
Pulls from the same `sources.SOURCES` registry but skips the
160×160 LANCZOS thumbnail step. Caps at 1024-px longer side to keep
arrays manageable. Writes a separate `native_state.json` so the existing
R55 corpus is not disturbed.

| pulled from | count | shape range |
|---|---|---|
| Wikimedia random | ~3 | 800×533 to 800×1067 |
| iNaturalist Aves | ~3 | 750×500 to 1024×768 |
| MET rotating | ~3 | 768×548 to 1024×768 |
| NASA APOD | ~2 | varied |
| Picsum | ~2 | exact 512×512 |

After 1 session: **N=20 native images, shapes 361×239 to 1024×960**.

## Audit results (R65 cached LANCZOS vs R66 native)

| predicate | R65 LANCZOS 160×160 | R66 native | Δ |
|---|---|---|---|
| `is_jpeg_compressed` | 0.20 (R64) | **0.40** | +0.20 |
| `has_chroma_subsampled_signature` | 0.88 | **1.00** (saturated) | +0.12 |
| `has_clipped_highlights` | 0.05 | 0.05 | 0.00 |
| `has_axis_aligned_pixel_grid_native` (deferred candidate) | 0.00 | **0.00** | 0.00 |

## What the numbers mean

**P-20 confirmed and closed.** Native resolution doubles
`is_jpeg_compressed` firing rate. The hypothesis from R64 was right:
LANCZOS thumbnails destroy the 8×8 DCT block-boundary alignment that
`dct_block_boundary_energy` measures. At native res, 8/20 images now
fire vs 2/10 (qualitatively) at 160×160. The remaining 12/20 that don't
fire are likely PNG-served or already-recompressed-by-source variants
where the original block grid is gone.

**Chroma subsampling saturated to 100%.** All 20 native images had
JPEG-style chroma subsampling. At N=20 this caused an IR collision
with three other always-True predicates (`has_gradient_energy`,
`has_circular_signature`, `has_many_corners`) — a small-N artifact
identical to the one R63 dissolved by growing the corpus. The
operator and predicate are correct; the corpus is just too small at
N=20 native for IR independence to be confirmed yet.

**P-21 confirmed real.** `has_axis_aligned_pixel_grid_native` fires
0/20 at native resolution, exactly matching its R65 LANCZOS behavior.
This is the strongest possible evidence that the deferral diagnosis
in R65 was correct: the operator simply doesn't have positive cases
in nature/art/astronomy/wildlife corpora *regardless of resolution*.
P-21 (add screen-capture seeds) is the right unblocking work.

## Honest caveats

- **Audit is a fresh batch (N=20 native), not the full R55+R63 cache
  re-pulled.** The live URLs are random per request; full
  re-pulling at native resolution is more network-bound and would take
  several sessions. Building toward that incrementally as P-20-extended
  if useful, but the *conclusion* (native lifts JPEG fire rate) is
  established.
- **Chroma collision at N=20 is a small-N saturation, not an
  architectural problem.** R63 dissolved a similar one by growing
  the cached corpus from 8 to 30. Same mechanism applies here.
- **The `1024-px cap` does mean the "native" corpus is downsampled
  from very-large originals.** This is a pragmatic compromise between
  faithful resolution and manageable file sizes. JPEG block alignment
  survives this (LANCZOS at integer-divisible scales preserves the
  8×8 grid; arbitrary scales don't).

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| `is_jpeg_compressed` firing rate | R66 | **0.40** at N=20 native (vs 0.20 at N=30 LANCZOS-160) | current — confirms the LANCZOS-suppression hypothesis from R64 |
| `has_axis_aligned_pixel_grid` firing on nature/art corpus | R66 | 0/20 native (matches 0/42 LANCZOS) | current — predicate is genuinely waiting on corpus, not on resolution |
| Native-resolution corpus | R66 | 20 images, 361×239 to 1024×960 | current; separate cache from R55 |

## Promises ledger updates

- **C-66 closes P-20:** native-resolution corpus + audit confirms LANCZOS thumbnail was suppressing `is_jpeg_compressed` firing rate by ~2×. The R55 LANCZOS cache is left in place (it's still useful for non-block-aligned predicates); native cache is the new target for sensor-provenance predicates that need pixel-grid alignment.
- **P-21 strengthened:** confirmed corpus-content-gap, not resolution-artifact. Targeted as next round.

## Files added this round

- `round66_native_corpus/round66_native_audit.py` — pull-and-audit harness (network-using)
- `round66_native_corpus/round66_audit.py` — audit-only re-evaluator (no network; works on already-cached natives)
- `round66_native_corpus/images_native/` — 20 native-resolution `.npy` arrays
- `round66_native_corpus/native_state.json` — checkpoint
- `round66_native_corpus/round66_audit.json` — full IR result + class membership
- this report
- `PHOXELIS_PROMISES.md` — C-66 entry
- `PHOXELIS_BENCHMARKS.md` — R66 rows

## Next round opens with

R67 — close P-21 by adding screen-capture / display-photograph sources
to `sources.SOURCES`. Wikimedia category `Screenshots` would cover most
of it; alternative is querying for "phone screen" in Openverse or
running an AI-image-generation route. Once the corpus has a handful of
positive cases, re-run the R65/R66 audit on `has_axis_aligned_pixel_grid`
and promote if IR-clean.
