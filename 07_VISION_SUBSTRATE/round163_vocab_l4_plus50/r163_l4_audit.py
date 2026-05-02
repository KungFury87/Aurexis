"""R163 - +50 more L4 predicates (85 cumulative). 4-datapoint linearity test."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round163_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
print(f"corpus N = {n}, baseline preds = {P}")

def fp(d, k): return d.get(k, False)

# R160 + R161 + R162 (35 cumulative)
PRIOR = {
    # R160 (5)
    'is_outdoor_horizon_scene': lambda f: fp(f, 'has_clear_horizon') and not fp(f, 'has_indoor_scene_signature'),
    'is_warm_indoor_low_key': lambda f: fp(f, 'has_indoor_scene_signature') and fp(f, 'has_warm_palette') and fp(f, 'has_low_key'),
    'is_high_contrast_centered': lambda f: fp(f, 'is_high_contrast_image') and fp(f, 'has_centered_subject'),
    'is_blue_dominant_outdoor': lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_clear_horizon'),
    'has_dramatic_lighting': lambda f: fp(f, 'has_high_dynamic_range') and (fp(f, 'has_clipped_highlights') or fp(f, 'has_underexposed_regions')),
    # R161 (10)
    'is_face_in_warm_scene': lambda f: fp(f, 'has_face_like_signature') and fp(f, 'has_warm_palette'),
    'is_low_key_blue': lambda f: fp(f, 'has_low_key') and fp(f, 'has_dominant_blue_hue'),
    'has_thirds_composition_HDR': lambda f: (fp(f, 'has_subject_at_thirds_top_left') or fp(f, 'has_subject_at_thirds_top_right')) and fp(f, 'has_high_dynamic_range'),
    'is_monochrome_low_contrast': lambda f: fp(f, 'has_monochrome') and not fp(f, 'is_high_contrast_image'),
    'is_textured_busy_scene': lambda f: fp(f, 'has_high_edge_density') and fp(f, 'has_high_frequency_residual'),
    'is_balanced_symmetric': lambda f: fp(f, 'has_strong_horizontal_balance') and fp(f, 'has_mirror_symmetry_vertical_axis'),
    'is_atmospheric_distant': lambda f: fp(f, 'has_strong_perspective') and fp(f, 'has_clear_horizon'),
    'is_punchy_warm_centered': lambda f: fp(f, 'is_high_contrast_image') and fp(f, 'has_warm_palette') and fp(f, 'has_centered_subject'),
    'is_skin_in_high_key': lambda f: fp(f, 'has_skin_tone_signature') and fp(f, 'has_high_key'),
    'is_oversaturated_warm_outdoor': lambda f: fp(f, 'has_oversaturated_palette') and fp(f, 'has_warm_palette') and not fp(f, 'has_indoor_scene_signature'),
    # R162 (20)
    'has_red_subject': lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_centered_subject'),
    'is_yellow_warm': lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_warm_palette'),
    'is_green_textured': lambda f: fp(f, 'has_significant_green_hue') and fp(f, 'has_high_edge_density'),
    'is_perspective_with_subject': lambda f: fp(f, 'has_strong_perspective') and fp(f, 'has_centered_subject'),
    'is_minimalist': lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_low_saturation'),
    'is_violet_oversaturated': lambda f: fp(f, 'has_significant_violet_hue') and fp(f, 'has_oversaturated_palette'),
    'is_high_red_centered': lambda f: fp(f, 'is_high_red_warm_scene') and fp(f, 'has_centered_subject'),
    'has_complex_polychromatic': lambda f: fp(f, 'has_polychromatic_palette') and fp(f, 'has_high_edge_density'),
    'is_thirds_left_warm': lambda f: fp(f, 'has_subject_at_thirds_top_left') and fp(f, 'has_warm_palette'),
    'is_thirds_right_cool': lambda f: fp(f, 'has_subject_at_thirds_top_right') and fp(f, 'has_cool_palette'),
    'is_curved_low_key': lambda f: fp(f, 'has_curved_signature') and fp(f, 'has_low_key'),
    'is_human_outdoor_warm': lambda f: fp(f, 'has_human_subject_signature') and fp(f, 'has_warm_palette') and not fp(f, 'has_indoor_scene_signature'),
    'has_blue_dominant_low_key': lambda f: fp(f, 'is_strongly_blue_dominated') and fp(f, 'has_low_key'),
    'is_achromatic_high_contrast': lambda f: fp(f, 'has_largely_achromatic_scene') and fp(f, 'is_high_contrast_image'),
    'is_red_high_contrast': lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'is_high_contrast_image'),
    'is_underexposed_blue': lambda f: fp(f, 'has_underexposed_regions') and fp(f, 'has_dominant_blue_hue'),
    'is_overexposed_warm': lambda f: fp(f, 'has_overexposed_regions') and fp(f, 'has_warm_palette'),
    'is_high_key_centered': lambda f: fp(f, 'has_high_key') and fp(f, 'has_centered_subject'),
    'is_HDR_atmospheric': lambda f: fp(f, 'has_high_dynamic_range') and fp(f, 'has_strong_perspective'),
    'is_negative_space_centered': lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_centered_subject'),
}

# R163 (+50)
R163 = {}

# Hue × Hue (5)
R163['is_red_yellow_warm']         = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_significant_yellow_hue')
R163['is_blue_green_cool']         = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_significant_green_hue')
R163['is_blue_violet']             = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_significant_violet_hue')
R163['is_yellow_cyan']             = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_significant_cyan_hue')
R163['is_red_green_complement']    = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_significant_green_hue')

# Color × Composition (5)
R163['is_red_thirds']              = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_subject_at_thirds_top_left')
R163['is_warm_negative_space']     = lambda f: fp(f, 'has_warm_palette') and fp(f, 'has_significant_negative_space')
R163['is_cool_horizon']            = lambda f: fp(f, 'has_cool_palette') and fp(f, 'has_clear_horizon')
R163['is_red_horizon']             = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_clear_horizon')
R163['is_yellow_centered']         = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_centered_subject')

# Color × Lighting (5)
R163['is_red_low_key']             = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_low_key')
R163['is_yellow_high_key']         = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_high_key')
R163['is_blue_high_key']           = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_high_key')
R163['is_green_low_key']           = lambda f: fp(f, 'has_significant_green_hue') and fp(f, 'has_low_key')
R163['is_yellow_low_key']          = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_low_key')

# Color × Texture (5)
R163['is_red_textured']            = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_high_edge_density')
R163['is_yellow_textured']         = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_high_edge_density')
R163['is_blue_smooth']             = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_low_edge_density')
R163['is_green_perspective']       = lambda f: fp(f, 'has_significant_green_hue') and fp(f, 'has_strong_perspective')
R163['is_red_HDR']                 = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_high_dynamic_range')

# Composition × Lighting (5)
R163['is_centered_low_key']        = lambda f: fp(f, 'has_centered_subject') and fp(f, 'has_low_key')
R163['is_negative_space_low_key']  = lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_low_key')
R163['is_thirds_left_low_key']     = lambda f: fp(f, 'has_subject_at_thirds_top_left') and fp(f, 'has_low_key')
R163['is_horizon_low_key']         = lambda f: fp(f, 'has_clear_horizon') and fp(f, 'has_low_key')
R163['is_horizon_high_key']        = lambda f: fp(f, 'has_clear_horizon') and fp(f, 'has_high_key')

# Composition × Texture (5)
R163['is_centered_textured']       = lambda f: fp(f, 'has_centered_subject') and fp(f, 'has_high_edge_density')
R163['is_thirds_textured']         = lambda f: fp(f, 'has_subject_at_thirds_top_right') and fp(f, 'has_high_edge_density')
R163['is_horizon_textured']        = lambda f: fp(f, 'has_clear_horizon') and fp(f, 'has_high_edge_density')
R163['is_negative_space_HDR']      = lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_high_dynamic_range')
R163['is_curved_centered']         = lambda f: fp(f, 'has_curved_signature') and fp(f, 'has_centered_subject')

# Lighting × Lighting (5)
R163['is_high_key_warm']           = lambda f: fp(f, 'has_high_key') and fp(f, 'has_warm_palette')
R163['is_low_key_cool']            = lambda f: fp(f, 'has_low_key') and fp(f, 'has_cool_palette')
R163['is_HDR_warm']                = lambda f: fp(f, 'has_high_dynamic_range') and fp(f, 'has_warm_palette')
R163['is_HDR_cool']                = lambda f: fp(f, 'has_high_dynamic_range') and fp(f, 'has_cool_palette')
R163['is_low_light_warm']          = lambda f: fp(f, 'has_low_light_signature') and fp(f, 'has_warm_palette')

# Subject × X (5)
R163['is_face_low_key']            = lambda f: fp(f, 'has_face_like_signature') and fp(f, 'has_low_key')
R163['is_human_high_key']          = lambda f: fp(f, 'has_human_subject_signature') and fp(f, 'has_high_key')
R163['is_skin_warm']               = lambda f: fp(f, 'has_skin_tone_signature') and fp(f, 'has_warm_palette')
R163['is_indoor_centered']         = lambda f: fp(f, 'has_indoor_scene_signature') and fp(f, 'has_centered_subject')
R163['is_indoor_low_saturation']   = lambda f: fp(f, 'has_indoor_scene_signature') and fp(f, 'has_low_saturation')

# 3-conjunctions (5)
R163['is_warm_outdoor_centered']   = lambda f: fp(f, 'has_warm_palette') and not fp(f, 'has_indoor_scene_signature') and fp(f, 'has_centered_subject')
R163['is_blue_horizon_HDR']        = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_clear_horizon') and fp(f, 'has_high_dynamic_range')
R163['is_red_warm_textured']       = lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_warm_palette') and fp(f, 'has_high_edge_density')
R163['is_minimalist_centered']     = lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_low_saturation') and fp(f, 'has_centered_subject')
R163['is_face_warm_high_key']      = lambda f: fp(f, 'has_face_like_signature') and fp(f, 'has_warm_palette') and fp(f, 'has_high_key')

# Edge/Orientation × Color (5)
R163['is_horizontal_warm']         = lambda f: fp(f, 'has_horizontal_dominant_edges') and fp(f, 'has_warm_palette')
R163['is_vertical_textured']       = lambda f: fp(f, 'has_vertical_dominant_edges') and fp(f, 'has_high_edge_density')
R163['is_horizontal_HDR']          = lambda f: fp(f, 'has_horizontal_dominant_edges') and fp(f, 'has_high_dynamic_range')
R163['is_yellow_HDR']              = lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_high_dynamic_range')
R163['is_blue_HDR']                = lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_high_dynamic_range')

# Lighting × Composition + symmetry (5)
R163['is_symmetric_warm']          = lambda f: fp(f, 'has_mirror_symmetry_vertical_axis') and fp(f, 'has_warm_palette')
R163['is_symmetric_HDR']           = lambda f: fp(f, 'has_mirror_symmetry_vertical_axis') and fp(f, 'has_high_dynamic_range')
R163['is_overexposed_centered']    = lambda f: fp(f, 'has_overexposed_regions') and fp(f, 'has_centered_subject')
R163['is_underexposed_warm']       = lambda f: fp(f, 'has_underexposed_regions') and fp(f, 'has_warm_palette')
R163['is_horizon_oversaturated']   = lambda f: fp(f, 'has_clear_horizon') and fp(f, 'has_oversaturated_palette')

print(f"new R163 count: {len(R163)}")

ALL_NEW = {**PRIOR, **R163}
n_new = len(ALL_NEW)
print(f"total new vs baseline: 35 (R160-R162) + 50 (R163) = {n_new}")

all_pred_names = pred_names + list(ALL_NEW.keys())
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp_d = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp_d.get(pn, False) else 0
    for k, (npn, fn) in enumerate(ALL_NEW.items()):
        M[i, P + k] = 1 if fn(fp_d) else 0

# Stats for R163 batch (last 50)
print(f"\n=== R163 fire rate distribution (50 new) ===")
fires = []
for k, npn in enumerate(R163, start=35):
    fr = M[:, P + k].mean()
    fires.append((npn, fr))
fires.sort(key=lambda x: -x[1])
for npn, fr in fires[:5]:  # top 5
    print(f"  TOP: {npn}: {fr:.3f}")
for npn, fr in fires[-5:]:  # bottom 5
    print(f"  BOT: {npn}: {fr:.3f}")
n_dead = sum(1 for _, fr in fires if fr == 0)
n_low = sum(1 for _, fr in fires if 0 < fr < 0.05)
n_healthy = sum(1 for _, fr in fires if 0.05 <= fr <= 0.95)
print(f"  bucket distribution: DEAD {n_dead}, LOW {n_low}, HEALTHY {n_healthy} of 50")

def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

ranks = {
    151: (compute_rank(M[:, :P], 0.90), compute_rank(M[:, :P], 0.99)),
    156: (compute_rank(M[:, :P+5], 0.90), compute_rank(M[:, :P+5], 0.99)),
    166: (compute_rank(M[:, :P+15], 0.90), compute_rank(M[:, :P+15], 0.99)),
    186: (compute_rank(M[:, :P+35], 0.90), compute_rank(M[:, :P+35], 0.99)),
    236: (compute_rank(M, 0.90), compute_rank(M, 0.99)),
}

print(f"\n=== R163 RANK PROGRESSION (4 datapoints, fixed N={n}) ===")
for v in [151, 156, 166, 186, 236]:
    print(f"  vocab={v}: rank_90={ranks[v][0]}, rank_99={ranks[v][1]}")
print(f"  Δ vocab=186→236 (+50): rank_90 +{ranks[236][0]-ranks[186][0]}, rank_99 +{ranks[236][1]-ranks[186][1]}")

e_R160 = (ranks[156][0] - ranks[151][0]) / 5
e_R161 = (ranks[166][0] - ranks[156][0]) / 10
e_R162 = (ranks[186][0] - ranks[166][0]) / 20
e_R163 = (ranks[236][0] - ranks[186][0]) / 50
print(f"\n=== Per-batch rank_90/pred efficiency (4 batches now) ===")
print(f"  R160 (+5):  {e_R160:.3f}")
print(f"  R161 (+10): {e_R161:.3f}")
print(f"  R162 (+20): {e_R162:.3f}")
print(f"  R163 (+50): {e_R163:.3f}")

predicted_linear = 54 + 85 * 0.200
print(f"\n=== Linearity test ===")
print(f"  predicted (linear extrapolation): {predicted_linear:.1f}")
print(f"  actual rank_90 at vocab=236: {ranks[236][0]}")
print(f"  deviation: {ranks[236][0] - predicted_linear:+.1f}")

if abs(e_R163 - 0.200) < 0.04:
    verdict = "LINEAR SCALING HOLDS at 4 datapoints"
elif e_R163 < 0.200 * 0.5:
    verdict = "STRONG SUBLINEAR SATURATION emerging"
else:
    verdict = "MILD SUBLINEAR SATURATION beginning"
print(f"\n  verdict: {verdict}")

audit = {
    "round": "R163", "date": "2026-05-01",
    "method": "+50 L4 predicates (85 cumulative). 4-datapoint vocab-vs-rank scaling test.",
    "n_corpus": n,
    "vocab_progression": {str(v): list(ranks[v]) for v in [151, 156, 166, 186, 236]},
    "delta_per_batch_rank_90": {"R160": e_R160, "R161": e_R161, "R162": e_R162, "R163": e_R163},
    "linear_predicted_rank_90_at_vocab236": predicted_linear,
    "actual_rank_90_at_vocab236": ranks[236][0],
    "deviation_from_linear": ranks[236][0] - predicted_linear,
    "R163_fires_count": {"DEAD": n_dead, "LOW": n_low, "HEALTHY": n_healthy},
    "R163_batch_size": 50,
    "verdict": verdict,
}
out = OUT / "round163_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
