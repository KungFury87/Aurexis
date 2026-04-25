# Aurexis Research Sim v1.6 - Fusion / arbitration redesign dossier

Per sub-primitive: single-ranker top-1, fused-ranker top-1, oracle-best,
plus per-feature attribution for every failed single ranker.

Single rankers: `area`, `mean_intensity`, `edge_density`, `compactness`.
Fused rankers:  `normalized_sum`, `borda`.

- `oracle_best` = max survival across ALL candidates
- `single_top1[r]` = survival under each single-feature ranker top-1
- `fused_top1[f]` = survival under each fused ranker top-1
- `attributions[r]` = z-score difference (picker - oracle) per feature
  for failed rankers; `+` means pushed AWAY from oracle. compactness
  is sign-inverted (lower compactness preferred).
- `confidence[r]` = top1/top2 raw feature score; >1 = decisive

Verdict:
- **FUSION_ROBUST**         oracle passes AND all fused top1 >= 0.80
- **FUSION_PARTIAL**        oracle passes; some fused pass, some fail
- **FUSION_INSUFFICIENT**   oracle passes; no fused ranker passes
- **PROPOSAL_QUALITY_LIMIT** oracle_best < 0.80

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **FUSION_INSUFFICIENT** |
| composite_cardinality_ranker_split | **FUSION_INSUFFICIENT** |

### composite_cardinality_with_decoy
- overall_verdict: **FUSION_INSUFFICIENT**
| sub | kind | oracle_best | area.top1 | mean_intensity.top1 | edge_density.top1 | compactness.top1 | normalized_sum.top1 | borda.top1 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| cardinality | cardinality | 1.000 | 0.333 | 0.333 | 0.333 | 0.000 | 0.333 | 0.333 | FUSION_INSUFFICIENT |

Failed-ranker attribution and confidence:

| sub | ranker | dominant | area dz | mean_intensity dz | edge_density dz | compactness dz | conf top1/top2 |
|---|---|---|---|---|---|---|---|
| cardinality | area | **area** | +1.88 | +0.66 | -0.15 | +0.68 | 1.43 |
| cardinality | mean_intensity | **mean_intensity** | +1.05 | +1.49 | +0.65 | -0.12 | 1.27 |
| cardinality | edge_density | **mean_intensity** | +1.05 | +1.49 | +0.65 | -0.12 | 1.26 |
| cardinality | compactness | **compactness** | -0.80 | -1.28 | -1.97 | +3.25 | 1.77 |

### composite_cardinality_ranker_split
- overall_verdict: **FUSION_INSUFFICIENT**
| sub | kind | oracle_best | area.top1 | mean_intensity.top1 | edge_density.top1 | compactness.top1 | normalized_sum.top1 | borda.top1 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| cardinality | cardinality | 1.000 | 1.000 | 0.333 | 0.333 | 0.000 | 0.333 | 0.333 | FUSION_INSUFFICIENT |

Failed-ranker attribution and confidence:

| sub | ranker | dominant | area dz | mean_intensity dz | edge_density dz | compactness dz | conf top1/top2 |
|---|---|---|---|---|---|---|---|
| cardinality | area | (passed) | - | - | - | - | 1.19 |
| cardinality | mean_intensity | **edge_density** | -1.50 | +1.70 | +1.72 | +0.43 | 1.22 |
| cardinality | edge_density | **edge_density** | -1.50 | +1.70 | +1.72 | +0.43 | 1.35 |
| cardinality | compactness | **compactness** | -3.34 | -1.28 | -1.30 | +2.98 | 1.00 |
