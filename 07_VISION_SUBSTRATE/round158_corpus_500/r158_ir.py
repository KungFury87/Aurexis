"""R158 IR audit on N=426 corpus."""
import json
from pathlib import Path
import numpy as np

OLD_FP_DIR = Path('/tmp/r111_fps')   # 226 fingerprints from R111
NEW_FP_DIR = Path('/tmp/r158_fps')   # 200 fingerprints from R158
OUT = Path('/tmp/round158_audit'); OUT.mkdir(exist_ok=True)

# Load all fingerprints
all_fps = {}
for fp_path in OLD_FP_DIR.glob('*.json'):
    all_fps[fp_path.stem] = json.loads(fp_path.read_text())
for fp_path in NEW_FP_DIR.glob('*.json'):
    all_fps[fp_path.stem] = json.loads(fp_path.read_text())

n = len(all_fps)
print(f"corpus N = {n}")

# Get predicate names from any fingerprint
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
print(f"predicates = {P}")

# Build firing matrix
M = np.zeros((n, P), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0

# Per-predicate fire rate
fire_rates = M.mean(axis=0)
buckets = {"DEAD": 0, "LOW": 0, "HEALTHY": 0, "HIGH": 0, "ALWAYS": 0}
for r in fire_rates:
    if r == 0: buckets["DEAD"] += 1
    elif r < 0.05: buckets["LOW"] += 1
    elif r > 0.95: buckets["ALWAYS" if r == 1.0 else "HIGH"] += 1
    else: buckets["HEALTHY"] += 1

# Equivalence classes
fingerprint_strs = {}
eq_classes = {}
for j, pn in enumerate(pred_names):
    sig = tuple(M[:, j].tolist())
    if sig not in eq_classes:
        eq_classes[sig] = []
    eq_classes[sig].append(pn)

n_eq = len(eq_classes)
n_multi = sum(1 for cls in eq_classes.values() if len(cls) > 1)

# Effective rank (variance-based)
M_centered = M.astype(np.float64) - M.mean(axis=0, keepdims=True)
U, S, Vt = np.linalg.svd(M_centered, full_matrices=False)
total_var = (S**2).sum()
cumvar = np.cumsum(S**2) / total_var
rank_90 = int(np.searchsorted(cumvar, 0.90) + 1)
rank_99 = int(np.searchsorted(cumvar, 0.99) + 1)

# Pairwise Jaccard for near-collisions
near_collisions = []
fire_cols = [set() for _ in range(P)]
for j in range(P):
    fire_cols[j] = set(np.where(M[:, j] == 1)[0].tolist())
for i in range(P):
    for j in range(i+1, P):
        a, b = fire_cols[i], fire_cols[j]
        if not a and not b: continue
        intersection = len(a & b); union = len(a | b)
        jac = intersection / union if union > 0 else 0
        if jac >= 0.95:
            near_collisions.append((pred_names[i], pred_names[j], round(jac, 3)))
near_collisions.sort(key=lambda x: -x[2])

# Always-firing
always = [pn for pn, r in zip(pred_names, fire_rates) if r >= 0.999]

audit = {
    "round": "R158", "date": "2026-05-01",
    "method": f"P-01 progress: corpus growth from R111 N=226 to R158 N={n} via 200 fresh picsum pulls; full IR audit at scale",
    "n_corpus": n,
    "n_predicates": P,
    "fire_buckets": buckets,
    "n_dead": buckets["DEAD"],
    "n_healthy": buckets["HEALTHY"],
    "n_always": buckets["ALWAYS"],
    "always_firing": always,
    "n_eq_classes": n_eq,
    "n_multi_eq": n_multi,
    "effective_rank_90": rank_90,
    "effective_rank_99": rank_99,
    "rank_per_N": round(rank_90 / n, 4),
    "n_near_collisions": len(near_collisions),
    "near_collisions_top": near_collisions[:8],
}
out = OUT / "round158_audit.json"
out.write_text(json.dumps(audit, indent=2))

print()
print(f"=== R158 IR AUDIT (N={n}) ===")
print(f"  vocab: {P} predicates")
print(f"  buckets: {buckets}")
print(f"  effective rank (90%): {rank_90}")
print(f"  effective rank (99%): {rank_99}")
print(f"  eq classes: {n_eq} ({n_multi} multi-member)")
print(f"  near-collisions (J>=0.95): {len(near_collisions)}")
print(f"  always-firing: {len(always)}")
print()
print(f"=== Scaling sequence (R77 -> R85 -> R109 -> R111 -> R158) ===")
print(f"  N: 76 -> 110 -> 76 -> 226 -> {n}")
print(f"  rank_90: 31 -> 39 -> 32 -> 48 -> {rank_90}")
print(f"  rank/N: 0.408 -> 0.355 -> 0.421 -> 0.212 -> {rank_90/n:.3f}")
