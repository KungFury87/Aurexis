# Aurexis Research Sim v1.3 - Inferred-binding dossier

Each composite sub-primitive is evaluated under:
- `unbound` (v1.0 global metric)
- `perfect` (v1.1 ROI from truth labels, dilated)
- `soft_worst` (v1.2 worst imperfect mode)
- `propose_threshold` (v1.3 image-only proposal)
- `propose_edges` (v1.3 image-only proposal)

Verdict:
- **SURVIVES_WITH_INFERENCE** best inferred >= 0.80
- **NEEDS_TIGHT_INFERENCE** perfect passes but inferred < 0.80
- **FAILS_EVEN_PERFECT** perfect < 0.80

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_ordering_role_zone | **SURVIVES_WITH_INFERENCE** |
| composite_repetition_cardinality | **NEEDS_TIGHT_INFERENCE** |
| composite_ordering_crowded_by_adjacency | **SURVIVES_WITH_INFERENCE** |

### composite_ordering_role_zone
- overall_verdict: **SURVIVES_WITH_INFERENCE**
| sub | kind | unbound | perfect | soft_worst | propose_threshold | propose_edges | best_proposal | best_inferred | verdict |
|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | propose_threshold | 1.000 | SURVIVES_WITH_INFERENCE |
| role_zone | role_zone | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | propose_threshold | 1.000 | SURVIVES_WITH_INFERENCE |

### composite_repetition_cardinality
- overall_verdict: **NEEDS_TIGHT_INFERENCE**
| sub | kind | unbound | perfect | soft_worst | propose_threshold | propose_edges | best_proposal | best_inferred | verdict |
|---|---|---|---|---|---|---|---|---|---|
| repetition | repetition | 0.921 | 0.958 | 0.523 | 0.956 | 0.929 | propose_threshold | 0.956 | SURVIVES_WITH_INFERENCE |
| cardinality | cardinality | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | propose_threshold | 0.000 | NEEDS_TIGHT_INFERENCE |

### composite_ordering_crowded_by_adjacency
- overall_verdict: **SURVIVES_WITH_INFERENCE**
| sub | kind | unbound | perfect | soft_worst | propose_threshold | propose_edges | best_proposal | best_inferred | verdict |
|---|---|---|---|---|---|---|---|---|---|
| ordering | ordering | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | propose_threshold | 1.000 | SURVIVES_WITH_INFERENCE |
| adjacency | adjacency | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | propose_threshold | 1.000 | SURVIVES_WITH_INFERENCE |
