# Round 74 — vocabulary coverage map; substrate is 78% healthy

**Date:** 2026-04-29
**Track:** T1 vocabulary health (introspection / methodology)
**Status:** complete — coverage map produced; **no retirements needed** (DEAD = corpus-mismatch, not predicate failure)

---

## Coverage map at N=76 combined corpus

128 predicates evaluated; bucketed by health:

| bucket | count | pct | meaning |
|---|---|---|---|
| **HEALTHY** | 100 | 78.1% | rate ∈ [0.05, 0.95] AND IR-clean |
| DEAD        |  12 |  9.4% | always-False on this corpus |
| LOW         |  11 |  8.6% | 0 < rate < 0.05 |
| ERRORED     |   3 |  2.3% | required field missing in bundle |
| COLLIDED    |   2 |  1.6% | IR-equal to another predicate |
| SATURATED   |   0 |  0.0% | always-True (R69 fixed the warm one) |
| HIGH        |   0 |  0.0% | rate > 0.95 |

## What the non-HEALTHY buckets actually are

**DEAD (12)** — every predicate in this bucket needs `image_stack` or
`raw_bayer` bundle fields that the cached photo corpus doesn't supply:

```
has_subframe_motion          has_motion_rightward      has_coherent_motion
has_global_brightness_drift  has_motion_leftward       has_chaotic_motion
has_screen_like_signature    has_motion_downward       has_fast_motion
has_real_motion_validated    has_motion_upward         has_shallow_depth_of_field
```

These are correct predicates evaluated against wrong corpus. R28 already
documented this as "corpus-type artifacts" and they continue to be that.
They activate when the corpus contains phone bursts (R23/R24/R47-era
sessions) or video frames. **Not retired.**

**ERRORED (3)** — same shape, needs `raw_bayer` field:

```
has_polarization_signal   has_subpixel_periodicity   has_spectral_band_anomaly
```

These are R23/R24 polarization predicates. They evaluate to error not
False (the field is missing). **Not retired.**

**COLLIDED (2)** — legitimate near-equivalence:

```
has_text_like_signature  ↔  is_text_dominant_subject
```

`is_text_dominant_subject` is an L4 wrapper around `has_text_like_signature`
(per R61). They naturally agree on most images. The L4 version exists
because text-dominance is a different *claim* than text-presence even
when verdicts coincide on the present corpus. **Not retired.**

**LOW (11)** — predicates with healthy thresholds but few positive cases
in the present corpus:

```
has_high_edge_density            screen_is_dominant_concept
has_screen_displaying_face       has_screen_displaying_text
has_significant_violet_hue       has_significant_magenta_hue
has_dominant_red_hue             has_rectilinear_signature
has_diagonal_signature           has_few_large_blobs
is_high_concept_diversity
```

These would fire more on a corpus with more screen photos / red-painting
art / structured architecture. **Kept; would benefit from corpus diversity.**

## What this means

The substrate is in the right shape — **78% of predicates are doing
useful discrimination on the current corpus**. The 22% that aren't are
either correct-on-wrong-corpus (DEAD, ERRORED), legitimate L1↔L4
redundancy (COLLIDED), or healthy-but-rare (LOW).

**Implication for vocabulary growth strategy:** future predicates should
target the bucket-HEALTHY territory (good discrimination on current
corpus content) rather than try to revive DEAD/ERRORED, which are
gated on corpus type rather than threshold tuning.

## Honest caveats

- **N=76 is small for sub-percent rate measurements.** Predicates at
  1.3% fire rate (1/76) might be less rare at N=10,000.
- **The "HEALTHY" category includes both highly-informative predicates
  (rate ~0.50) and barely-firing ones (rate ~0.08).** Future passes
  could subdivide HEALTHY by entropy.
- **No structural retirement was performed this round.** R75 had been
  scheduled to do the pruning; the coverage map showed there was
  nothing to prune cleanly. R75 is therefore re-purposed or skipped.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Vocabulary health at N=76 | R74 | 100/128 HEALTHY (78.1%); 0 saturated; 12 DEAD (corpus-mismatch); 11 LOW; 2 COLLIDED L1↔L4 | current — first explicit coverage map |
| Predicates needing different bundle fields | R74 | 15 (12 motion/burst + 3 raw_bayer) | current — gated on corpus type, not predicate quality |

## Files added this round

- `round74_coverage_map/round74_audit.py` — coverage-map audit
- `round74_coverage_map/round74_audit.json` — full bucket assignments + per-predicate details
- `PHOXELIS_PROMISES.md` — C-74 entry
- this report

## Next round opens with

R75 was scheduled for pruning, but R74 found no cleanly-prunable
predicates. R75 redirects to whatever delivers next — either P-13
density ceiling (R76's planned target) or another batch L3 author-loop
targeting the LOW-corpus-coverage axes (red, magenta, diagonal,
rectilinear) by adding diverse seeds.
