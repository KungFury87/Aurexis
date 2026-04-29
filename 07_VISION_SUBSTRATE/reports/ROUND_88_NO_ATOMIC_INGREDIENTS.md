# Round 88 — there are no tight ingredients; composition is non-monotonic

**Date:** 2026-04-29
**Track:** T6 substrate-purpose (R87 follow-up)
**Status:** complete — two architectural findings; R87's wide-ingredient empirical-map approach was already optimal for this substrate

---

## What R88 tested

R87 named the next move: design *tight ingredients* (single-pixel red
dot, 2-pixel horizon line, 32×32 corner clip) that aim to flip exactly
1–2 predicates each. Test whether they raise precision and whether they
compose cleanly. R88 did exactly that.

12 tight ingredients designed, each with explicit `intended` predicate
list (1–2 entries). Empirical fire map measured against neutral 50%-gray
base. Pairwise composition test (66 pairs). Then re-ran R86's 5 demos
using only the tight library.

## Finding 1 — There are no tight ingredients on this substrate

Every "tight" ingredient still fires 10–18 predicates beyond neutral:

```
ingredient            +fires  -fires  intent_hit  breadth
t_red_patch              15      2     1/1        WIDE
t_thin_horizon           18      6     1/1        WIDE
t_corner_blow            12      8     0/1        WIDE
t_dim_corner             10      8     0/1        MEDIUM
t_blue_band              15      7     1/1        WIDE
t_green_band             17      8     1/1        WIDE
t_few_dots               10      7     1/1        MEDIUM
t_offcenter_blob         15     10     2/2        WIDE
t_thin_diagonal          16      4     1/1        WIDE
t_warm_wash              11      4     1/1        WIDE
t_subtle_gradient        12      2     1/1        WIDE
t_low_amp_noise          15     10     1/1        WIDE
```

Every ingredient breadth is ≥10 added predicates. Worse, every tight
ingredient also REMOVES 2–10 baseline predicates that fire on neutral
gray. The "minimum viable perturbation" still moves >12% of the
substrate.

**Why:** predicates depend on global statistics — mean, std, edge
density, gradient mass, FFT energy, palette diversity. Touching any
pixel changes all of those. The substrate has no operators that respond
to local-only changes; therefore no ingredient can be local-only.

This is a deep substrate-shape finding, not a planner failure.

## Finding 2 — Composition is non-monotonic

Of 66 ordered pairs of tight ingredients, **only 5 composed additively**
(actual fires after stacking = union of solo fires). The other 61 had
cancellations: stacking ingredient B on top of ingredient A *removed*
predicates that A had established.

Five concrete cancellation examples:

```
t_red_patch + t_thin_horizon  → loses 7 predicates incl.
    has_mirror_symmetry_horizontal_axis, has_rectilinear_signature
t_red_patch + t_corner_blow   → loses 10 predicates incl.
    has_centered_subject, has_chroma_subsampled_signature
t_red_patch + t_dim_corner    → loses 9
t_red_patch + t_blue_band     → loses 11 incl. has_dominant_red_hue
t_red_patch + t_green_band    → loses 9 incl. has_red_dominant
```

The red patch made the image fire `has_red_dominant` and
`has_dominant_red_hue`. Adding a blue band makes those FALSE because
the global red-mean drops below the dominance threshold.

**Implication:** backward synthesis is non-monotonic under ingredient
composition. Greedy planners that assume "fires accumulate" are wrong
when stacking ingredients. The actual operation is set-difference
+ set-union, and predicting it requires modeling each ingredient's
removal effects — not just additions.

## Re-run results (tight only) vs R86/R87

```
                          P       R       F1
R86 baseline             0.066   0.550   0.113
R87 wide + empirical     0.077   0.700   0.138
R88 tight only           0.068   0.500   0.119
```

**R88 underperforms R87.** Tighter ingredients did NOT improve precision
— in fact recall dropped (0.70 → 0.50) because cancellations destroy
target-predicate fires when stacking.

R87 was already the right method for this substrate's shape.

## What this changes architecturally

The dual-fiber claim has a sharper specification now:

> **The substrate is coarsely surjective in both fibers AND
> non-monotonic under composition in the backward fiber.** Forward
> fiber: an image fires many predicates because real-world signal
> lights many measurements. Backward fiber: an ingredient fires many
> predicates AND cancels many predicates established by prior
> ingredients. The two fibers are structurally asymmetric in this
> respect — forward composition (more signal → more fires, monotonic)
> is not the inverse of backward composition (more ingredients → mixed
> add+cancel, non-monotonic).

This is a non-trivial finding about the calculus the charter postulated.

## Naming the cycle (charter §7)

R86 step 1: synthesizer artifact. R87 step 2: empirical map. R88 step
3 (this round): tight ingredients widening. The widening I'm naming
explicitly: **"increase precision by atomicizing ingredients" was a
plausible-sounding step 4 candidate, and R88 falsified it.** The
substrate forbids that path. So the next widening isn't "tighter
ingredients"; it's accepting non-monotonicity and asking what the
right backward-fiber abstraction actually is — likely
*neighborhood satisfaction* (R84-style nearest-neighbor framing) rather
than *exact-target satisfaction*.

I'm not claiming the next move; I'm naming the dead end.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Tightest ingredient breadth | R88 | 10 predicates added (the smallest of 12 tight ingredients) | current — substrate has no atomic operators |
| Composition cleanness | R88 | 5/66 ordered pairs (7.6%) compose additively | current — backward fiber is non-monotonic |
| Tight-only synthesis F1 | R88 | 0.119 vs R87's 0.138 (wide) | current — tighter ingredients DO NOT improve backward fiber |
| Architectural finding | R88 | "no atomic ingredients" + "non-monotonic composition" | current — sharpens dual-fiber claim |

## Promises ledger updates

- **C-88 closes:** R87 follow-up; tight-ingredient hypothesis falsified; substrate's structural shape on the backward fiber sharpened.

## Files added this round

- `round88_tight_ingredients/round88_audit.json` — 12-ingredient empirical map + 66-pair composition test + 5-demo re-run
- `round88_tight_ingredients/synth_tight_*.png` — 5 constructed images using only tight ingredients
- this report
- `PHOXELIS_PROMISES.md` — C-88 entry
- `PHOXELIS_BENCHMARKS.md` — R88 row

## Next round opens with

R89 — open. Backward fiber's structural shape is now characterized.
The honest next move is reframing: *neighborhood satisfaction* via R84
fingerprint similarity (the constructed image's predicate-fingerprint
should be NEAR the target, not equal to it), or accepting that the
forward fiber is the substrate's strong direction and finding
applications that don't depend on inverting it.

Vincent's call.
