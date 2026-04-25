# Aurexis Research Sim v0.7 - Scenario-conditioned atlas

Scenarios: phone_mild, phone_moderate, phone_hostile, low_light, fast_motion

## Per-scenario relation survival
| probe | phone_mild | phone_moderate | phone_hostile | low_light | fast_motion |
|-------|---|---|---|---|---|
| ordering_probe_hard | 1.000 | 1.000 | 0.861 | 0.921 | 0.988 |
| adjacency_probe_hard | 1.000 | 0.667 | 0.000 | 0.167 | 0.000 |
| symmetry_probe_hard | 0.928 | 0.782 | 0.518 | 0.531 | 0.602 |
| orientation_probe_hard | 1.000 | 1.000 | 0.750 | 1.000 | 0.500 |
| hierarchy_probe_hard | 1.000 | 1.000 | 0.333 | 0.771 | 0.885 |
| repetition_probe | 0.939 | 0.932 | 0.921 | 0.934 | 0.850 |
| cardinality_probe | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |
| role_zone_probe | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Per-scenario classification
| probe | phone_mild | phone_moderate | phone_hostile | low_light | fast_motion |
|-------|---|---|---|---|---|
| ordering_probe_hard | ROBUST | ROBUST | ROBUST | ROBUST | ROBUST |
| adjacency_probe_hard | ROBUST | CONDITIONAL | FRAGILE | FRAGILE | FRAGILE |
| symmetry_probe_hard | ROBUST | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL |
| orientation_probe_hard | ROBUST | ROBUST | CONDITIONAL | ROBUST | CONDITIONAL |
| hierarchy_probe_hard | ROBUST | ROBUST | FRAGILE | CONDITIONAL | ROBUST |
| repetition_probe | ROBUST | ROBUST | ROBUST | ROBUST | ROBUST |
| cardinality_probe | ROBUST | ROBUST | FRAGILE | FRAGILE | ROBUST |
| role_zone_probe | ROBUST | ROBUST | ROBUST | ROBUST | ROBUST |

## Stability summary
| probe | majority | verdict | R/C/F | range | mean |
|-------|----------|---------|-------|-------|------|
| ordering_probe_hard | ROBUST | STABLE_ROBUST | 5/0/0 | 0.139 | 0.954 |
| adjacency_probe_hard | FRAGILE | SCENARIO_DEPENDENT | 1/1/3 | 1.000 | 0.367 |
| symmetry_probe_hard | CONDITIONAL | SCENARIO_DEPENDENT | 1/4/0 | 0.409 | 0.672 |
| orientation_probe_hard | ROBUST | SCENARIO_DEPENDENT | 3/2/0 | 0.500 | 0.850 |
| hierarchy_probe_hard | ROBUST | SCENARIO_DEPENDENT | 3/1/1 | 0.667 | 0.798 |
| repetition_probe | ROBUST | STABLE_ROBUST | 5/0/0 | 0.089 | 0.915 |
| cardinality_probe | ROBUST | SCENARIO_DEPENDENT | 3/0/2 | 1.000 | 0.600 |
| role_zone_probe | ROBUST | STABLE_ROBUST | 5/0/0 | 0.000 | 1.000 |
