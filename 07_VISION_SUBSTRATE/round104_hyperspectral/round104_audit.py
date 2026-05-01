"""Round 104 — hyperspectral dtype + 3 spectral predicates.

Test: can the substrate discriminate scenes that are near-identical
in RGB but spectrally distinct? If yes, hyperspectral predicates are
adding genuine new signal beyond the 146 RGB-based predicates.

Method:
  - Synthesize 5 31-band hyperspectral cubes (HxWx31, λ ∈ [400nm, 700nm])
  - Render each to RGB via standard CIE-like sensitivity curves
  - The KEY pair is vegetation vs green-plastic: both render to similar RGB
    but have completely different spectra
  - Run substrate (146 RGB preds + 3 new hyperspectral preds)
  - Check: does adding hyperspectral predicates lower the
    vegetation/green-plastic Jaccard (= they look more different now)?
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
F.VALID_DTYPES = F.VALID_DTYPES | {"hyperspectral"}

from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops, operators as ops
from aurexis_workbench.visual_intake import _bundle_from_single

H = W = 160
N_BANDS = 31  # 400nm to 700nm in 10nm steps
RNG = np.random.default_rng(104)

# Wavelengths centered on each band: 400, 410, ... 700
WAVELENGTHS = np.linspace(400, 700, N_BANDS)


# ---- Spectral profiles (per-band reflectance) ----------------------------

def gaussian(center, width):
    """Normalized gaussian over WAVELENGTHS."""
    g = np.exp(-((WAVELENGTHS - center)**2) / (2*width**2))
    return g / g.max()

def _vegetation_spectrum():
    """Chlorophyll: drops in red, rises sharply in near-infrared."""
    # Approximate: low blue, higher green, drop ~660nm (red absorption),
    # then strong rise toward 700nm (start of NIR plateau)
    s = np.full(N_BANDS, 0.15)
    s += 0.25 * gaussian(550, 30)   # green peak
    # red drop (chlorophyll absorption)
    s -= 0.10 * gaussian(670, 20)
    # NIR plateau rise (everything past ~680)
    nir_mask = WAVELENGTHS > 680
    s[nir_mask] = 0.55
    return np.clip(s, 0, 1)

def _green_plastic_spectrum():
    """Narrow green peak at 540nm, low everywhere else. RGB looks green."""
    s = np.full(N_BANDS, 0.10)
    s += 0.55 * gaussian(540, 20)  # narrow green peak
    return np.clip(s, 0, 1)

def _red_paint_spectrum():
    """Narrow red peak at 640nm. RGB looks red."""
    s = np.full(N_BANDS, 0.08)
    s += 0.65 * gaussian(640, 25)
    return np.clip(s, 0, 1)

def _incandescent_spectrum():
    """Broad warm spectrum, ramps from low at 400nm to high at 700nm."""
    s = 0.10 + 0.50 * (WAVELENGTHS - 400) / 300
    return np.clip(s, 0, 1)

def _daylight_spectrum():
    """Broad and flat — D65-ish."""
    s = np.full(N_BANDS, 0.45) + RNG.normal(0, 0.02, N_BANDS)
    return np.clip(s, 0, 1)

SCENE_SPECTRA = {
    "vegetation":   _vegetation_spectrum,
    "green_plastic": _green_plastic_spectrum,
    "red_paint":    _red_paint_spectrum,
    "incandescent": _incandescent_spectrum,
    "daylight":     _daylight_spectrum,
}


# ---- Build 31-band hyperspectral cube + RGB render -----------------------

def make_hyperspectral_scene(spectrum_fn, kind="block"):
    """Build a HxWx31 cube with some spatial structure + the given
    spectrum populated in the foreground region."""
    cube = np.full((H, W, N_BANDS), 0.05, dtype=np.float64)
    spec = spectrum_fn()
    if kind == "block":
        cube[40:120, 30:130] = spec[None, None, :]
    else:
        cube[:] = spec[None, None, :]
    # add tiny pixel noise per-band
    cube = np.clip(cube + RNG.normal(0, 0.01, cube.shape), 0, 1)
    return cube


# Simple RGB sensitivity (peaks ~600/540/450nm, gaussian-shaped)
RED_SENS   = gaussian(610, 35)
GREEN_SENS = gaussian(540, 35)
BLUE_SENS  = gaussian(450, 35)
RGB_BASIS = np.stack([RED_SENS, GREEN_SENS, BLUE_SENS], axis=0)  # 3xN_BANDS

def render_rgb(cube):
    """cube HxWxN_BANDS -> RGB HxWx3 uint8."""
    flat = cube.reshape(-1, N_BANDS)            # (H*W, N_BANDS)
    rgb_flat = flat @ RGB_BASIS.T                # (H*W, 3)
    rgb = rgb_flat.reshape(H, W, 3)
    rgb = rgb / max(rgb.max(), 1e-6)             # normalize per-scene
    return (rgb * 255).clip(0, 255).astype(np.uint8)


# ---- Hyperspectral operators --------------------------------------------

def _band_centroid(cube):
    """Mean wavelength weighted by per-band total energy, normalized to [0,1]."""
    # Per-band total energy across all pixels
    band_energy = cube.sum(axis=(0, 1))     # (N_BANDS,)
    if band_energy.sum() < 1e-9:
        return 0.5
    band_idx = np.arange(N_BANDS)
    centroid = float((band_energy * band_idx).sum() / band_energy.sum())
    return centroid / (N_BANDS - 1)

def _spectral_variance(cube):
    """std of per-band total energy / mean (scale-free spread)."""
    band_energy = cube.sum(axis=(0, 1))
    m = float(band_energy.mean())
    s = float(band_energy.std())
    return s / (abs(m) + 1e-9)

def _narrow_peak_score(cube):
    """max band energy / total energy across all bands.
    High value = single dominant wavelength.
    Low value = energy spread across bands.
    """
    band_energy = cube.sum(axis=(0, 1))
    total = band_energy.sum()
    return float(band_energy.max() / (total + 1e-9))


# ---- DSL predicates -----------------------------------------------------

HYPER_VOCAB = """
predicate has_narrow_spectral_peak
  expects spectral:hyperspectral
  returns bool
  intent  detect_single_dominant_wavelength_signature
  body    gt(narrow_peak_score(spectral), 0.075)


predicate has_broad_spectral_distribution
  expects spectral:hyperspectral
  returns bool
  intent  detect_broadband_continuous_spectrum
  body    lt(narrow_peak_score(spectral), 0.045)


predicate has_red_shifted_centroid
  expects spectral:hyperspectral
  returns bool
  intent  detect_long_wavelength_dominant_spectrum
  body    gt(band_centroid(spectral), 0.6)
"""


def main():
    out_dir = Path("/tmp/round104_hyperspectral"); out_dir.mkdir(exist_ok=True)
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

    ops.register("band_centroid", ("hyperspectral",), "scalar", _band_centroid,
                  "Energy-weighted mean band index, normalized [0,1].")
    ops.register("spectral_variance", ("hyperspectral",), "scalar",
                  _spectral_variance, "std/mean of per-band total energies.")
    ops.register("narrow_peak_score", ("hyperspectral",), "scalar",
                  _narrow_peak_score, "max band / total energy.")

    hyper_pred_names = []
    for pp in dsl.parse_source(HYPER_VOCAB):
        if not pp.ok:
            print("PARSE FAIL", pp.diagnostics)
            continue
        try:
            P.type_check(pp.pred); runtime.install(pp.pred)
            hyper_pred_names.append(pp.pred.name)
        except Exception as e:
            print(f"TYPE FAIL {pp.pred.name}: {e}")
    print(f"loaded {base_count} base + {len(hyper_pred_names)} hyperspectral = {len(runtime.installed())}")

    pred_names = runtime.installed()
    fingerprints = {}
    spectra_summary = {}
    for scene_name, spec_fn in SCENE_SPECTRA.items():
        cube = make_hyperspectral_scene(spec_fn)
        rgb = render_rgb(cube)
        Image.fromarray(rgb).save(img_dir / f"{scene_name}_rgb.png")

        # Save spectrum plot data (per-band mean over foreground region)
        spec_avg = cube[40:120, 30:130, :].mean(axis=(0, 1))
        spectra_summary[scene_name] = {
            "spectrum_per_band": [round(float(v), 4) for v in spec_avg],
            "rgb_means": [int(rgb[..., c].mean()) for c in range(3)],
        }

        luma = (0.299*rgb[...,0] + 0.587*rgb[...,1] + 0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, scene_name, patch_size=64, color=color)
        bundle.add_value("spectral", "hyperspectral", cube, "31-band cube")

        fp = {}
        for pname in pred_names:
            rec = runtime.evaluate(pname, bundle)
            v = bool(rec.value) if (rec.error is None and rec.value is not None) else False
            fp[pname] = v
        fingerprints[scene_name] = fp

        bc = _band_centroid(cube)
        sv = _spectral_variance(cube)
        np_score = _narrow_peak_score(cube)
        hyper_v = {p: fp[p] for p in hyper_pred_names}
        print(f"\n{scene_name}: {sum(fp.values())}/{len(fp)} fired total")
        print(f"  RGB mean: R={rgb[...,0].mean():.0f} G={rgb[...,1].mean():.0f} B={rgb[...,2].mean():.0f}")
        print(f"  band_centroid={bc:.3f} spectral_variance={sv:.3f} narrow_peak_score={np_score:.3f}")
        print(f"  hyperspectral verdicts: {hyper_v}")

    # Discrimination check
    discrimination = {}
    for hp in hyper_pred_names:
        fires = [s for s in SCENE_SPECTRA if fingerprints[s][hp]]
        discrimination[hp] = {
            "fires_on": fires, "n_fires": len(fires),
            "ir_clean": 0 < len(fires) < len(SCENE_SPECTRA),
        }

    # Pairwise Jaccards: with vs without hyperspectral predicates
    base_only = {s: {k:v for k,v in fp.items() if k not in hyper_pred_names}
                  for s,fp in fingerprints.items()}
    def jacc(a,b):
        A = {k for k,v in a.items() if v}; B = {k for k,v in b.items() if v}
        if not A and not B: return 1.0
        return len(A&B)/len(A|B)

    pair_deltas = {}
    base_pairs, full_pairs = [], []
    for s1,s2 in combinations(SCENE_SPECTRA.keys(), 2):
        b = jacc(base_only[s1], base_only[s2])
        f = jacc(fingerprints[s1], fingerprints[s2])
        base_pairs.append(b); full_pairs.append(f)
        pair_deltas[f"{s1} vs {s2}"] = {"base_J": round(b, 3), "full_J": round(f, 3),
                                           "delta": round(f - b, 3)}
    base_J = np.array(base_pairs); full_J = np.array(full_pairs)

    # KEY check: vegetation vs green_plastic — should the most-discriminated pair
    veg_vs_green = pair_deltas.get("vegetation vs green_plastic", {})

    result = {
        "round": "R104", "date": "2026-05-01",
        "method": "5 synthetic 31-band hyperspectral cubes (400-700nm, 10nm steps)",
        "n_scenes": len(SCENE_SPECTRA), "n_bands": N_BANDS,
        "n_base_predicates": base_count,
        "n_hyperspectral_predicates": len(hyper_pred_names),
        "hyperspectral_predicates": hyper_pred_names,
        "discrimination": discrimination,
        "ir_clean_count": sum(1 for v in discrimination.values() if v["ir_clean"]),
        "pairwise_J_baseline_146": float(np.mean(base_J)),
        "pairwise_J_with_hyperspectral_149": float(np.mean(full_J)),
        "delta_J_mean": float(np.mean(full_J - base_J)),
        "key_pair_vegetation_vs_green_plastic": veg_vs_green,
        "all_pair_deltas": pair_deltas,
        "rgb_means_per_scene": {s: spectra_summary[s]["rgb_means"]
                                  for s in spectra_summary},
    }
    (out_dir/"round104_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R104 RESULTS ===")
    print(json.dumps({k:v for k,v in result.items() if k != "all_pair_deltas"}, indent=2))


if __name__ == "__main__":
    main()
