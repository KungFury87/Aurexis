# Round 155 — 3-group lr REJECTS pre-registered "all 7 axes converge" prediction; R155 worse than R153 (0.646 vs 0.342); architectural finding: SEQUENTIAL convergence beats PARALLEL convergence in 7-DOF Phase 4

**Date:** 2026-05-01
**Track:** T7 (Phase 4 7-DOF lr-group structure)
**Status:** complete — 3-group lr [translation 1.0×, rotation 0.3×, scale 0.1×] gave dist7D=**0.646** at iter 24 (45.0% reduction), WORSE than R153's 2-group 0.1× (0.342, 71%); per-axis: scale converges (91%), ry well (87%), but tx stuck (41%), rz back to stuck (7%), rx partial (63%); pre-registered "all 7 axes converge to dist7D ~0.10-0.15" REJECTED; deeper architectural finding: in finite-diff 7-DOF Phase 4, **SEQUENTIAL convergence (translation finishes first while everything else stays slow) beats PARALLEL convergence (all axes moving simultaneously)** because rotations changing during translation makes translation gradient direction noisy

---

## What R155 settles

R152-R154 mapped the 7-DOF Phase 4 lr-group structure: uniform lr fails
(R152 scale overshoots), 0.1× rot+scale works partially (R153 best so
far at 71%), 0.3× rot+scale fails differently (R154 scale overshoots).
The architectural insight from R154: scale and rotation need DIFFERENT
lr scalings — they can't share a group.

R155 tested the obvious 3-group fix: translation 1.0×, rotation 0.3×
(R154-confirmed working for rotations), scale 0.1× (R153-confirmed
working for scale).

Pre-registered prediction: all 7 axes converge cleanly to dist7D
~0.10-0.15, matching 3-DOF quality.

The data rejected this. R155 is WORSE than R153 (dist7D 0.646 vs 0.342).
The architectural insight is more interesting than the per-group concept
suggested.

## Method

Identical to R153/R154 except `LR_GROUP = [1.0, 1.0, 1.0, 0.3, 0.3, 0.3, 0.1]`.
Three independent lr scalings: translation full, rotation 0.3× (the
R154 sweet spot for rotations), scale 0.1× (the R153 sweet spot for
scale). 24 iterations.

## Results — at iter 24

```
axis    init     current    target    progress%   verdict
tx      1.000    0.595      0.000     40.5%       STUCK
ty      0.500    0.143      0.000     71.4%       partial
tz      0.000   -0.047      0.000     drift
rx      0.200   -0.073      0.000     63.4%       partial
ry      0.200    0.026      0.000     86.8%       OK
rz      0.200    0.187      0.000     6.5%        STUCK (rebounded)
s       1.100    1.009      1.000     91.1%       OK
```

dist7D = 0.646 (45.0% reduction). Worse than R153's 0.342 (71%).

### Four-condition comparison

| round | LR config | best dist7D | redux | scale | rotations | translation |
|---|---|---|---|---|---|---|
| R152 | uniform 1.0× | 0.881 | 25% | overshoots -229% | rx 94% / others stuck | tx 22% stuck |
| **R153** | 2-group 0.1× rot+scale | **0.342** | **71%** | converges 95% | stuck 5/39/5% | tx 97% / ty 90% |
| R154 | 2-group 0.3× rot+scale | 0.509 | 57% | overshoots -93% | rx 88 / ry 84 / rz 71% | tx 55% stuck |
| R155 | 3-group T=1/R=0.3/S=0.1 | 0.646 | 45% | converges 91% | rx 63 / ry 87 / rz 7% | tx 41% stuck |

R155 has the WORST translation convergence of any condition (tx 41%
stuck, vs R153's 97%). Even though scale converges (91%) and one
rotation moves well (ry 87%), the failure to drive translation
dominates net dist7D.

### Finding 1: pre-registered "all 7 axes converge" REJECTED

The hypothesis was elegant: combine R153's scale-handling (0.1×) with
R154's rotation-handling (0.3×) and translation should converge as it
did in R153.

The data: translation converged in R153 because everything else was
slow (rotations 5%, scale 95% with smooth descent). It did NOT converge
in R155 because rotations moving at 0.3× provided continuous gradient
perturbations.

### Finding 2: rz REBOUNDED to stuck pattern

R154 had rz at 71% (the "rz unobservable" claim was overstatement).
R155 has rz back at **6.5%** — barely moved from init.

Why the regression? R154's success on rz came from rotations moving
together — rx, ry, rz all rotating consistently. With scale also
moving, the combined gradient signal stayed strong. In R155, scale's
slow update means scale stays mismatched longer, which interferes
with rotation gradients differently.

This is consistent with the parallel-vs-sequential framing: rz needs
not just enough lr, but a stable enough gradient to be informative.
When other axes are moving in directions that affect rz's gradient,
the per-axis Adam normalization takes time to converge.

### Finding 3: SEQUENTIAL > PARALLEL convergence in 7-DOF finite-diff

The architectural finding from R152-R155:

```
R153 (2-group, 0.1×):  rotations slow → translation finishes first → 71% redux
R154 (2-group, 0.3×):  rotations medium → mixed convergence → 57% redux
R155 (3-group, optimal-per-axis on paper): all moving → conflict → 45% redux
```

Counterintuitively, the PARALLEL approach (each axis at "right" lr)
performs WORSE than the SEQUENTIAL approach (one axis at right lr,
rest at slow lr). The mechanism:

- **Finite-diff gradient noise scales with neighbor-axis movement.**
  When other axes are mid-update during finite-diff probing, the
  loss difference (loss(p+ε)-loss(p-ε)) for a given axis includes
  noise from how the other axes' values have shifted between probes.
- **Adam's per-axis m and v moments** assume gradient signal stability
  for momentum to be useful. With multi-axis movement, the gradient
  for any single axis fluctuates more, polluting the moments.

In autograd, this would be cleaner — gradients are computed at a single
parameter snapshot. With finite-diff, the noise compounds.

The right strategy for finite-diff 7-DOF Phase 4 might therefore be
**STAGED training**:
- Phase 1 (iters 1-15): freeze rot+scale at init, train translation
- Phase 2 (iters 16-25): freeze translation, train rotations
- Phase 3 (iters 26-35): freeze all but scale, train scale to hit 1.0
- Phase 4 (iters 36-45): unfreeze all, fine-tune

R156 candidate.

### Finding 4: substrate J=0.873 mid-convergence — content-validity preserved

R155 substrate J reaches 0.873 by iter 24. Lower than R153's 0.971
(at translation-converged state) but well above R152's 0.842 (at
fully-stalled state).

Substrate is "knowing the right approximate content" even when spatial
parameters disagree. The content-validity-as-regularizer architecture
(R142) holds across all 7-DOF configurations tested; the question is
purely about which spatial dimensions converge first.

## Architectural picture (refined post-R155)

Phase 4 7-DOF training has TWO related-but-distinct issues:

**Issue 1 — per-axis lr magnitude (R152-R154 mapped):**
- Translation: lr = 1.0× (any slower = stuck)
- Rotation: lr = 0.3× (10× too slow, 1.0× has rotation-trans coupling)
- Scale: lr = 0.1× (faster = scale-trans coupling)

**Issue 2 — gradient stability under simultaneous multi-axis updates (R155 surfaced):**
- Finite-diff gradients become noisy when other axes are mid-update
- Sequential (one at a time) > parallel (all at once) for finite-diff
- Autograd would dissolve this issue; finite-diff makes it structural

R155's data rejects the "just combine the right lrs" approach because
it doesn't address Issue 2. The fix path is staged training (R156)
or autograd (R161+ multi-round arc).

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| **3-group lr does NOT outperform R153's 2-group** | R155 | dist7D=0.646 (45%) vs R153's 0.342 (71%); per-axis: tx stuck 41% (R153 had 97%), rz rebounded to 7% (R154 had 71%) | round155 | current — naive per-group lr combination fails |
| **SEQUENTIAL > PARALLEL convergence in finite-diff 7-DOF** | R152-R155 | 4-condition arc shows: when one axis is right-lr and others slow (R153), translation converges in 27 iters; when all axes have "right" lr (R155), they interfere via finite-diff gradient noise | round152-155 | current — architectural insight; staged training is the fix |
| Phase 4 7-DOF needs STAGED training (R156 candidate) | R152+R153+R154+R155 | freeze rot+scale, train translation; freeze translation, train rotations; freeze all but scale, train scale; finally unfreeze all | round152-155 | predicted — R156 will test |
| Twenty-round Phase 4 arc (R134-R155) | R134-R155 | + 3-group rejection (R155); architectural insight crystallized: 7-DOF finite-diff needs staged not parallel training | round134-155 | current — Phase 4 7-DOF production recipe needs sequential structure |

## Honest caveats

- **24 iters not full convergence.** R155 might still descend with
  more iters at smaller lr; R153 was best at iter 16 and stable
  through 27. R155 is still descending slowly.
- **The "noise compounding" mechanism is partly speculation.** The
  4-condition data is consistent with sequential > parallel, but the
  specific noise mechanism would be confirmed by autograd comparison
  (which would have stable gradients).
- **rz at 6.5% in R155 vs 71% in R154 is striking.** It's not just
  "slightly worse" — rz fully reverted to stuck. This deserves
  isolated study; could be Adam-state-leftover effects from the
  resumed training pattern.
- **Pre-registered prediction REJECTED. Pattern (5 of last 9 fully
  confirmed, 4 partial, 0 fully rejected before R155) is now 5/10/1.**
  Quantitative predictions still tend to fail; the directional
  prediction "3-group structure is needed" was right (R154 confirmed
  it) — what was wrong was assuming the lr-magnitudes alone fix it.
- **R155 result is real production data even if "negative":** the
  architectural insight (sequential > parallel) is more useful for
  Phase 4 than another %% improvement would have been.

## Promises ledger updates

- **C-155 closes:** 3-group lr structure [translation 1.0×, rotation
  0.3×, scale 0.1×] does NOT outperform R153's 2-group 0.1×. Best
  dist7D=0.646 (45% reduction) vs R153's 0.342 (71%). Pre-registered
  "all 7 axes converge to dist7D ~0.10-0.15" REJECTED. Deeper
  architectural finding: in finite-diff 7-DOF Phase 4, SEQUENTIAL
  convergence (one axis at right lr, others slow) beats PARALLEL
  convergence (all axes at "right" lr) because finite-diff gradient
  noise compounds when multiple axes update simultaneously. The fix
  path narrows: staged training (R156) or autograd (multi-round arc).

## Files added this round

- `round155_3group/r155_3group.py`
- `round155_3group/round155_audit.json`
- `round155_3group/adam_state.json`
- this report
- `PHOXELIS_PROMISES.md` — C-155 entry
- `PHOXELIS_BENCHMARKS.md` — R155 rows + 20-round arc summary

## Next round opens with

R156 candidates:

**A — push R155.** Single-round-add to a fresh push.bat.

**B — staged training.** 3-phase: train translation only (freeze
rotation+scale), then rotation only, then scale only. R155 architectural
prediction tested. Cheapest direct test.

**C — staged training with overlap.** Phase 1 (1-15): translation
unfrozen, rotation+scale frozen. Phase 2 (16-25): translation+rotation
unfrozen, scale frozen. Phase 3 (26-35): all unfrozen. Tests
gradual-unfreezing.

**D — autograd implementation.** Multi-round arc. Eliminates finite-diff
gradient noise entirely. Predicts R155-style 3-group lr WOULD work
with autograd.

**E — multi-init confidence interval at R153.** Establishes whether
0.342 is robust or lucky.

**F — different scene composition at R153.** Tests whether 71%
generalizes.

Lean **A then B**. B is the cheapest direct test of the SEQUENTIAL
architectural prediction. If staged training reaches dist7D < 0.15,
the architectural insight is confirmed and Phase 4 has a complete
finite-diff-compatible 7-DOF recipe. If staged training also stalls,
autograd becomes the unambiguous next priority.
