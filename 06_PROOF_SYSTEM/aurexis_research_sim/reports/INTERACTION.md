# Aurexis Research Sim v1.0 - Composite / interaction dossier

For each composite probe we evaluate each constituent primitive's survival in-composite vs alone, under a shared moderate hostile capture. Interference = alone - in_composite. Flags: BINDING_OK (< 0.05), CROWDING (< 0.30), BINDING_FAILURE (>= 0.30).

## Overall summary
| composite | overall flag |
|-----------|--------------|
| composite_ordering_role_zone | **BINDING_OK** |
| composite_repetition_cardinality | **BINDING_FAILURE** |
| composite_ordering_crowded_by_adjacency | **BINDING_OK** |

### composite_ordering_role_zone
- overall_flag: **BINDING_OK**
| sub_primitive | in_composite | alone | interference | flag |
|---------------|--------------|-------|--------------|------|
| ordering | 1.000 | 1.000 | +0.000 | BINDING_OK |
| role_zone | 1.000 | 1.000 | +0.000 | BINDING_OK |

### composite_repetition_cardinality
- overall_flag: **BINDING_FAILURE**
| sub_primitive | in_composite | alone | interference | flag |
|---------------|--------------|-------|--------------|------|
| repetition | 0.921 | 0.932 | +0.011 | BINDING_OK |
| cardinality | 0.000 | 1.000 | +1.000 | BINDING_FAILURE |

### composite_ordering_crowded_by_adjacency
- overall_flag: **BINDING_OK**
| sub_primitive | in_composite | alone | interference | flag |
|---------------|--------------|-------|--------------|------|
| ordering | 1.000 | 1.000 | +0.000 | BINDING_OK |
| adjacency | 1.000 | 1.000 | +0.000 | BINDING_OK |
