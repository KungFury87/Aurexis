# Round 152 — 7-DOF Phase 4 STALLS at dist7D=0.88 (25% reduction); R151 lr-decay recipe doesn't extend cleanly to higher-dim training; scale-translation gradient coupling identified as the failure mode

**Date:** 2026-05-01
**Track:** T7 (Phase 4 higher-dim parameter space)
**Status:** complete — 7-DOF (3 trans + 3 rot + 1 scale) Adam+lr-decay run stalled at iter 20 with dist7D=0.881 (25.0% reduction toward target identity transform), vs 3-DOF reaching 92% reduction by iter 19; per-axis diagnostic shows ty (92%) and rx (94%) converged well, but **scale OVERSHOT badly (1.1 → 0.67, target 1.0; -229% "progress")** and tx (22%), rz (-1%) stuck; the optimizer found a local basin where tx-shift trades off against scale-shrinkage to produce similar substrate fingerprint and photo MSE — substrate-as-regularizer architecture has a 7-DOF limit when scale and translation can compensate for each other

---

## What R152 settles

R134-R151 closed the 3-DOF translation case end-to-end: production
recipe (Adam + lr-decay + α=0.20 multi-view + finite-diff eps=0.05)
reaches dist=0.065 (94% reduction) with sustained J=1.000. Open
question: does the recipe extend to richer parameter spaces?

R152 tested 7-DOF: 3 translation + 3 XYZ rotation + 1 isotropic scale.
Init off in every axis (tx=1.0, ty=0.5, rx=ry=rz=0.2, s=1.1). Target
identity transform (all zeros, scale=1).

Result: recipe doesn't extend cleanly. Optimizer stalls at dist7D=0.88
(25% reduction) by iter 20 and oscillates without further progress.
Per-axis diagnostic identifies scale-translation coupling as the
failure mode.

## Method

Same target (cube+sphere asymmetric, 4 azimuth views), same MV α=0.20,
image_size=192, finite-diff Adam, eps=0.05, R151 lr-decay schedule.
Only difference: 7-DOF parameter space instead of 3.

```
params = (tx, ty, tz, rx, ry, rz, s)
target = (0, 0, 0, 0, 0, 0, 1)
init   = (1.0, 0.5, 0, 0.2, 0.2, 0.2, 1.1)
init dist7D = 1.175
```

Phoxel field transform: positions → R(rx,ry,rz) @ positions × s + (tx,ty,tz),
where R is XYZ Euler rotation matrix.

Ran 22 iterations (4 chunks × 3-4 iters at sandbox time budget).

## Results — recipe stalls; per-axis diagnostic reveals coupling

```
iter   dist7D   lr        photo MSE    J       reduction
0      1.175             0.0468       0.736   0.0%
5      0.933    0.10     0.0462       0.785   20.6%
10     0.953    0.10     0.0322       0.807   18.9%   ← already plateauing
15     0.903    0.05     0.0280       0.790   23.2%
20     0.881    0.025    0.0273       0.842   25.0%   ← BEST
22     0.884    0.0125   0.0269       0.838   24.7%
```

Photo MSE plateaus at ~0.027 (vs 3-DOF reaching 0.005 at iter 30).
Substrate J peaks at 0.86 (vs 3-DOF reaching 1.000 at iter 13).

### Per-axis state at iter 22

```
axis  init   current   target   |dist|    progress%
tx    1.000  0.784     0.000    0.784     21.6%   ← STUCK
ty    0.500  -0.040    0.000    0.040     92.0%   ← OK (overshot slightly)
tz    0.000  0.078     0.000    0.078     drifted (started at target)
rx    0.200  -0.013    0.000    0.013     93.6%   ← OK
ry    0.200  -0.100    0.000    0.100     50.2%   ← PARTIAL
rz    0.200  0.203     0.000    0.203     -1.3%   ← STUCK
s     1.100  0.671     1.000    0.329     -229%   ← WILDLY OVERSHOT (1.1→0.67)
```

### Finding 1: scale wildly overshoots target

`s` started 10% above target (1.1, target 1.0). After 22 iters, it's
**33% below target** (0.671). The optimizer pushed scale DOWN past
target and kept going. The progress metric goes to -229% — the scale
is now further from target than it was at init.

This is the dominant remaining error. Scale=0.67 makes the cube+sphere
look 33% smaller in every view, which compensates for the residual
tx=0.78 translation error to produce roughly correct render at each
azimuth.

### Finding 2: scale-translation coupling is a local basin

Together, tx=0.78 and s=0.67 mean the rendered field is "smaller and
shifted right" — but from cameras at azimuths 0/90/180/270, this looks
similar enough to the target (correctly-positioned, correctly-sized)
that:
- Photo MSE plateaus at 0.027 (not bad, not great)
- Substrate J reaches 0.84 (most predicates fire correctly)
- Per-axis gradients point in directions that the optimizer can't
  resolve cleanly (moving tx → 0 increases scale_error in worse direction)

This is the "wrong basin" that 3-DOF Phase 4 didn't have access to.
With only translation params, there's no other parameter for the
optimizer to trade against — translation must converge.

### Finding 3: rotation rz didn't move at all

rz started at 0.2 (rotation about z-axis = up-axis). The 4-view
camera setup has cameras at azimuths 0/90/180/270 around the same
z-axis. Rotating the field about z doesn't change ANY view's render
(beyond a mod-90° shift that the cube's 4-fold symmetry absorbs).

So the gradient with respect to rz is approximately zero by
construction — rz is unobservable from this camera configuration.
The optimizer correctly leaves rz alone.

This is a feature of the test setup (4 cameras around z-axis), not
a bug. Real splatting with non-axis-aligned camera distributions
wouldn't have this degenerate dimension.

### Finding 4: substrate-as-regularizer doesn't disambiguate scale

The substrate fingerprint (boolean predicate vector over layout-invariant
predicates) is by design **invariant** to many transforms. Including,
apparently, isotropic scale to first approximation. When the cube+sphere
shrinks by 33% AND shifts right by 0.78, the layout-invariant predicates
that fire — has_blue_dominant, is_high_contrast, etc. — fire similarly
to the target, even though pixels don't match exactly.

This means substrate-as-regularizer (R142's architectural conclusion)
**doesn't penalize scale-translation coupling** the way it penalizes
pure-translation error. Substrate's "is this the same content?" check
gives "yes" for "smaller version of same content."

For 7-DOF Phase 4 to work with substrate, the vocabulary needs predicates
sensitive to scale (e.g. has_object_taking_up_25%_of_frame vs
has_object_taking_up_50%). The current 151-predicate vocab doesn't
include these.

### Finding 5: 3-DOF success doesn't generalize uniformly to 7-DOF

R151's recipe achieves 94% reduction in 30 iters at 3-DOF.
R152's same recipe achieves 25% reduction in 22 iters at 7-DOF.

The success isn't "Phase 4 trains phoxel fields"; it's "Phase 4
trains TRANSLATION when other parameters are correct." The full 7-DOF
case requires either:
- A scale-discriminative substrate vocabulary (more predicates)
- Per-group lr (translation lr=0.1, rotation+scale lr=0.01)
- Constrained training (freeze scale, train translation + rotation, then unfreeze)
- Different parameter representation (log-scale instead of linear scale, axis-angle instead of Euler)

R152 doesn't test any fix — it documents the limit.

## Architectural conclusion

R134-R151 framing: "Phase 4 production training: Adam + lr-decay +
α tracking + substrate-as-regularizer reaches dist→0 with sustained
J=1.000 in ~30 iters."

R152 corrects: "...for 3-DOF translation case. For richer parameter
spaces (7-DOF translation+rotation+scale), the substrate fingerprint's
scale-invariance allows scale-translation gradient coupling to trap
the optimizer in a local basin at ~25% reduction. The recipe is
TRANSLATION-COMPLETE but not POSE-COMPLETE."

This is honest and important. Real splatting needs full 6-DOF (or
higher) pose training, so R151's clean 3-DOF result is a partial
deliverable. R153+ candidates address the 7-DOF gap.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **R151 lr-decay recipe DOES NOT extend to 7-DOF cleanly** | R152 | 7-DOF (3 trans + 3 rot + 1 scale) at MV α=0.20, image_size=192, R151 schedule, 22 iters: best dist7D=**0.881** (25% reduction); vs 3-DOF reaching 92% by iter 19 | round152 | current — recipe is translation-complete but not pose-complete |
| **Scale-translation gradient coupling is the 7-DOF failure mode** | R152 | scale wildly overshoots (init 1.1 → iter22 0.67, target 1.0; -229% progress); tx stuck at 0.78 (22% progress); substrate-as-regularizer doesn't penalize scale shrinkage when paired with tx-shift; substrate vocab is scale-invariant by design | round152 | current — substrate vocab needs scale-discriminative predicates for 7-DOF Phase 4 |
| **Phase 4 architecture's substrate scale-invariance is feature AND bug** | R142+R152 | scale-invariance helps content-fingerprint use cases (R96-R99: substrate beats pHash on geometric transforms because invariant to small geometric change) AND hurts pose training (R152: substrate doesn't disambiguate scale from translation) | round142-152 | current — clean architectural observation; same property has opposite effects across use cases |
| Seventeen-round Phase 4 arc (R134-R152) | R134-R152 | + 7-DOF recipe limit (R152); 3-DOF translation case fully closed; pose-complete training requires architectural extensions | round134-152 | current — Phase 4 limits empirically characterized |

## Honest caveats

- **22 iters is fewer than R151's 30.** Could R152 break out of the
  local basin given more iters at smaller lr? Probably not — the
  trajectory has been flat for ~10 iters. But not formally tested.
- **rz being unobservable is a setup artifact.** 4 cameras at azimuth
  0/90/180/270 with cube symmetry means z-axis rotation doesn't show.
  More views (e.g. azimuth + elevation) would fix this. Doesn't
  affect the scale-coupling finding.
- **Single init.** The basin attractor at (tx=0.78, s=0.67) might
  be reachable only from this specific init. Other inits could
  converge correctly. Multi-init test deserves checking.
- **Pre-registration directional verdict: confirmed (the recipe DOES
  hit a limit) but the predicted limit (just slower) was wrong**
  — actual limit is "stalls in wrong basin," not "reaches target
  with more iters."
- **3-DOF success is still real.** R152 doesn't invalidate R134-R151;
  it bounds them. Production splatting that uses pretrained pose
  initialization + Phase 4 fine-tuning would benefit from the 3-DOF
  result; from-scratch 7-DOF training needs more work.

## Promises ledger updates

- **C-152 closes:** R151 lr-decay recipe does not extend cleanly to
  7-DOF Phase 4 training. 7-DOF (3 translation + 3 rotation + 1 scale)
  stalls at dist7D=0.88 (25% reduction) due to scale-translation
  gradient coupling — substrate fingerprint's scale-invariance allows
  the optimizer to trade tx-shift against scale-shrinkage in a local
  basin. Recipe is translation-complete but not pose-complete.
  Architectural fixes for full pose training: scale-discriminative
  substrate predicates, per-group lr, constrained sequential training,
  or different parameter representation. Phase 4 limits empirically
  characterized.

## Files added this round

- `round152_7dof/r152_7dof.py`
- `round152_7dof/round152_audit.json`
- `round152_7dof/adam_state.json` (full 22-iter trajectory)
- this report
- `PHOXELIS_PROMISES.md` — C-152 entry
- `PHOXELIS_BENCHMARKS.md` — R152 rows + 17-round arc summary

## Next round opens with

R153 candidates:

**A — push R152.** Single-round-add to a fresh push.bat.

**B — per-group lr at 7-DOF.** Translation lr=0.1, rotation+scale
lr=0.01. Tests whether scale-translation coupling is fixable by giving
fast and slow params different lrs.

**C — sequential training.** First train translation (freeze rotation
+ scale at init values), then rotation, then scale. Tests whether
constrained 1-axis-at-a-time training reaches better convergence.

**D — scale-discriminative predicate.** Add `has_object_size_above_X`
or `has_dominant_object_aspect_ratio` to vocab. Tests whether substrate
with these new predicates can distinguish scale.

**E — different init.** Try init (0.5, 0.25, 0, 0.1, 0.1, 0.1, 1.05)
— closer to target. Tests whether basin attractor is wide or local.

**F — autograd implementation.** Multi-round engineering. Eliminates
finite-diff. Doesn't directly fix scale-coupling but gives cleaner
gradients for diagnosing.

Lean **A then B**. B is the cheapest one-line test of whether
per-group lr fixes scale coupling. If yes, the recipe has a clean
extension to 7-DOF. If no, D (vocabulary extension) becomes the
primary path.
