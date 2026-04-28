# Round 25 — Matte control falsifies `has_local_polarization_signal`

**Date:** 2026-04-28
**Sessions:**
- Round 24 positive: `AUREXIS_3e226dcc_polarization_pair.aurex-session.zip`
  (drinking glass + Nintendo Switch 2 LCD)
- Round 25 control: same sessionId zip uploaded as `(1)`
  (matte non-polarizing target — blanket / fabric)

Both v3.0.1 build, 60 frames, 30/30 axis split, ~270–290 lux indoor.

## TL;DR

The new predicate from Round 24 fired **harder on the matte control
than on the actual polarization scene**. Predicate retired.
Capture protocol cannot deliver the geometric precision the predicate
needs on handheld data.

## Numbers (luma 0–1, after 5×5 box smoothing)

| metric | glass + Switch | matte control |
|---|---|---|
| `cap0_mean` | 0.412 | 0.580 |
| `cap90_mean` | 0.424 | 0.507 |
| `rotated_pair_anisotropy` (global, OLD) | 0.013 | 0.066 |
| `aligned_local_polarization_max` p95 (NEW) | 0.260 | **0.427** |
| `aligned_local_polarization_max` p99 | 0.341 | 0.529 |
| frac of pixels with aniso > 0.15 | 27.7% | 35.4% |
| frac of pixels with aniso > 0.25 | 5.8% | **22.2%** |

The control scene shows 4× more pixels above the 0.25 anisotropy
band than the polarized scene. That's a definitive falsification.

## I tried to rescue the predicate via registration

FFT phase-correlation between `cap_axis_0` and the rotated
`cap_axis_90` to estimate an integer (dy, dx) shift, then nudge
the rotated image into alignment before measuring anisotropy.

| | glass+Switch | control |
|---|---|---|
| recovered shift | dy=+0, dx=+18 px | dy=−51, dx=+22 px |
| peak SNR of the correlation | 2.7 | 1.9 |
| p95 anisotropy AFTER registration | 0.191 | 0.343 |

Registration brought both numbers down a bit, but the **control
still fires almost twice as hard** as the polarized scene. Worse,
the SNR of the recovered shifts (1.9 and 2.7) is too low to trust:
phase correlation is finding a peak that's barely distinguishable
from the noise floor of a non-rigid transform. Handheld rotation
isn't a clean translation — it's rotation around a point that
isn't the lens, plus tilt, plus a few cm of translation, plus
non-rigid hand drift over the ~30 s gap between bursts.

## What the predicate is actually measuring

Per-pixel anisotropy after a coarse rigid transform = **the residual
from imperfect handheld geometric registration**, not polarization.

A matte target with high spatial frequency (blanket fibres) has
*more* per-pixel detail to mis-register, so it produces *more*
apparent anisotropy under handheld jitter than a scene whose
polarized signal lives in a relatively flat region (the LCD
backlight is structurally uniform compared to fabric).

## Methodology lesson logged

Per-pixel-difference predicates over physically-rotated handheld
captures cannot be trusted without sub-pixel alignment, and
sub-pixel alignment of a 90°-rotated handheld image pair is not
achievable with FFT phase correlation alone. To make a
polarization predicate work we need either:

1. **Tripod / fixed mount.** Phone body translation goes to zero;
   only the polarization filter on the lens is rotated. This is
   the standard polarimetry setup.
2. **Rotating polarizer accessory.** A clip-on linear polarizer in
   front of the lens, rotated by hand 90° between bursts, with
   the phone held steady. Same effect — only the polarization
   axis changes, not the camera pose.
3. **Single-shot polarization-aware sensor** (Sony IMX250MZR /
   IMX250MYR or similar). Out of scope for current hardware.

Without one of those, the polarization protocol the harness ships
generates a session that is **structurally valid** (manifest is
clean, axis labels are correct, the bridge populates `cap_axis_0`
and `cap_axis_90`) but whose payload contains too much geometric
noise for any per-pixel comparison to extract polarization signal.

## Changes shipped in this round

* `data/vision/vocab.aurex` — `has_local_polarization_signal`
  commented out with full retirement note explaining why. Vocabulary
  drops from 100 → 99 predicates.
* `aurexis_workbench/vision_ops.py` — `_aligned_local_polarization_max`
  docstring rewritten to document its limitations. Operator kept
  available because the same alignment + smoothing primitive is
  useful for any *fixed-mount* polarization predicate added later.
* `cli_vision` keeps the auto-bump of `max_frames` for
  polarization-pair sessions — that's an unambiguous improvement
  even if the polarization predicates don't work yet.

## What is *still* true after this round

* The harness can capture two-axis sessions correctly (Round 23
  v3.0.1 fix is solid — 30/30 split, axis labels, schema 1.2).
* The vision bridge can split a session into `cap_axis_0` /
  `cap_axis_90` from the manifest (Round 24 cli_vision fix).
* The methodology lesson is now baked into the vocabulary file
  itself, so the next time someone reaches for a per-pixel
  polarization predicate they'll see why this approach failed.

## Vocabulary state after Round 25

* **99 predicates** (back to where Round 22 left off)
* **92 operators** (kept the alignment primitive)
* `has_polarization_signal` (global) is the only active polarization
  predicate. It's not very sensitive but it doesn't lie about what
  it measures.
