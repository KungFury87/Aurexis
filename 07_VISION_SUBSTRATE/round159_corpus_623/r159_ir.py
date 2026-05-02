"""R159 IR audit on combined corpus (fix filename collision)."""
import json
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round159_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        # Prefix to avoid filename collisions
        key = f"{prefix}_{fp_path.stem}"
        all_fps[key] = json.loads(fp_path.read_text())

n = len(all_fps)
print(f"corpus N = {n}")
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)

M = np.zeros((n, P), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0

fire_rates = M.mean(axis=0)
buckets = {"DEAD": 0, "LOW": 0, "HEALTHY": 0, "HIGH": 0, "ALWAYS": 0}
for r in fire_rates:
    if r == 0: buckets["DEAD"] += 1
    elif r < 0.05: buckets["LOW"] += 1
    elif r >= 1.0: buckets["ALWAYS"] += 1
    elif r > 0.95: buckets["HIGH"] += 1
    else: buckets["HEALTHY"] += 1

eq_classes = {}
for j, pn in enumerate(pred_names):
    sig = tuple(M[:, j].tolist())
    eq_classes.setdefault(sig, []).append(pn)
n_eq = len(eq_classes)
n_multi = sum(1 for cls in eq_classes.values() if len(cls) > 1)

M_centered = M.astype(np.float64) - M.mean(axis=0, keepdims=True)
U, S, Vt = np.linalg.svd(M_centered, full_matrices=False)
total_var = (S**2).sum()
cumvar = np.cumsum(S**2) / total_var
rank_90 = int(np.searchsorted(cumvar, 0.90) + 1)
rank_99 = int(np.searchsorted(cumvar, 0.99) + 1)

near_collisions = []
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P)]
for i in range(P):
    for j in range(i+1, P):
        a, b = fire_cols[i], fire_cols[j]
        if not a and not b: continue
        intersection = len(a & b); union = len(a | b)
        jac = intersection / union if union > 0 else 0
        if jac >= 0.95:
            near_collisions.append((pred_names[i], pred_names[j], round(jac, 3)))
near_collisions.sort(key=lambda x: -x[2])

always = [pn for pn, r in zip(pred_names, fire_rates) if r >= 0.999]

audit = {
    "round": "R159", "date": "2026-05-01",
    "method": f"P-01 corpus growth from R158 N=426 to R159 N={n} via 197 fresh picsum pulls; full IR audit at scale (using prefixed keys to avoid filename collision)",
    "n_corpus": n, "n_predicates": P, "fire_buckets": buckets,
    "n_dead": buckets["DEAD"], "n_healthy": buckets["HEALTHY"],
    "n_always": buckets["ALWAYS"], "always_firing": always,
    "n_eq_classes": n_eq, "n_multi_eq": n_multi,
    "effective_rank_90": rank_90, "effective_rank_99": rank_99,
    "rank_per_N": round(rank_90 / n, 4),
    "n_near_collisions": len(near_collisions),
    "near_collisions_top": near_collisions[:8],
}
out = OUT / "round159_audit.json"
out.write_text(json.dumps(audit, indent=2))

print(f"\n=== R159 IR AUDIT (N={n}) ===")
print(f"  buckets: {buckets}")
print(f"  effective rank 90%: {rank_90} (R158: 53, Δ={rank_90-53:+d})")
print(f"  effective rank 99%: {rank_99} (R158: 94, Δ={rank_99-94:+d})")
print(f"  eq classes: {n_eq} ({n_multi} multi-member)")
print(f"  near-collisions J>=0.95: {len(near_collisions)}")
print(f"  always-firing: {len(always)}")
print()
print(f"=== 6-point scaling sequence ===")
print(f"  R77/R85/R109/R111/R158/R159: N=76/110/76/226/426/{n}")
print(f"  rank_90: 31/39/32/48/53/{rank_90}")
print(f"  rank/N: 0.408/0.355/0.421/0.212/0.124/{rank_90/n:.3f}")
