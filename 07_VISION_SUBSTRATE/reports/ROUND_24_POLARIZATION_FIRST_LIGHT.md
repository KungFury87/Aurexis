# Round 24 — Polarization first-light + local-aware predicate

**Date:** 2026-04-28
**Session:** `AUREXIS_3e226dcc_polarization_pair.aurex-session.zip`
**Scene:** drinking glass placed in front of a Nintendo Switch 2 screen
**Capture build:** harness v3.0.1 (the portrait-lock fix from Round 23)
**Lighting:** indoor, ~270 lux

## Capture went clean

Manifest confirms the v3.0.1 fix did its job:

```
schemaVersion : aurex-session-1.2
protocolId    : polarization_pair
app_version   : 3.0.1
targetCount   : 60
frameCount    : 60
axisLabels    : {'0deg': 30, '90deg': 30}
axis change at frame 31  (gap of ~35 s for the user to rotate)
```

Both bursts captured into a single session. The activity survived
the 90° rotation, which was the whole point of the round-23 hotfix.

## The vision bridge had a quiet bug

`vision_bridge.load_session_bundle` defaults to `max_frames=10`.
For a 60-frame polarization-pair session, that meant only the first
10 frames (all axis-0) were loaded — `cap_axis_90` never got
populated, and `has_polarization_signal` returned **BLOCKED**.

Fix in `cli_vision.py`: peek at the manifest before loading, and
if `protocolId == "polarization_pair"` bump `max_frames` to the
full frame count for that session. No effect on other protocols.

After that, `cap_axis_0` and `cap_axis_90` both populate and the
predicate evaluates.

## The original predicate was too coarse

```
predicate has_polarization_signal
  body  gt(abs_s(rotated_pair_anisotropy(cap_axis_0, cap_axis_90)), 0.10)
```

`rotated_pair_anisotropy` is `(I0_mean - I90_mean) / (I0_mean + I90_mean)`
— a single global scalar over the whole image. On the Switch+glass
scene that came out to **0.013**, way under the 0.10 threshold.
Verdict False.

But the per-pixel difference between the two captures was real:

| metric | value |
|---|---|
| mean absolute pixel diff | 0.109 (luma 0–1) |
| fraction of pixels with diff > 0.10 | 47% |
| fraction with diff > 0.20 | 15% |

Polarization from an LCD or from a Brewster-angle reflection is a
**localized** signal. A scene-wide mean averages it away.

There is also an alignment problem: when the phone rotates 90°,
the world inside the captured frame rotates 90° too (the lens body
turned, so the image content turned). Comparing `cap_axis_0[r,c]`
to `cap_axis_90[r,c]` is comparing different parts of the scene.

## New operator + predicate

`vision_ops._aligned_local_polarization_max(image_a, image_b)`:

1. Rotate `image_b` by 90° clockwise (`np.rot90(b, k=-1)`) to put
   the world content back in `image_a`'s pixel frame.
2. Crop both to a common central square.
3. Smooth each with a 5×5 box filter (`scipy.ndimage.uniform_filter`)
   to suppress shot noise.
4. Compute per-pixel anisotropy `|A - B| / (A + B + ε)`.
5. Return the **95th percentile** — captures the "is there a strong
   anisotropic region anywhere in the frame" signal without being
   fooled by single hot pixels.

```
predicate has_local_polarization_signal
  expects cap_axis_0:image, cap_axis_90:image
  returns bool
  intent  detect_local_polarization_after_alignment
  body    gt(aligned_local_polarization_max(cap_axis_0, cap_axis_90), 0.20)
```

## Result on the Switch + glass scene

Direct numerical run (cropped to 204×204 luma after resize):

| metric | value | threshold | verdict |
|---|---|---|---|
| `rotated_pair_anisotropy` (old, global) | 0.013 | 0.10 | False |
| `aligned_local_polarization_max` p95 (new) | **0.260** | 0.20 | **True** |
| same, p99 | 0.341 | — | — |
| same, max single pixel | 0.508 | — | — |
| frac of pixels with aniso > 0.15 | 27.7% | — | — |
| frac of pixels with aniso > 0.25 | 5.8% | — | — |

The Switch's LCD emits linearly polarized light through its
backlight + polarizer stack, and the glass surface produces
specular reflections that polarize at oblique angles. After
rotation alignment, ~28% of the image shows >15% axis-dependent
anisotropy. The new predicate catches that. The old one missed it.

## Vocabulary state after Round 24

* 100 predicates (was 99) — added `has_local_polarization_signal`.
  `has_polarization_signal` (the global one) is kept as a less
  sensitive but still defensible scalar.
* 92 operators (was 91) — added `aligned_local_polarization_max`.
* `cli_vision` auto-bumps max-frames for polarization-pair sessions
  so users don't need `--max-frames 60`.

## What this proves and doesn't prove

**Proves:**
- The harness can produce two-axis bursts the language can compare.
- The language now has a polarization predicate that fires on a
  real polarized scene (LCD + glass) without firing on the global
  brightness average.
- The full pipeline — phone capture → axis labels → bridge →
  alignment → operator → predicate → True — runs end-to-end.

**Doesn't prove:**
- That this predicate doesn't false-positive on non-polarized
  scenes with handshake-induced shifts. We need a control session
  on a matte non-polarized surface (paper, fabric, painted wall)
  to check the false-positive floor. That's Round 25.
- That polarization angle is recovered, only that anisotropy is
  detected. Recovering the polarization vector would need at least
  three axes (0°, 45°, 90°) — out of scope for now.
