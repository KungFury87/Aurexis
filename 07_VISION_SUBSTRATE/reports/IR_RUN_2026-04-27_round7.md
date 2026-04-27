================================================================================
VOCAB IR ANALYSIS v2 (after Round 7 tightenings + corpus pumps)
corpus: 25 inputs, vocabulary: 33 predicates
================================================================================

FIRING RATES
  predicate                                    rate    n_evaluated
  has_subframe_motion                          0.16    25/25
  has_global_brightness_drift                  0.04    25/25
  has_anisotropy_in_brightest_patch            0.76    25/25
  has_structural_anisotropy_whole_image        0.04    25/25
  has_polarization_signal                        -     0/25
  has_subpixel_periodicity                       -     0/25
  has_spectral_band_anomaly                      -     0/25
  has_gradient_energy                          0.96    25/25
  is_uniform_field                             0.04    25/25
  has_repetitive_horizontal_structure          0.76    25/25
  has_high_frequency_residual                  0.36    25/25
  has_centered_subject                         0.36    25/25
  has_horizontal_dominant_edges                0.00    25/25
  has_vertical_dominant_edges                  0.12    25/25
  has_high_edge_density                        0.00    25/25
  has_low_edge_density                         0.04    25/25
  has_high_dynamic_range                       0.24    25/25
  has_mirror_symmetry_horizontal_axis          0.36    25/25
  has_mirror_symmetry_vertical_axis            0.08    25/25
  has_face_like_signature                      0.08    25/25
  has_text_like_signature                      0.32    25/25
  has_screen_like_signature                    0.04    25/25
  has_horizon_line_signature                   0.00    25/25
  has_real_motion_validated                    0.12    25/25
  face_is_dominant_concept                     0.16    25/25
  text_is_dominant_concept                     0.72    25/25
  screen_is_dominant_concept                   0.08    25/25
  horizon_is_dominant_concept                  0.00    25/25
  has_genuine_face_not_screen                  0.08    25/25
  has_screen_displaying_face                   0.36    25/25
  has_genuine_text_not_screen                  0.56    25/25
  has_screen_displaying_text                   0.40    25/25
  no_named_concept_dominant                    0.00    25/25

REDUNDANT PAIRS (agreement = 1.00 across 25 inputs)
  count: 10
  equivalence classes: 1
    {has_high_edge_density, has_horizon_line_signature, has_horizontal_dominant_edges, horizon_is_dominant_concept, no_named_concept_dominant}
