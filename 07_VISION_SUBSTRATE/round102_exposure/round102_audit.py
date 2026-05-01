"""Round 102 — HDR exposure-bracket fingerprint test.

Synthetic high-DR test scenes (each designed to exercise a different
exposure-sensitive subset of the substrate). Pure simulation; no
internet pulls — Wikimedia's thumbnail policy changed and the
methodology is cleaner with controlled sources anyway.

Each 'scene' is a deliberate composition of brights + darks + textures.
We apply EV brackets at -2/-1/0/+1/+2 and ask: does the substrate
fingerprint stay scene-coherent across exposure changes?
"""
from __future__ import annotations
import io, json, sys, time
from itertools import combinations
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
            "Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE")
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.visual_intake import _bundle_from_single

H = W = 320
RNG = np.random.default_rng(42)


def scene_landscape():
    """Sky (bright) + mountain (mid) + foreground (dark)."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    # Sky gradient (bright top → blue mid)
    for y in range(H//2):
        t = y / (H//2)
        img[y] = [int(220 - 80*t), int(230 - 60*t), int(255 - 30*t)]
    # Mountain
    for x in range(W):
        peak = int(H//2 + 60*np.sin(x*0.02) + 20*np.cos(x*0.07))
        img[peak:peak+80, x] = [70, 80, 90]
    # Dark foreground
    img[H//2 + 100:] = [25, 30, 20]
    # Add texture
    img = np.clip(img + RNG.integers(-12, 12, img.shape), 0, 255).astype(np.uint8)
    return img


def scene_indoor_window():
    """Dark indoor (most pixels) + bright window (small high-DR region)."""
    img = np.full((H, W, 3), 35, dtype=np.uint8)  # dark room
    # Bright window in upper-right
    img[40:160, 180:280] = 245
    # Window mullion
    img[95:105, 180:280] = 60
    img[40:160, 225:235] = 60
    # Some indoor objects (medium gray)
    img[200:260, 60:140] = 120
    img[230:290, 180:240] = 90
    img = np.clip(img + RNG.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    return img


def scene_sunset():
    """Wide bright→dark gradient with red/orange tones."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        if t < 0.4:  # bright orange sky
            img[y] = [int(255 - 30*t), int(180 - 60*t), int(80 - 50*t)]
        elif t < 0.5:  # horizon line, very bright
            img[y] = [255, 220, 150]
        else:  # dark land
            tt = (t - 0.5) / 0.5
            img[y] = [int(80 - 60*tt), int(50 - 40*tt), int(40 - 30*tt)]
    img = np.clip(img + RNG.integers(-10, 10, img.shape), 0, 255).astype(np.uint8)
    return img


def scene_tiles():
    """Repeating colorful tile pattern — high spatial freq, mid-DR."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    palette = np.array([[200,80,80],[80,200,80],[80,80,200],[200,200,80],
                        [200,80,200],[80,200,200],[200,150,80],[150,80,200]],
                       dtype=np.uint8)
    tile = 32
    for ty in range(H // tile):
        for tx in range(W // tile):
            c = palette[(ty*3 + tx*7) % len(palette)]
            img[ty*tile:(ty+1)*tile, tx*tile:(tx+1)*tile] = c
    img = np.clip(img + RNG.integers(-12, 12, img.shape), 0, 255).astype(np.uint8)
    return img


def scene_portrait():
    """Skin-toned blob center + dark hair top + light bg."""
    img = np.full((H, W, 3), 200, dtype=np.uint8)
    # Hair (dark, top)
    yy, xx = np.mgrid[0:H, 0:W]
    hair_mask = ((xx-W//2)**2/80**2 + (yy-90)**2/60**2) < 1
    img[hair_mask] = [40, 30, 25]
    # Face (skin tone)
    face_mask = ((xx-W//2)**2/70**2 + (yy-160)**2/80**2) < 1
    img[face_mask] = [220, 180, 145]
    # Eyes (dark)
    img[140:155, 130:145] = [40, 40, 50]
    img[140:155, 175:190] = [40, 40, 50]
    img = np.clip(img + RNG.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    return img


SCENES = {
    "landscape": scene_landscape,
    "indoor_window": scene_indoor_window,
    "sunset": scene_sunset,
    "tiles": scene_tiles,
    "portrait": scene_portrait,
}


def apply_exposure(rgb_u8, ev, gamma=2.2):
    lin = (rgb_u8.astype(np.float64)/255.0) ** gamma
    gained = lin * (2.0 ** ev)
    out = (np.clip(gained, 0.0, 1.0) ** (1.0/gamma)) * 255.0
    return np.clip(out, 0, 255).astype(np.uint8)


def fingerprint(rgb_u8, name, runtime, pred_names):
    luma = (0.299*rgb_u8[...,0] + 0.587*rgb_u8[...,1] + 0.114*rgb_u8[...,2]).astype(np.float64)/255.0
    color = rgb_u8.astype(np.float64)/255.0
    bundle, _ = _bundle_from_single(luma, name, patch_size=64, color=color)
    fp = {}
    for pname in pred_names:
        rec = runtime.evaluate(pname, bundle)
        fp[pname] = bool(rec.value) if (rec.error is None and rec.value is not None) else False
    return fp


def jaccard(a, b):
    aset = {k for k,v in a.items() if v}; bset = {k for k,v in b.items() if v}
    if not aset and not bset: return 1.0
    return len(aset & bset) / len(aset | bset)


def auc(pos, neg):
    nc = nt = 0
    for p in pos:
        for n in neg:
            if p > n: nc += 1
            elif p == n: nc += 0.5
            nt += 1
    return nc/nt if nt else float("nan")


def main():
    out_dir = Path("/tmp/round102_exposure"); out_dir.mkdir(exist_ok=True)
    img_dir = out_dir / "images"; img_dir.mkdir(exist_ok=True)
    vision_ops.register_all()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    runtime = Runtime()
    for pp in dsl.parse_source(text):
        if not pp.ok: continue
        try:
            P.type_check(pp.pred); runtime.install(pp.pred)
        except Exception: pass
    pred_names = runtime.installed()
    print(f"loaded {len(pred_names)} predicates")

    EVS = [-2.0, -1.0, 0.0, 1.0, 2.0]
    fingerprints = {}
    for scene_name, fn in SCENES.items():
        print(f"--- {scene_name} ---")
        rgb = fn()
        Image.fromarray(rgb).save(img_dir / f"{scene_name}_source.png")
        for ev in EVS:
            tic = time.time()
            mod = apply_exposure(rgb, ev)
            if scene_name == "landscape":
                Image.fromarray(mod).save(img_dir / f"{scene_name}_ev{ev:+.0f}.png")
            fp = fingerprint(mod, f"{scene_name}_ev{ev:+.1f}", runtime, pred_names)
            fingerprints[(scene_name, ev)] = fp
            print(f"  ev={ev:+.1f}  {sum(fp.values())}/{len(fp)} fired ({time.time()-tic:.1f}s)")

    same, diff = [], []
    by_evp = {}
    for (s1,e1),(s2,e2) in combinations(list(fingerprints.keys()), 2):
        j = jaccard(fingerprints[(s1,e1)], fingerprints[(s2,e2)])
        if s1 == s2:
            same.append((s1,e1,e2,j))
            by_evp.setdefault(tuple(sorted((e1,e2))), []).append(j)
        else:
            diff.append((s1,e1,s2,e2,j))

    same_J = np.array([t[3] for t in same])
    diff_J = np.array([t[4] for t in diff])
    auc_val = auc(same_J, diff_J)
    ratio = float(same_J.mean()/diff_J.mean()) if len(diff_J) else float("nan")

    per_scene = {}
    for s in SCENES:
        per = [t[3] for t in same if t[0]==s]
        if per:
            per_scene[s] = {"n": len(per), "mean_J": float(np.mean(per)),
                              "min_J": float(np.min(per)), "max_J": float(np.max(per))}
    evp_stats = {f"{a:+.1f}vs{b:+.1f}": {"n": len(v), "mean_J": float(np.mean(v)),
                  "min_J": float(np.min(v))} for (a,b),v in by_evp.items()}

    result = {
        "round": "R102", "date": "2026-05-01",
        "method": "synthetic high-DR scenes (5) × 5 EV stops (-2/-1/0/+1/+2)",
        "n_scenes": len(SCENES), "ev_levels": EVS,
        "n_fingerprints": len(fingerprints),
        "same_scene_pairs": int(len(same_J)),
        "diff_scene_pairs": int(len(diff_J)),
        "same_scene_mean_J": float(same_J.mean()),
        "same_scene_median_J": float(np.median(same_J)),
        "same_scene_min_J": float(same_J.min()),
        "diff_scene_mean_J": float(diff_J.mean()),
        "diff_scene_median_J": float(np.median(diff_J)),
        "ratio_same_to_diff": ratio, "auc_same_vs_diff": auc_val,
        "per_scene_stability": per_scene,
        "ev_pair_stability": dict(sorted(evp_stats.items(),
                                            key=lambda kv: kv[1]["mean_J"], reverse=True)),
    }
    (out_dir/"round102_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R102 RESULTS ===")
    print(json.dumps({k:v for k,v in result.items()
                       if k not in ("per_scene_stability","ev_pair_stability")}, indent=2))
    print("\nper_scene:")
    for k,v in per_scene.items():
        print(f"  {k:14s}  mean_J={v['mean_J']:.3f}  min={v['min_J']:.3f}  max={v['max_J']:.3f}")
    print("\nev_pair (sorted, top→bottom):")
    for k,v in result["ev_pair_stability"].items():
        print(f"  {k}: mean_J={v['mean_J']:.3f}  min={v['min_J']:.3f}")

if __name__ == "__main__":
    main()
