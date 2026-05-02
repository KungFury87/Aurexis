"""R164 - operator-level vocab additions: 12 new predicates with novel thresholds on lightweight image stats.

Tests whether operator-level vocab additions beat L4 compositions' 0.200 rank/pred efficiency.
"""
import json, time
from pathlib import Path
import numpy as np
from PIL import Image

DESK = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved')
R55 = DESK / 'round55_corpus_harness/corpus_images'
R85 = DESK / 'round85_corpus_growth/images_diverse'
R111 = Path('/tmp/round111_pull')
R158 = Path('/tmp/round158_pull')
R159 = Path('/tmp/round159_pull')

OUT = Path('/tmp/round164_audit'); OUT.mkdir(exist_ok=True)
OP_STATS = Path('/tmp/r164_opstats'); OP_STATS.mkdir(exist_ok=True)

# Same key prefixing as r111/r158/r159 fingerprints used (just match what's in fps cache)
# Need to compute new operator-level stats on the same images that fingerprints exist for
# r111 fps: from R55 npy + R85 npy + R111 jpg
# r158 fps: from R158 jpg
# r159 fps: from R159 jpg

# Build mapping: (prefix, stem) -> image path
def get_imgs():
    imgs = {}
    for f in sorted(R55.glob('*.npy')):
        imgs[('r111', f.stem)] = ('npy', f)
    for f in sorted(R85.glob('*.npy')):
        imgs[('r111', f.stem)] = ('npy', f)
    for f in sorted(R111.glob('*.jpg')):
        imgs[('r111', f.stem)] = ('jpg', f)
    for f in sorted(R158.glob('*.jpg')):
        imgs[('r158', f.stem)] = ('jpg', f)
    for f in sorted(R159.glob('*.jpg')):
        imgs[('r159', f.stem)] = ('jpg', f)
    return imgs

imgs = get_imgs()
print(f"image map: {len(imgs)} entries")

# Compute lightweight stats per image (cached)
def compute_stats(kind, path, stem_key):
    cache = OP_STATS / f"{stem_key}.json"
    if cache.exists(): return json.loads(cache.read_text())
    try:
        if kind == 'npy':
            rgb = np.load(path)
        else:
            rgb = np.asarray(Image.open(path).convert('RGB'))
        if rgb.ndim != 3 or rgb.shape[-1] != 3: return None
        img = Image.fromarray(rgb); img.thumbnail((320, 320), Image.LANCZOS)
        rgb = np.asarray(img).astype(np.float64)/255.0
        H, W = rgb.shape[:2]
        luma = 0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]
        # mean/std intensity
        mean_i = float(luma.mean()); std_i = float(luma.std())
        # gradient magnitude
        gx = np.abs(np.diff(luma, axis=1)).mean()
        gy = np.abs(np.diff(luma, axis=0)).mean()
        grad_mean = float((gx + gy) / 2)
        # top vs bottom
        top_mean = float(luma[:H//2].mean()); bot_mean = float(luma[H//2:].mean())
        ratio_tb = top_mean / max(bot_mean, 0.01)
        # center vs edges
        cy, cx = H//2, W//2
        center = luma[cy-H//8:cy+H//8, cx-W//8:cx+W//8].mean() if H >= 8 and W >= 8 else mean_i
        # ring around center (edges)
        mask = np.ones_like(luma, dtype=bool)
        mask[H//4:3*H//4, W//4:3*W//4] = False
        edges_mean = float(luma[mask].mean()) if mask.any() else mean_i
        ratio_ce = center / max(edges_mean, 0.01)
        # saturation
        max_c = rgb.max(axis=-1); min_c = rgb.min(axis=-1)
        sat = (max_c - min_c) / (max_c + 1e-6)
        sat_mean = float(sat.mean())
        # hue diversity (count of distinct 30deg buckets with >5% pixel mass)
        H_chan = np.zeros_like(luma)
        # Approximate hue computation
        for i in range(H_chan.shape[0]):
            for j in range(H_chan.shape[1]):
                r,g,b = rgb[i,j]
                mx = max(r,g,b); mn = min(r,g,b)
                if mx == mn: H_chan[i,j] = 0
                elif mx == r: H_chan[i,j] = (60 * ((g-b)/(mx-mn)) + 360) % 360
                elif mx == g: H_chan[i,j] = 60 * ((b-r)/(mx-mn)) + 120
                else: H_chan[i,j] = 60 * ((r-g)/(mx-mn)) + 240
        # Count buckets with >5% mass (filter low-saturation pixels too)
        hues_meaningful = H_chan[sat > 0.15]
        if len(hues_meaningful) > 100:
            buckets = (hues_meaningful // 30).astype(int)
            hist = np.bincount(buckets, minlength=12)
            n_distinct = int((hist > 0.05 * len(hues_meaningful)).sum())
        else:
            n_distinct = 0
        # texture density variance
        text_var = float(np.std(luma[:H//2]) - np.std(luma[H//2:]))
        result = {
            'mean_i': mean_i, 'std_i': std_i, 'grad_mean': grad_mean,
            'ratio_tb': float(ratio_tb), 'ratio_ce': float(ratio_ce),
            'sat_mean': sat_mean, 'n_distinct_hues': n_distinct,
            'text_var_top_minus_bot': text_var,
        }
        cache.write_text(json.dumps(result))
        return result
    except Exception as e:
        return None

# Load existing fingerprints
all_fps = {}
for prefix, d in [('r111', Path('/tmp/r111_fps')), ('r158', Path('/tmp/r158_fps')), ('r159', Path('/tmp/r159_fps'))]:
    for fp_path in d.glob('*.json'):
        all_fps[f"{prefix}_{fp_path.stem}"] = json.loads(fp_path.read_text())
n = len(all_fps)
print(f"fingerprints: {n}")

# Compute stats for all images (with time budget)
t0 = time.time()
stats_map = {}
done = 0; new = 0; missed = 0
for key in all_fps:
    prefix, stem = key.split('_', 1)
    img_key = (prefix, stem)
    if img_key not in imgs:
        missed += 1; continue
    cache_path = OP_STATS / f"{key}.json"
    if cache_path.exists():
        stats_map[key] = json.loads(cache_path.read_text())
        done += 1; continue
    if time.time() - t0 > 35: break
    kind, path = imgs[img_key]
    s = compute_stats(kind, path, key)
    if s is not None:
        stats_map[key] = s; new += 1
    else: missed += 1

print(f"stats computed: cached {done}, new {new}, missing {missed}, total {len(stats_map)}/{n}")
