# Aurexis Research Sim v0.5 - shipped reports

## 1D sweeps (per-probe right axis)
- ordering_hard_vs_noise                 [ordering_probe_hard] axis=gauss_noise: not reached
- adjacency_hard_vs_sensor_noise         [adjacency_probe_hard] axis=sensor_noise: collapse@0.5 at sensor_noise=0.08 (surv=0.500)
- symmetry_hard_vs_rotate                [symmetry_probe_hard] axis=rotate_deg: not reached
- orientation_hard_vs_blur               [orientation_probe_hard] axis=blur_sigma: collapse@0.5 at blur_sigma=6 (surv=0.500)
- hierarchy_hard_vs_noise                [hierarchy_probe_hard] axis=gauss_noise: not reached
- ordering_hard_vs_blur_info_only        [ordering_probe_hard] axis=blur_sigma: not reached

## 2D grids (collapse fraction below 0.5)
- ordering_hard_blur_x_noise               [ordering_probe_hard]  frac_below_0.5 = 0.00
- adjacency_hard_blur_x_sensornoise        [adjacency_probe_hard]  frac_below_0.5 = 0.44
- hierarchy_hard_blur_x_sensornoise        [hierarchy_probe_hard]  frac_below_0.5 = 0.06

## Confusion tables (per-relation survival under shared capture)
### mild_hard
- ordering_probe_hard          1.000
- adjacency_probe_hard         0.667
- symmetry_probe_hard          0.874
- orientation_probe_hard       1.000
- hierarchy_probe_hard         1.000

### hostile_hard
- ordering_probe_hard          0.861
- adjacency_probe_hard         0.000
- symmetry_probe_hard          0.518
- orientation_probe_hard       0.750
- hierarchy_probe_hard         0.333

### mild_easy
- ordering_probe               1.000
- adjacency_probe              1.000
- symmetry_probe               0.952
- orientation_probe            1.000
- hierarchy_probe              1.000

### hostile_easy
- ordering_probe               0.971
- adjacency_probe              0.750
- symmetry_probe               0.571
- orientation_probe            0.500
- hierarchy_probe              1.000
