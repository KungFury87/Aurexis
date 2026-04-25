# Aurexis Research Sim v1.9 - Arbitration-boundary mapping dossier

v1.7 demonstrated target-conditioned cardinality scoring.
v1.8 added a strip-based fix and showed primitive-aware arbitration
helps for repetition too. v1.9 introduces an ROI-sensitive role_zone
metric and maps where target conditioning helps, where it does not,
and where the metric itself is the bottleneck.

Verdict (per composite):
- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes
- **PRIMITIVE_AWARE_HELPS**        only primitive-aware passes
- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both fail
- **PROPOSAL_QUALITY_LIMIT**       oracle_best < 0.80
- **METRIC_GAP_ROI_INSENSITIVE**   metric is label-scoped; no ROI-aware variant; arbitration test not possible
- **ARBITRATION_INVARIANT**        primitive metric is genuinely ROI-insensitive (not used in v1.9)

## Family boundary map

| family | boundary_tag | per-composite verdicts |
|--------|--------------|------------------------|
| adjacency | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| cardinality | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS, GENERIC_FUSION_SUFFICIENT |
| hierarchy | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| ordering | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| orientation | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| repetition | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |
| role_zone | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |
| symmetry | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |

## Overall summary (per composite)
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **PRIMITIVE_AWARE_HELPS** |
| composite_cardinality_ranker_split | **GENERIC_FUSION_SUFFICIENT** |
| composite_repetition_distractor | **PRIMITIVE_AWARE_HELPS** |
| composite_role_zone_decoy | **PRIMITIVE_AWARE_HELPS** |

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

### composite_role_zone_decoy
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| role_zone | role_zone | target_satellites=4 | 1.000 | 0.000 (area) | 1.000 | PRIMITIVE_AWARE_HELPS |
