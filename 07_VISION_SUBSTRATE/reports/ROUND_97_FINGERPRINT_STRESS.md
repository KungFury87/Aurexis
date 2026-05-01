# Round 97 — content-fingerprint stress test (R96 corrected)

**Date:** 2026-04-29
**Track:** T6 substrate-purpose; correction to R96
**Status:** complete — **R96's 100% top-1 was a corpus-selection artifact**; honest numbers are 79% top-1 / 99% top-3 / AUC 0.975 across 100 trials including hard modifications

---

## Why R97 corrects R96

R96 claimed 100% top-1 / AUC=1.000 on 40 mild-variant trials with 10
specific corpus images. R97 reran the same setup with a slightly
different 10-image selection (took the first k from each source glob
instead of name-filtered) and got **80% top-1** on the same mild
variants.

The difference: when two original images happen to have very similar
fingerprints, a variant of A can land closest to B in fingerprint space.
The negative-pair max Jaccard in R97 is **1.000** — at least one
variant exactly tied with a non-origin image's fingerprint.

R96's 100% was real on its specific 10 images; it didn't generalize.
**R97's larger 100-trial measurement is the credible number.**

## Honest results across 100 trials (10 originals × 10 variants)

```
                       n     top-1     top-3     AUC      pos_J     neg_J
mild (R96 reproduce)  40   80.0%    100.0%    0.986     0.926     0.332
hard (R97 stress)     60   78.3%     98.3%    0.970     0.839     0.321
all combined         100   79.0%     99.0%    0.975     0.874     0.325
```

The mild and hard subsets are nearly identical at top-1 (80% vs 78%).
Top-3 retrieval stays high under both (100% mild, 98% hard). AUC drops
modestly under hard variants but stays strong (0.97).

## Per-variant top-1 accuracy

```
severity  variant              top-1    pos-J mean
mild      mild:filter           8/10      0.967
mild      mild:noise02          8/10      0.870
mild      mild:jpeg85           8/10      0.950
mild      mild:crop5            8/10      0.915
hard      hard:jpeg30           8/10      0.932    JPEG q=30
hard      hard:noise08          8/10      0.711    σ=0.08 noise
hard      hard:crop20           7/10      0.685    20% crop ← weakest
hard      hard:oversat+jpeg50   8/10      0.940    combined transform
hard      hard:rotate5          8/10      0.840    5° rotation
hard      hard:downup           8/10      0.928    2x downsample-upsample
```

**8/10 top-1 across virtually every variant** — both mild and hard.
The single weak case is hard:crop20 at 7/10. Even σ=0.08 noise (where
R94 measured single-image J=0.71) achieves 8/10 top-1 because the
matching is comparative — even a degraded fingerprint can still be
the closest to its origin.

## What R97 actually establishes

The substrate works as a content-fingerprint, but with limits:

1. **Top-3 retrieval is reliable** (99/100 = 99%). For practical
   image search "show me the K most similar images," K=3 essentially
   never misses the origin in this trial.
2. **Top-1 hits ~80%.** The substrate doesn't always rank the origin
   FIRST among similar fingerprints. Some originals are themselves
   close enough in predicate-space that variants tie or cross over.
3. **AUC 0.975** is strong discrimination but not perfect. There's a
   small overlap between near-duplicate and unrelated Jaccard
   distributions — measurable error rate exists.
4. **Robustness to severity is high.** Hard variants don't degrade
   top-1 significantly more than mild variants. The bottleneck isn't
   the variant severity; it's the inter-original similarity.

## Why this matters more than R96's "100%"

R96 said the substrate is a perfect content-fingerprint. R97 says it's
an *imperfect* but useful one. The latter is testable, falsifiable,
and matches the structural results of R74-R95:

- R77 effective rank 31/76 → fingerprints don't fully discriminate at
  N=76 corpus
- R85 rank 39/110 → growing
- R74 78% HEALTHY → 22% of vocabulary is corpus-mismatch or low-fire
- R94 J=0.71 at σ=0.05 → individual fingerprint preservation IS partial

A substrate with effective rank 39/110 carrying 99% top-3 and 79%
top-1 retrieval is *exactly* what those structural results predict.
R96's "100%" was inconsistent with its own substrate; R97's numbers
are consistent.

## Comparison to standard image-hash baselines (untested but worth flagging)

For context, typical perceptual hash benchmarks on similar tasks:
- pHash: ~95% top-1 on mild modifications
- dHash: ~90% top-1 on mild modifications
- Learned (CLIP, DINOv2): >99% top-1 on mild modifications

R97's 79% top-1 is below these baselines. The substrate's value is
NOT that it beats learned alternatives at this task — it's that it
hits 99% top-3 *without any training, embedding, or learned weights*,
using only 146 hand-authored predicates running in NumPy.

A future round could benchmark side-by-side against pHash/dHash on
the same trial set. R97 doesn't make the comparative claim.

## Honest caveats

- **N=10 originals** is still small. The 79% top-1 estimate has wide
  confidence intervals (±~10%). 100+ originals would tighten.
- **Single corpus** — variants of the corpus images. A real
  image-search task involves a much larger gallery.
- **No comparison to baselines.** R97 doesn't claim "better than X";
  it claims "works at this level."
- **The R96 result was reported in good faith** but not stress-
  tested. The lesson is: AUC=1.000 on 40 trials should ALWAYS prompt
  a 10× larger replication before publication. This is exactly what
  the audit Vincent did at R85 was supposed to catch.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Substrate as content-fingerprint, top-1 | R96 | 100% (40 trials) | superseded by R97 — corpus-selection artifact |
| Substrate as content-fingerprint, top-1 | R97 | **79% (100 trials)** | current — credible measurement |
| Substrate as content-fingerprint, top-3 | R97 | **99% (100 trials)** | current — robust at top-3 |
| Substrate as content-fingerprint, ROC AUC | R97 | **0.975** | current |
| Worst variant (top-1) | R97 | hard:crop20 at 7/10 (heavy crop) | current |

## Promises ledger updates

- **C-97 closes:** R96 stress-tested and corrected; substrate
  content-fingerprint operates at 79%/99%/0.975 (top-1/top-3/AUC),
  not the perfect numbers R96 claimed.

## Files added this round

- `round97_fingerprint_stress/round97_audit.py`
- `round97_fingerprint_stress/round97_audit.json`
- this report
- `PHOXELIS_PROMISES.md` — C-97 entry; supersede C-96 numbers
- `PHOXELIS_BENCHMARKS.md` — corrected R96 row → R97 row

## Naming the cycle (charter §7)

R96 was step 1 (concrete artifact, "we have content-fingerprinting").
R97 is the widening: the artifact's claimed perfection broke under
larger trial. I named the dead-end ("100% AUC at small N is unsafe to
publish") explicitly. The substrate's real capability is at the
99%-top-3 / 79%-top-1 / AUC-0.975 level — useful but not magic.

## Next round

R98 — the natural extension. Either:
- Benchmark vs pHash / dHash on the same 100-trial setup
- Scale to 100+ originals to tighten the top-1 estimate
- Apply substrate fingerprint to a real image dataset (CIFAR-100,
  ImageNet sample) for downstream classification benchmark
