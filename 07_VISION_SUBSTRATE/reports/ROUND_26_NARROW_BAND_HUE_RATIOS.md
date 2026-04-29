# Round 26 — Narrow-band hue ratios for material detection

**Date:** 2026-04-28
**Direction picked:** the recommendation from the end of Round 25 — lean
into predicates handheld capture genuinely supports. Adds three new
RGB-ratio operators and four new predicates that name materials and
light conditions the older hue-bucket vocabulary could only describe
abstractly.

## What this round adds

### Three operators (`vision_ops.py`)

1. **`vari_score(color_image)`** — Visible Atmospherically Resistant
   Index, the visible-band stand-in for NDVI when no near-infrared
   channel is available.
   ```
   VARI = (G - R) / (G + R - B)
   ```
   Vegetation pushes positive (chlorophyll reflects green, absorbs
   red/blue). Sky / water / pavement / skin land near or below zero.

2. **`red_blue_ratio(color_image)`** — `mean(R) / mean(B)`. Pure ratio,
   not a weighted sum, so it isolates color *temperature* (warm-vs-cool
   light source) from chroma intensity. Distinct from `rgb_warmth_score`,
   which mixes the green channel and a clamp.

3. **`skin_tone_fraction(color_image)`** — Fraction of pixels in the
   standard YCbCr skin-chromaticity window: `Cr ∈ [0.53, 0.70]`,
   `Cb ∈ [0.42, 0.55]`, plus a luma floor `Y > 0.20` so deep-shadow
   pixels don't trigger.

### Four predicates (`vocab.aurex`)

```
predicate has_vegetation_signature        → vari_score > 0.05
predicate has_skin_tone_signature         → skin_tone_fraction > 0.25
predicate has_warm_color_temperature      → red_blue_ratio > 1.10
predicate has_cool_color_temperature      → red_blue_ratio < 0.95
```

## Threshold tuning was empirical, not theoretical

First pass on 13 real phone photos (all I had handy as a control
corpus) revealed two saturating predicates:

| predicate | initial threshold | initial rate | retuned threshold | final rate |
|---|---|---|---|---|
| `has_skin_tone_signature` | 0.05 | **13 / 13** (saturated) | 0.25 | 5 / 13 |
| `has_warm_color_temperature` | 1.30 | 0 / 13 | 1.10 | 0 / 13 |
| `has_cool_color_temperature` | 0.80 | 0 / 13 | 0.95 | 4 / 13 |
| `has_vegetation_signature` | 0.05 | 4 / 13 | 0.05 (kept) | 4 / 13 |

The skin window is famously permissive on indoor scenes — wood,
beige walls, lamp light, skin-tone fabrics all hit the same YCbCr
chromaticity. Bumping the area-fraction threshold from 5% to 25%
tightens it from "any pixel matches" to "a meaningful patch of skin
chromaticity is present." Still not a face detector — that needs
spatial/connectivity constraints — but it's a defensible probe.

R/B ratio for natural indoor light clusters tightly around 1.0
(σ ≈ 0.06 on this corpus). The 1.30/0.80 thresholds I picked
on intuition were ~5 σ — fired on nothing real. 1.10/0.95 are
~1.5 σ each, which fires when the scene is meaningfully off neutral.

## Per-photo results on the 13-photo corpus

```
photo                    VARI    R/B   skin%    fired
20260415_195321.jpg    -0.063   1.05   17.8%    -
20260416_071900.jpg    +0.088   0.93   13.1%    VEG COOL
20260416_071906.jpg    +0.085   0.93   12.4%    VEG COOL
20260416_071913.jpg    -0.029   1.04   27.6%    SKIN
20260416_071915.jpg    -0.036   1.07   26.2%    SKIN
20260416_073955.jpg    -0.035   1.06   30.1%    SKIN
20260416_074005.jpg    +0.087   0.94   12.9%    VEG COOL
20260416_134642.jpg    -0.036   1.01   11.2%    -
20260416_141505.jpg    -0.060   1.04   15.9%    -
20260416_141509.jpg    -0.014   1.01   11.4%    -
20260416_143930.jpg    -0.062   1.08   33.2%    SKIN
20260416_143933.jpg    -0.056   1.08   33.8%    SKIN
20260416_143941.jpg    +0.064   0.94   12.3%    VEG COOL

Final firing rates: VEG 4/13   SKIN 5/13   WARM 0/13   COOL 4/13
```

## VEG and COOL co-fire on the same shots

That looks like redundancy on this corpus, but it isn't. Morning
outdoor shots are simultaneously (a) green-pixel-dominant from
vegetation reflectance and (b) blue-tinted from cool morning sky.
The two predicates would diverge on:

- A green LED screen (VEG fires, COOL doesn't — warm illuminator
  on a green emitter)
- An overcast empty sky shot of pavement (COOL fires, VEG doesn't)
- A picture of grass at sunset (VEG fires, WARM fires, COOL doesn't)

The IR run will pick that up over a larger corpus.

## `WARM` fires 0/13 honestly

This corpus genuinely lacks warm-tinted scenes — no sunsets, no
tungsten-lit interiors, no candlelight. The predicate is operational
(threshold 1.10 on R/B is reachable; VARI's 4/13 hit rate using
the same RGB pipeline confirms the operators read pixels correctly).
A future pass over a corpus with sunset shots would fire it.

Documented as a known-empty firing rate rather than a dead predicate.
If a future IR run shows it permanently at 0% across multiple corpora,
we'd retire it. One pass isn't enough evidence either way.

## Vocabulary state after Round 26

* **103 predicates** (was 99 after Round 25 retirement)
* **95 operators** (was 92)
* All four new predicates have positive supporting evidence except
  `has_warm_color_temperature`, which is operational but corpus-blind.

## What wasn't done in this round (and why)

- **No new synthetic corpus scenes.** The four new predicates fire on
  real photos already (3/4 of them). Adding synthetic stimuli for
  `has_warm_color_temperature` would be cheap, but synthetic-only
  evidence is what got the polarization predicate retired in
  Round 25 — adding more would push the vocabulary in the wrong
  direction. Better to wait for a real warm-tinted scene.
- **No water-detection predicate.** Considered, but RGB-only water
  detection without spatial constraints (top of frame, low texture,
  blue-dominant) gets confused with sky in any handheld scene that
  contains a horizon. That's a Round-27 candidate where it can be
  composed with the existing `has_horizon_at_*_third` predicates.
- **No IR re-run on the larger corpus.** The Workbench/Core mount
  has been showing stale views of the source files in this session,
  which makes a full IR run unreliable from the analysis side. The
  push.bat regenerates the roadmap on Windows, where the file view
  is correct. A separate IR pass after push will show the EQ-class
  / always-False numbers for the new predicates.
