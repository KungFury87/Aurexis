"""R166 IR audit: 8 NEW operator-level predicates with novel measurement dimensions."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')), ('r158', Path('/tmp/r158_fps')), ('r159', Path('/tmp/r159_fps'))]
NEW_OPS = Path('/tmp/r166_newops')
OUT = Path('/tmp/round166_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())
new_ops_map = {p.stem: json.loads(p.read_text()) for p in NEW_OPS.glob('*.json')}
common_keys = sorted(k for k in all_fps if k in new_ops_map)
n = len(common_keys)
print(f"common N={n}")
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)

# Show distribution of new operator values to pick reasonable thresholds
print("\n=== Distribution of new operators (for threshold selection) ===")
for op_name in ['local_entropy', 'p99_minus_p1', 'color_corr_lag5', 'rot_corr_180', 
                'gradient_isotropy', 'lab_chroma_total', 'hf_lf_power_ratio', 'bright_peak_density']:
    vals = [new_ops_map[k][op_name] for k in common_keys]
    p25, p50, p75 = np.percentile(vals, [25, 50, 75])
    print(f"  {op_name}: q25={p25:.3f} q50={p50:.3f} q75={p75:.3f} min={min(vals):.3f} max={max(vals):.3f}")

# Choose thresholds: use median + percentile points to get 8 predicates
# Pick thresholds that produce ~10-50% fire rates (HEALTHY range)
def fire_rate(op_name, op_val_func):
    return sum(1 for k in common_keys if op_val_func(new_ops_map[k][op_name])) / n

# Define 8 NEW operator-level predicates
NEW_PREDS = [
    ('has_high_local_entropy',        'local_entropy',       lambda x: x > 4.5),     # rich texture
    ('has_low_local_entropy',         'local_entropy',       lambda x: x < 3.5),     # uniform texture
    ('has_extreme_dynamic_range',     'p99_minus_p1',        lambda x: x > 0.85),   # full DR
    ('has_smooth_color_transitions',  'color_corr_lag5',     lambda x: x > 0.95),    # high spatial corr
    ('has_180deg_rotational_signature','rot_corr_180',       lambda x: x > 0.6),     # symmetric content
    ('has_isotropic_gradient',        'gradient_isotropy',   lambda x: x > 0.4),     # not edge-dominant
    ('has_high_chromatic_spread',     'lab_chroma_total',    lambda x: x > 0.10),    # colorful
    ('has_low_chromatic_spread',      'lab_chroma_total',    lambda x: x < 0.04),    # near-monochrome
    ('has_high_frequency_dominance',  'hf_lf_power_ratio',   lambda x: x > 0.05),   # textured/noisy
    ('has_multiple_bright_peaks',     'bright_peak_density', lambda x: x > 1.0),     # multiple light sources
]
print(f"\n=== R166 fire rates ===")
for npn, op_name, fn in NEW_PREDS:
    fr = fire_rate(op_name, fn)
    print(f"  {npn}: {fr:.3f}")

# Build firing matrix
all_pred_names = pred_names + [npn for npn, _, _ in NEW_PREDS]
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, key in enumerate(common_keys):
    fp = all_fps[key]; ops = new_ops_map[key]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0
    for k, (npn, op_name, fn) in enumerate(NEW_PREDS):
        try: M[i, P+k] = 1 if fn(ops[op_name]) else 0
        except: M[i, P+k] = 0

def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

r90_base = compute_rank(M[:, :P], 0.90)
r99_base = compute_rank(M[:, :P], 0.99)
r90_ext = compute_rank(M, 0.90)
r99_ext = compute_rank(M, 0.99)

print(f"\n=== R166 RANK ===")
print(f"  baseline (151 preds): rank_90={r90_base}, rank_99={r99_base}")
print(f"  +{len(NEW_PREDS)} new operators: rank_90={r90_ext}, rank_99={r99_ext}")
print(f"  Δ: rank_90 +{r90_ext-r90_base}, rank_99 +{r99_ext-r99_base}")

e_new = (r90_ext - r90_base) / len(NEW_PREDS)
print(f"  per-pred efficiency: {e_new:.3f}")

print(f"\n=== Vocab-additions hierarchy update (4 datapoints) ===")
print(f"  L4 compositions (R160-R163): 0.200/pred")
print(f"  Op-level novel thresholds (R164): 0.333/pred (1.67x L4)")
print(f"  NEW operators (R166): {e_new:.3f}/pred ({e_new/0.200:.2f}x L4, {e_new/0.333:.2f}x op-level)")

# Near-collisions
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P_ext)]
new_collisions = []
for k in range(len(NEW_PREDS)):
    new_idx = P + k
    npn = NEW_PREDS[k][0]
    for j in range(P):
        a, b = fire_cols[new_idx], fire_cols[j]
        if not a and not b: continue
        u = len(a | b)
        if u == 0: continue
        jac = len(a & b) / u
        if jac >= 0.95:
            new_collisions.append((npn, all_pred_names[j], round(jac, 3)))
print(f"\nnew op collisions (J>=0.95): {len(new_collisions)}")
for c in new_collisions[:5]: print(f"  {c[0]} ↔ {c[1]} (J={c[2]})")

audit = {
    "round": "R166", "date": "2026-05-01",
    "method": "8 genuinely-new measurement-dimension operators (entropy, percentile DR, autocorr, rotational symmetry, gradient isotropy, LAB chroma spread, FFT HF/LF, peak density) with predicates; tests upper bound of vocab-additions hierarchy.",
    "n_corpus": n,
    "n_new_predicates": len(NEW_PREDS),
    "new_pred_fire_rates": {npn: fire_rate(op, fn) for npn, op, fn in NEW_PREDS},
    "rank_90_baseline": r90_base, "rank_90_extended": r90_ext,
    "rank_99_baseline": r99_base, "rank_99_extended": r99_ext,
    "delta_rank_90": r90_ext - r90_base,
    "delta_rank_99": r99_ext - r99_base,
    "per_pred_rank_90_efficiency": e_new,
    "comparison": {
        "L4_R160_R163": 0.200,
        "op_level_R164_novel_thresholds": 0.333,
        "new_operators_R166": e_new,
        "ratio_R166_vs_L4": e_new / 0.200,
        "ratio_R166_vs_R164": e_new / 0.333,
    },
    "n_new_collisions": len(new_collisions),
    "new_collisions": new_collisions,
}
out = OUT / "round166_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
