# Round 135 — continuous-relaxation reveals a deeper Phase 4 architectural finding: the layout-invariant subset can't drive a translation gradient

**Date:** 2026-05-01
**Track:** T7 (Phase 4 design — substantive negative result with architectural implication)
**Status:** complete — continuous-relaxation MSE loss on a 7-dim scalar operator vector failed to converge for the same fundamental reason as R134's boolean Jaccard loss: the layout-invariant subset is by design weakly dependent on object position, so gradient descent on it can't drive translation toward a target

---

## Why this round + first-pass mistake

R134's Phase 3 first-light demo trained translation parameters via
finite-difference gradient descent on a boolean Jaccard loss against
a target fingerprint. Loss decreased 24% then plateaued at gradient=0
— characteristic of boolean fingerprint discreteness.

R135 hypothesized: replace boolean with continuous scalar values
from the underlying operators, use MSE loss, and the optimizer
should converge smoothly. Tested two scalar formulations:

1. **Naive MSE on raw scalar vector** — loss dominated by
   `fft_peak_to_floor` (=152.9 vs other ops ~0.1-1.5); gradient
   exploded immediately, params went to (-1178, -782, -319) in
   iteration 1.
2. **Relative MSE on dimensionless 7-op scalar vector** —
   loss bounced around 0.16-0.55 across 12 iterations; distance to
   target oscillated 1.118-1.344, settled at 1.262 (slightly
   *worse* than initial); 24% loss reduction overall but no
   monotonic convergence.

Neither variant converged. The first-pass mistake was assuming the
boolean discreteness was the bottleneck. R135 reveals a deeper
limitation that affects both formulations equally.

## The actual finding

**R130 split the substrate vocabulary into 115 layout-invariant +
36 layout-sensitive predicates.** The partition was driven by the
empirical question "which predicates fire identically across
viewpoints of the same scene?" That's the *content* of "layout-
invariant" — predicates that DON'T change when spatial composition
changes.

The implication R130 didn't surface but R135 makes empirical:
**predicates that are layout-invariant are also weakly responsive
to translation parameters.** That's the same fact stated two ways.
If a predicate doesn't change when the cube swaps to where the
sphere was (R128's layout-shift), it also doesn't change much when
the cube moves a small distance.

So when you build a content-loss on the layout-invariant subset:
- Loss is stable across viewpoints (R130: J=1.000) ✓
- Loss discriminates between scene types (R131: J range 0.33-0.87) ✓
- Loss is locally smooth under perturbations (R133: J ≥ 0.95) ✓
- **Loss has weak gradient with respect to translation parameters** ✗

The first three are exactly what Phase 3 needs for stability and
smoothness. The fourth is what Phase 4 needs for *trainability
toward a target position*. They're in tension by construction.

## What this means for Phase 4

R134's gradient descent couldn't escape its plateau because:
- The layout-invariant subset doesn't have a strong enough signal
  on the boolean side to flip when translation changes by small amounts
  (R134 plateau)
- The same subset doesn't have strong enough signal on the
  continuous side to give monotonic gradient descent toward a target
  position (R135 oscillation)

**Both R134 and R135 are detecting the same property of the
layout-invariant subset: weak responsiveness to position parameters.**

For splatting training to actually converge toward a target
position, Phase 4 needs a loss that DOES depend strongly on
position. Three architectural options:

### Option A: Use the layout-sensitive subset for single-view training

The 36 layout-sensitive predicates (composition, balance, subject
placement, symmetry, horizon, color distributions) directly encode
"where things are in image space." A training loss on these would
have strong position gradients.

Tradeoff: this loss is view-unstable (R128). It works for matching
a SPECIFIC viewpoint's composition but doesn't generalize to other
views of the same 3D scene. So splatting becomes per-viewpoint
training.

### Option B: Develop scalar position-aware fingerprints

Add new operators that explicitly compute position signals (mean x
of phoxel-rendered pixels, centroid of bright regions, subject
center y, etc.). These by definition change monotonically with
translation. New predicate family in the substrate vocabulary.

Tradeoff: requires substrate vocabulary growth. Should follow the
R107 promote/retire/recalibrate protocol.

### Option C: Multi-view loss

Sum loss across multiple training viewpoints. R134 used a single
fixed view (az=0); the gradient signal was sparse because moving
the cube only affected one view's predicates. With multiple views,
phoxel positions affect ALL viewpoint renders differently, giving
richer gradient structure.

Tradeoff: 3-4× compute per iteration; still uses the same
layout-invariant subset which has the responsiveness problem.

### Option D: Photometric loss with substrate as regularizer

Use the standard pixel-MSE loss as primary signal (which DOES have
strong position gradient) and add the substrate fingerprint loss
as a regularizer to constrain the field toward semantically valid
configurations.

Tradeoff: this is closest to standard splatting practice; uses
substrate for what it's best at (semantic similarity) and standard
photometric loss for what IT's best at (position convergence).

## Why R135 is genuine progress despite "PARTIAL" verdict

The negative result diagnoses an architectural question that R130's
positive result didn't surface. The R130 partition has consequences
for Phase 4 that I didn't appreciate when calling R130 + R131 + R133
a "complete Phase 3 prerequisite validation."

The honest characterization: **R130-R133 validated the substrate's
layout-invariant subset is good for content-fingerprinting (which
is what R98/R99/R120/R122 demonstrated), but content-fingerprinting
and gradient-trainability-toward-target-position are different
properties.** R134 + R135 reveal this separation empirically.

This is the Phase 2 → Phase 3 transition working correctly. Phase 2
(viability) is real. Phase 3 (training) is harder than R124-R133
suggested because the fingerprint-as-loss claim has a tension we
hadn't measured.

## Concrete R136 candidate

The most actionable next step is **Option D (photometric +
substrate regularizer)** because it's closest to existing splatting
literature. R136 would:

1. Render forward, compute per-pixel MSE against target render
2. Add α × (substrate-fingerprint-loss) where α is small (0.01-0.1)
3. Train translation parameters with combined loss
4. Verify: photometric loss alone converges; combined loss converges
   with substrate-induced bias toward "correct content" (not just
   "correct pixels")

This validates the substrate's role: **regularizer that prefers
semantically-valid intermediate states**, not the primary training
signal.

R137+ candidates: implement Options A, B, C as honest comparisons
and characterize the tradeoff space.

## Honest caveats

- **7-op scalar vector might be too small.** A larger curated set
  could have richer signal. But the same finding (weak position
  dependence) would likely apply because all layout-invariant ops
  share the property.
- **Single-viewpoint training inherently has sparser gradients than
  multi-view.** R134/R135 might converge under multi-view loss
  even with the layout-invariant subset.
- **Cube target is rotationally too symmetric for some translation
  test.** A more asymmetric target (single colored sphere with a
  visible "front") would give the layout-invariant subset more
  signal. But the architectural finding generalizes.
- **Naive optimizer.** Adam + warm restarts + variable lr might
  squeeze more out of either loss. R135 doesn't claim the loss is
  unoptimizable in principle; it claims the architectural pairing
  (layout-invariant fingerprint + translation params) is weakly
  coupled.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Layout-invariant subset is weakly responsive to translation parameters** | R134 + R135 | R134 boolean: 24% loss reduction, gradient=0 plateau; R135 continuous: 24% loss reduction, oscillation, no convergence; both diagnose the same property | current — Phase 4 finding; layout-invariant subset is good for content-fingerprinting but not for direct position-gradient training |
| Phase 4 architectural options characterized | R135 | A: layout-sensitive single-view training; B: position-aware scalar ops; C: multi-view loss; D: photometric + substrate regularizer | current — design-space mapped; R136 candidate is option D (photometric primary + substrate regularizer) |

## Promises ledger updates

- **C-135 closes:** continuous-relaxation hypothesis tested and
  partially refuted. Boolean discreteness wasn't the bottleneck;
  the deeper issue is the layout-invariant subset's weak
  responsiveness to translation parameters. R136 architectural
  options named.

## Files added this round

- `round135_continuous/r135_continuous.py`
- `round135_continuous/round135_audit.json`
- `round135_continuous/target.png` + `iter_{00..12}.png`
- this report
- `PHOXELIS_PROMISES.md` — C-135 entry
- `PHOXELIS_BENCHMARKS.md` — R135 row

## Next round opens with

R136 candidates:

**A — push R134 + R135.** Anti-drift; small.

**B — implement Option D (photometric + substrate regularizer).**
Per-pixel MSE as primary loss, substrate fingerprint as
regularizer. Lean Phase 4 starting point because it composes with
existing splatting practice.

**C — implement Option C (multi-view loss with layout-invariant
subset).** Test whether single-viewpoint sparsity was the issue,
not the subset's intrinsic responsiveness.

**D — implement Option A (layout-sensitive subset for single-view
training).** Cleanest test of "is the layout-sensitive subset
position-trainable?" — if yes, validates the partition's intended
use distinction.

**E — Option B requires substrate vocabulary growth (new
position-aware ops + R107-protocol promotion). Multi-round arc.**

Lean **A then D then B**. D directly tests the partition's
implication and is cheap. If D succeeds, the substrate has
"content-fingerprint loss" (invariant subset) AND "position-
gradient loss" (sensitive subset) as separate Phase 4 building
blocks. B becomes the long-term Phase 5 work.
