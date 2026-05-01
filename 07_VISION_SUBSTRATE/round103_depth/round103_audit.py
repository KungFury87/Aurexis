"""Round 103 — depth field type + 3 depth-aware predicates."""
from __future__ import annotations
import json, sys
from itertools import combinations
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path("/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/"
            "Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE")
sys.path.insert(0, str(ROOT))

from aurexis_workbench import fields as F
F.VALID_DTYPES = F.VALID_DTYPES | {"depth"}

from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops, operators as ops
from aurexis_workbench.visual_intake import _bundle_from_single

H = W = 320
RNG = np.random.default_rng(101)


def scene_indoor_close():
    img = np.full((H, W, 3), 200, dtype=np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    subj = ((xx - W//2)**2/60**2 + (yy - H//2)**2/80**2) < 1
    img[subj] = [180, 100, 80]
    img = np.clip(img + RNG.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    depth = np.full((H, W), 0.9, dtype=np.float64)
    depth[subj] = 0.2
    return img, depth

def scene_landscape():
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H//2):
        t = y / (H//2)
        img[y] = [int(220-60*t), int(230-50*t), int(255-30*t)]
    for x in range(W):
        peak = int(H//2 + 60*np.sin(x*0.02))
        img[peak:peak+80, x] = [70, 80, 90]
    img[H//2 + 100:] = [25, 30, 20]
    img = np.clip(img + RNG.integers(-10, 10, img.shape), 0, 255).astype(np.uint8)
    depth = np.zeros((H, W), dtype=np.float64)
    for y in range(H):
        depth[y] = 1.0 - 0.5*(y/H)
    return img, depth

def scene_flat_wall():
    img = np.full((H, W, 3), 160, dtype=np.uint8)
    img = np.clip(img + RNG.integers(-30, 30, img.shape), 0, 255).astype(np.uint8)
    depth = np.full((H, W), 0.6, dtype=np.float64) + RNG.normal(0, 0.005, (H,W))
    return img, depth

def scene_object_on_table():
    img = np.full((H, W, 3), 140, dtype=np.uint8)
    img[180:280, 80:240] = [90, 50, 30]
    img = np.clip(img + RNG.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    depth = np.full((H, W), 0.7, dtype=np.float64)
    depth[180:280, 80:240] = 0.25
    return img, depth

def scene_layered():
    img = np.full((H, W, 3), 200, dtype=np.uint8)
    img[40:120, 40:280] = [150, 170, 200]
    img[170:260, 100:220] = [80, 60, 50]
    img[260:, :] = [40, 30, 20]
    img = np.clip(img + RNG.integers(-8, 8, img.shape), 0, 255).astype(np.uint8)
    depth = np.full((H, W), 0.95, dtype=np.float64)
    depth[40:120, 40:280] = 0.5
    depth[170:260, 100:220] = 0.15
    depth[260:, :] = 0.3
    return img, depth

SCENES = {
    "indoor_close": scene_indoor_close,
    "landscape":    scene_landscape,
    "flat_wall":    scene_flat_wall,
    "object_table": scene_object_on_table,
    "layered":      scene_layered,
}


def _mean_depth(d): return float(np.mean(d))
def _depth_variance_score(d):
    m = float(np.mean(d)); s = float(np.std(d))
    return s / (abs(m) + 1e-6)
def _foreground_fraction(d, threshold):
    return float(np.mean(d < float(threshold)))


DEPTH_VOCAB = """
predicate has_shallow_depth_signal
  expects depth_field:depth
  returns bool
  intent  detect_strong_depth_variation_typical_of_subject_separation
  body    gt(depth_variance_score(depth_field), 0.4)


predicate has_dominant_foreground
  expects depth_field:depth, foreground_threshold:scalar
  returns bool
  intent  detect_significant_close_subject_in_frame
  body    gt(foreground_fraction(depth_field, foreground_threshold), 0.25)


predicate has_far_field_dominance
  expects depth_field:depth
  returns bool
  intent  detect_distant_landscape_or_far_dominant_scene
  body    gt(mean_depth(depth_field), 0.7)
"""


def main():
    out_dir = Path("/tmp/round103_depth"); out_dir.mkdir(exist_ok=True)
    img_dir = out_dir / "images"; img_dir.mkdir(exist_ok=True)

    vision_ops.register_all()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    runtime = Runtime()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    base_count = len(runtime.installed())

    ops.register("mean_depth", ("depth",), "scalar", _mean_depth, "Mean depth.")
    ops.register("depth_variance_score", ("depth",), "scalar", _depth_variance_score, "std/mean depth.")
    ops.register("foreground_fraction", ("depth","scalar"), "scalar", _foreground_fraction, "Frac < threshold.")

    depth_pred_names = []
    for pp in dsl.parse_source(DEPTH_VOCAB):
        if not pp.ok:
            print("PARSE FAIL", pp.diagnostics if hasattr(pp,"diagnostics") else pp)
            continue
        try:
            P.type_check(pp.pred); runtime.install(pp.pred)
            depth_pred_names.append(pp.pred.name)
        except Exception as e:
            print(f"TYPE FAIL {pp.pred.name}: {e}")
    print(f"loaded {base_count} base + {len(depth_pred_names)} depth = {len(runtime.installed())} total")

    pred_names = runtime.installed()
    fingerprints = {}
    for scene_name, fn in SCENES.items():
        rgb, depth = fn()
        Image.fromarray(rgb).save(img_dir / f"{scene_name}_rgb.png")
        Image.fromarray((depth*255).astype(np.uint8)).save(img_dir / f"{scene_name}_depth.png")
        luma = (0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, scene_name, patch_size=64, color=color)
        bundle.add_value("depth_field", "depth", depth, "depth map")
        bundle.add_value("foreground_threshold", "scalar", 0.4, "fg threshold")

        fp = {}
        for pname in pred_names:
            rec = runtime.evaluate(pname, bundle)
            v = bool(rec.value) if (rec.error is None and rec.value is not None) else False
            fp[pname] = v
        fingerprints[scene_name] = fp
        depth_v = {p: fp[p] for p in depth_pred_names}
        print(f"\n{scene_name}: {sum(fp.values())}/{len(fp)} fired")
        print(f"  mean={np.mean(depth):.3f} var_score={np.std(depth)/(np.mean(depth)+1e-6):.3f} fg_frac={(depth<0.4).mean():.3f}")
        print(f"  depth verdicts: {depth_v}")

    discrimination = {}
    for dp in depth_pred_names:
        fires = [s for s in SCENES if fingerprints[s][dp]]
        discrimination[dp] = {
            "fires_on": fires, "n_fires": len(fires),
            "ir_clean": 0 < len(fires) < len(SCENES),
        }

    base_only = {s: {k:v for k,v in fp.items() if k not in depth_pred_names}
                  for s,fp in fingerprints.items()}
    def jacc(a,b):
        A = {k for k,v in a.items() if v}; B = {k for k,v in b.items() if v}
        if not A and not B: return 1.0
        return len(A&B)/len(A|B)
    base_pairs, full_pairs = [], []
    for s1,s2 in combinations(SCENES.keys(), 2):
        base_pairs.append(jacc(base_only[s1], base_only[s2]))
        full_pairs.append(jacc(fingerprints[s1], fingerprints[s2]))
    base_J = np.array(base_pairs); full_J = np.array(full_pairs)

    result = {
        "round": "R103", "date": "2026-05-01",
        "method": "5 synthetic scenes with hand-authored depth maps",
        "n_scenes": len(SCENES), "n_base_predicates": base_count,
        "n_depth_predicates": len(depth_pred_names),
        "depth_predicates": depth_pred_names,
        "discrimination": discrimination,
        "ir_clean_count": sum(1 for v in discrimination.values() if v["ir_clean"]),
        "pairwise_J_baseline_146": float(np.mean(base_J)),
        "pairwise_J_with_depth_149": float(np.mean(full_J)),
        "delta_J_mean": float(np.mean(full_J - base_J)),
        "n_pairs_changed_by_depth": int(np.sum(np.abs(full_J - base_J) > 0.001)),
    }
    (out_dir/"round103_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R103 RESULTS ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
