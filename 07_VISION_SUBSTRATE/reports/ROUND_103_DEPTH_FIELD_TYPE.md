# Round 103 — depth field type + 3 depth-aware predicates IR-clean first light

**Date:** 2026-05-01
**Track:** T8 — phoxel-native capture (depth axis)
**Status:** complete — `depth` dtype operational; 3/3 authored depth predicates IR-clean; depth contributes orthogonal discrimination to substrate fingerprint

---

## What this round adds

The substrate's typed-field interface gains a new dtype: `depth`. This is
the first time the substrate has a non-photometric input modality. The
load-bearing operator registry, predicate language, and runtime needed
exactly **two** things to support it:

1. `"depth"` added to `VALID_DTYPES` in `aurexis_workbench/fields.py`.
2. Three new operators registered with input type `("depth",)` /
   `("depth", "scalar")` and output `"scalar"`.

Everything else — the DSL parser, type checker, runtime, predicate
authoring, and Jaccard machinery — works unchanged. That's the test of
the typed-field interface: a new modality enters as a new dtype, and
predicates compose across modalities (depth + RGB) at the fingerprint
level.

## Method

5 synthetic scenes designed to exercise different depth structures,
each paired with a hand-authored depth map:

| scene | RGB content | depth structure |
|---|---|---|
| `indoor_close` | small subject blob on light background | subject at 0.2, background at 0.9 |
| `landscape` | sky→mountain→foreground | smooth gradient 1.0 (top) → 0.5 (bottom) |
| `flat_wall` | textured uniform color | uniform 0.6 + tiny sensor noise |
| `object_table` | dark object on mid table | object at 0.25, table at 0.7 |
| `layered` | sky + building + tree + ground | 4 distinct depth layers (0.15, 0.3, 0.5, 0.95) |

3 depth operators registered:

```python
mean_depth(depth) -> scalar             # mean depth value
depth_variance_score(depth) -> scalar   # std/mean (scale-free spread)
foreground_fraction(depth, scalar) -> scalar  # fraction of pixels closer than threshold
```

3 depth predicates authored in surface DSL:

```
predicate has_shallow_depth_signal
  expects depth_field:depth
  body    gt(depth_variance_score(depth_field), 0.4)

predicate has_dominant_foreground
  expects depth_field:depth, foreground_threshold:scalar
  body    gt(foreground_fraction(depth_field, foreground_threshold), 0.25)

predicate has_far_field_dominance
  expects depth_field:depth
  body    gt(mean_depth(depth_field), 0.7)
```

## Results — 3/3 IR-clean discrimination

```
predicate                   fires_on                    n_fires   IR-clean
has_shallow_depth_signal    [layered]                   1/5       ✓
has_dominant_foreground     [layered]                   1/5       ✓
has_far_field_dominance     [indoor_close, landscape]   2/5       ✓
```

Each predicate fires on a *strict subset* of the corpus (no always-True,
no always-False). All three are IR-clean at N=5.

**Sanity check on physics:**

- `has_shallow_depth_signal` (var_score > 0.4) fires on `layered`
  because `layered` has 4 distinct depth layers (var_score=0.48). It
  doesn't fire on `indoor_close` (var_score=0.25) because the subject
  is only ~10% of pixels — most pixels share one depth.
- `has_dominant_foreground` (>25% pixels closer than 0.4) fires on
  `layered` (29.3% foreground from tree+ground). It doesn't fire on
  `object_table` (15.6% — close, but below threshold). Threshold is
  in the right neighborhood; calibration is reasonable.
- `has_far_field_dominance` (mean > 0.7) fires on `indoor_close`
  (mean=0.83) and `landscape` (mean=0.75). Both have most of their
  pixels at far depths.

The predicates are doing what their names say.

## Composition with the existing 146-predicate vocabulary

```
metric                           value
n_base_predicates                146
n_depth_predicates               3
n_predicates_total               149

mean pairwise Jaccard (146 only) 0.354
mean pairwise Jaccard (149)      0.344
delta_J mean                    -0.010
pairs changed by depth           9 / 10
```

Adding the 3 depth predicates **changes 9 of 10** pairwise Jaccards in
the 5-scene corpus. The mean Jaccard drops slightly (0.354 → 0.344)
which means the new predicates are adding discrimination signal, not
redundant signal — pairs that used to look more similar now look
slightly less similar because the depth axis differentiates them.

This is the right shape for a useful new predicate family. Compare
to R74-style coverage analysis: predicates that produce delta J ≈ 0
across the corpus are redundant; predicates that produce delta J ≠ 0
are adding to the substrate's fingerprint geometry.

## Why this matters for T8

The substrate's "phoxel-native capture" promise has been:

- R101 — sensor pipeline (RAW vs JPEG) → cleared via predicate flip
- R102 — exposure brackets → cleared via 2.42× Jaccard ratio
- **R103 — depth modality → cleared via dtype + IR-clean predicates**

Three different signal modalities now compose through the same typed
predicate language. The substrate is no longer "RGB in, predicates
out"; it's "any typed field bundle, predicates out."

The next axes (R104 hyperspectral 31-band, R105 multi-view) should drop
in by the same pattern: add dtype, register operators, author predicates,
audit IR-clean.

## Honest caveats

- **N=5 scenes is small.** Each predicate fires on 1-2 scenes; with
  N=20+ we'd see whether they hold IR-clean at scale or collapse into
  the existing equivalence classes (R63 small-N collapse hypothesis).
- **Depth maps are hand-authored.** Real LiDAR/structured-light depth
  has measurement noise, depth-edge halos, and missing-data regions
  that synthetic depth doesn't have. R103 establishes the dtype works;
  it doesn't claim production-grade depth-predicate behavior.
- **The 3 predicates are not yet promoted to vocab.aurex.** R103 is
  experimental; promotion happens after a corpus-scale audit (R103
  follow-up or part of T1 vocabulary-health track).
- **Operators use simple aggregate statistics** (mean, std/mean,
  fraction-below-threshold). Real depth analysis can be much richer
  (gradient histograms, surface normal extraction, depth-edge
  detection). R103 is the first-light bar, not the ceiling.

## Compositional cross-modality is now testable

A specific T8 test that wasn't possible before R103:

```
predicate has_close_subject_against_far_background
  expects depth_field:depth, scene:image
  returns bool
  body    AND(
            has_shallow_depth_signal(depth_field),
            has_centered_subject(scene)
          )
```

This is a depth-and-photometric composition. The substrate now has the
machinery to author and evaluate such predicates. R104+ can use this
to test whether multi-modal predicates produce richer fingerprints than
single-modality predicates.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Depth dtype + 3 depth predicates | R103 | 3/3 IR-clean at N=5; 9/10 pairwise J changed | current — `depth` modality operational |
| Cross-modality predicate composition | R103 | substrate now supports `image` + `depth` + `color_image` + `image_stack` co-evaluation in one bundle | current — typed-field interface validated as multi-modal |

## Promises ledger updates

- **C-103 closes:** depth dtype operational; 3 IR-clean depth predicates
  authored. T8 phoxel-native capture track now active across 3 axes
  (sensor pipeline R101, exposure R102, depth R103).

## Files added this round

- `round103_depth/round103_audit.py`
- `round103_depth/round103_audit.json`
- `round103_depth/images/` — 5 RGB scenes + 5 paired depth maps
- this report
- `PHOXELIS_PROMISES.md` — C-103 entry
- `PHOXELIS_BENCHMARKS.md` — R103 row

The depth predicates are NOT yet promoted to `vocab.aurex` — held
experimental until corpus-scale audit.

## Next round opens with

R104 candidate: hyperspectral. Add `hyperspectral` dtype (a 3D
HxWxN_bands tensor where N_bands=31 for CAVE), register 2-3
hyperspectral operators (band centroid, band variance, narrow-peak
detection), author 2-3 predicates, validate IR-clean. Same pattern
as R103.

Alternative R104: instead of pulling actual hyperspectral data,
synthesize 31-band test scenes (each band = different spectral
projection of a known scene) and test whether the substrate can
discriminate things RGB cannot. This sidesteps the CAVE-bot-blocking
question and produces a controlled A/B.
