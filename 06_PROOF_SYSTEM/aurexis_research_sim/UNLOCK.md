# Aurexis Research Sim v2.0 - Blocked-family unlock dossier

v1.9 mapped 3 of 8 primitive families as PRIMITIVE_AWARE_HELPS
and tagged 5 as METRIC_GAP_ROI_INSENSITIVE. v2.0 unlocks two of
those (ordering, symmetry) by adding ROI-sensitive metrics +
target-conditioned rankers + distractor composites. The result
is 5 of 8 primitive families confirmed PRIMITIVE_AWARE_HELPS;
3 of 8 (adjacency, orientation, hierarchy) remain blocked.

Verdict (per composite):
- **GENERIC_FUSION_SUFFICIENT**    best generic ranker passes
- **PRIMITIVE_AWARE_HELPS**        only primitive-aware passes
- **PRIMITIVE_AWARE_STILL_FAILS**  oracle passes; both fail
- **PROPOSAL_QUALITY_LIMIT**       oracle_best < 0.80
- **METRIC_GAP_ROI_INSENSITIVE**   metric is label-scoped; no ROI-aware variant; arbitration test not possible

## Family boundary map (v2.0)

| family | boundary_tag | per-composite verdicts |
|--------|--------------|------------------------|
| adjacency | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| cardinality | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS, GENERIC_FUSION_SUFFICIENT |
| hierarchy | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| ordering | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |
| orientation | **METRIC_GAP_ROI_INSENSITIVE** | METRIC_GAP_ROI_INSENSITIVE |
| repetition | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |
| role_zone | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |
| symmetry | **PRIMITIVE_AWARE_HELPS** | PRIMITIVE_AWARE_HELPS |

## Overall summary (per composite)
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **PRIMITIVE_AWARE_HELPS** |
| composite_cardinality_ranker_split | **GENERIC_FUSION_SUFFICIENT** |
| composite_repetition_distractor | **PRIMITIVE_AWARE_HELPS** |
| composite_role_zone_decoy | **PRIMITIVE_AWARE_HELPS** |
| composite_ordering_distractor | **PRIMITIVE_AWARE_HELPS** |
| composite_symmetry_distractor | **PRIMITIVE_AWARE_HELPS** |

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

### composite_ordering_distractor
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| ordering | ordering | target_count=5 | 1.000 | 0.700 (area) | 1.000 | PRIMITIVE_AWARE_HELPS |

### composite_symmetry_distractor
- overall_verdict: **PRIMITIVE_AWARE_HELPS**
| sub | kind | target | oracle_best | best_generic (which) | primitive_aware | verdict |
|---|---|---|---|---|---|---|
| symmetry | symmetry | axis=vertical | 0.980 | 0.383 (area) | 0.980 | PRIMITIVE_AWARE_HELPS |
