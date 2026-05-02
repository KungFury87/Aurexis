"""R166 - compute 6 NEW measurement-dimension operators per image."""
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
NEW_OPS = Path('/tmp/r166_newops'); NEW_OPS.mkdir(exist_ok=True)

def get_imgs():
    imgs = {}
    for f in sorted(R55.glob('*.npy')): imgs[('r111', f.stem)] = ('npy', f)
    for f in sorted(R85.glob('*.npy')): imgs[('r111', f.stem)] = ('npy', f)
    for f in sorted(R111.glob('*.jpg')): imgs[('r111', f.stem)] = ('jpg', f)
    for f in sorted(R158.glob('*.jpg')): imgs[('r158', f.stem)] = ('jpg', f)
    for f in sorted(R159.glob('*.jpg')): imgs[('r159', f.stem)] = ('jpg', f)
    return imgs

imgs = get_imgs()

def compute_new_ops(kind, path, key):
    cache = NEW_OPS / f"{key}.json"
    if cache.exists(): return json.loads(cache.read_text())
    try:
        if kind == 'npy': rgb = np.load(path)
        else: rgb = np.asarray(Image.open(path).convert('RGB'))
        if rgb.ndim != 3 or rgb.shape[-1] != 3: return None
        img = Image.fromarray(rgb); img.thumbnail((192, 192), Image.LANCZOS)
        rgb = np.asarray(img).astype(np.float64) / 255.0
        H, W = rgb.shape[:2]
        luma = 0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]
        
        # 1. Local entropy (Shannon entropy of luma histogram, 32-bin)
        hist, _ = np.histogram(luma, bins=32, range=(0, 1))
        p = hist / hist.sum() if hist.sum() > 0 else np.array([1.0])
        p_nonzero = p[p > 0]
        local_entropy = float(-np.sum(p_nonzero * np.log2(p_nonzero)))
        
        # 2. Percentile 99-1 dynamic range
        p99_p1 = float(np.percentile(luma, 99) - np.percentile(luma, 1))
        
        # 3. Color correlation at distance 5 (autocorrelation of luma, lag=5)
        if W > 10 and H > 10:
            l_h = luma[:, :W-5]; l_h2 = luma[:, 5:]
            corr_h = float(np.corrcoef(l_h.flatten(), l_h2.flatten())[0,1])
            l_v = luma[:H-5, :]; l_v2 = luma[5:, :]
            corr_v = float(np.corrcoef(l_v.flatten(), l_v2.flatten())[0,1])
            color_corr_5 = (corr_h + corr_v) / 2
        else:
            color_corr_5 = 0.0
        
        # 4. Rotational symmetry (180-deg flip overlap, structure tensor)
        flipped = luma[::-1, ::-1]
        rot_corr_180 = float(np.corrcoef(luma.flatten(), flipped.flatten())[0,1])
        
        # 5. Structure tensor isotropy (lambda_min / lambda_max of gradient covariance)
        gx = np.diff(luma, axis=1, append=luma[:, -1:])
        gy = np.diff(luma, axis=0, append=luma[-1:, :])
        Jxx = (gx*gx).mean(); Jxy = (gx*gy).mean(); Jyy = (gy*gy).mean()
        trace = Jxx + Jyy
        det = Jxx*Jyy - Jxy*Jxy
        if trace > 0:
            lam1 = trace/2 + np.sqrt(max(0, (trace/2)**2 - det))
            lam2 = trace/2 - np.sqrt(max(0, (trace/2)**2 - det))
            isotropy = float(abs(lam2)/max(abs(lam1), 1e-10))
        else:
            isotropy = 1.0
        
        # 6. LAB color spread (use OKLab-like approximation)
        # Approximate Lab a-channel: 0.5 * (R - G), b-channel: 0.5 * (G - B)
        a = 0.5 * (rgb[...,0] - rgb[...,1])
        b = 0.5 * (rgb[...,1] - rgb[...,2])
        lab_a_std = float(a.std())
        lab_b_std = float(b.std())
        lab_chroma_total = float(np.sqrt(lab_a_std**2 + lab_b_std**2))
        
        # 7. HF/LF power ratio (FFT)
        fft = np.fft.fft2(luma)
        spec = np.abs(fft)**2
        cy, cx = H//2, W//2
        # shift
        spec = np.fft.fftshift(spec)
        Y, X = np.ogrid[:H, :W]
        r = np.sqrt((Y-cy)**2 + (X-cx)**2)
        max_r = min(H, W) // 2
        low_band = spec[r < max_r * 0.2].sum()
        high_band = spec[r > max_r * 0.5].sum()
        hf_lf_ratio = float(high_band / max(low_band, 1e-10))
        
        # 8. Local maxima count after blur (peak count)
        from scipy.ndimage import gaussian_filter, maximum_filter
        smoothed = gaussian_filter(luma, sigma=4.0)
        local_max = (smoothed == maximum_filter(smoothed, size=15))
        local_max = local_max & (smoothed > 0.5)  # only bright peaks
        peak_count = int(local_max.sum())
        peak_count_normalized = float(peak_count / (H * W / 1000))  # peaks per 1000 pixels
        
        result = {
            'local_entropy': local_entropy,
            'p99_minus_p1': p99_p1,
            'color_corr_lag5': color_corr_5,
            'rot_corr_180': rot_corr_180,
            'gradient_isotropy': isotropy,
            'lab_chroma_total': lab_chroma_total,
            'hf_lf_power_ratio': hf_lf_ratio,
            'bright_peak_density': peak_count_normalized,
        }
        cache.write_text(json.dumps(result))
        return result
    except Exception as e:
        return None

import sys
all_fps_keys = set()
for prefix, d in [('r111', Path('/tmp/r111_fps')), ('r158', Path('/tmp/r158_fps')), ('r159', Path('/tmp/r159_fps'))]:
    for fp_path in d.glob('*.json'):
        all_fps_keys.add(f"{prefix}_{fp_path.stem}")

t0 = time.time()
done = 0; new = 0
for key in all_fps_keys:
    cache = NEW_OPS / f"{key}.json"
    if cache.exists():
        done += 1; continue
    if time.time() - t0 > 35: break
    prefix, stem = key.split('_', 1)
    img_key = (prefix, stem)
    if img_key not in imgs: continue
    kind, path = imgs[img_key]
    s = compute_new_ops(kind, path, key)
    if s is not None: new += 1

print(f"cached {done}, new {new}, total {sum(1 for _ in NEW_OPS.glob('*.json'))}/{len(all_fps_keys)}")
