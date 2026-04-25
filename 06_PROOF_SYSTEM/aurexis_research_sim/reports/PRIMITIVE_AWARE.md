# Aurexis Research Sim v1.7 - Primitive-aware / target-conditioned dossier

Per sub-primitive: best of generic single + fused rankers vs
a target-conditioned primitive-aware ranker that uses the
survival metric itself as the ranking signal against known
target parameters (e.g., target_count for cardinality).

Single rankers : `area`, `mean_intensity`, `edge_density`, `compactness`.
Fused rankers  : `normalized_sum`, `borda`.
Primitive-aware: `cardinality_target`, `repetition_target`.

Verdict:
- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes; primitive-aware adds nothing
- **PRIMITIVE_AWARE_HELPS**        generic best fails; primitive-aware passes
- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both generic and primitive-aware fail
- **PROPOSAL_QUALITY_LIMIT**       oracle_best < 0.80

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **PRIMITIVE_AWARE_HELPS** |
| composite_cardinality_ranker_split | **GENERIC_FUSION_SUFFICIENT** |

### composite_cardinality_with_decoy
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| cardinality | cardinality | target_count=3 | 1.000 | 0.333 (area) | 1.000 | PRIMITIVE_AWARE_HELPS |

Per-generic-ranker top-1 (for reference):

| sub | area | mean_intensity | edge_density | compactness | normalized_sum | borda |
|---|---|---|---|---|---|---|
| cardinality | 0.333 | 0.333 | 0.333 | 0.000 | 0.333 | 0.333 |

### composite_cardinality_ranker_split
- overall_verdict: **GENERIC_FUSION_SUFFICIENT**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| cardinality | cardinality | target_count=3 | 1.000 | 1.000 (area) | 1.000 | GENERIC_FUSION_SUFFICIENT |

Per-generic-ranker top-1 (for reference):

| sub | area | mean_intensity | edge_density | compactness | normalized_sum | borda |
|---|---|---|---|---|---|---|
| cardinality | 1.000 | 0.333 | 0.333 | 0.000 | 0.333 | 0.333 |
