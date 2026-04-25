# Aurexis Research Sim v0.8 - Promoted-primitive validation

Thresholds: base >= 0.80 per scenario, hard >= 0.50 per scenario, negative controls <= 0.50.

## Verdict summary
| primitive | base probe | hard probe | verdict |
|-----------|------------|------------|---------|
| ordering | ordering_probe_hard | ordering_probe_hard | **SUSPECT** |
| repetition | repetition_probe | repetition_probe_hard | **WEAK_ROBUST** |
| role_zone | role_zone_probe | role_zone_probe_hard | **WEAK_ROBUST** |

### ordering
- verdict: **SUSPECT**
- base_probe: ordering_probe_hard
- hard_probe: ordering_probe_hard
- base_survival_per_scenario:
    - phone_mild: 1.000
    - phone_moderate: 1.000
    - phone_hostile: 0.861
    - low_light: 0.921
    - fast_motion: 0.988
- hard_survival_per_scenario:
    - phone_mild: 1.000
    - phone_moderate: 1.000
    - phone_hostile: 0.800
    - low_light: 0.895
    - fast_motion: 0.974
- negative_control_results:
    - scrambled_ordering_probe::[('n', 8), ('size', 128)]: 0.560
    - null_relation_probe::[('relation_kind', 'ordering'), ('size', 128)]: 0.000

### repetition
- verdict: **WEAK_ROBUST**
- base_probe: repetition_probe
- hard_probe: repetition_probe_hard
- base_survival_per_scenario:
    - phone_mild: 0.939
    - phone_moderate: 0.932
    - phone_hostile: 0.921
    - low_light: 0.934
    - fast_motion: 0.850
- hard_survival_per_scenario:
    - phone_mild: 1.000
    - phone_moderate: 1.000
    - phone_hostile: 0.408
    - low_light: 1.000
    - fast_motion: 0.386
- negative_control_results:
    - non_repetition_probe::[('n', 7), ('size', 128)]: 0.044
    - null_relation_probe::[('relation_kind', 'repetition'), ('size', 128)]: 0.152

### role_zone
- verdict: **WEAK_ROBUST**
- base_probe: role_zone_probe
- hard_probe: role_zone_probe_hard
- base_survival_per_scenario:
    - phone_mild: 1.000
    - phone_moderate: 1.000
    - phone_hostile: 1.000
    - low_light: 1.000
    - fast_motion: 1.000
- hard_survival_per_scenario:
    - phone_mild: 1.000
    - phone_moderate: 0.667
    - phone_hostile: 0.333
    - low_light: 0.333
    - fast_motion: 0.167
- negative_control_results:
    - equalized_role_zone_probe::[('n_secondary', 4), ('size', 128)]: 0.000
    - null_relation_probe::[('relation_kind', 'role_zone'), ('size', 128)]: 0.000
