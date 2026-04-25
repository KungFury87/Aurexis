# Aurexis Research Sim v0.9 - Primitive redesign dossier

For each promoted primitive we evaluate 3 property challenges under a shared hostile capture and rank properties by sensitivity (= baseline - challenge).

## Redesign summary
| primitive | baseline | dominant weakness | suggested redesign |
|-----------|----------|-------------------|--------------------|
| ordering | 0.861 | low_contrast | increase intensity separation OR encode with color / shape / spatial cue rather than intensity alone |
| repetition | 0.921 | small_markers | require a minimum marker radius relative to expected PSF; scale-floor the primitive |
| role_zone | 1.000 | tight_anchor_margin | widen anchor/companion contrast OR add a second cue (color, shape, position) so role survives when intensity contrast collapses |

### ordering
- baseline_survival (hostile capture): 0.861
- challenge survivals:
    - baseline: 0.861
    - low_contrast: 0.685
    - tight_spacing: 0.800
    - small_markers: 0.903
- property sensitivities (baseline - challenge):
    - low_contrast: +0.176
    - tight_spacing: +0.061
    - small_markers: -0.042
- ranked_properties (most sensitive first):
    - low_contrast: sensitivity=+0.176
    - tight_spacing: sensitivity=+0.061
    - small_markers: sensitivity=-0.042
- dominant_weakness: **low_contrast**
- suggested_redesign: increase intensity separation OR encode with color / shape / spatial cue rather than intensity alone

### repetition
- baseline_survival (hostile capture): 0.921
- challenge survivals:
    - baseline: 0.921
    - low_contrast: 0.828
    - tight_period: 0.632
    - small_markers: 0.310
- property sensitivities (baseline - challenge):
    - low_contrast: +0.093
    - tight_period: +0.289
    - small_markers: +0.611
- ranked_properties (most sensitive first):
    - small_markers: sensitivity=+0.611
    - tight_period: sensitivity=+0.289
    - low_contrast: sensitivity=+0.093
- dominant_weakness: **small_markers**
- suggested_redesign: require a minimum marker radius relative to expected PSF; scale-floor the primitive

### role_zone
- baseline_survival (hostile capture): 1.000
- challenge survivals:
    - baseline: 1.000
    - low_contrast: 0.500
    - many_secondaries: 1.000
    - tight_anchor_margin: 0.333
- property sensitivities (baseline - challenge):
    - low_contrast: +0.500
    - many_secondaries: +0.000
    - tight_anchor_margin: +0.667
- ranked_properties (most sensitive first):
    - tight_anchor_margin: sensitivity=+0.667
    - low_contrast: sensitivity=+0.500
    - many_secondaries: sensitivity=+0.000
- dominant_weakness: **tight_anchor_margin**
- suggested_redesign: widen anchor/companion contrast OR add a second cue (color, shape, position) so role survives when intensity contrast collapses
