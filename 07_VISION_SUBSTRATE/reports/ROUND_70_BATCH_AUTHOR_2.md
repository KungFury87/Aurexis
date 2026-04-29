# Round 70 — second batch L3 author-loop, base-rate data emerges

**Date:** 2026-04-29
**Track:** T1 vocabulary health, P-10 (LLM-as-author at scale)
**Status:** complete — vocabulary 117 → 122; 5/10 candidates promoted; cumulative R68+R70 base rate 11/18 = 61%

---

## What got built

10 candidate predicates targeting unrepresented territory:
- color extremes (grayscale, blue/green channel dominance)
- spatial orientation mass (H/V/diagonal)
- center-vs-edge lighting variations
- L4 composites (blur+low-contrast, vivid+high-contrast)

All bodies use existing operators. No new operators registered.

## R70 candidate audit (combined N=76)

| candidate | fired | rate | result |
|---|---|---|---|
| has_pure_grayscale_palette              | 14/76 | 18.42% | **PROMOTE** |
| has_dominant_blue_channel               | 32/76 | 42.11% | **PROMOTE** |
| has_dominant_green_channel              | 36/76 | 47.37% | **PROMOTE** |
| has_strong_horizontal_orientation_mass  | 10/76 | 13.16% | **PROMOTE** |
| is_blurry_low_contrast_scene            |  5/76 |  6.58% | **PROMOTE** |
| has_strong_vertical_orientation_mass    |  2/76 |  2.63% | defer (low rate) |
| has_diagonal_orientation_mass           |  2/76 |  2.63% | defer (twin: `has_diagonal_signature`) |
| has_bright_center_dark_edges            | 13/76 | 17.11% | defer (twin: `has_center_weighted_lighting` R17) |
| has_dark_center_bright_edges            |  6/76 |  7.89% | defer (twin: `has_edge_weighted_lighting` R17) |
| is_vivid_high_contrast_scene            |  3/76 |  3.95% | defer (low rate + small-N borderline) |

**5/10 promoted, 5/10 deferred.** Vocabulary 117 → 122. Eq classes 110, multi 6.

## Cumulative batch-author base rate

| round | promoted | total | rate |
|---|---|---|---|
| R68 | 6 | 8 | 75% |
| R70 | 5 | 10 | 50% |
| **cumulative** | **11** | **18** | **61%** |

Base rate stabilizing around 60% across two batches. With small-batch
variance this could easily land in [50%, 70%] long-term.

## Rejection-type taxonomy (from R70)

| reject type | count | what it means |
|---|---|---|
| IR-collision with existing predicate | 3 | the substrate already discriminates this distinction (R17 lighting predicates re-discovered) |
| Fire rate too low (<5%) | 1 | predicate is real but corpus has too few positive cases |
| Both (low rate + collision/borderline) | 1 | needs corpus growth to validate |

The IR-collision rejects are *useful diagnostic*: they tell me the
substrate is denser than my candidate-generation pass assumed. Future
batches should consult `vocab.aurex` for likely overlaps before
authoring.

## What this round changes

1. **Base-rate data accumulates.** Two batches give 11/18 = 61%. P-10
   ("LLM-as-author at scale") now has empirical grounding rather
   than aspirational framing.
2. **R17 lighting predicates re-discovered as collision partners.**
   `has_center_weighted_lighting` and `has_edge_weighted_lighting`
   were added in R17 and have been quietly serving — R70 candidates
   collided with them, surfacing them as live discriminators on the
   current corpus.
3. **L4 composite still partially redundant.** R68's
   `is_likely_jpeg_pipeline_output` collapsed to its constituent;
   R70's `is_vivid_high_contrast_scene` has fire rate 3/76 — so
   even though it might be IR-clean at higher N, it's currently
   below useful firing density. Composite predicates need both
   constituents to fire on overlapping but distinct subsets to add
   discrimination.

## Honest caveats

- **N=76 is still small for IR analysis at 122-predicate scale.**
  R63 hypothesis suggests further small-N collisions will dissolve
  with corpus growth.
- **Two of the deferred (vertical orientation, vivid-high-contrast)
  may IR-clean later.** Re-test in a future round with N>200.
- **R17 collisions don't mean the R70 candidates are wrong.** They
  mean the substrate already names that distinction; my candidates
  were redundant rather than incorrect.

## Headline benchmark rows

| metric | round | value | status |
|---|---|---|---|
| Total predicates | R70 | **122** (117 + 5 batch-authored) | current |
| Cumulative batch-author base rate | R70 | 11/18 = 61% | first multi-round datapoint |
| Rejection types observed | R70 | IR-collision with existing predicate (R70:3, R68:1), low fire rate (R70:2), saturation (R68:1) | current |

## Files added this round

- `round70_batch_authoring_2/round70_candidates.aurex` — 10 candidate predicates
- `round70_batch_authoring_2/round70_audit.py` — audit script
- `round70_batch_authoring_2/round70_audit.json` — full results
- `vocab.aurex` — 5 promoted + comment block on 5 deferred
- `PHOXELIS_PROMISES.md` — C-70 entry
- `PHOXELIS_BENCHMARKS.md` — R70 row + cumulative base-rate row
- this report

## Next round opens with

R71 — incremental corpus growth at native resolution (push toward P-01)
+ optional: re-audit deferred R70 candidates at the larger N to see if
fire rates or IR-collisions resolve.
