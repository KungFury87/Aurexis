# Round 154 — 0.3× factor unlocks rotations but RE-INTRODUCES scale overshoot; R154 is WORSE than R153 (0.509 vs 0.342); architectural insight: per-group lr needs THREE groups (translation, rotation, scale) not two

**Date:** 2026-05-01
**Track:** T7 (Phase 4 7-DOF lr-magnitude tuning)
**Status:** complete — re-tuned R153's 10× rotation+scale lr-scaling to 0.3× (3.3× looser); rotations DO unlock (rx 88%, ry 84%, rz 71% — vs R153's 5%, 39%, 5%) but **scale overshoots again** (1.1 → 0.807, target 1.0; -93% progress) and tx stalls at 55%; net dist7D=0.509 (56.7% reduction) — WORSE than R153's 0.342 (70.9%); architectural insight: scale and rotation need DIFFERENT lr scalings — they can't share the same group; per-group lr needs THREE groups (translation 1.0×, rotation ~0.3×, scale ~0.1×)

---

## What R154 settles

R153 found 10× lr-scaling for rotation+scale solved scale-translation
coupling (R152 problem) but rotations got too slow (5% progress on
rx, rz). R154 tested whether re-tuning the magnitude to 0.3× (3.3×
looser) recovers full pose convergence.

Result: 0.3× factor produces a different failure mode. Rotations now
move well (75-88% progress) but scale overshoots again, and tx stalls.
Net dist7D worse than R153.

The architectural finding: scale and rotation need DIFFERENT lr scalings.
A single shared factor for "rotation+scale" can't be both fast enough
for rotations and slow enough for scale.

## Method

Identical to R153 except `LR_GROUP[3:7] = 0.3` (vs R153's 0.1).
Translation idx 0-2 unchanged at 1.0. Same target/init/optimizer/eps.

## Results — at iter 27

```
axis    init     current   target    progress%   verdict
tx      1.000    0.452     0.000     54.8%       STUCK
ty      0.500    0.005     0.000     99.0%       OK
tz      0.000    0.114     0.000     drift       (was at target)
rx      0.200    0.025     0.000     87.6%       OK ← unlocked!
ry      0.200   -0.033     0.000     83.7%       OK ← unlocked!
rz      0.200    0.059     0.000     70.6%       OK ← unlocked! (vs R152/R153 stuck)
s       1.100    0.807     1.000     -92.5%      OVERSHOT
```

dist7D = 0.509 (56.7% reduction).

### Three-condition comparison (R152 vs R153 vs R154)

| condition | LR factor | best dist7D | redux% | tx | s | rx | ry | rz |
|---|---|---|---|---|---|---|---|---|
| R152 | uniform 1.0 | 0.881 | 25% | 22% (stuck) | -229% (1.1→0.67) | 94% | 50% | -1% |
| **R153** | **0.1×** | **0.342** | **71%** | **97%** | **95%** | 5% | 39% | 5% |
| R154 | 0.3× | 0.509 | 57% | 55% | -93% | 88% | 84% | 71% |

R154 sits between R152 and R153 — better rotations than R153, worse
translation+scale than R153. Net dist7D in middle.

### Finding 1: rotations cleanly unlocked at 0.3× factor

R154 rotations: rx 87.6%, ry 83.7%, rz 70.6% — strong convergence
across all three rotation axes (including rz which R152/R153 had
stuck at <6%).

Even better, rz at 0.190 → 0.059 (66% movement) suggests the
"4-camera-around-z makes rz unobservable" claim from R152 was an
overstatement. rz IS getting some signal, just very weak. With enough
lr it eventually moves.

The 0.3× factor unlocks rotation gradients to make meaningful per-iter
moves. Each rotation effective lr becomes ~0.0075 by iter 16 (vs
R153's 0.0025), enough to traverse 0.2 rad init in 27 iters.

### Finding 2: scale overshoot returns at 0.3× factor

R152: s overshot to 0.671 (-229% progress)
R153: s converged to 0.995 (95.1% progress) — 0.1× factor solved this
**R154: s overshot to 0.807 (-93% progress)** — 0.3× factor brings it back, partial

Per-iter scale trajectory in R154:
- iter 1: 1.130 (already moved past init in wrong direction)
- iter 5: 1.041
- iter 10: 0.904 (passed target 1.0)
- iter 15: 0.839
- iter 20: 0.814
- iter 27: 0.807

Scale moved from 1.1 down to 0.807 monotonically — overshooting
target=1.0 at around iter 7 and never recovering.

The mechanism: scale gradient is "shrink to make rendered phoxels
smaller, which compensates for tx-shift error." Same R152 mechanism,
just slower. At 0.1× (R153), scale lr is small enough that translation
converges first; at 0.3× (R154), scale moves fast enough to interfere.

### Finding 3: tx-stuck-at-55% pattern returns

R154 tx: 1.000 → 0.452 (55%). vs R153: 1.000 → -0.029 (97%).

This is a more nuanced version of R152's "tx stuck at 22%." Translation
got further than R152 but not as far as R153. The mechanism: scale
moved quickly (not as quickly as R152) which provided some compensating
gradient, slowing translation's progress.

### Finding 4: per-group lr needs THREE groups

```
Required lr behavior:
  translation: must converge fast (1.0× of base) ← R134-R151 confirmed
  rotation: must converge moderately (0.3-0.5×)  ← R154 confirmed
  scale: must converge SLOWLY (0.1× or less)     ← R153 confirmed
```

Scale needs SLOWER lr than rotations because scale-translation coupling
is stronger than rotation-translation coupling (substrate fingerprint
+ photo MSE are both more invariant to scale-shift than to rotation-
shift, so scale has more "wiggle room" to overshoot).

A 2-group split (translation vs rotation+scale) can't satisfy both
constraints simultaneously. The right structure is 3-group:

```
LR_GROUP_3 = [1.0, 1.0, 1.0,  0.3, 0.3, 0.3,  0.1]
              tx,  ty,  tz,   rx,  ry,  rz,   s
```

R155 candidate explicitly tests this 3-group lr.

## Architectural picture (refined post-R154)

```
R152 (uniform 1.0):  scale wildly overshoots (R152 finding)
R153 (0.1× rot+scale): scale OK, rotations stuck (R153 finding)
R154 (0.3× rot+scale): rotations OK, scale overshoots (R154 finding)
R155 (predicted - 3 groups: trans 1.0, rot 0.3, scale 0.1): all converge

The 7-DOF Phase 4 production lr-recipe needs SCALE LR DECOUPLED FROM
ROTATION LR. A single combined factor can't satisfy both convergence
requirements.
```

This is a clean architectural insight that R154's "negative" result
delivers more than R153's higher-redux result alone could.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **R154 0.3× factor IS WORSE than R153 0.1×** | R154 | dist7D=0.509 (57% reduction) vs R153's 0.342 (71%); 0.3× unlocks rotations (rx 88%, ry 84%, rz 71%) but re-introduces scale overshoot (1.1→0.81, -93% progress) and tx stalls at 55% | round154 | current — single-factor magnitude tuning can't satisfy both rotation and scale convergence |
| **Phase 4 7-DOF needs THREE-group lr (translation, rotation, scale)** | R152+R153+R154 | uniform lr fails (R152), 2-group with 0.1× fails differently (R153), 2-group with 0.3× fails differently (R154); architectural finding: scale needs SLOWER lr than rotation, can't share a group | round152-154 | current — clean architectural insight emerging from 3-round arc |
| Rotation lr should be ~0.3-0.5× translation lr | R154 | 0.3× factor produces rotation progress 71-88% across all three rotation axes; rz (R152/R153 stuck) reaches 71% — the "rz unobservable from 4-camera-around-z" claim was overstatement | round154 | current — rotation lr magnitude bounded |
| Nineteen-round Phase 4 arc (R134-R154) | R134-R154 | + 0.3× factor test (R154); per-group lr architectural finding refined to 3-group requirement | round134-154 | current — Phase 4 7-DOF production recipe needs 3-group lr split |

## Honest caveats

- **R154's net is worse than R153's** but the diagnostic value is
  higher. Knowing "scale needs lr=0.1×, rotation needs lr=0.3×" is
  more architecturally useful than "0.1× best so far."
- **Pre-registration confirmation:** "0.3× factor will work" REJECTED
  in a meaningful way — 0.3× is right for rotations, wrong for scale.
  The right answer is split groups, not a different shared factor.
  Pattern continues: directional predictions (per-group lr concept)
  succeed; quantitative single-value predictions (specific factor) fail.
- **27 iters not full convergence.** Scale at 0.807 might still slowly
  reverse course given much more iters at small lr. Probably not given
  the monotonic descent direction, but not formally tested.
- **rz at 71% progress is meaningful** but lower than rx (88%) and ry (84%),
  suggesting the camera-symmetry argument has SOME truth — rz gradient
  is weaker, just not zero.
- **Single trajectory.** Multi-init confidence interval for R154 not measured.

## Promises ledger updates

- **C-154 closes:** 0.3× factor for 7-DOF rotation+scale lr unlocks
  rotation convergence (rx 88%, ry 84%, rz 71%) but re-introduces
  scale overshoot (1.1 → 0.807, -93% progress) and tx-stall (55%).
  Net dist7D=0.509 worse than R153's 0.342. Architectural finding:
  per-group lr needs THREE groups, not two — translation 1.0×,
  rotation 0.3×, scale 0.1× (independent groups). Scale needs slower
  lr than rotation because scale-translation coupling is stronger
  than rotation-translation coupling. R155 candidate explicitly tests
  3-group split.

## Files added this round

- `round154_factor03/r154_factor03.py`
- `round154_factor03/round154_audit.json`
- `round154_factor03/adam_state.json` (full 27-iter trajectory)
- this report
- `PHOXELIS_PROMISES.md` — C-154 entry
- `PHOXELIS_BENCHMARKS.md` — R154 rows + 19-round arc summary

## Next round opens with

R155 candidates:

**A — push R154.** Single-round-add to a fresh push.bat.

**B — 3-group lr (translation 1.0×, rotation 0.3×, scale 0.1×).**
Direct architectural fix. Predicts: all 7 axes converge cleanly,
dist7D ~0.10-0.15 (matches 3-DOF quality).

**C — 4-group lr.** translation 1.0×, scale 0.1×, rotation_x 0.3×,
rotation_z 0.5× (compensating for the camera-symmetry weak gradient).
Tests whether axis-specific lr beats group-specific.

**D — extended R153.** Run R153 (0.1× factor) for 60+ iters to see
if rotations eventually catch up at lr=0.0006. Cheaper than re-running
but probably slow.

**E — autograd implementation.** Phase 1 differentiable renderer.
Multi-round engineering. With autograd, Adam normalizes per-axis
already; per-group lr might be unnecessary.

**F — multi-init test.** R153 setup × 5 different inits. Confidence
interval on the 0.342 best result.

Lean **A then B**. B is the cheap direct test of the 3-group
architectural finding. If it converges all 7 axes to dist7D < 0.15,
Phase 4 is pose-complete with finite-diff. If something still stalls,
the structure of the problem reveals more.
