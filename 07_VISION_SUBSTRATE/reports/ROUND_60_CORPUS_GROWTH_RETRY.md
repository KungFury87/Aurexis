# Round 60 — corpus growth + retry small-N collisions

**Date:** 2026-04-29
**Track:** T1 (Vocabulary Health)
**Status:** complete — corpus N=20→36; 1 L4 predicate's IR-collision dissolved; vocabulary growth path empirically validated

---

## What this round opened on

R59 superseded P-08, P-16, P-17 — Vincent's correct callout that named-social-platform demos do not advance the substrate. The honest next move was the actual structural unblocker: grow the R55 corpus past the small-N regime that had been blocking R54's LLM-authored predicate and 3/5 of R56's L4 predicates.

## What got done

1. **Ran R55 corpus harness ~4 more sessions** via `corpus_harness.py`. State went from N=20 → N=36 across 4 sessions. Output capture was unreliable due to bash pipe interaction with the warning-suppressed Python invocation, but `--report` confirmed N=36, 4 sessions logged.

2. **Re-audited R56's 5 L4 predicates** against the cached verdict matrix at N=36 in `round60_retry_collisions.py`. Result: 3/5 IR-clean (was 2/5 at N=20). One previously-collided L4 predicate (`is_high_concept_diversity`) separated from its small-N twin and now carries information independent of any L1 predicate.

3. **Could not retry R54's `has_busy_textured_scene`** because the R55 corpus_state.json caches verdicts but not images. Logged as P-18 (extend harness to persist enough state to re-evaluate new predicates against the historical corpus).

## Trajectory

| N | always-False | EQ classes | Largest EQ | L4 IR-clean |
|---|---|---|---|---|
| 4 | 52 | 12 | 52 | — |
| 12 | 27 | 11 | 27 | — |
| 20 | 23 | 6 | 23 | 2/5 |
| **36** | **15** | **2** | **15** | **3/5** |
| R28 baseline (N=161) | 12 | 2 | ~12 | — |

Every metric still converging monotonically toward the R28 baseline. **At N=36 the eq-class count already matches R28's 2.** The architecture's small-N collapse story (R53/R54/R56) is now empirically resolved: more corpus → false equivalence classes break apart.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Small-N collapse dissolves with corpus growth | R60 | At N=36, 3/5 L4 predicates IR-clean (was 2/5 at N=20); EQ classes drop 6→2; one collision (`is_high_concept_diversity`) genuinely resolved | 36 web-pulled images, 4 sessions, R55 corpus_state | current — first empirical validation of the corpus-size-floor hypothesis from R53 |

## L4 predicates promotable

Three L4 predicates now qualify for promotion to `vocab.aurex` as IR-clean compositional predicates:

```
is_indoor_warm_scene       has_indoor_scene_signature AND has_warm_palette
is_text_dominant_subject   has_text_like_signature AND has_genuine_text_not_screen
is_high_concept_diversity  has_polychromatic_palette AND has_many_small_blobs
```

The remaining two collisions don't dissolve from corpus growth alone:
- `is_outdoor_landscape`: stays always-False because `has_horizon_line_signature AND has_low_edge_density` rarely co-occur in the source-router corpus mix. This is a *coverage* issue, not an IR issue — needs a corpus with more landscape photos.
- `is_busy_warm_scene`: still ≡ `has_warm_palette` because `has_many_corners` fires on 91% of images at R28. The composite is genuinely dominated by warm-palette. Either redefine the predicate or accept the collision.

The vocabulary would go from 103 to **106 predicates** if these three are promoted. Note: L4 predicates currently live in `round56_l4_compositional/` as Python lambdas, not in the surface DSL. **R61 (Sensor layer in DSL)** is the right next round for promoting both R56 L4 predicates and R58 sensor predicates to first-class typed substrate.

## Promises ledger updates

- **C-60** opens: corpus growth N=20→36 + L4 retry; first empirical validation of the corpus-size-floor hypothesis.
- **P-18** opens: extend the corpus harness to persist enough per-image state that new predicates can be evaluated against the historical corpus retroactively.
- **P-19** opens: actually promote the 3 IR-clean L4 predicates to `vocab.aurex` as first-class DSL predicates (subsumes part of R61's "sensor layer in DSL").

## What this round changes

The audit's "small-N collapse caveat" that's been attached to every L4/L2/sensor measurement since R53 now has a counter-measurement: **the collapse dissolves with corpus growth as the architecture predicts**. The pattern works. The harness is real.

## Files added this round

- `round60_retry_at_n36/round60_retry_collisions.py` — re-audit script
- `round60_retry_at_n36/round60_results.json` — full L4 verdict patterns + IR-cleanness
- `round55_corpus_harness/corpus_state.json` — updated state (N=36, 4 sessions)
- this report

## Next round opens with

`python phoxelis_audit.py`. STALE count after R60 should be 5 (P-08/P-16/P-17 superseded R59 cleared 1 long-stale + 2 fresh-stale; R60 closed nothing stale but moved P-19 candidate work into the queue).

R61 candidates:
- **R61 — DSL-promote the IR-clean L4 predicates** to first-class surface DSL form (P-19 partial close). Subsumes "sensor layer in DSL" if R58 gets the same treatment.
- **R61 — Run harness 3-5 more sessions** to push N from 36 to ~70+, retry all small-N concerns one final time, see if any others dissolve.
- **R61 — Extend harness to persist images (P-18)** so R54's predicate and any future LLM-authored ones can be retried retroactively.
