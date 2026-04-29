# Round 87 — backward fiber: empirical ingredient map; recall lifts, precision stuck

**Date:** 2026-04-29
**Track:** T6 substrate-purpose (R86 follow-up)
**Status:** complete — recall 55%→70% via empirical map; honest architectural finding that precision is ingredient-design-limited, not planner-limited

---

## Method

R86's synthesizer used hand-annotated `targets` per ingredient (what
each ingredient AIMS to fire). R87:

1. **Empirical ingredient map.** Run each of the 13 ingredients on a
   neutral 50%-gray base; record the actual predicate fires. Subtract
   the neutral baseline (19 predicates that fire on neutral gray) to
   get each ingredient's "added fires" set.

2. **Precision-aware planner.** Greedy ingredient selection now scores
   `(target_hits − λ × off_target)` using the empirical fire sets, not
   the hand-annotated `targets`. λ ∈ {0.0, 0.30, 0.60, 1.00}.

3. **Re-run R86's 5 demo target states** at each λ. Verify by full vocab
   evaluation on the constructed image (not the estimated fire set).

## Empirical ingredient fire map

| ingredient | total fires (post-neutral) | added | intent-hit ratio |
|---|---|---|---|
| ing_warm_tint        |  29 |  +14 | **6/6** |
| ing_cool_tint        |  28 |  +13 | 4/5 |
| ing_horizontal_stripes | 23 | +13 | 3/5 |
| ing_vertical_stripes |  26 |  +15 | **2/2** |
| ing_horizon_line     |  31 |  +18 | 3/4 |
| ing_clip_highlights  |  39 |  +31 | 3/4 |
| ing_underexpose      |  23 |   +4 | 3/4 |
| ing_grayscale        |  19 |   +0 | **0/5** |
| ing_high_contrast    |  19 |   +0 | **0/2** |
| ing_centered_blob    |  34 |  +24 | 2/3 |
| ing_bright_spots     |  28 |  +14 | **3/3** |
| ing_noise_texture    |  25 |  +17 | 1/4 |
| ing_sky_gradient     |  33 |  +22 | 2/5 |

Neutral 50%-gray base alone fires 19 predicates (`has_centered_subject`,
`has_uniform_field`, etc. — the trivial ones that match a flat gray scene).

**Two dud ingredients** (`ing_grayscale`, `ing_high_contrast`) added zero
new fires when applied to neutral gray. They aren't broken — they need a
non-neutral starting state to make a difference. R86 was running them
post-stack without checking that.

**Three "perfect intent" ingredients** (warm_tint 6/6, vertical_stripes
2/2, bright_spots 3/3) hit every predicate they aimed to fire.

## R87 vs R86 results

```
                     recall   precision   F1
R86 baseline (R86):   0.550     ~0.066    0.113
R87 λ = 0.0:          0.700     0.077     0.138
R87 λ = 0.3:          0.150     0.030     0.050
R87 λ = 0.6:          0.100     0.021     0.035
R87 λ = 1.0:          0.100     0.021     0.035
```

**At λ=0, recall jumped 0.550 → 0.700; F1 0.113 → 0.138.** The empirical
map alone (no penalty term) lifted both metrics over R86 because the
planner now avoids dud ingredients and prefers high-intent-hit ones.

**At λ≥0.3, the planner refuses to use ingredients** because every
ingredient has 13–31 off-target fires, so any non-zero λ makes most
ingredient choices score negative. Synthesis stalls early.

## What this means architecturally

The honest finding: **backward-fiber precision is ingredient-design-
limited, not planner-limited.** Tuning a tradeoff parameter doesn't help
because the tradeoff curve barely exists — every ingredient is a wide
brush. The map shows there are no clean tools.

To push precision higher, the right move is **design tighter
ingredients**: micro-modifications that flip exactly one or two
predicates at a time. Examples (next-round candidates):

- `ing_pure_red_pixel` — replace one pixel with red; targets only
  `has_significant_red_hue` without affecting orientation/structure.
- `ing_thin_horizontal_line` — paint a single 1-pixel-wide row;
  targets `has_horizon_line_signature` without firing edge density.
- `ing_blow_corner_pixel` — clip 1-pixel-area corner to 1.0; targets
  `has_clipped_highlights` without firing exposure-dominant.

Whether tight ingredients can compose without canceling each other out
is the open question. R87 doesn't answer it; R87 documents that it's
the question.

## Naming the cycle (charter §7)

R86 was step 1 (concrete artifact: synthesizer). R87 is step 2 (the
artifact's frame widens — "this works but the precision is terrible").
The widening point: **the substrate has no atomic ingredients**. Every
operator a predicate uses is a coarse global measurement, so every
ingredient that flips a target predicate also flips many bystander
predicates that depend on overlapping operators. This is symmetric to
the forward-fiber observation that every photograph fires 24+ predicates
because real-world signal content lights up many measurements at once.

R86 + R87 jointly say: the substrate is *coarsely surjective* in both
directions. That's the empirical shape, not "the dual-fiber problem is
solved."

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Backward-fiber recall | R87 | **0.700** at λ=0 (up from R86's 0.550) | current |
| Backward-fiber F1 | R87 | **0.138** at λ=0 (up from R86's 0.113) | current |
| Backward-fiber precision | R87 | **0.077** at λ=0 (essentially unchanged from R86's 0.066); architectural finding — ingredient-design-limited, not planner-limited | current |
| Empirical "perfect intent" ingredients | R87 | 3/13 (warm_tint, vertical_stripes, bright_spots) | current — pointer for next-round tighter-ingredient work |

## Promises ledger updates

- **C-87 closes:** empirical ingredient map + precision-aware planner; recall lift; honest architectural finding on precision ceiling.

## Files added this round

- `round87_backward_precision/round87.py` (initial, slow version) and `round87_audit.py` (fast version actually used)
- `round87_backward_precision/round87_audit.json` — empirical map + 4-lambda × 5-target sweep
- `round87_backward_precision/synth_lam{0.0,0.3,0.6,1.0}_*.png` — 20 constructed images
- this report
- `PHOXELIS_PROMISES.md` — C-87 entry
- `PHOXELIS_BENCHMARKS.md` — R87 row

## Next round opens with

R88 — design tighter ingredients (micro-modifications that flip exactly
one or two predicates) and test whether they can compose. If yes,
backward-fiber precision can rise. If no, the substrate has an
architectural ceiling that's worth naming explicitly.
