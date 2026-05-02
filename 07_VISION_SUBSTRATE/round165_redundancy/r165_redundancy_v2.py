import json
from pathlib import Path
import numpy as np
from collections import defaultdict

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())
n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
M = np.zeros((n, P), dtype=np.int8)
for i, name in enumerate(sorted(all_fps.keys())):
    fp = all_fps[name]
    for j, pn in enumerate(pred_names):
        M[i, j] = 1 if fp.get(pn, False) else 0

# Find ALL pairs at all Jaccard ranges
fire_cols = [set(np.where(M[:, j] == 1)[0].tolist()) for j in range(P)]
all_jacs = []
for i in range(P):
    for j in range(i+1, P):
        a, b = fire_cols[i], fire_cols[j]
        union = len(a | b)
        if union == 0: continue
        jac = len(a & b) / union
        if jac >= 0.80:
            all_jacs.append((pred_names[i], pred_names[j], jac))

all_jacs.sort(key=lambda x: -x[2])
print(f"Top-30 high-Jaccard pairs in 151-pred canonical vocab on N={n}:")
print(f"{'rank':<5}{'a':<35}{'b':<35}{'J':<6}")
for rk, (a, b, j) in enumerate(all_jacs[:30], 1):
    print(f"{rk:<5}{a:<35}{b:<35}{j:.3f}")

# specifically check the 3 R161+R164 reports
print("\n=== Check R161/R164 reported equivalences ===")
def jaccard_pair(a, b):
    if a not in pred_names or b not in pred_names: return None
    ia, ib = pred_names.index(a), pred_names.index(b)
    sa, sb = fire_cols[ia], fire_cols[ib]
    u = len(sa | sb)
    return len(sa & sb)/u if u > 0 else None

print(f"  has_high_edge_density vs has_high_frequency_residual: J={jaccard_pair('has_high_edge_density', 'has_high_frequency_residual')}")
print(f"    fire rates: {sum(M[:, pred_names.index('has_high_edge_density')])}/{n} vs {sum(M[:, pred_names.index('has_high_frequency_residual')])}/{n}")
print(f"  has_low_key vs has_low_light_signature: J={jaccard_pair('has_low_key', 'has_low_light_signature')}")
print(f"  is_low_contrast_image: in vocab? {'is_low_contrast_image' in pred_names}")
