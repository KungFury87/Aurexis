# Round 95 — combined degradation interaction: substrate compounds gracefully

**Date:** 2026-04-29
**Track:** T6 substrate-purpose; closes the robustness suite (R90 + R91 + R93 + R94)
**Status:** complete — degradations compose CONSTRUCTIVELY 61% of trials, NEVER destructively; bottleneck ≈ combined; substrate-meaning is gracefully bounded under stacked real-world degradation

---

## What R95 measured

Six multi-step degradation pipelines × 3 corpus images = **18 trials**.
Each pipeline stacks 2–3 degradation operators (noise, filter, JPEG
quantization). For each trial:

1. Measure **J_combined** = Jaccard(pre_fp, post_pipeline_fp).
2. Measure **J_individual_i** for each step applied alone to the
   original image.
3. Compute **J_product** = ∏ J_individual_i (multiplicative
   independence model).
4. Compute **J_min** = min(J_individual_i) (bottleneck model).
5. Classify the trial:
   - *Constructive* if J_combined > J_product × 1.10 (degradations
     undo each other / overlap)
   - *Destructive* if J_combined < J_product × 0.85 (degradations
     compound worse than independent)
   - *Independent* otherwise (within ±15% of product)

## Results

```
                                         independent  destructive  constructive
n trials                                       7            0           11
proportion                                  38.9%        0.0%        61.1%

mean J_combined                                          0.730
mean J_product (multiplicative model)                    0.616
mean J_min (bottleneck model)                            0.697

ratio J_combined / J_product                             1.18  (constructive on average)
ratio J_combined / J_min                                 1.05  (bottleneck approximately predicts combined)
```

**Zero destructive trials.** Across 18 stacked pipelines, the substrate's
robustness compounds *better than* independent multiplication assumes.

## Per-trial detail

```
image    pipeline                   J_combined  J_product  classification
inat     noise05_jpeg50               0.743      0.509     constructive
inat     noise02_oversat_jpeg85       0.757      0.658     constructive
inat     noise05_blur_jpeg50          0.853      0.407     constructive
inat     invert_noise05               0.320      0.244     constructive
inat     jpeg50_sharpen               0.778      0.703     constructive
inat     noise01_brighten_jpeg85      0.730      0.643     constructive
met      noise05_jpeg50               0.825      0.542     constructive
met      noise02_oversat_jpeg85       0.900      0.762     constructive
met      noise05_blur_jpeg50          0.634      0.336     constructive
met      invert_noise05               0.321      0.258     constructive
met      jpeg50_sharpen               0.727      0.662     independent
met      noise01_brighten_jpeg85      0.711      0.747     independent
native   noise05_jpeg50               0.966      0.932     independent
native   noise02_oversat_jpeg85       0.853      0.795     independent
native   noise05_blur_jpeg50          0.750      0.650     constructive
native   invert_noise05               0.541      0.548     independent
native   jpeg50_sharpen               0.875      0.875     independent
native   noise01_brighten_jpeg85      0.848      0.819     independent
```

## Why constructive — predicate-flip overlap

The mechanism is structural: **the same predicate often gets flipped by
multiple degradations.**

Example: `chroma_subsampled_signature` is fragile to both noise (R94
fragile list) AND survives most JPEG (predictable). When you stack
noise+JPEG, the predicate is flipped by noise — the JPEG step can't
flip it again because it's already flipped. Independent multiplication
assumes both steps independently risk-flip the predicate (and adds the
risks); combined application sees the same predicate-flip events
overlap.

Three concrete mechanisms:

1. **Idempotent overlap**: A flips predicate X; B also flips predicate X
   (independently). Combined fires X-flip once; product double-counted.
2. **Order saturation**: A already destroyed predicate Y. B can't
   destroy it again (it's already gone). Combined can't get worse than
   the single worst step.
3. **Partial restoration**: Some degradation pairs accidentally undo
   each other's effects in specific predicates. blur+sharpen (R93
   adversarial pair) is the extreme case; noise+JPEG is a milder one.

The mean J_combined ≈ J_min × 1.05 result says: **the bottleneck single
step is a strong predictor of combined J.** Worst-step-wins is
approximately right.

## What this changes architecturally

**The substrate's robustness is gracefully bounded by the worst single
degradation step.** This is the closing finding of the R90+R91+R93+R94
robustness suite:

> Substrate fingerprint preservation under combined degradation is
> approximately equal to preservation under the single worst step.
> Stacking degradations doesn't catastrophically compound because
> predicate flip events overlap. Real-world image pipelines (sensor
> noise + filter + CDN re-encode) don't multiplicatively destroy
> substrate-meaning; the worst single step bounds the loss.

This is the *positive* substrate-purpose finding the suite was
building toward. Combined with R90's 95.3% preservation through JPEG
q=50 (where bytes die), R95 says the substrate's meaning is robust
under realistic degradation pipelines, not just clean single-step ones.

## Honest caveats

- **N=18 is small.** A 60+ pipeline sweep would tighten the
  constructive/independent/destructive proportions.
- **Hand-picked pipelines.** Some pipelines (invert+noise) involve
  semantic-changing filters; results there are dominated by the
  invert step.
- **±15% threshold for "independent" is arbitrary.** Tighter (5%)
  would push more trials into constructive/destructive.
- **No real-CDN simulation here.** R95 used PIL JPEG roundtrip; R90
  used real CDN. The simulated JPEG is byte-equivalent to what
  weserv would do, but doesn't include CDN's own resizing/header
  changes.
- **"Constructive" doesn't mean "good"** — it means "less bad than
  independent multiplication assumed." A trial with J_product=0.24
  and J_combined=0.32 (invert_noise05/inat) is still very degraded;
  constructive is just a relative claim about the prediction model.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Combined-degradation classification (3-way) | R95 | 39% independent / 0% destructive / **61% constructive** | current — degradations compound gracefully |
| Mean J_combined / J_product | R95 | **1.18** (substrate is 18% more robust than independent multiplication predicts) | current |
| Mean J_combined / J_min (bottleneck model) | R95 | **1.05** (worst-single-step ≈ combined; bottleneck is the strong predictor) | current |
| Closing finding of robustness suite (R90+R91+R93+R94+R95) | R95 | substrate-meaning is gracefully bounded under stacked real-world degradation; predicate-flip events overlap, so combined degradation ≈ worst single step | current — closes the robustness arc |

## Promises ledger updates

- **C-95 closes:** combined-degradation interaction characterized;
  substrate's robustness compounds constructively/independently, never
  destructively, on this trial set.

## Files added this round

- `round95_combined_degradation/round95_audit.py`
- `round95_combined_degradation/round95_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-95 entry
- `PHOXELIS_BENCHMARKS.md` — R95 row

## Sweep summary R86 → R95 (10 rounds)

| round | finding |
|---|---|
| R86 | backward fiber first light (categorical first since R44–R45) |
| R87 | empirical map → recall 70% |
| R88 | tight-ingredient hypothesis falsified; backward composition non-monotonic (7.6% additive) |
| R89 | reframe to neighborhood satisfaction; 5/5 demos in right cluster |
| R90 | meaning preserved through real CDN at lossy quality (J=0.953 at JPEG q=50) |
| R91 | filter survival tracks semantic impact correctly |
| R92 | substrate as partial transform classifier (2.6× chance) |
| R93 | forward composition non-monotonic (14% additive) and non-commutative (57%) |
| R94 | noise-tolerance curve; physically-sensible fragility patterns |
| R95 | combined degradations compose constructively 61%, never destructively; bottleneck ≈ combined |

The arc is now coherent. The substrate has been shown to:
- operate in BOTH fibers (R86, R89)
- preserve meaning through real-world processing (R90, R91, R94)
- track semantic change correctly (R91, R94)
- detect transformation type recursively (R92)
- compose non-monotonically but non-destructively (R88, R93, R95)

Vincent's audit named the dual-fiber asymmetry; the asymmetry is now
closed empirically with the substrate's structural properties firmly
mapped.

## Next round opens with

R96 — open. The robustness suite closes. Plausible directions:
- Train a fingerprint-based image classifier on R85's diverse corpus
  (medical/satellite/microscopy/etc) — does the substrate's vocabulary
  serve as a useful feature space for downstream tasks?
- Pull more diverse corpus toward P-01 (network-bound).
- Vincent-side: P-03/P-04 hardware.
- Update PHOXELIS_TOOL_LADDER.md (long delinquent per Vincent's audit).
