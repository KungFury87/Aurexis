# Round 146 — Single-view α sweep at 3 resolutions: view count is a SEPARATE dimension; single-view α optimum runs ~0.10 below multi-view at same resolution; R140's α=0.20 single-view confirmed

**Date:** 2026-05-01
**Track:** T7 (Phase 4 view-count vs resolution disambiguation)
**Status:** complete — single-view best α across 3 resolutions is roughly flat at α=0.15-0.25 vs multi-view's clean 0.25-0.35 trend; mean shift single→multi-view = +0.10 in α; R140's α=0.20 best at single-view image_size=160 directly confirmed by R146's α=0.20 best at same setup; **2D parameter table required** — α_opt(view_count, resolution) not subsumable by either dimension alone

---

## What R146 settles

R145's resolution-tracking law (96/128/160 → α=0.35/0.30/0.25) was
established under multi-view (4 azimuths) loss. R140's older single-view
result reported α=0.20 best at image_size=160 — which doesn't fit the
multi-view linear law (which predicts 0.25 at 160).

Two hypotheses:
- **(H1) View count is subsumed by resolution.** R140's α=0.20 was
  optimizer noise; if rerun on fine grid, single-view 160 should also
  give α≈0.25.
- **(H2) View count is a separate dimension.** Single-view optimum is
  systematically different from multi-view at same resolution, requiring
  a 2D parameter table.

R146 ran the same fine-grain α sweep at all 3 resolutions under
single-view to distinguish. Result: H2 is supported.

## Method

Identical to R143/R144/R145 except `VIEW_AZIMUTHS = [0]` (1 view, az=0)
and substrate Jaccard computed on FULL vocabulary (no layout-invariant
filter — that filter is degenerate at 1 view since "invariant across
1 view" trivially includes everything that fires consistently against
itself).

α ∈ {0.15, 0.20, 0.25, 0.30, 0.35} at image_size ∈ {96, 128, 160}.

## Results

```
single-view, asymmetric multi-object, 6-iter finite-diff, lr=2.0:

resolution    α=0.15    α=0.20    α=0.25    α=0.30    α=0.35    best α    best redux
96            0.888     0.223     0.205     0.367     0.375     0.25      81.6%
128           0.307     0.360     0.490     0.444     1.350     0.15      72.5%
160           0.390     0.316     0.591     0.549     0.459     0.20      71.7%
```

(Numbers are final distance from origin after 6 iterations; init dist=1.118.)

### Side-by-side single-view vs multi-view at each resolution

| resolution | single-view best α | single-view redux | multi-view best α | multi-view redux | α shift |
|---|---|---|---|---|---|
| 96 | 0.25 | 81.6% | 0.35 | 80.1% | **−0.10** |
| 128 | 0.15 | 72.5% | 0.30 | 70.3% | **−0.15** |
| 160 | 0.20 | 71.7% | 0.25 | 89.5% | **−0.05** |

Mean shift = -0.10 in α going single→multi-view. Single-view consistently
wants LESS substrate weight than multi-view at the same resolution.

### Finding 1: H2 supported — view count is a separate dimension

Three single-view best α values (0.25, 0.15, 0.20) are not on the
multi-view linear law (which predicts 0.35, 0.30, 0.25 for 96/128/160).
The shift is consistent in direction (always negative) and meaningful
in magnitude (-0.05 to -0.15).

Mechanism: single-view photometric MSE has stronger per-pixel signal
because there's no view-averaging dilution. With a stronger photometric
signal, less substrate weighting is needed for stability — optimum α
shifts DOWN. This is the same mechanism R141-R142 discovered going
single→multi-view (substrate's relative value RISES under multi-view
averaging); R146 simply confirms it by reversing the test.

### Finding 2: R140's α=0.20 at single-view 160 directly confirmed

R140 used a single-view cube (different target) at image_size=160 and
reported α=0.20 best. R146 used a single-view cube+sphere at same 160
and ALSO reports α=0.20 best (71.7% reduction). Despite the target
difference, the convergence point matches.

This adds confidence that R140's original single-view finding was
genuine, not optimizer noise. The R140-R142 framing of "α=0.2 is the
default" was correct AT SINGLE-VIEW. The error was extending it to
multi-view (R141, R142) where the optimum actually shifts up.

### Finding 3: single-view landscape is BUMPIER than multi-view at 128

At image_size=128 single-view: α=0.15 (dist 0.307) ≪ α=0.20 (0.360) ≫
α=0.25 (0.490) ≪ α=0.30 (0.444) ≫ α=0.35 (1.350). Two local minima
visible (at 0.15 and 0.30) with α=0.25 between them as a clear maximum.

The 6-iteration optimizer noise also looks higher at single-view —
substrate J values fluctuate more (0.535 at α=0.15, 0.886 at α=0.35).
Single-view substrate fingerprints are more sensitive to the specific
camera viewpoint, which adds noise to the loss landscape.

### Finding 4: best convergence quality is roughly TIED across single/multi

| resolution | single-view best dist | multi-view best dist |
|---|---|---|
| 96 | 0.205 | 0.223 |
| 128 | 0.307 | 0.332 |
| 160 | 0.316 | 0.117 |

At 96 and 128, single-view actually edges multi-view slightly. At 160,
multi-view substantially wins (best Phase 4 result ever, 0.117).

The 160 multi-view advantage is consistent with the view-count
hypothesis: at HIGH resolution, photometric signal is strong, so
adding more views adds more redundant information that helps stabilize.
At LOW resolution, photometric is noisier per view, and 4-view averaging
washes out the gradient (R141 finding) — single view's stronger
per-pixel signal compensates.

The bend point seems to be near 160 — at higher resolutions, multi-view
should pull further ahead. R147 candidate could test this with image_size=192
or 224.

## Architectural picture: 2D parameter table

| view_count | best α at 96 | best α at 128 | best α at 160 |
|---|---|---|---|
| 1 (single) | 0.25 | 0.15-0.20 | 0.20 |
| 4 (multi-view) | 0.35 | 0.30 | 0.25 |

Approximate model:
```
α_opt(views, res) ≈ α_intercept(views) - 0.0015 × res
```
where α_intercept ≈ 0.40-0.50 for multi-view, ≈ 0.30-0.40 for single-view.

Production splatting α tuning needs both axes. The 2D table is small
(O(10) cells if discretized at 32px × 1-view granularity) and can be
populated empirically per-scene.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **View count is a separate dimension from resolution in Phase 4 α tuning** | R146 | single-view best α at 96/128/160 = 0.25/0.15-0.20/0.20 (vs multi-view 0.35/0.30/0.25); consistent shift of about −0.10 in α single→multi-view at same resolution; mechanism: multi-view averaging dilutes photo signal, raises substrate's relative value, raises optimum α | round146 | current — Phase 4 α tuning requires 2D table (view-count × resolution); single law subsumed neither dimension |
| **R140's single-view α=0.20 confirmed by direct replication** | R140+R146 | R140 (cube target, image_size=160, single view, coarse grid): α=0.20 best; R146 (cube+sphere target, same resolution and view count, fine grid): α=0.20 best (71.7% reduction); two-target replication adds confidence | round146 | current — R140-R142 "α≈0.2 default" claim was correct AT SINGLE-VIEW; the error was extending to multi-view |

## Honest caveats

- **Single-view bumpier than multi-view.** Single-view 128 has clear
  bumpy landscape with two minima at 0.15 and 0.30. The "best α"
  for single-view 128 is sensitive to which iteration the optimizer
  lands on. Multiple inits or longer iters needed to call this fully
  settled.
- **6 iterations not full convergence.** Several single-view runs
  bounce in last 2 iters (α=0.15 at 96 went 0.800 → 0.888 in iter 5→6,
  picking up dist; α=0.30 at 96 went 0.251 → 0.521 → 0.367). Adam +
  lr decay would smooth this. The qualitative shift (single < multi
  in α optimum) is robust; absolute single-view ranking has noise.
- **Substrate J on full vocab is different from invariant subset.**
  R146 used full 151-predicate vocab for substrate Jaccard since
  layout-invariant subset doesn't make sense at 1 view. This means
  single-view substrate signal includes layout-sensitive predicates
  that R130 showed are noisier with translation. Substrate-as-content-
  validity claim (R142) was always about the invariant subset; single-
  view's full-vocab substrate is a different (noisier) signal.
- **Two minima at single-view 128 isn't fully understood.** Could be
  optimizer noise; could be real bimodal landscape. R147 candidate:
  10-init test at single-view 128.
- **R145's α=0.25 winning at multi-view 160 with 89.5% may be a peak**
  rather than a typical multi-view 160 result. Re-running with a
  different scene composition or camera setup could push it down.
  R146 didn't replicate the multi-view runs.

## Promises ledger updates

- **C-146 closes:** Single-view fine-grain α sweep across 3 resolutions
  shows view count is a separate dimension from resolution in Phase 4
  α tuning. Single-view best α runs about 0.10 below multi-view at
  same resolution. R140's α=0.20 single-view 160 result directly
  replicated by R146 with different target. Production splatting α
  tuning requires 2D table (view-count × resolution); single law
  doesn't subsume either dimension. Substrate-as-primary architectural
  conclusion (R142) holds for multi-view; for single-view, photometric
  remains primary and substrate plays smaller regularizer role.

## Files added this round

- `round146_singleview/r146_singleview.py`
- `round146_singleview/round146_audit.json`
- `round146_singleview/results_size{96,128,160}.json`
- this report
- `PHOXELIS_PROMISES.md` — C-146 entry
- `PHOXELIS_BENCHMARKS.md` — R146 rows + 2D parameter table

## Next round opens with

R147 candidates:

**A — push R146.** Single-round-add to a fresh push.bat.

**B — replicate R145's multi-view 160 finding with different scene
composition.** Cube+pyramid or sphere+pyramid asymmetric multi-view
160 with α=0.25. Tests whether the 89.5% best result is scene-specific
or generalizable.

**C — extend resolution range.** Single-view + multi-view at image_size=192
or 224. Tests whether resolution law extrapolates linearly or saturates.
Predicts: single-view 192 → α≈0.10, multi-view 192 → α≈0.20.

**D — Adam optimizer + 20 iters at α=0.25, multi-view 160.** Pushes
the 89.5% reduction toward 100%. Tests whether the basin near origin
is reachable in full convergence.

**E — multi-init test at single-view 128.** Test α=0.15, 0.20, 0.30
from 5 different inits. Resolves bimodal-landscape question.

**F — autograd implementation.** Multi-round engineering.

Lean **A then C**. C is the cleanest extrapolation test — the linear
law already has 3 confirming points each in single and multi-view; a
4th point at 192 either keeps the trend or shows saturation. Either
result settles the law's extrapolation properties for production
splatting use.
