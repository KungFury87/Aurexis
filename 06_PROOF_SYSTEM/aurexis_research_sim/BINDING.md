# Aurexis Research Sim v1.1 - Scene-scoped binding dossier

For each composite sub-primitive we report survival
WITHOUT ROI binding (v1.0 global metric) and WITH ROI
binding (mask derived from sub-labels). Verdict:

- **SURVIVES_GLOBAL** both pass: primitive is robust even unbound.
- **NEEDS_BINDING** unbound fails, bound passes: metric was scene-blind.
- **FAILS_EVEN_BOUND** primitive fails even with ROI: primitive is the problem.
- Tag **SCENE_AMBIGUITY** when bound - unbound >= 0.30.

## Overall summary
| composite | overall verdict |
|-----------|-----------------|
| composite_ordering_role_zone | **SURVIVES_GLOBAL** |
| composite_repetition_cardinality | **NEEDS_BINDING** |
| composite_ordering_crowded_by_adjacency | **SURVIVES_GLOBAL** |

### composite_ordering_role_zone
- overall_verdict: **SURVIVES_GLOBAL**
| sub_primitive | kind | unbound | bound | binding_boost | verdict | tags |
|---------------|------|---------|-------|---------------|---------|------|
| ordering | ordering | 1.000 | 1.000 | +0.000 | SURVIVES_GLOBAL |  |
| role_zone | role_zone | 1.000 | 1.000 | +0.000 | SURVIVES_GLOBAL |  |

### composite_repetition_cardinality
- overall_verdict: **NEEDS_BINDING**
| sub_primitive | kind | unbound | bound | binding_boost | verdict | tags |
|---------------|------|---------|-------|---------------|---------|------|
| repetition | repetition | 0.921 | 0.958 | +0.037 | SURVIVES_GLOBAL |  |
| cardinality | cardinality | 0.000 | 1.000 | +1.000 | NEEDS_BINDING | SCENE_AMBIGUITY |

### composite_ordering_crowded_by_adjacency
- overall_verdict: **SURVIVES_GLOBAL**
| sub_primitive | kind | unbound | bound | binding_boost | verdict | tags |
|---------------|------|---------|-------|---------------|---------|------|
| ordering | ordering | 1.000 | 1.000 | +0.000 | SURVIVES_GLOBAL |  |
| adjacency | adjacency | 1.000 | 1.000 | +0.000 | SURVIVES_GLOBAL |  |
