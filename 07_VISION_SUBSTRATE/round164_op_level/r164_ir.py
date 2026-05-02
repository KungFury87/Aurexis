"""R164 IR audit: 12 new operator-level predicates with novel thresholds."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OP_STATS = Path('/tmp/r164_opstats')
OUT = Path('/tmp/round164_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

# Load all stats
stats_map = {}
for s_path in OP_STATS.glob('*.json'):
    stats_map[s_path.stem] = json.loads(s_path.read_text())

# Subset to keys present in BOTH
common_keys = sorted(k for k in all_fps if k in stats_map)
n = len(common_keys)
print(f"corpus N = {n} (intersection of fingerprints + stats)")

pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)

# Define 12 new operator-level predicates
def has_low_overall_brightness(s):       return s['mean_i'] < 0.30
def has_high_overall_brightness(s):      return s['mean_i'] > 0.70
def has_high_local_variance(s):          return s['std_i'] > 0.25
def has_low_local_variance(s):           return s['std_i'] < 0.10
def has_strong_gradient_magnitude(s):    return s['grad_mean'] > 0.10
def has_top_brighter_than_bottom(s):     return s['ratio_tb'] > 1.30
def has_bottom_brighter_than_top(s):     return s['ratio_tb'] < 0.70
def has_centered_brightness(s):          return s['ratio_ce'] > 1.30
def has_dim_center(s):                   return s['ratio_ce'] < 0.70
def has_saturated_image(s):              return s['sat_mean'] > 0.40
def has_desaturated_image(s):            return s['sat_mean'] < 0.15
def has_diverse_hues_5plus(s):           return s['n_distinct_hues'] >= 5

NEW = [
    ('has_low_overall_brightness', has_low_overall_brightness),
    ('has_high_overall_brightness', has_high_overall_brightness),
    ('has_high_local_variance', has_high_local_variance),
    ('has_low_local_variance', has_low_local_variance),
    ('has_strong_gradient_magnitude', has_strong_gradient_magnitude),
    ('has_top_brighter_than_bottom', has_top_brighter_than_bottom),
    ('has_bottom_brighter_than_top', has_bottom_brighter_than_top),
    ('has_centered_brightness', has_centered_brightness),
    ('has_dim_center', has_dim_center),
    ('has_saturated_image', has_saturated_image),
    ('has_desaturated_image', has_desaturated_image),
    ('has_diverse_hues_5plus', has_diverse_hues_5plus),
]

# Build firing matrix: baseline + new operator preds (NO L4 from R160-R163; this is operator-level vs baseline test)
all_pred_names = pred_names + [n for n,_ in NEW]
P_ext = len(all_pred_names)
M = np.zeros((n, P_ext), dtype=np.int8)
for i, key in enumerate(common_keys):
    fp = all_fps[key]
    s = stats_map[key]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0
    for k, (npn, fn) in enumerate(NEW):
        try: M[i, P+k] = 1 if fn(s) else 0
        except: M[i, P+k] = 0

# Fire rates
print(f"\n=== R164 operator-level pred fire rates ===")
for k, (npn, _) in enumerate(NEW):
    fr = M[:, P+k].mean()
    print(f"  {npn}: {fr:.3f} ({int(M[:, P+k].sum())} of {n})")

# Compute rank
def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

r90_base = compute_rank(M[:, :P], 0.90)
r99_base = compute_rank(M[:, :P], 0.99)
r90_ext = compute_rank(M, 0.90)
r99_ext = compute_rank(M, 0.99)

print(f"\n=== R164 RANK (operator-level vs baseline) ===")
print(f"  baseline (151 preds): rank_90={r90_base}, rank_99={r99_base}")
print(f"  +12 op-level preds:   rank_90={r90_ext}, rank_99={r99_ext}")
print(f"  Δ_total: rank_90 +{r90_ext-r90_base}, rank_99 +{r99_ext-r99_base}")

# Per-pred efficiency
e_op = (r90_ext - r90_base) / 12
print(f"  per-predicate rank_90 efficiency: {e_op:.3f}")

# Compare to L4 batches
print(f"\n=== Operator-level vs L4 efficiency comparison ===")
print(f"  L4 R160 (+5):   0.200")
print(f"  L4 R161 (+10):  0.200")
print(f"  L4 R162 (+20):  0.200")
print(f"  L4 R163 (+55):  0.200")
print(f"  OP R164 (+12):  {e_op:.3f}")
if e_op > 0.300:
    verdict = f"OPERATOR-LEVEL BEATS L4: {e_op/0.200:.2f}x more efficient per predicate"
elif e_op > 0.200:
    verdict = f"OPERATOR-LEVEL slightly better than L4: {e_op/0.200:.2f}x"
elif e_op > 0.150:
    verdict = f"OPERATOR-LEVEL comparable to L4 (within noise)"
else:
    verdict = f"OPERATOR-LEVEL WORSE than L4 (likely too redundant with existing operators)"
print(f"\n  verdict: {verdict}")

# Near-collisions of new vs existing
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P_ext)]
new_collisions = []
for k in range(12):
    new_idx = P + k
    npn = NEW[k][0]
    for j in range(P):
        a, b = fire_cols[new_idx], fire_cols[j]
        if not a and not b: continue
        union = len(a | b)
        if union == 0: continue
        jac = len(a & b) / union
        if jac >= 0.95:
            new_collisions.append((npn, all_pred_names[j], round(jac, 3)))
print(f"\nnew operator-level pred collisions vs existing (J>=0.95): {len(new_collisions)}")
for c in new_collisions[:5]: print(f"  {c[0]} ↔ {c[1]} (J={c[2]})")

# DEAD/HEALTHY
fire_rates_new = [M[:, P+k].mean() for k in range(12)]
n_dead = sum(1 for r in fire_rates_new if r == 0)
n_low = sum(1 for r in fire_rates_new if 0 < r < 0.05)
n_healthy = sum(1 for r in fire_rates_new if 0.05 <= r <= 0.95)
print(f"buckets: DEAD {n_dead}, LOW {n_low}, HEALTHY {n_healthy}")

audit = {
    "round": "R164", "date": "2026-05-01",
    "method": "Operator-level vocab expansion: 12 new predicates with novel thresholds on lightweight image stats (mean/std/gradient/sat/hue-diversity etc.)",
    "n_corpus": n,
    "rank_90_baseline": r90_base,
    "rank_90_extended": r90_ext,
    "rank_99_baseline": r99_base,
    "rank_99_extended": r99_ext,
    "delta_rank_90": r90_ext - r90_base,
    "delta_rank_99": r99_ext - r99_base,
    "per_pred_rank_90_efficiency": e_op,
    "L4_per_pred_efficiency_R160_R163": 0.200,
    "ratio_op_vs_L4": e_op / 0.200,
    "buckets": {"DEAD": n_dead, "LOW": n_low, "HEALTHY": n_healthy},
    "n_new_collisions": len(new_collisions),
    "new_collisions": new_collisions,
    "verdict": verdict,
    "fire_rates": {npn: float(M[:, P+k].mean()) for k, (npn, _) in enumerate(NEW)},
}
out = OUT / "round164_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
