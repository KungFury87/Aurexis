"""R165 - find all J=1.0 and near-equivalence pairs in canonical 151-pred vocab on N=623."""
import json
from pathlib import Path
import numpy as np
from collections import defaultdict

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round165_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
print(f"corpus N = {n}, vocab = {P}")

# Build firing matrix
M = np.zeros((n, P), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0

fire_rates = M.mean(axis=0)

# Find all pairwise Jaccards
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P)]

# All pairs at J >= 0.90
collisions = []
for i in range(P):
    for j in range(i+1, P):
        a, b = fire_cols[i], fire_cols[j]
        union = len(a | b)
        if union == 0: continue
        jac = len(a & b) / union
        if jac >= 0.90:
            collisions.append((pred_names[i], pred_names[j], jac))

# Group by Jaccard threshold
exact = [c for c in collisions if c[2] >= 0.999]
near_high = [c for c in collisions if 0.95 <= c[2] < 0.999]
near_med = [c for c in collisions if 0.90 <= c[2] < 0.95]

print(f"\n=== R165 redundancy findings ===")
print(f"  J >= 1.0 (exact equivalence):       {len(exact)} pairs")
print(f"  0.95 <= J < 1.0 (near-equivalence): {len(near_high)} pairs")
print(f"  0.90 <= J < 0.95:                    {len(near_med)} pairs")
print()
print(f"=== EXACT EQUIVALENCES (J = 1.000) ===")
for a, b, j in sorted(exact, key=lambda x: x[0]):
    fa = sum(1 for k in fire_cols[pred_names.index(a)])
    print(f"  {a} ≡ {b} (fire rate {fa/n:.3f})")

print(f"\n=== NEAR-EQUIVALENCES (0.95 <= J < 1.0) ===")
for a, b, j in sorted(near_high, key=lambda x: -x[2]):
    print(f"  {a} ↔ {b} (J={j:.3f})")

# Build equivalence classes from exact equivalences
parent = {pn: pn for pn in pred_names}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry: parent[rx] = ry

for a, b, _ in exact:
    union(a, b)

classes = defaultdict(list)
for pn in pred_names:
    classes[find(pn)].append(pn)

multi_classes = {k: v for k, v in classes.items() if len(v) > 1}
print(f"\n=== EQUIVALENCE CLASSES (J=1.0 graph) ===")
print(f"  Total equivalence classes: {len(classes)}")
print(f"  Multi-member classes: {len(multi_classes)}")
print(f"  Effective canonical vocab size: {len(classes)} (vs published 151)")
print()
for rep, members in sorted(multi_classes.items()):
    print(f"  Class of {len(members)} preds: {members}")

# Recompute rank with one rep per class (collapse equivalences)
canonical_keep_idx = []
seen_class = set()
for j, pn in enumerate(pred_names):
    rep = find(pn)
    if rep not in seen_class:
        canonical_keep_idx.append(j)
        seen_class.add(rep)

M_canonical = M[:, canonical_keep_idx]
def compute_rank(matrix, target=0.90):
    cent = matrix.astype(np.float64) - matrix.mean(axis=0, keepdims=True)
    S = np.linalg.svd(cent, full_matrices=False, compute_uv=False)
    cumvar = np.cumsum(S**2) / (S**2).sum()
    return int(np.searchsorted(cumvar, target) + 1)

r90_full = compute_rank(M, 0.90)
r99_full = compute_rank(M, 0.99)
r90_collapsed = compute_rank(M_canonical, 0.90)
r99_collapsed = compute_rank(M_canonical, 0.99)

print(f"\n=== Rank with collapsed equivalences ===")
print(f"  Full 151-pred vocab:           rank_90={r90_full}, rank_99={r99_full}")
print(f"  Collapsed ({len(canonical_keep_idx)} preds): rank_90={r90_collapsed}, rank_99={r99_collapsed}")
print(f"  Δ from collapsing: rank_90 {r90_collapsed-r90_full:+d}, rank_99 {r99_collapsed-r99_full:+d}")
print(f"  Conclusion: {len(pred_names) - len(canonical_keep_idx)} redundant preds collapse without affecting rank")

audit = {
    "round": "R165", "date": "2026-05-01",
    "method": "Vocab-redundancy audit pass: find all J>=0.90 pairs in canonical 151-pred vocab on N=623 corpus; group into equivalence classes; measure rank with collapsed equivalences.",
    "n_corpus": n, "n_predicates": P,
    "n_pairs_J_1_0_exact": len(exact),
    "n_pairs_J_0_95_to_1_0": len(near_high),
    "n_pairs_J_0_90_to_0_95": len(near_med),
    "exact_equivalences": [{"a": a, "b": b} for a, b, _ in sorted(exact, key=lambda x: x[0])],
    "near_high_equivalences": [{"a": a, "b": b, "J": round(j, 3)} for a, b, j in sorted(near_high, key=lambda x: -x[2])],
    "n_equivalence_classes": len(classes),
    "n_multi_member_classes": len(multi_classes),
    "effective_canonical_vocab_size": len(canonical_keep_idx),
    "redundant_pred_count": len(pred_names) - len(canonical_keep_idx),
    "rank_90_full": r90_full,
    "rank_90_collapsed": r90_collapsed,
    "rank_99_full": r99_full,
    "rank_99_collapsed": r99_collapsed,
    "multi_member_classes_detail": {rep: members for rep, members in multi_classes.items()},
}
out = OUT / "round165_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
