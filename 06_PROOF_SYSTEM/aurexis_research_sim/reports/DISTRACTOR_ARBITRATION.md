# Aurexis Research Sim v1.5 - Distractor-arbitration / ranking-brittleness dossier

Two distractor-rich composites are evaluated. Per sub-primitive
we union connected-component candidates across both image-only
proposal methods and measure survival under four label-blind
rankers: `area`, `mean_intensity`, `edge_density`, `compactness`.

- `oracle_best`         max survival across all candidates
- `per_ranker_top1`     survival at each ranker's top-1 pick
- `ranker_disagreement` number of distinct top-1 indices across rankers
- `distractor_burden`   oracle_best - min(per_ranker_top1)

Verdict:
- **SURVIVES_UNDER_DISTRACTORS**  all rankers' top1 >= 0.80
- **RANKER_BRITTLE**              oracle passes, some rankers fail
- **DISTRACTOR_DOMINATED**        oracle passes, NO ranker passes
- **FAILS_EVEN_ORACLE**           oracle_best < 0.80

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_cardinality_with_decoy | **DISTRACTOR_DOMINATED** |
| composite_cardinality_ranker_split | **RANKER_BRITTLE** |

### composite_cardinality_with_decoy
- overall_verdict: **DISTRACTOR_DOMINATED**
| sub | kind | n_cands | oracle_best | area.top1 | mean_intensity.top1 | edge_density.top1 | compactness.top1 | disagree | burden | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| cardinality | cardinality | 8 | 1.000 | 0.333 | 0.333 | 0.333 | 0.000 | 3 | 1.000 | DISTRACTOR_DOMINATED |

### composite_cardinality_ranker_split
- overall_verdict: **RANKER_BRITTLE**
| sub | kind | n_cands | oracle_best | area.top1 | mean_intensity.top1 | edge_density.top1 | compactness.top1 | disagree | burden | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| cardinality | cardinality | 19 | 1.000 | 1.000 | 0.333 | 0.333 | 0.000 | 3 | 1.000 | RANKER_BRITTLE |
