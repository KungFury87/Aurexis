# Round 61 — first L4 promotions land in DSL: vocabulary 103 → 106

**Date:** 2026-04-29
**Track:** L4 (compositional inference)
**Status:** complete — P-19 closed; first L4 predicates as first-class DSL entries

---

## What this round opened on

R60 confirmed three L4 predicates from R56 were IR-clean at N=36:
- `is_indoor_warm_scene`
- `is_text_dominant_subject`
- `is_high_concept_diversity` (the one whose collision dissolved with corpus growth)

P-19 opened with the promotion task: lift them from R56's Python lambdas into vocab.aurex as first-class DSL predicates.

## The DSL-shape problem

The surface DSL composes operators over typed fields, not predicates over predicate verdicts. So an L4 predicate written naturally as `AND(predicate_verdict("has_warm_palette"), predicate_verdict("has_indoor_scene_signature"))` doesn't parse — there's no `predicate_verdict` operator yet.

Two options:
- **Inline the L1 bodies** into each L4 predicate's body. Works today; mechanically equivalent; uglier source.
- Add a `predicate_verdict(name)` operator to the runtime. Cleaner; needs runtime + DSL changes.

Picked inlining. When the DSL grows the cleaner operator (a future round if it earns its keep), these can be rewritten in their natural composite form.

## Promoted predicates

```
predicate is_indoor_warm_scene
  expects scene:image, color_scene:color_image
  returns bool
  intent  composite_indoor_scene_AND_warm_palette
  body    AND(AND(OR(lt(mean(scene), 0.45),
                     gt(center_minus_edge_brightness(scene), 0.05)),
                  lt(atmospheric_haze_score(color_scene), 0.10)),
              gt(sub_s(rgb_warmth_score(color_scene),
                       rgb_coolness_score(color_scene)), 0.10))

predicate is_text_dominant_subject
  expects scene:image, row_y:int
  returns bool
  intent  composite_text_like_AND_genuine_text_not_screen
  body    AND(AND(AND(gt(row_autocorr_peak(scene, row_y), 0.30),
                      gt(high_frequency_residual(scene), 0.15)),
                  gt(edge_density(scene, 1.0), 0.10)),
              AND(gt(text_likeness_score(scene, row_y), 0.50),
                  gt(sub_s(text_likeness_score(scene, row_y),
                           screen_likeness_score(scene, row_y)), 0.05)))

predicate is_high_concept_diversity
  expects scene:image, color_scene:color_image
  returns bool
  intent  composite_polychromatic_AND_many_small_blobs
  body    AND(gt(hue_diversity_score(color_scene), 0.50),
              gt_int(blob_count_thresh(scene, 1.5), 15))
```

## Verification

```
parsed: 106 ok, 0 errors
Installed: 106
audit integrity check: OK (loaded 95 ops, 106 preds)
```

Smoke-tested by evaluating the new predicates on a synthetic warm-uniform image:
- `has_warm_palette` = True (correct — colors are warm)
- `has_indoor_scene_signature` = False (no center-vs-edge brightness gradient)
- **`is_indoor_warm_scene` = False** (composite: warm AND indoor → False because indoor is False) ✓

Behavior matches the R56 R60-validated semantics.

## Headline

| metric | round | value | status |
|---|---|---|---|
| Vocabulary size | R61 | **106 predicates** (103 L1 + 3 L4) | current — first L4 promotions in DSL |
| total predicates | R26 | 103 | superseded by R61 |

## Promises ledger updates

- **P-19** closes with C-61 evidence.

## What this changes

For 103 predicates' worth of project history, the DSL had been a single-layer thing — L1 only. R61 is the first time the DSL holds a predicate that is *defined in terms of compositions that mean something at a higher layer*. The substrate is now multi-layer not just architecturally but lexically.

The integrity check now reads 106 predicates from disk and the charter says 106 — they agree. If they ever disagree again the audit's WARN will catch it (this is what the integrity check was built for in R48).

## Files added this round

- `Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE/data/vision/vocab.aurex` — 3 new predicate blocks appended (29795 → 31498 bytes; 103 → 106 predicates)
- this report

## Next round

R62 current: P-18 image-cache harness — extend the R55 corpus harness to persist enough per-image state that newly-authored predicates can be evaluated against historical corpus retroactively. R54's `has_busy_textured_scene` is still pending its retry; once the harness can replay against new predicates, that retry becomes possible. Then R63 push the corpus to N≥70.
