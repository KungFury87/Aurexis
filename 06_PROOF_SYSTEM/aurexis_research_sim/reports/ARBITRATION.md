# Aurexis Research Sim v1.4 - Arbitration / proposal-competition dossier

Each image-only proposal mask is split into connected-
component candidate ROIs. A scene-agnostic ranker
(`largest_area`) picks the top-1 without
truth access. Per sub-primitive:

- `oracle_best` - max survival across ALL candidates (ceiling)
- `top1`        - best of each method's top-1 pick (honest)
- `worst`       - min survival (false-positive burden)
- `spread`      - oracle_best - worst (arbitration pressure)

Verdict:
- **SURVIVES_WITH_TOP1**       top1 >= 0.80
- **NEEDS_ORACLE_ARBITRATION** oracle passes but top1 < 0.80
- **FAILS_UNDER_COMPETITION**  oracle_best < 0.80

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_ordering_role_zone | **SURVIVES_WITH_TOP1** |
| composite_repetition_cardinality | **FAILS_UNDER_COMPETITION** |
| composite_ordering_crowded_by_adjacency | **SURVIVES_WITH_TOP1** |

### composite_ordering_role_zone
- overall_verdict: **SURVIVES_WITH_TOP1**
| sub | kind | n_cands | oracle_best | top1 | worst | spread | propose_threshold.top1 | propose_edges.top1 | propose_threshold.n | propose_edges.n | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 27 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 7 | 20 | SURVIVES_WITH_TOP1 |
| role_zone | role_zone | 27 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 7 | 20 | SURVIVES_WITH_TOP1 |

### composite_repetition_cardinality
- overall_verdict: **FAILS_UNDER_COMPETITION**
| sub | kind | n_cands | oracle_best | top1 | worst | spread | propose_threshold.top1 | propose_edges.top1 | propose_threshold.n | propose_edges.n | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| repetition | repetition | 19 | 0.921 | 0.921 | 0.000 | 0.921 | 0.921 | 0.921 | 12 | 7 | SURVIVES_WITH_TOP1 |
| cardinality | cardinality | 19 | 0.600 | 0.600 | 0.000 | 0.600 | 0.200 | 0.600 | 12 | 7 | FAILS_UNDER_COMPETITION |

### composite_ordering_crowded_by_adjacency
- overall_verdict: **SURVIVES_WITH_TOP1**
| sub | kind | n_cands | oracle_best | top1 | worst | spread | propose_threshold.top1 | propose_edges.top1 | propose_threshold.n | propose_edges.n | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 29 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 3 | 26 | SURVIVES_WITH_TOP1 |
| adjacency | adjacency | 29 | 1.000 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 3 | 26 | SURVIVES_WITH_TOP1 |
