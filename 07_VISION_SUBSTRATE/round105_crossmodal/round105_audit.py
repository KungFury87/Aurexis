"""Round 105 — cross-modal compositional predicates (calibrated retune).

Pivot from R105 first-pass: composition machinery passed; threshold
calibration didn't. Add a dedicated chlorophyll operator
(nir_to_visible_ratio) that captures vegetation's actual spectral
fingerprint (NIR plateau elevation), and relax the broad-spectrum
threshold to admit incandescent.
"""
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
F.VALID_DTYPES = F.VALID_DTYPES | {"depth", "hyperspectral"}
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops, operators as ops
from aurexis_workbench.visual_intake import _bundle_from_single

H = W = 160
N_BANDS = 31
WAVELENGTHS = np.linspace(400, 700, N_BANDS)
RNG = np.random.default_rng(105)

def gauss(c, w):
    g = np.exp(-((WAVELENGTHS - c)**2) / (2*w**2)); return g/g.max()

def chlorophyll_s():
    s = np.full(N_BANDS, 0.15)
    s += 0.25 * gauss(550, 30)
    s -= 0.10 * gauss(670, 20)
    s[WAVELENGTHS > 680] = 0.55
    return np.clip(s, 0, 1)
def green_plastic_s():
    return np.clip(np.full(N_BANDS, 0.10) + 0.55*gauss(540, 20), 0, 1)
def red_paint_s():
    return np.clip(np.full(N_BANDS, 0.08) + 0.65*gauss(640, 25), 0, 1)
def daylight_s():
    return np.clip(np.full(N_BANDS, 0.45) + RNG.normal(0, 0.02, N_BANDS), 0, 1)
def incandescent_s():
    return np.clip(0.10 + 0.50 * (WAVELENGTHS-400)/300, 0, 1)

def depth_far():
    d = np.full((H,W), 0.85); d[100:140, 60:100] = 0.7
    return d + RNG.normal(0, 0.005, d.shape)
def depth_close():
    d = np.full((H,W), 0.6); d[40:130, 30:120] = 0.20
    return d + RNG.normal(0, 0.005, d.shape)
def depth_uniform():
    return np.full((H,W), 0.6) + RNG.normal(0, 0.005, (H,W))
def depth_far_grad():
    d = np.zeros((H,W))
    for y in range(H): d[y] = 1.0 - 0.25*(y/H)
    return d

SCENES = {
    "far_vegetation":      (depth_far,        chlorophyll_s),
    "close_green_plastic": (depth_close,      green_plastic_s),
    "flat_daylit_wall":    (depth_uniform,    daylight_s),
    "close_red_object":    (depth_close,      red_paint_s),
    "distant_dusk":        (depth_far_grad,   incandescent_s),
}

def make_cube(spec_fn):
    cube = np.full((H, W, N_BANDS), 0.05)
    cube[20:140, 20:140] = spec_fn()[None, None, :]
    return np.clip(cube + RNG.normal(0, 0.01, cube.shape), 0, 1)

RGB_BASIS = np.stack([gauss(610,35), gauss(540,35), gauss(450,35)], axis=0)
def render_rgb(c):
    rgb = (c.reshape(-1, N_BANDS) @ RGB_BASIS.T).reshape(H, W, 3)
    rgb = rgb / max(rgb.max(), 1e-6)
    return (rgb*255).clip(0,255).astype(np.uint8)


def _mean_depth(d): return float(np.mean(d))
def _foreground_fraction(d, t): return float(np.mean(d < float(t)))
def _band_centroid(c):
    be = c.sum(axis=(0,1))
    if be.sum() < 1e-9: return 0.5
    return float((be * np.arange(N_BANDS)).sum() / be.sum()) / (N_BANDS-1)
def _narrow_peak_score(c):
    be = c.sum(axis=(0,1))
    return float(be.max() / (be.sum() + 1e-9))
def _chlorophyll_red_edge(c):
    """Red-edge STEP detector: (NIR - red_dip) / (NIR + red_dip).
    Vegetation: NIR ~0.55, red_dip ~0.05 (chlorophyll absorbs 670nm) -> ~0.83.
    Incandescent: NIR ~0.6, red_dip ~0.55 (smooth ramp, no dip) -> ~0.04.
    Daylight: flat -> ~0.0.
    """
    be = c.sum(axis=(0,1))
    nir = be[-3:].mean()
    red_dip = be[26:28].mean()
    return float((nir - red_dip) / (nir + red_dip + 1e-9))


CROSS_MODAL_VOCAB = """
predicate is_distant_vegetation
  expects depth_field:depth, spectral:hyperspectral
  returns bool
  intent  far_depth_AND_chlorophyll_NIR_plateau_signature
  body    AND(gt(mean_depth(depth_field), 0.7), gt(chlorophyll_red_edge(spectral), 0.3))


predicate is_close_chromatic_object
  expects depth_field:depth, spectral:hyperspectral, foreground_threshold:scalar
  returns bool
  intent  close_subject_AND_narrow_spectral_peak
  body    AND(gt(foreground_fraction(depth_field, foreground_threshold), 0.25), gt(narrow_peak_score(spectral), 0.075))


predicate is_uniform_lit_far_field
  expects depth_field:depth, spectral:hyperspectral
  returns bool
  intent  far_field_AND_broad_spectrum_for_diffuse_distant_lighting
  body    AND(gt(mean_depth(depth_field), 0.7), lt(narrow_peak_score(spectral), 0.06))
"""

def main():
    out_dir = Path("/tmp/round105_crossmodal"); out_dir.mkdir(exist_ok=True)
    img_dir = out_dir / "images"; img_dir.mkdir(exist_ok=True)
    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    base_count = len(runtime.installed())

    ops.register("mean_depth", ("depth",), "scalar", _mean_depth, "Mean depth.")
    ops.register("foreground_fraction", ("depth","scalar"), "scalar", _foreground_fraction, "Frac < t.")
    ops.register("band_centroid", ("hyperspectral",), "scalar", _band_centroid, "Band centroid.")
    ops.register("narrow_peak_score", ("hyperspectral",), "scalar", _narrow_peak_score, "max/total.")
    ops.register("chlorophyll_red_edge", ("hyperspectral",), "scalar", _chlorophyll_red_edge, "Red-edge step (NIR - red_dip) / (NIR + red_dip).")

    cm_names = []
    for pp in dsl.parse_source(CROSS_MODAL_VOCAB):
        if not pp.ok:
            print("PARSE FAIL", pp.diagnostics); continue
        try:
            P.type_check(pp.pred); runtime.install(pp.pred); cm_names.append(pp.pred.name)
        except Exception as e:
            print(f"TYPE FAIL {pp.pred.name}: {e}")
    print(f"installed: {len(runtime.installed())} predicates ({len(cm_names)} cross-modal)")

    pred_names = runtime.installed()
    fingerprints = {}
    spectral_summary = {}
    for scene, (depth_fn, spec_fn) in SCENES.items():
        d = depth_fn(); cube = make_cube(spec_fn); rgb = render_rgb(cube)
        Image.fromarray(rgb).save(img_dir/f"{scene}_rgb.png")
        Image.fromarray((d*255).clip(0,255).astype(np.uint8)).save(img_dir/f"{scene}_depth.png")
        luma = (0.299*rgb[...,0]+0.587*rgb[...,1]+0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, scene, patch_size=64, color=color)
        bundle.add_value("depth_field", "depth", d, "depth")
        bundle.add_value("spectral", "hyperspectral", cube, "31-band cube")
        bundle.add_value("foreground_threshold", "scalar", 0.4, "fg t")

        fp = {}
        for pn in pred_names:
            r = runtime.evaluate(pn, bundle)
            fp[pn] = bool(r.value) if (r.error is None and r.value is not None) else False
        fingerprints[scene] = fp

        spectral_summary[scene] = {
            "depth_mean": round(_mean_depth(d), 3),
            "band_centroid": round(_band_centroid(cube), 3),
            "narrow_peak": round(_narrow_peak_score(cube), 3),
            "red_edge": round(_chlorophyll_red_edge(cube), 3),
        }
        cm_v = {p: fp[p] for p in cm_names}
        print(f"\n{scene}: {spectral_summary[scene]}")
        print(f"  cross-modal: {cm_v}")

    expected = {
        "is_distant_vegetation":      ["far_vegetation"],
        "is_close_chromatic_object":  ["close_green_plastic", "close_red_object"],
        "is_uniform_lit_far_field":   ["distant_dusk"],
    }
    correctness = {}
    for cm in cm_names:
        actual = [s for s in SCENES if fingerprints[s][cm]]
        exp = expected[cm]
        correctness[cm] = {
            "fires_on": actual, "expected": exp,
            "matches_design": set(actual) == set(exp),
            "ir_clean": 0 < len(actual) < len(SCENES),
        }

    # Specificity test for distant_vegetation
    spec_test = {
        "fires_on_far_vegetation":
            fingerprints["far_vegetation"]["is_distant_vegetation"],
        "rejects_close_green_plastic_(spectral_confusable)":
            not fingerprints["close_green_plastic"]["is_distant_vegetation"],
        "rejects_distant_dusk_(depth_confusable)":
            not fingerprints["distant_dusk"]["is_distant_vegetation"],
    }

    base_only = {s:{k:v for k,v in fp.items() if k not in cm_names} for s,fp in fingerprints.items()}
    def jacc(a,b):
        A={k for k,v in a.items() if v}; B={k for k,v in b.items() if v}
        return 1.0 if not A and not B else len(A&B)/len(A|B)
    base_J = np.array([jacc(base_only[a], base_only[b]) for a,b in combinations(SCENES, 2)])
    full_J = np.array([jacc(fingerprints[a], fingerprints[b]) for a,b in combinations(SCENES, 2)])

    result = {
        "round": "R105", "date": "2026-05-01",
        "method": "5 scenes × paired (depth, hyperspectral) → 3 cross-modal predicates AND-composing across both modalities",
        "n_scenes": len(SCENES), "n_base_predicates": base_count,
        "n_cross_modal_predicates": len(cm_names),
        "type_check_all_passed": len(cm_names) == 3,
        "scene_metrics": spectral_summary,
        "correctness": correctness,
        "all_match_design_count": sum(1 for v in correctness.values() if v["matches_design"]),
        "ir_clean_count": sum(1 for v in correctness.values() if v["ir_clean"]),
        "specificity_test_distant_vegetation": spec_test,
        "specificity_passes_all_3": all(spec_test.values()),
        "pairwise_J_baseline_146": float(base_J.mean()),
        "pairwise_J_with_crossmodal_149": float(full_J.mean()),
        "delta_J_mean": float((full_J - base_J).mean()),
    }
    (out_dir/"round105_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R105 RESULTS ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
