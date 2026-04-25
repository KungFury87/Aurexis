# Aurexis Research Sim v1.8 - Primitive-aware coverage / repetition-fix dossier

v1.7 demonstrated target-conditioned cardinality scoring on the
v1.5 distractor composites. v1.8 adds a fixed strip-based repetition
metric, a new repetition distractor composite, and an
ARBITRATION_INVARIANT verdict for label-scoped primitives.

Single rankers : `area`, `mean_intensity`, `edge_density`, `compactness`.
Fused rankers  : `normalized_sum`, `borda`.
Primitive-aware: `cardinality_target`, `repetition_target_strip`.

Verdict:
- **GENERIC_FUSION_SUFFICIENT**    best generic passes; primitive-aware adds nothing
- **PRIMITIVE_AWARE_HELPS**        generic best fails; primitive-aware passes
- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both generic and primitive-aware fail
- **PROPOSAL_QUALITY_LIMIT**       oracle_best < 0.80
- **ARBITRATION_INVARIANT**        primitive's metric is ROI-insensitive (label-scoped)

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **PRIMITIVE_AWARE_HELPS** |
| composite_cardinality_ranker_split | **GENERIC_FUSION_SUFFICIENT** |
| composite_repetition_distractor | **PRIMITIVE_AWARE_HELPS** |

### composite_cardinality_with_decoy
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| cardinality | cardinality | target_count=3 | 1.000 | 0.333 (area) | 1.000 | PRIMITIVE_AWARE_HELPS |

### composite_cardinality_ranker_split
- overall_verdict: **GENERIC_FUSION_SUFFICIENT**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| cardinality | cardinality | target_count=3 | 1.000 | 1.000 (area) | 1.000 | GENERIC_FUSION_SUFFICIENT |

### composite_repetition_distractor
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| repetition | repetition | target_period=21.0, row_y=96 | 0.813 | 0.000 (area) | 0.813 | PRIMITIVE_AWARE_HELPS |
