"""R160 - L4 compositional predicates from existing fingerprints; test whether vocab growth bumps rank-90."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round160_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
print(f"corpus N = {n}")
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)

# Define 5 L4 compositional predicates
def fp_of(fp, name): return fp.get(name, False)

def is_outdoor_horizon_scene(fp):
    return fp_of(fp, 'has_clear_horizon') and not fp_of(fp, 'has_indoor_scene_signature')

def is_warm_indoor_low_key(fp):
    return fp_of(fp, 'has_indoor_scene_signature') and fp_of(fp, 'has_warm_palette') and fp_of(fp, 'has_low_key')

def is_high_contrast_centered(fp):
    return fp_of(fp, 'is_high_contrast_image') and fp_of(fp, 'has_centered_subject')

def is_blue_dominant_outdoor(fp):
    return fp_of(fp, 'has_dominant_blue_hue') and fp_of(fp, 'has_clear_horizon')

def has_dramatic_lighting(fp):
    return fp_of(fp, 'has_high_dynamic_range') and (fp_of(fp, 'has_clipped_highlights') or fp_of(fp, 'has_underexposed_regions'))

NEW_PREDS = {
    'is_outdoor_horizon_scene': is_outdoor_horizon_scene,
    'is_warm_indoor_low_key': is_warm_indoor_low_key,
    'is_high_contrast_centered': is_high_contrast_centered,
    'is_blue_dominant_outdoor': is_blue_dominant_outdoor,
    'has_dramatic_lighting': has_dramatic_lighting,
}

# Build extended firing matrix
all_pred_names = pred_names + list(NEW_PREDS.keys())
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0
    for k, (npn, fn) in enumerate(NEW_PREDS.items()):
        M[i, P + k] = 1 if fn(fp) else 0

# Compute fire rates for new preds
print(f"\n=== R160 L4 PREDICATE FIRE RATES (N={n}) ===")
for k, npn in enumerate(NEW_PREDS):
    fr = M[:, P + k].mean()
    print(f"  {npn}: {fr:.3f} ({int(M[:, P+k].sum())} of {n})")

# IR audit on extended matrix
fire_rates = M.mean(axis=0)
buckets = {"DEAD": 0, "LOW": 0, "HEALTHY": 0, "HIGH": 0, "ALWAYS": 0}
for r in fire_rates:
    if r == 0: buckets["DEAD"] += 1
    elif r < 0.05: buckets["LOW"] += 1
    elif r >= 1.0: buckets["ALWAYS"] += 1
    elif r > 0.95: buckets["HIGH"] += 1
    else: buckets["HEALTHY"] += 1

# Effective rank
M_centered = M.astype(np.float64) - M.mean(axis=0, keepdims=True)
U, S, Vt = np.linalg.svd(M_centered, full_matrices=False)
total_var = (S**2).sum()
cumvar = np.cumsum(S**2) / total_var
rank_90 = int(np.searchsorted(cumvar, 0.90) + 1)
rank_99 = int(np.searchsorted(cumvar, 0.99) + 1)

# Compare baseline (only original 151)
M_base = M[:, :P]
M_base_centered = M_base.astype(np.float64) - M_base.mean(axis=0, keepdims=True)
S_base = np.linalg.svd(M_base_centered, full_matrices=False, compute_uv=False)
cumvar_base = np.cumsum(S_base**2) / (S_base**2).sum()
rank_90_base = int(np.searchsorted(cumvar_base, 0.90) + 1)
rank_99_base = int(np.searchsorted(cumvar_base, 0.99) + 1)

# Near-collisions involving new preds
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P_ext)]
new_col_collisions = []
for k in range(5):
    new_idx = P + k
    npn = list(NEW_PREDS.keys())[k]
    for j in range(P):
        a, b = fire_cols[new_idx], fire_cols[j]
        if not a and not b: continue
        union = len(a | b)
        if union == 0: continue
        jac = len(a & b) / union
        if jac >= 0.95:
            new_col_collisions.append((npn, all_pred_names[j], round(jac, 3)))

# DEAD diagnostic
n_dead_new = sum(1 for k in range(5) if M[:, P+k].sum() == 0)

print(f"\n=== R160 IR AUDIT (vocab=156 vs 151, N={n}) ===")
print(f"  baseline rank_90 (151 preds): {rank_90_base}")
print(f"  extended rank_90 (156 preds): {rank_90}")
print(f"  Δrank_90 from +5 L4 preds: {rank_90 - rank_90_base}")
print(f"  baseline rank_99: {rank_99_base}")
print(f"  extended rank_99: {rank_99}")
print(f"  Δrank_99: {rank_99 - rank_99_base}")
print(f"  buckets (extended): {buckets}")
print(f"  DEAD new preds: {n_dead_new}")
print(f"  near-collisions of new vs existing (J>=0.95): {len(new_col_collisions)}")
for c in new_col_collisions:
    print(f"    {c[0]} ↔ {c[1]} (J={c[2]})")

audit = {
    "round": "R160", "date": "2026-05-01",
    "method": "L4 compositional vocab expansion test: 5 new predicates as boolean compositions of existing fingerprints; re-run IR on N=623 corpus; tests architectural claim 'substrate expressiveness bounded by VOCAB not DATA'.",
    "n_corpus": n,
    "n_predicates_baseline": P,
    "n_predicates_extended": P_ext,
    "new_predicates": list(NEW_PREDS.keys()),
    "new_pred_fire_rates": {k: float(M[:, P+i].mean()) for i, k in enumerate(NEW_PREDS)},
    "rank_90_baseline": rank_90_base,
    "rank_90_extended": rank_90,
    "delta_rank_90": rank_90 - rank_90_base,
    "rank_99_baseline": rank_99_base,
    "rank_99_extended": rank_99,
    "delta_rank_99": rank_99 - rank_99_base,
    "buckets_extended": buckets,
    "n_dead_new_preds": n_dead_new,
    "near_collisions_new_vs_existing": new_col_collisions,
    "verdict": (
        f"VOCAB-GROWTH-BUMPS-RANK CONFIRMED" if rank_90 > rank_90_base else
        f"VOCAB-GROWTH-DOES-NOT-BUMP-RANK (L4 compositions are linearly dependent on parents — expected)"
    ),
}
out = OUT / "round160_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nverdict: {audit['verdict']}")
print(f"wrote {out}")
