# Round 52 — density sweep on the real-CDN pipeline

**Date:** 2026-04-29
**Track:** T2 (Phoxelis as Medium)
**Status:** complete — 128-byte byte-exact recovery at 32×32 grid through real public CDN; ceiling not yet found

---

## What this round opened on

R51 demonstrated the autonomy pattern at the floor of the encoder's density (8 bytes / 8×8 grid). Useful as a proof-of-pattern but not informative about the encoder's actual limits when running through real public services. R52 sweeps grid sizes upward to find where things start to fail.

## Pipeline

Same as R51:

```
encode_bytes(random N-byte payload, grid=g, img=img_size)
  -> save PNG locally
  -> POST to litterbox.catbox.moe (anonymous, 1-hour TTL)
  -> get public URL
  -> for each transform:
       GET images.weserv.nl/?url=...&output=jpg&q=...
       Pillow.open(response)
       (resize back to encoder dimensions if shrunk)
       decode_bytes(arr, grid_w=g, grid_h=g)
       compare to original payload byte-for-byte
```

## Results

```
  grid       payload    transform    http  fmt   size      bytes  decode
  8x8-256    8          identity-png 200   PNG   256x256    1922  8/8 OK
  8x8-256    8          jpeg-q85     200   JPEG  256x256     840  8/8 OK
  8x8-256    8          jpeg-q50     200   JPEG  256x256     803  8/8 OK
  8x8-256    8          webp-q90     200   WEBP  256x256     530  8/8 OK
  16x16-512  32         identity-png 200   PNG   512x512    7552  32/32 OK
  16x16-512  32         jpeg-q85     200   JPEG  512x512    2683  32/32 OK
  16x16-512  32         jpeg-q50     200   JPEG  512x512    2507  32/32 OK
  16x16-512  32         webp-q90     200   WEBP  512x512    2336  32/32 OK
  32x32-1024 128        identity-png 200   PNG   1024x1024 28448  128/128 OK
  32x32-1024 128        jpeg-q85     200   JPEG  1024x1024  9666  128/128 OK
  32x32-1024 128        jpeg-q50     200   JPEG  1024x1024  9014  128/128 OK
  32x32-1024 128        webp-q90     200   WEBP  1024x1024  7982  128/128 OK
```

12/12 byte-exact. Ceiling not yet reached at 32×32.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Real public-CDN round-trip survival, density-swept | R52 | **128 bytes byte-exact at 32×32 grid** through PNG/JPEG q=85/JPEG q=50/WebP q=90 | live network round-trip via litter.catbox.moe + images.weserv.nl | current — 16× R51 density; ceiling not yet found |

## What this round does NOT yet show

The original 4-grid × 6-transform sweep (8→48 grid, including JPEG q=95 and q=75) timed out the 45s sandbox budget. R52 ran the trimmed 3-grid × 4-transform sweep that fit. The actual cliff — the smallest grid at which any transform first fails — is somewhere ≥ 48×48 (which would carry ≥ 288 bytes at 32 px/cell). That measurement remains future work.

The current encoder is also still R36 v0.2 (red/green binary, 1 bit/cell). The R39 8-hue stack (8 bits/cell) is the harder test that hasn't yet been put through the real-CDN pipeline.

## Promises ledger updates

- **C-52** opens (this round): density-swept real-CDN round-trip with 12/12 byte-exact recovery up to 128 B at 32×32 grid.
- **P-13** opens (this round): find the real-CDN density ceiling — sweep grid sizes 48×48 → 96×96, find the cliff, report. Probably needs a checkpointing harness that splits across multiple bash calls.

## Files added this round

- `round52_density_sweep/round52_density_sweep.py` — sweep script
- `round52_density_sweep/round52_results.json` — full data
- `round52_density_sweep/transit_pngs/` — every transformed image, saved
- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/reports/ROUND_52_DENSITY_SWEEP_REAL_CDN.md` — this file

## Next round opens with

`python phoxelis_audit.py`. Three (probably four) STALE pending. Strongest single needle-mover candidates:
- **R53 — push to find the actual ceiling**: extend R52 with checkpointing across bash calls; sweep 48×48 → 96×96. Real-CDN density-cliff number.
- **R53 — switch encoder to R39 8-hue density and re-run**: this is the harder test that would settle whether the categorical-first claim generalises to the project's actual maximum density.
- **R53 — pull a real phone-camera corpus from Pexels / Wikimedia and run the IR audit at scale**: continues the autonomy-from-Vincent pattern, makes progress on P-01 (10k+ image IR audit).
