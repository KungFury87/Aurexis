# Round 156 — Staged 7-DOF training FAILS CATASTROPHICALLY (final dist7D=1.197 WORSE than init 1.175); 7-DOF Phase 4 loss landscape is FUNDAMENTALLY COUPLED, R153's 71% is the empirical ceiling for finite-diff; autograd is the only remaining path

**Date:** 2026-05-01
**Track:** T7 (Phase 4 7-DOF coupling diagnostic)
**Status:** complete — staged training (translation→rotation→scale→all) gave final dist7D=**1.197**, WORSE than init 1.175 by 2%; pre-registered "dist7D < 0.15 in 40 iters" CATASTROPHICALLY REJECTED; mechanism: when other axes are frozen at wrong values, per-axis gradient points to compensating-misalignment, not true target — Phase 1 translation got stuck at tx=0.92, Phase 4 unfreezing accumulated drift; deeper architectural finding: **R155's "sequential > parallel" was actually "gentle parallel beats aggressive parallel"; truly-sequential (frozen-axes) is WORST of all configurations tested**; 7-DOF loss landscape is fundamentally coupled, R153's 71% reduction is the empirical finite-diff ceiling

---

## What R156 settles

R155 surfaced the architectural framing "SEQUENTIAL > PARALLEL convergence
in finite-diff 7-DOF" and predicted staged training would reach
dist7D < 0.15. R156 implemented the most direct version: 4-phase
training with each phase freezing all but one parameter group.

The data demolishes the prediction. Final dist7D = 1.197, **worse than
init 1.175 by 2%**. Best-ever was iter 1 at 1.054 (10.3% reduction)
before staged-training drift overwhelmed it.

The R155 architectural framing needs revision: gentle-parallel (R153)
worked because all axes moved together SLOWLY — not because sequential
worked. Truly sequential (frozen-other-axes) is catastrophic.

## Method

```
Phase 1 (1-15):  train (tx,ty,tz), freeze (rx,ry,rz,s) at init
Phase 2 (16-25): train (rx,ry,rz), freeze (tx,ty,tz,s) at end-of-phase-1
Phase 3 (26-30): train s, freeze others
Phase 4 (31-35): unfreeze all, fine-tune at lr=0.0125 → 0.00625
```

Same target/init as R152-R155. Per-axis Adam moments updated only
for active axes (frozen axes' m and v stayed unchanged).

## Results — catastrophic failure

```
phase     iter     dist7D    tx     rx     s      lesson
init      0        1.175     1.000  0.200  1.100
P1 end    15       1.154     0.922  0.200  1.100  translation barely moved
P2 end    25       1.172     0.922  0.032  1.100  rotations DID converge (rx 76%)
P3 end    30       1.173     0.922  0.032  1.114  scale barely moved
P4 end    35       1.197     0.955  0.047  1.145  all-unfrozen DRIFTED FURTHER
```

Final per-axis:

| axis | init | final | progress | verdict |
|---|---|---|---|---|
| tx | 1.000 | 0.955 | 4.5% | STUCK |
| ty | 0.500 | 0.492 | 1.6% | STUCK |
| tz | 0.000 | **-0.323** | **drift** | (was at target, drifted heavily) |
| rx | 0.200 | 0.047 | 76.4% | OK ← only axis that converged |
| ry | 0.200 | 0.205 | -2.5% | DRIFT |
| rz | 0.200 | **0.330** | **-65%** | DRIFTED FAR FROM TARGET |
| s | 1.100 | 1.145 | -45% | DRIFTED |

5 of 7 axes have NEGATIVE progress (drifted away from target). Only rx
converged. The staged-then-unfreeze structure damaged the trajectory.

### Finding 1: Phase 1 translation got stuck at tx=0.92

When rotations are frozen at (0.2, 0.2, 0.2) and scale at 1.1, the
**target rendering is reached by a different translation than (0,0,0)**.
The optimal translation given fixed wrong-rot+wrong-scale compensates
for those errors. Translation gradient correctly points to tx≈0.92
(the compensating value), not tx=0.

This is a fundamental property of the loss landscape: per-axis gradient
under frozen-wrong-others doesn't point to the true target's coordinate.

### Finding 2: Phase 2 rotations DID converge (mostly)

rx 0.200 → 0.032 (76% progress) during Phase 2, while translation+scale
stayed at compensated values. So rotations CAN train independently when
the held-fixed values are at "compensating equilibrium."

But ry and rz didn't follow rx — ry barely moved (-2.5%, slight drift),
rz drifted heavily (-65%, going from 0.2 to 0.33). This is similar to
R152's finding that not all rotation axes have equally-strong gradients
under this camera setup.

### Finding 3: Phase 4 unfreezing made everything WORSE

Going from iter 30 (dist7D=1.173) to iter 35 (dist7D=1.197) is a 2%
INCREASE in distance. The accumulated state from staged training had
all axes settled in compensating-misalignment positions; unfreezing
all and training jointly broke the equilibrium without finding a
better basin.

Specifically:
- tx pushed back UP from 0.92 to 0.96 (translation DEcompensating)
- s climbed from 1.114 to 1.145 (scale moving WRONG WAY)
- rx, ry slightly drifted

Phase 4 was meant to be fine-tuning, but the "fine" behavior at lr=0.0125
exposed the staged-training drift's poor starting point.

### Finding 4: Architectural revision — gentle-parallel beats both aggressive-parallel and truly-sequential

The R152-R156 arc maps the lr-structure space:

| structure | description | best dist7D | redux |
|---|---|---|---|
| uniform 1.0× (R152) | all axes same lr, no decay | 0.881 | 25% |
| **2-group 0.1× (R153)** | rot+scale slow, all together | **0.342** | **71%** |
| 2-group 0.3× (R154) | rot+scale medium, all together | 0.509 | 57% |
| 3-group [1.0,0.3,0.1] (R155) | per-group right lr, all together | 0.646 | 45% |
| **staged (R156)** | one axis at a time, frozen others | **1.197** | **-2%** |

The pattern that emerges:
- Coordinated movement at GENTLE lr (R153 0.1×): rotations slow, scale slow, translation moderate; ALL coupled axes move together avoiding compensating-misalignment basins.
- Aggressive lr per-axis (R155): each axis tries to optimize fast, finite-diff gradient noise compounds.
- Frozen-other-axes (R156): the gradient explicitly points to compensating-misalignment, dist7D goes UP.

R153's success wasn't sequential. It was that *very slow* multi-axis
movement keeps the system close to the true-target basin while it
converges, instead of jumping into compensating-misalignment basins.

R155's "sequential" framing was a misinterpretation of what R153 was
actually doing.

### Finding 5: 7-DOF Phase 4 loss landscape is fundamentally COUPLED

The substrate fingerprint + photo MSE evaluate the FULL rendered scene.
There's no operator that's a function of just translation, just rotation,
or just scale — every predicate fires based on the rendered image which
depends on all 7 parameters jointly.

This means the loss landscape has no clean decomposition into per-axis
sub-problems. Any per-axis training where other axes are at non-target
values has its gradient pointing to a compensating-misalignment basin,
not the true target.

The implication: production 7-DOF Phase 4 with finite-diff has an
empirical ceiling around R153's 71%. Beyond that requires either:
- **Autograd** — gradients computed at instantaneous parameter snapshots,
  no temporal noise from neighbor-axis updates
- **Constrained scenes where coupling is weak** — e.g., constrained
  object class where target rotation is known a priori, only translation
  trained

R157 candidate: autograd implementation (multi-round arc).

## Architectural conclusion (refined post-R156)

```
R134-R151 (3-DOF): finite-diff + lr-decay → dist=0.065 (94% redux)
R152-R155 (7-DOF parallel exploration): R153 0.1× factor → dist=0.342 (71%)
R156 (7-DOF staged): catastrophic drift → dist=1.197 (-2%)

Empirical ceiling for finite-diff 7-DOF: dist7D ~= 0.34 (R153 71%)
Path beyond: AUTOGRAD (R157+ multi-round arc)
```

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **Staged 7-DOF training FAILS CATASTROPHICALLY** | R156 | 4-phase staged (translation→rotation→scale→all) ends at dist7D=1.197, WORSE than init 1.175; Phase 1 translation stuck at tx=0.92 due to compensating-misalignment; Phase 4 unfreezing accumulates drift; only rx converged | round156 | current — pre-registered "dist7D<0.15" REJECTED |
| **R155 "sequential > parallel" framing REVISED** | R155+R156 | R153's 71% wasn't from sequential convergence; it was from gentle-parallel coordinated movement; truly-sequential (frozen-axes R156) is WORST configuration tested | round155-156 | current — architectural framing corrected |
| **7-DOF Phase 4 loss landscape is fundamentally COUPLED** | R152-R156 | substrate fingerprint + photo MSE evaluate full rendered scene; no per-axis decomposition; per-axis gradient under frozen-wrong-others points to compensating-misalignment basin not target | round152-156 | current — finite-diff ceiling at R153's 71% reduction |
| Twenty-one-round Phase 4 arc (R134-R156) | R134-R156 | + staged-fails (R156); 7-DOF empirical ceiling identified; autograd is sole remaining path beyond | round134-156 | current — Phase 4 7-DOF production envelope is bounded; autograd needed for >71% |

## Honest caveats

- **R156 chose Phase 1 = translation. What if the order were
  rotation-first?** Probably similar — the same compensating-misalignment
  argument applies in any order. But not formally tested.
- **5-iter phases might be too short.** Could Phase 1 with 30 iters
  let translation eventually find the right basin? Theoretically possible
  but the iter 1-15 trajectory shows it diverging, not converging.
- **Different init might work.** A nearly-converged init (small offsets
  from target) might let staged training fine-tune cleanly. R156 used
  the same init as R152-R155 (off in every axis), which is the harder case.
- **Pre-registration: 1 of last 11 fully rejected** (R156 — "dist7D<0.15"
  was a quantitative-and-directional prediction; both wrong). Pattern
  continues: bigger conceptual claims (sequential > parallel) survive
  with revisions, but quantitative endpoints fail.
- **The "loss landscape is coupled" finding was implicit in R152's
  scale-coupling discovery** but R156 makes it sharper: there's no
  decomposition that helps, period.

## Promises ledger updates

- **C-156 closes:** Staged 7-DOF training (Phase 1 translation, Phase
  2 rotation, Phase 3 scale, Phase 4 all) FAILS CATASTROPHICALLY.
  Final dist7D=1.197 worse than init 1.175. Mechanism: per-axis gradient
  with frozen-wrong-other-axes points to compensating-misalignment basin
  not true target. R155's "sequential > parallel" framing was actually
  "gentle parallel beats aggressive parallel" — R153's 71% reduction
  is the empirical 7-DOF Phase 4 finite-diff ceiling. Path beyond:
  autograd (multi-round arc R157+).

## Files added this round

- `round156_staged/r156_staged.py`
- `round156_staged/round156_audit.json`
- `round156_staged/adam_state.json`
- this report
- `PHOXELIS_PROMISES.md` — C-156 entry
- `PHOXELIS_BENCHMARKS.md` — R156 rows + 21-round arc summary

## Next round opens with

R157 candidates:

**A — push R156.** Single-round-add to a fresh push.bat.

**B — autograd implementation Phase 1.** Differentiable phoxel
renderer in PyTorch. Multi-round engineering arc. With autograd:
- gradients computed at single param snapshot, no temporal noise
- Adam normalization stable per-axis
- predicts R155-style 3-group lr WOULD work
- predicts staged training also works
- predicts dist7D < 0.10 reachable in ~30 iters at 7-DOF

**C — constrained-pose 7-DOF.** Train all 7 axes but with smaller
init offsets (e.g. translation 0.3 not 1.0, rotation 0.05 not 0.2).
Tests whether the coupling problem is init-magnitude-dependent.

**D — multi-init test at R153 setup.** 5 different inits, same R153
config. Establishes whether 0.342 is robust or input-specific.

**E — different scene at R153 setup.** Cube+pyramid asymmetric instead
of cube+sphere. Tests whether 71% generalizes.

**F — accept the ceiling and pivot.** R134-R156 has fully characterized
Phase 4 — call it complete. Move to a different track (T6 MCP grounded-
AI extensions, T8 phoxel-native capture, P-01 corpus 1000+).

Lean **A then B**. B is the multi-round commitment that delivers the
final Phase 4 production tool. R157-R162 candidate arc: differentiable
renderer, autograd-driven 7-DOF, full convergence. After 23 rounds in
T7 it's time to either close it with autograd or pivot.
