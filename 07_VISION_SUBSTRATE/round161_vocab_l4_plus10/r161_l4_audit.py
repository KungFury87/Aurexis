"""R161 - +10 more L4 compositional predicates (15 total cumulative); test linear vocab scaling."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round161_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
print(f"corpus N = {n}, baseline preds = {P}")

def fp_of(fp, name): return fp.get(name, False)

# R160 predicates (5)
R160_PREDS = {
    'is_outdoor_horizon_scene': lambda fp: fp_of(fp, 'has_clear_horizon') and not fp_of(fp, 'has_indoor_scene_signature'),
    'is_warm_indoor_low_key': lambda fp: fp_of(fp, 'has_indoor_scene_signature') and fp_of(fp, 'has_warm_palette') and fp_of(fp, 'has_low_key'),
    'is_high_contrast_centered': lambda fp: fp_of(fp, 'is_high_contrast_image') and fp_of(fp, 'has_centered_subject'),
    'is_blue_dominant_outdoor': lambda fp: fp_of(fp, 'has_dominant_blue_hue') and fp_of(fp, 'has_clear_horizon'),
    'has_dramatic_lighting': lambda fp: fp_of(fp, 'has_high_dynamic_range') and (fp_of(fp, 'has_clipped_highlights') or fp_of(fp, 'has_underexposed_regions')),
}

# R161 predicates (+10)
R161_PREDS = {
    'is_face_in_warm_scene':       lambda fp: fp_of(fp, 'has_face_like_signature') and fp_of(fp, 'has_warm_palette'),
    'is_low_key_blue':             lambda fp: fp_of(fp, 'has_low_key') and fp_of(fp, 'has_dominant_blue_hue'),
    'has_thirds_composition_HDR':  lambda fp: (fp_of(fp, 'has_subject_at_thirds_top_left') or fp_of(fp, 'has_subject_at_thirds_top_right')) and fp_of(fp, 'has_high_dynamic_range'),
    'is_monochrome_low_contrast':  lambda fp: fp_of(fp, 'has_monochrome') and not fp_of(fp, 'is_high_contrast_image'),
    'is_textured_busy_scene':      lambda fp: fp_of(fp, 'has_high_edge_density') and fp_of(fp, 'has_high_frequency_residual'),
    'is_balanced_symmetric':       lambda fp: fp_of(fp, 'has_strong_horizontal_balance') and fp_of(fp, 'has_mirror_symmetry_vertical_axis'),
    'is_atmospheric_distant':     lambda fp: fp_of(fp, 'has_strong_perspective') and fp_of(fp, 'has_clear_horizon'),
    'is_punchy_warm_centered':    lambda fp: fp_of(fp, 'is_high_contrast_image') and fp_of(fp, 'has_warm_palette') and fp_of(fp, 'has_centered_subject'),
    'is_skin_in_high_key':        lambda fp: fp_of(fp, 'has_skin_tone_signature') and fp_of(fp, 'has_high_key'),
    'is_oversaturated_warm_outdoor': lambda fp: fp_of(fp, 'has_oversaturated_palette') and fp_of(fp, 'has_warm_palette') and not fp_of(fp, 'has_indoor_scene_signature'),
}

ALL_NEW = {**R160_PREDS, **R161_PREDS}
n_new = len(ALL_NEW)
print(f"new predicates: 5 (R160) + 10 (R161) = {n_new}")

# Build extended firing matrix
all_pred_names = pred_names + list(ALL_NEW.keys())
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0
    for k, (npn, fn) in enumerate(ALL_NEW.items()):
        M[i, P + k] = 1 if fn(fp) else 0

# Fire rates for new
print(f"\n=== R161 new predicate fire rates (just the 10 new) ===")
for k, npn in enumerate(R161_PREDS, start=5):
    fr = M[:, P + k].mean()
    print(f"  {npn}: {fr:.3f} ({int(M[:, P+k].sum())} of {n})")

# Compute three rank values: 151 base, 156 (R160), 166 (R161)
def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

rank_90_151 = compute_rank(M[:, :P], 0.90)
rank_90_156 = compute_rank(M[:, :P+5], 0.90)
rank_90_166 = compute_rank(M, 0.90)
rank_99_151 = compute_rank(M[:, :P], 0.99)
rank_99_156 = compute_rank(M[:, :P+5], 0.99)
rank_99_166 = compute_rank(M, 0.99)

print(f"\n=== R161 RANK PROGRESSION (fixed N={n}) ===")
print(f"  vocab=151 (R159 baseline): rank_90={rank_90_151}, rank_99={rank_99_151}")
print(f"  vocab=156 (R160 +5):       rank_90={rank_90_156}, rank_99={rank_99_156}  Δ_vs_151: +{rank_90_156-rank_90_151}, +{rank_99_156-rank_99_151}")
print(f"  vocab=166 (R161 +10):      rank_90={rank_90_166}, rank_99={rank_99_166}  Δ_vs_156: +{rank_90_166-rank_90_156}, +{rank_99_166-rank_99_156}")
print(f"  Δ_total (151→166):         rank_90 +{rank_90_166-rank_90_151}, rank_99 +{rank_99_166-rank_99_151}")

# Per-unit efficiency
delta_per_pred_R160 = (rank_90_156 - rank_90_151) / 5
delta_per_pred_R161 = (rank_90_166 - rank_90_156) / 10
print(f"\nrank_90 per-predicate efficiency:")
print(f"  R160 batch (+5): {delta_per_pred_R160:.3f} rank/pred")
print(f"  R161 batch (+10): {delta_per_pred_R161:.3f} rank/pred")

# DEAD/healthy buckets, near-collisions for new preds
fire_rates = M.mean(axis=0)
buckets = {"DEAD": 0, "LOW": 0, "HEALTHY": 0, "HIGH": 0, "ALWAYS": 0}
for r in fire_rates:
    if r == 0: buckets["DEAD"] += 1
    elif r < 0.05: buckets["LOW"] += 1
    elif r >= 1.0: buckets["ALWAYS"] += 1
    elif r > 0.95: buckets["HIGH"] += 1
    else: buckets["HEALTHY"] += 1

n_dead_new = sum(1 for k in range(n_new) if M[:, P+k].sum() == 0)

# Near-collisions of new preds vs all
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P_ext)]
new_collisions = []
for k in range(n_new):
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

print(f"\nnew DEAD: {n_dead_new}, near-collisions of new preds (J>=0.95): {len(new_collisions)}")
if new_collisions:
    for c in new_collisions[:5]: print(f"  {c[0]} ↔ {c[1]} (J={c[2]})")

audit = {
    "round": "R161", "date": "2026-05-01",
    "method": "+10 L4 compositional predicates added to R160's +5 (total 15 new on top of 151 baseline). Re-run IR on N=623. Tests vocab scaling linearity.",
    "n_corpus": n,
    "vocab_baseline": 151,
    "vocab_R160": 156,
    "vocab_R161": 166,
    "new_R161_preds": list(R161_PREDS.keys()),
    "new_R161_fire_rates": {k: float(M[:, P+5+i].mean()) for i, k in enumerate(R161_PREDS)},
    "rank_90_151": rank_90_151,
    "rank_90_156": rank_90_156,
    "rank_90_166": rank_90_166,
    "rank_99_151": rank_99_151,
    "rank_99_156": rank_99_156,
    "rank_99_166": rank_99_166,
    "delta_rank_90_R160": rank_90_156 - rank_90_151,
    "delta_rank_90_R161": rank_90_166 - rank_90_156,
    "delta_rank_90_total": rank_90_166 - rank_90_151,
    "per_pred_efficiency_R160": delta_per_pred_R160,
    "per_pred_efficiency_R161": delta_per_pred_R161,
    "buckets_extended": buckets,
    "n_dead_new": n_dead_new,
    "n_collisions_new": len(new_collisions),
    "verdict": (
        "LINEAR VOCAB SCALING CONFIRMED" if delta_per_pred_R161 >= delta_per_pred_R160 * 0.7 else
        "SUBLINEAR VOCAB SCALING - L4 compositional saturation begins"
    ),
}
out = OUT / "round161_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nverdict: {audit['verdict']}")
print(f"wrote {out}")
