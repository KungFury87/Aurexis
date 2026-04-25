# Aurexis Research Sim v0.6 - Primitive Survivability Atlas

Thresholds: mild>=0.90/hostile>=0.70 -> ROBUST; mild>=0.80/hostile>=0.40 -> CONDITIONAL; else FRAGILE. Near-tie < 0.05 tagged HIGH-CONFUSION.

## Ranked fragility under hostile capture
| rank | probe | hostile_hard_survival | classification |
|------|-------|-----------------------|----------------|
| 1 | adjacency_probe_hard | 0.000 | FRAGILE |
| 2 | hierarchy_probe_hard | 0.333 | FRAGILE |
| 3 | symmetry_probe_hard | 0.518 | CONDITIONAL |
| 4 | orientation_probe_hard | 0.750 | ROBUST |
| 5 | ordering_probe_hard | 0.861 | ROBUST |

## Per-relation record
### ordering_probe_hard
- classification: **ROBUST**
- mild_hard_survival: 1.000
- hostile_hard_survival: 0.861
- stage_first_below_0_8: None
- stage_first_below_0_5: None
- right_axis (gauss_noise) collapse@0.5: not reached
- grid (blur_sigma, sensor_noise) collapse fraction <0.5: 0.00

### adjacency_probe_hard
- classification: **FRAGILE**
- mild_hard_survival: 0.667
- hostile_hard_survival: 0.000
- stage_first_below_0_8: noise
- stage_first_below_0_5: None
- right_axis (sensor_noise) collapse@0.5: val=0.08 surv=0.500
- grid (blur_sigma, sensor_noise) collapse fraction <0.5: 0.44

### symmetry_probe_hard
- classification: **CONDITIONAL**
- mild_hard_survival: 0.874
- hostile_hard_survival: 0.518
- stage_first_below_0_8: noise
- stage_first_below_0_5: None
- right_axis (rotate_deg) collapse@0.5: not reached

### orientation_probe_hard
- classification: **ROBUST**
- mild_hard_survival: 1.000
- hostile_hard_survival: 0.750
- stage_first_below_0_8: None
- stage_first_below_0_5: None
- right_axis (blur_sigma) collapse@0.5: val=6 surv=0.500

### hierarchy_probe_hard
- classification: **FRAGILE**
- mild_hard_survival: 1.000
- hostile_hard_survival: 0.333
- stage_first_below_0_8: None
- stage_first_below_0_5: None
- right_axis (gauss_noise) collapse@0.5: not reached
- grid (blur_sigma, sensor_noise) collapse fraction <0.5: 0.06
