"""R167 - T6 grounded-reasoning demo: multi-image comparative reasoning from substrate fingerprints alone."""
import json, random
from pathlib import Path
import numpy as np

DIRS = [('r111', Path('/tmp/r111_fps')),
        ('r158', Path('/tmp/r158_fps')),
        ('r159', Path('/tmp/r159_fps'))]
OUT = Path('/tmp/round167_audit'); OUT.mkdir(exist_ok=True)

all_fps = {}
for prefix, d in DIRS:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())

n = len(all_fps)
pred_names = sorted(next(iter(all_fps.values())).keys())
P = len(pred_names)
keys = sorted(all_fps.keys())

# Convert fingerprints to numpy boolean
fp_arrays = {}
for k in keys:
    fp = all_fps[k]
    fp_arrays[k] = np.array([1 if fp.get(p, False) else 0 for p in pred_names], dtype=np.int8)

def jaccard(a, b):
    inter = ((a == 1) & (b == 1)).sum()
    union = ((a == 1) | (b == 1)).sum()
    return inter / union if union > 0 else 0.0

def comparative_reasoning(image_keys, label):
    """Given 5 image keys, demonstrate multi-image reasoning."""
    print(f"\n=== {label} ===")
    print(f"input images: {image_keys}\n")
    
    n_imgs = len(image_keys)
    # Pairwise Jaccard
    J = np.zeros((n_imgs, n_imgs))
    for i in range(n_imgs):
        for j in range(n_imgs):
            J[i, j] = jaccard(fp_arrays[image_keys[i]], fp_arrays[image_keys[j]])
    
    # Most similar pair (off-diagonal)
    best_pair = (0, 1, J[0, 1])
    for i in range(n_imgs):
        for j in range(i+1, n_imgs):
            if J[i, j] > best_pair[2]:
                best_pair = (i, j, J[i, j])
    print(f"PAIRWISE JACCARDS:")
    for i in range(n_imgs):
        for j in range(i+1, n_imgs):
            mark = " ← MOST SIMILAR" if (i,j) == (best_pair[0], best_pair[1]) else ""
            print(f"  {image_keys[i][:25]:25s} ↔ {image_keys[j][:25]:25s}: J={J[i,j]:.3f}{mark}")
    
    # Outlier: image with lowest mean Jaccard to others
    mean_J = []
    for i in range(n_imgs):
        others = [J[i, j] for j in range(n_imgs) if j != i]
        mean_J.append(np.mean(others))
    outlier_idx = int(np.argmin(mean_J))
    cluster = [i for i in range(n_imgs) if i != outlier_idx]
    print(f"\nMEAN J PER IMAGE (lower = more outlier):")
    for i in range(n_imgs):
        mark = " ← OUTLIER" if i == outlier_idx else ""
        print(f"  {image_keys[i][:30]:30s}: mean_J={mean_J[i]:.3f}{mark}")
    
    # Shared-but-distinguishing properties
    # Find predicates that fire on ALL cluster images but NOT outlier
    cluster_fps = [fp_arrays[image_keys[i]] for i in cluster]
    outlier_fp = fp_arrays[image_keys[outlier_idx]]
    
    shared = np.ones(P, dtype=bool)
    for fp in cluster_fps:
        shared = shared & (fp == 1)
    not_in_outlier = (outlier_fp == 0)
    
    distinguishing = shared & not_in_outlier
    print(f"\nSHARED-BUT-DISTINGUISHING PROPERTIES (cluster has, outlier lacks):")
    if distinguishing.any():
        for i, pn in enumerate(pred_names):
            if distinguishing[i]:
                print(f"  • {pn}")
    else:
        print("  (none — cluster doesn't share any property the outlier lacks)")
    
    # Reverse: predicates outlier has but cluster lacks
    cluster_lacks = np.ones(P, dtype=bool)
    for fp in cluster_fps:
        cluster_lacks = cluster_lacks & (fp == 0)
    distinguishing_rev = (outlier_fp == 1) & cluster_lacks
    print(f"\nREVERSE-DISTINGUISHING (outlier has, cluster lacks):")
    if distinguishing_rev.any():
        for i, pn in enumerate(pred_names):
            if distinguishing_rev[i]:
                print(f"  • {pn}")
    else:
        print("  (none)")
    
    return {
        'images': image_keys,
        'pairwise_jaccard': J.tolist(),
        'most_similar_pair': [image_keys[best_pair[0]], image_keys[best_pair[1]], float(best_pair[2])],
        'mean_J_per_image': [float(x) for x in mean_J],
        'outlier': image_keys[outlier_idx],
        'cluster': [image_keys[i] for i in cluster],
        'distinguishing_cluster_has': [pred_names[i] for i in range(P) if distinguishing[i]],
        'distinguishing_outlier_has': [pred_names[i] for i in range(P) if distinguishing_rev[i]],
    }

# Demo 1: 5 random images
random.seed(42)
random_5 = random.sample(keys, 5)
result_1 = comparative_reasoning(random_5, "DEMO 1: 5 random corpus images")

# Demo 2: 4 most-similar to first + 1 random
first = keys[0]
similarities = [(k, jaccard(fp_arrays[first], fp_arrays[k])) for k in keys if k != first]
similarities.sort(key=lambda x: -x[1])
top_4 = [first] + [s[0] for s in similarities[:4]]
result_2 = comparative_reasoning(top_4, "DEMO 2: 5 most-similar corpus images")

# Demo 3: 4 similar + 1 deliberately-different
random.seed(7)
plant_image = random.choice(keys)
sims = [(k, jaccard(fp_arrays[plant_image], fp_arrays[k])) for k in keys if k != plant_image]
sims.sort(key=lambda x: -x[1])
similar_4 = [plant_image] + [s[0] for s in sims[:3]]
# Add an outlier (low Jaccard to plant)
outlier_choice = sims[-10][0]
mixed_5 = similar_4 + [outlier_choice]
result_3 = comparative_reasoning(mixed_5, "DEMO 3: 4 similar + 1 deliberate outlier (planted test)")

audit = {
    "round": "R167", "date": "2026-05-01",
    "method": "T6 grounded-reasoning demo: multi-image comparative reasoning from substrate fingerprints alone — most-similar pair, outlier detection, distinguishing-property attribution.",
    "n_corpus": n, "vocab_size": P,
    "demo_1_random_5": result_1,
    "demo_2_top_5_similar": result_2,
    "demo_3_planted_outlier": result_3,
}
out = OUT / "round167_audit.json"
out.write_text(json.dumps(audit, indent=2))
print(f"\nwrote {out}")
