"""R162 - +20 more L4 predicates (35 cumulative); test 3-datapoint vocab scaling linearity."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round162_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
print(f"corpus N = {n}, baseline preds = {P}")

def fp(d, k): return d.get(k, False)

# R160+R161 (15)
PRIOR = {
    'is_outdoor_horizon_scene': lambda f: fp(f, 'has_clear_horizon') and not fp(f, 'has_indoor_scene_signature'),
    'is_warm_indoor_low_key': lambda f: fp(f, 'has_indoor_scene_signature') and fp(f, 'has_warm_palette') and fp(f, 'has_low_key'),
    'is_high_contrast_centered': lambda f: fp(f, 'is_high_contrast_image') and fp(f, 'has_centered_subject'),
    'is_blue_dominant_outdoor': lambda f: fp(f, 'has_dominant_blue_hue') and fp(f, 'has_clear_horizon'),
    'has_dramatic_lighting': lambda f: fp(f, 'has_high_dynamic_range') and (fp(f, 'has_clipped_highlights') or fp(f, 'has_underexposed_regions')),
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
}

# R162 (+20 new)
R162 = {
    'has_red_subject':                    lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'has_centered_subject'),
    'is_yellow_warm':                     lambda f: fp(f, 'has_significant_yellow_hue') and fp(f, 'has_warm_palette'),
    'is_green_textured':                  lambda f: fp(f, 'has_significant_green_hue') and fp(f, 'has_high_edge_density'),
    'is_perspective_with_subject':        lambda f: fp(f, 'has_strong_perspective') and fp(f, 'has_centered_subject'),
    'is_minimalist':                      lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_low_saturation'),
    'is_violet_oversaturated':            lambda f: fp(f, 'has_significant_violet_hue') and fp(f, 'has_oversaturated_palette'),
    'is_high_red_centered':               lambda f: fp(f, 'is_high_red_warm_scene') and fp(f, 'has_centered_subject'),
    'has_complex_polychromatic':          lambda f: fp(f, 'has_polychromatic_palette') and fp(f, 'has_high_edge_density'),
    'is_thirds_left_warm':                lambda f: fp(f, 'has_subject_at_thirds_top_left') and fp(f, 'has_warm_palette'),
    'is_thirds_right_cool':               lambda f: fp(f, 'has_subject_at_thirds_top_right') and fp(f, 'has_cool_palette'),
    'is_curved_low_key':                  lambda f: fp(f, 'has_curved_signature') and fp(f, 'has_low_key'),
    'is_human_outdoor_warm':              lambda f: fp(f, 'has_human_subject_signature') and fp(f, 'has_warm_palette') and not fp(f, 'has_indoor_scene_signature'),
    'has_blue_dominant_low_key':          lambda f: fp(f, 'is_strongly_blue_dominated') and fp(f, 'has_low_key'),
    'is_achromatic_high_contrast':        lambda f: fp(f, 'has_largely_achromatic_scene') and fp(f, 'is_high_contrast_image'),
    'is_red_high_contrast':               lambda f: fp(f, 'has_significant_red_hue') and fp(f, 'is_high_contrast_image'),
    'is_underexposed_blue':               lambda f: fp(f, 'has_underexposed_regions') and fp(f, 'has_dominant_blue_hue'),
    'is_overexposed_warm':                lambda f: fp(f, 'has_overexposed_regions') and fp(f, 'has_warm_palette'),
    'is_high_key_centered':               lambda f: fp(f, 'has_high_key') and fp(f, 'has_centered_subject'),
    'is_HDR_atmospheric':                 lambda f: fp(f, 'has_high_dynamic_range') and fp(f, 'has_strong_perspective'),
    'is_negative_space_centered':         lambda f: fp(f, 'has_significant_negative_space') and fp(f, 'has_centered_subject'),
}

ALL_NEW = {**PRIOR, **R162}
n_new = len(ALL_NEW)
print(f"new predicates: 15 (R160+R161) + 20 (R162) = {n_new}")

all_pred_names = pred_names + list(ALL_NEW.keys())
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp_d = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp_d.get(pn, False) else 0
    for k, (npn, fn) in enumerate(ALL_NEW.items()):
        M[i, P + k] = 1 if fn(fp_d) else 0

# Fire rates for R162 batch
print(f"\n=== R162 new predicate fire rates (just the 20 new) ===")
for k, npn in enumerate(R162, start=15):
    fr = M[:, P + k].mean()
    print(f"  {npn}: {fr:.3f} ({int(M[:, P+k].sum())} of {n})")

def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

ranks = {
    151: (compute_rank(M[:, :P], 0.90), compute_rank(M[:, :P], 0.99)),
    156: (compute_rank(M[:, :P+5], 0.90), compute_rank(M[:, :P+5], 0.99)),
    166: (compute_rank(M[:, :P+15], 0.90), compute_rank(M[:, :P+15], 0.99)),
    186: (compute_rank(M, 0.90), compute_rank(M, 0.99)),
}

print(f"\n=== R162 RANK PROGRESSION (fixed N={n}) ===")
print(f"  vocab=151 (R159): rank_90={ranks[151][0]}, rank_99={ranks[151][1]}")
print(f"  vocab=156 (R160): rank_90={ranks[156][0]}, rank_99={ranks[156][1]}  Δ_step:+{ranks[156][0]-ranks[151][0]}/+{ranks[156][1]-ranks[151][1]}")
print(f"  vocab=166 (R161): rank_90={ranks[166][0]}, rank_99={ranks[166][1]}  Δ_step:+{ranks[166][0]-ranks[156][0]}/+{ranks[166][1]-ranks[156][1]}")
print(f"  vocab=186 (R162): rank_90={ranks[186][0]}, rank_99={ranks[186][1]}  Δ_step:+{ranks[186][0]-ranks[166][0]}/+{ranks[186][1]-ranks[166][1]}")
print(f"  Δ_total (151→186): rank_90 +{ranks[186][0]-ranks[151][0]}, rank_99 +{ranks[186][1]-ranks[151][1]}")

# Per-batch efficiency
e_R160 = (ranks[156][0] - ranks[151][0]) / 5
e_R161 = (ranks[166][0] - ranks[156][0]) / 10
e_R162 = (ranks[186][0] - ranks[166][0]) / 20
print(f"\nrank_90 per-predicate efficiency:")
print(f"  R160 batch (+5):  {e_R160:.3f}")
print(f"  R161 batch (+10): {e_R161:.3f}")
print(f"  R162 batch (+20): {e_R162:.3f}")

# Buckets
fire_rates = M.mean(axis=0)
buckets = {"DEAD": 0, "LOW": 0, "HEALTHY": 0, "HIGH": 0, "ALWAYS": 0}
for r in fire_rates:
    if r == 0: buckets["DEAD"] += 1
    elif r < 0.05: buckets["LOW"] += 1
    elif r >= 1.0: buckets["ALWAYS"] += 1
    elif r > 0.95: buckets["HIGH"] += 1
    else: buckets["HEALTHY"] += 1

n_dead_R162 = sum(1 for k in range(15, n_new) if M[:, P+k].sum() == 0)

# New collisions for R162 batch only
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P_ext)]
new_collisions = []
for k in range(15, n_new):
    new_idx = P + k
    npn = list(ALL_NEW.keys())[k]
    for j in range(P_ext):
        if j == new_idx: continue
        a, b = fire_cols[new_idx], fire_cols[j]
        if not a and not b: continue
        union = len(a | b)
        if union == 0: continue
        jac = len(a & b) / union
        if jac >= 0.95:
            new_collisions.append((npn, all_pred_names[j], round(jac, 3)))

print(f"\nR162 batch DEAD: {n_dead_R162}, near-collisions (J>=0.95): {len(new_collisions)}")
for c in new_collisions[:5]: print(f"  {c[0]} ↔ {c[1]} (J={c[2]})")

# Predict if linear: vocab=186 should give rank_90 = 54 + 35*0.20 = 61
predicted_linear_90 = 54 + 35 * 0.200
print(f"\nlinear extrapolation predicted rank_90 at vocab=186: {predicted_linear_90:.1f}")
print(f"actual: {ranks[186][0]}")
print(f"deviation: {ranks[186][0] - predicted_linear_90:+.1f}")

audit = {
    "round": "R162", "date": "2026-05-01",
    "method": "+20 L4 predicates (35 cumulative on 151 baseline). Re-run IR on N=623. Tests 3-datapoint vocab scaling.",
    "n_corpus": n,
    "vocab_progression": {"151": 54, "156": ranks[156][0], "166": ranks[166][0], "186": ranks[186][0]},
    "ranks_99": {"151": 95, "156": ranks[156][1], "166": ranks[166][1], "186": ranks[186][1]},
    "delta_per_batch_rank_90": {"R160": e_R160, "R161": e_R161, "R162": e_R162},
    "linear_predicted_rank_90_at_vocab186": predicted_linear_90,
    "actual_rank_90_at_vocab186": ranks[186][0],
    "deviation_from_linear": ranks[186][0] - predicted_linear_90,
    "buckets_extended": buckets,
    "n_dead_R162_batch": n_dead_R162,
    "n_new_collisions_R162": len(new_collisions),
    "new_R162_fire_rates": {k: float(M[:, P+15+i].mean()) for i, k in enumerate(R162)},
    "new_R162_collisions": new_collisions,
}
out = OUT / "round162_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
