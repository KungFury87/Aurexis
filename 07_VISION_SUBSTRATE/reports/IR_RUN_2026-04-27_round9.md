================================================================================
VOCAB IR ANALYSIS v2 (after Round 7 tightenings + corpus pumps)
corpus: 29 inputs, vocabulary: 43 predicates
================================================================================

FIRING RATES
  predicate                                    rate    n_evaluated
  has_subframe_motion                          0.14    29/29
  has_global_brightness_drift                  0.03    29/29
  has_anisotropy_in_brightest_patch            0.69    29/29
  has_structural_anisotropy_whole_image        0.07    29/29
  has_polarization_signal                        -     0/29
  has_subpixel_periodicity                       -     0/29
  has_spectral_band_anomaly                      -     0/29
  has_gradient_energy                          0.97    29/29
  is_uniform_field                             0.03    29/29
  has_repetitive_horizontal_structure          0.69    29/29
  has_high_frequency_residual                  0.38    29/29
  has_centered_subject                         0.31    29/29
  has_horizontal_dominant_edges                0.03    29/29
  has_vertical_dominant_edges                  0.07    29/29
  has_high_edge_density                        0.03    29/29
  has_low_edge_density                         0.03    29/29
  has_high_dynamic_range                       0.21    29/29
  has_mirror_symmetry_horizontal_axis          0.31    29/29
  has_mirror_symmetry_vertical_axis            0.07    29/29
  has_face_like_signature                      0.07    29/29
  has_text_like_signature                      0.31    29/29
  has_screen_like_signature                    0.03    29/29
  has_horizon_line_signature                   0.03    29/29
  has_real_motion_validated                    0.10    29/29
  face_is_dominant_concept                     0.07    29/29
  text_is_dominant_concept                     0.76    29/29
  screen_is_dominant_concept                   0.10    29/29
  horizon_is_dominant_concept                  0.03    29/29
  has_genuine_face_not_screen                  0.24    29/29
  has_screen_displaying_face                   0.03    29/29
  has_genuine_text_not_screen                  0.55    29/29
  has_screen_displaying_text                   0.14    29/29
  no_named_concept_dominant                    0.10    29/29
  has_red_dominant                             0.45    29/29
  has_green_dominant                           0.03    29/29
  has_blue_dominant                            0.21    29/29
  has_warm_palette                             0.03    29/29
  has_cool_palette                             0.03    29/29
  has_high_saturation                          0.14    29/29
  has_low_saturation                           0.31    29/29
  has_monochrome                               0.31    29/29
  has_high_color_diversity                     0.76    29/29
  has_low_color_diversity                      0.14    29/29

REDUNDANT PAIRS (agreement = 1.00 across 29 inputs)
  count: 5
  equivalence classes: 3
    {has_horizon_line_signature, has_horizontal_dominant_edges, horizon_is_dominant_concept}
    {face_is_dominant_concept, has_face_like_signature}
    {has_low_saturation, has_monochrome}
