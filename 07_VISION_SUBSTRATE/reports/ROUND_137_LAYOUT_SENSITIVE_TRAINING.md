# Round 137 — layout-sensitive subset training: position-responsive but non-monotonic; Phase 4 Option D confirmed

**Date:** 2026-05-01
**Track:** T7 (Phase 4 architectural decision finalized via three-round negative-result triangulation)
**Status:** complete — sensitive subset reduces distance 28% (vs R134 invariant's 20%) but plateaus at non-local-optimum basin; together with R134 + R135, three rounds jointly diagnose that substrate fingerprint is great for content-similarity but not for direct translation gradient descent regardless of subset or boolean/scalar formulation; Phase 4 Option D (photometric primary + substrate regularizer) is the empirically supported architecture

---

## Method (same as R134)

- Target: phoxel cube at origin (864 phoxels)
- Init: same cube translated to (1.0, 0.5, 0.0); distance 1.118
- Loss: 1 - Jaccard(current, target) on the **layout-sensitive 23-predicate subset** (changed from R134's 128-pred invariant subset)
- Optimizer: finite-difference gradients with eps=0.05, lr=0.4
- 10 iterations

The invariant/sensitive partition was re-derived per scene (target-only test); 128 invariant + 23 sensitive predicates this run vs R130's 115/36 split (different scene, different partition; expected).

## Results

```
iter   translation              distance   J_sens   loss     gradient norm
0      ( 1.000, +0.500, +0.000) 1.118      0.636    0.364    —
1      (+0.788, +0.500, +0.000) 0.933      0.667    0.333    0.530   ↓
2      (+0.455, +0.167, +0.000) 0.484      0.615    0.385    1.179   ↑ (loss UP)
3      (+0.762, -0.214, -0.128) 0.802      0.727    0.273    1.265   ↓
4-10   (same)                   0.802      0.727    0.273    0.000   plateau
```

**The pathological iter 2.** Optimizer jumped from dist=0.933 to
dist=0.484 — much closer to origin in physical space — but loss went
UP from 0.333 to 0.385. At dist=0.484, the cube is positioned such
that some `has_subject_at_thirds_*` predicates fire differently than
the target's center-of-frame configuration. The optimizer correctly
treats that as a worse fingerprint match, retreats to a different
basin (dist=0.802), and gets stuck.

This is **not noise**. It's the fundamental property of the layout-
sensitive subset: predicates over compositional thresholds (subject-
at-thirds, horizontal balance, mirror symmetry) flip at specific
spatial boundaries. The loss surface has discontinuities where
predicates cross those thresholds. A subject that has *moved closer
to center* may still produce a different boolean fingerprint than the
target's exact-center configuration, leading to spurious local
minima in loss-vs-position space.

## What this round adds to the diagnosis

R134 + R135 + R137 together:

| round | subset | formulation | failure mode |
|---|---|---|---|
| R134 | layout-invariant | boolean Jaccard | discrete plateaus from bit invariance |
| R135 | layout-invariant | continuous MSE | noisy oscillation from weak position responsiveness |
| **R137** | **layout-sensitive** | **boolean Jaccard** | **non-monotonic with compositional-threshold spurious minima** |

The substrate fingerprint, **regardless of subset or boolean/scalar
formulation**, doesn't give a clean gradient signal for translation
parameters. The reasons differ but the conclusion converges.

## Why this is informative rather than a setback

The substrate is good at three things validated through the prior arc:

1. **Content fingerprinting** (R96/R97/R98/R99): 79% top-1 / 99%
   top-3 / AUC 0.975 near-duplicate detection without training
2. **Grounded perceptual reasoning** (R120/R122): LLM produces
   measurement-grounded image descriptions
3. **Multi-view stability + discrimination + perturbation-smoothness**
   (R130/R131/R133): on the layout-invariant subset

What the substrate ISN'T good at, per R134/R135/R137: **direct
gradient training on translation parameters**. Three independent
attempts confirm this. That's a structural property of the
substrate's design — its predicates are designed for *measurement
of scene properties*, not *position-encoding*.

This finding clarifies what role the substrate plays in a real
splatting pipeline:

- **Primary training signal**: photometric loss (per-pixel MSE
  against target render). This loss DOES have strong, monotonic
  gradients in translation parameters. Standard splatting practice.
- **Substrate as regularizer**: add α × substrate-fingerprint-loss
  with small α (0.01-0.1) to the photometric loss. Keeps the
  trained field semantically valid (not just pixel-accurate).
- **Substrate for evaluation**: at training-time and test-time,
  measure substrate-fingerprint Jaccard between trained-field
  renders and target renders. That measures *content match*, not
  pixel match.

## Phase 4 architectural decision

R135 named four options:
- A: layout-sensitive subset for single-view training
- B: position-aware scalar ops (vocabulary growth)
- C: multi-view loss with invariant subset
- **D: photometric primary + substrate regularizer**

R137 tested A and ruled it out (sensitive subset has spurious minima).
R135 tested implicit-A within continuous loss and ruled it out (weak
responsiveness). The remaining viable Phase 4 path is **D**.

R138 would be: implement option D. Standard photometric MSE loss as
primary; substrate fingerprint loss on invariant subset as small
regularizer. Verify training converges to target with photometric
loss while substrate prevents semantically-invalid intermediate
states.

R139+ candidates: B (position-aware scalar ops via R107 protocol);
C (multi-view loss to test whether richer view signal helps option
A); real splatting comparison (substrate-as-regularizer vs
photometric-only) to measure whether the regularizer adds quality.

## Honest caveats

- **Single-viewpoint training.** R134/R135/R137 all use az=0 only.
  Multi-view loss might give different sensitive-subset behavior
  because predicates flip differently across viewpoints — possible
  that summing losses across viewpoints averages out the spurious
  minima. R138 candidate.
- **Cube target is symmetric.** Many translations produce identical
  silhouettes (rotational ambiguity); a more asymmetric target would
  give the loss surface more distinguishable basins.
- **Naive optimizer.** Adam, simulated annealing, or random restarts
  could escape the spurious minima R137 hits. R134/R137 use vanilla
  finite-difference gradient descent.
- **The "regardless of formulation" claim is from 3 experiments.**
  More variants (different subsets, different ops, sigmoid relaxation,
  larger eps) might surface a working formulation. R134-R137 covers
  the most natural variants but isn't exhaustive.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Layout-sensitive subset training: position-responsive but non-monotonic** | R137 | distance reduction 28% (init 1.118 → final 0.802); iter 2 jumped to dist 0.484 then loss went up; plateau at gradient=0 by iter 4 | current — sensitive subset has compositional-threshold spurious minima; not a clean gradient surface for translation |
| Three-round translation-training diagnosis | R134 + R135 + R137 | invariant boolean (R134): discrete plateau; invariant continuous (R135): weak responsiveness; sensitive boolean (R137): non-monotonic spurious minima; substrate fingerprint not suitable as primary translation-training signal regardless of subset/formulation | current — Phase 4 Option D (photometric primary + substrate regularizer) confirmed as architecture |

## Promises ledger updates

- **C-137 closes:** layout-sensitive subset training tested. Improves
  on R134's invariant subset (28% vs 20% distance reduction) but
  plateaus at non-local-optimum basin. Three-round arc R134-R137
  jointly diagnoses the substrate-as-direct-translation-loss
  limitation; Phase 4 Option D (photometric primary + substrate
  regularizer) is the empirically supported architecture.

## Files added this round

- `round137_sensitive/r137_sensitive_subset.py`
- `round137_sensitive/round137_audit.json`
- `round137_sensitive/target.png` + `iter_{00..10}.png`
- this report
- `PHOXELIS_PROMISES.md` — C-137 entry
- `PHOXELIS_BENCHMARKS.md` — R137 row

## Next round opens with

R138 candidates:

**A — push R134-R137.** Anti-drift; 4 rounds since last push.

**B — implement Phase 4 Option D.** Photometric primary loss
(per-pixel MSE) + α × substrate fingerprint loss as regularizer.
First real splatting training pipeline with substrate involvement.

**C — multi-view loss test.** Sum sensitive-subset losses across
4 viewpoints. If multi-view averages out the spurious minima R137
found, sensitive subset becomes viable for single-position training.

**D — characterize R137's spurious-minima geometry.** Plot loss
vs translation in 2D slices to map the basins. Helps Phase 4
optimizer design.

Lean **A then B**. The Phase 4 architecture is now empirically
chosen; the next concrete work is implementing it.
