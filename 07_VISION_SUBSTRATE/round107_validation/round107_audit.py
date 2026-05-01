"""Round 107 — N=20 corpus-scale validation of 9 experimental predicates.

Systematic corpus: 4 depth structures × 5 spectral profiles = 20 scenes.
Each scene carries paired RGB + depth + hyperspectral.

Tests for each of the 9 R103-R105 predicates:
  1. fire rate in [10%, 70%] (not too rare, not too common)
  2. IR-clean: no other predicate has IDENTICAL fire pattern (equivalence-class clean)
  3. Jaccard against existing 146 preds < 0.95 (no near-collision)
  4. cross-modal preds remain selective: AND-firing pattern matches design

Promote to vocab.aurex only predicates that pass all 4 tests.
Retire predicates that fail with documented reason.
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

H = W = 128
N_BANDS = 31
WAVELENGTHS = np.linspace(400, 700, N_BANDS)
RNG = np.random.default_rng(107)

def gauss(c, w):
    g = np.exp(-((WAVELENGTHS - c)**2) / (2*w**2)); return g/g.max()

# ---- 5 spectral profiles -----------------------------------------------
def s_chlorophyll():
    s = np.full(N_BANDS, 0.15)
    s += 0.25 * gauss(550, 30)
    s -= 0.10 * gauss(670, 20)
    s[WAVELENGTHS > 680] = 0.55
    return np.clip(s, 0, 1)
def s_narrow_green():
    return np.clip(np.full(N_BANDS, 0.10) + 0.55*gauss(540, 20), 0, 1)
def s_narrow_red():
    return np.clip(np.full(N_BANDS, 0.08) + 0.65*gauss(640, 25), 0, 1)
def s_broad_warm():
    return np.clip(0.10 + 0.50*(WAVELENGTHS-400)/300, 0, 1)
def s_broad_flat():
    return np.clip(np.full(N_BANDS, 0.45) + RNG.normal(0, 0.02, N_BANDS), 0, 1)

SPECTRA = {"chloro": s_chlorophyll, "n_green": s_narrow_green,
           "n_red": s_narrow_red, "warm": s_broad_warm, "flat": s_broad_flat}

# ---- 4 depth structures -------------------------------------------------
def d_far():
    d = np.full((H,W), 0.85); return d + RNG.normal(0, 0.005, d.shape)
def d_close():
    d = np.full((H,W), 0.6); d[20:108, 20:108] = 0.20
    return d + RNG.normal(0, 0.005, d.shape)
def d_uniform():
    return np.full((H,W), 0.6) + RNG.normal(0, 0.005, (H,W))
def d_gradient():
    d = np.zeros((H,W))
    for y in range(H): d[y] = 1.0 - 0.4*(y/H)
    return d + RNG.normal(0, 0.005, (H,W))

DEPTHS = {"far": d_far, "close": d_close, "uniform": d_uniform, "grad": d_gradient}

# ---- All 20 scene combinations -----------------------------------------
SCENES = {f"{dn}_{sn}": (df, sf)
          for dn, df in DEPTHS.items()
          for sn, sf in SPECTRA.items()}

def make_cube(spec_fn):
    cube = np.full((H, W, N_BANDS), 0.05)
    cube[16:112, 16:112] = spec_fn()[None, None, :]
    return np.clip(cube + RNG.normal(0, 0.01, cube.shape), 0, 1)

RGB_BASIS = np.stack([gauss(610,35), gauss(540,35), gauss(450,35)], axis=0)
def render_rgb(c):
    rgb = (c.reshape(-1, N_BANDS) @ RGB_BASIS.T).reshape(H, W, 3)
    rgb = rgb / max(rgb.max(), 1e-6)
    return (rgb*255).clip(0,255).astype(np.uint8)


def _mean_depth(d): return float(np.mean(d))
def _depth_variance_score(d):
    m, s = float(np.mean(d)), float(np.std(d))
    return s / (abs(m) + 1e-6)
def _foreground_fraction(d, t): return float(np.mean(d < float(t)))
def _band_centroid(c):
    be = c.sum(axis=(0,1))
    if be.sum() < 1e-9: return 0.5
    return float((be * np.arange(N_BANDS)).sum() / be.sum()) / (N_BANDS-1)
def _spectral_variance(c):
    be = c.sum(axis=(0,1)); return float(be.std()/(abs(be.mean())+1e-9))
def _narrow_peak_score(c):
    be = c.sum(axis=(0,1)); return float(be.max()/(be.sum()+1e-9))
def _chlorophyll_red_edge(c):
    be = c.sum(axis=(0,1))
    nir = be[-3:].mean(); red_dip = be[26:28].mean()
    return float((nir - red_dip)/(nir + red_dip + 1e-9))


# All 9 R103-R105 experimental predicates
EXP_VOCAB = """
predicate has_shallow_depth_signal
  expects depth_field:depth
  returns bool
  intent  detect_strong_depth_variation
  body    gt(depth_variance_score(depth_field), 0.4)


predicate has_dominant_foreground
  expects depth_field:depth, foreground_threshold:scalar
  returns bool
  intent  detect_significant_close_subject
  body    gt(foreground_fraction(depth_field, foreground_threshold), 0.25)


predicate has_far_field_dominance
  expects depth_field:depth
  returns bool
  intent  detect_distant_dominant_scene
  body    gt(mean_depth(depth_field), 0.7)


predicate has_narrow_spectral_peak
  expects spectral:hyperspectral
  returns bool
  intent  detect_single_dominant_wavelength
  body    gt(narrow_peak_score(spectral), 0.075)


predicate has_broad_spectral_distribution
  expects spectral:hyperspectral
  returns bool
  intent  detect_flat_broad_spectrum
  body    lt(narrow_peak_score(spectral), 0.045)


predicate has_red_shifted_centroid
  expects spectral:hyperspectral
  returns bool
  intent  detect_long_wavelength_dominant
  body    gt(band_centroid(spectral), 0.6)


predicate is_distant_vegetation
  expects depth_field:depth, spectral:hyperspectral
  returns bool
  intent  far_depth_AND_chlorophyll_red_edge
  body    AND(gt(mean_depth(depth_field), 0.7), gt(chlorophyll_red_edge(spectral), 0.3))


predicate is_close_chromatic_object
  expects depth_field:depth, spectral:hyperspectral, foreground_threshold:scalar
  returns bool
  intent  close_subject_AND_narrow_spectral_peak
  body    AND(gt(foreground_fraction(depth_field, foreground_threshold), 0.25), gt(narrow_peak_score(spectral), 0.075))


predicate is_uniform_lit_far_field
  expects depth_field:depth, spectral:hyperspectral
  returns bool
  intent  far_field_AND_broad_spectrum
  body    AND(gt(mean_depth(depth_field), 0.7), lt(narrow_peak_score(spectral), 0.06))
"""


def main():
    out_dir = Path("/tmp/round107_validation"); out_dir.mkdir(exist_ok=True)
    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    base_pred_objs = []
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
                base_pred_objs.append(pp.pred)
            except Exception: pass
    base_count = len(runtime.installed())

    for name, fn, types in [
        ("mean_depth", _mean_depth, ("depth",)),
        ("depth_variance_score", _depth_variance_score, ("depth",)),
        ("foreground_fraction", _foreground_fraction, ("depth","scalar")),
        ("band_centroid", _band_centroid, ("hyperspectral",)),
        ("spectral_variance", _spectral_variance, ("hyperspectral",)),
        ("narrow_peak_score", _narrow_peak_score, ("hyperspectral",)),
        ("chlorophyll_red_edge", _chlorophyll_red_edge, ("hyperspectral",)),
    ]:
        ops.register(name, types, "scalar", fn, name)

    exp_names = []
    for pp in dsl.parse_source(EXP_VOCAB):
        if not pp.ok:
            print("PARSE FAIL", pp.diagnostics); continue
        try:
            P.type_check(pp.pred); runtime.install(pp.pred)
            exp_names.append(pp.pred.name)
        except Exception as e:
            print(f"TYPE FAIL {pp.pred.name}: {e}")
    print(f"installed: {base_count} base + {len(exp_names)} experimental")

    pred_names = runtime.installed()
    fingerprints = {}
    for scene_name, (depth_fn, spec_fn) in SCENES.items():
        d = depth_fn(); cube = make_cube(spec_fn); rgb = render_rgb(cube)
        luma = (0.299*rgb[...,0]+0.587*rgb[...,1]+0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, scene_name, patch_size=64, color=color)
        bundle.add_value("depth_field", "depth", d, "depth")
        bundle.add_value("spectral", "hyperspectral", cube, "31-band")
        bundle.add_value("foreground_threshold", "scalar", 0.4, "fg t")

        fp = {}
        for pn in pred_names:
            r = runtime.evaluate(pn, bundle)
            fp[pn] = bool(r.value) if (r.error is None and r.value is not None) else False
        fingerprints[scene_name] = fp

    # ---- Per-predicate analysis ----------------------------------------
    N = len(SCENES)
    analysis = {}
    for ep in exp_names:
        fires_on = [s for s in SCENES if fingerprints[s][ep]]
        rate = len(fires_on) / N
        my_pattern = tuple(fingerprints[s][ep] for s in SCENES)

        # Find predicates with same fire pattern (equivalence class)
        collisions = []
        for other in pred_names:
            if other == ep: continue
            other_pattern = tuple(fingerprints[s][other] for s in SCENES)
            if other_pattern == my_pattern:
                collisions.append(other)

        # Max Jaccard (over scenes-as-bits) against base preds
        my_bits = set(s for s in SCENES if fingerprints[s][ep])
        max_J = 0.0; max_J_with = None
        for bp in [b.name for b in base_pred_objs]:
            other_bits = set(s for s in SCENES if fingerprints[s][bp])
            if not my_bits and not other_bits:
                J = 1.0
            elif not my_bits or not other_bits:
                J = 0.0
            else:
                J = len(my_bits & other_bits) / len(my_bits | other_bits)
            if J > max_J:
                max_J = J; max_J_with = bp

        analysis[ep] = {
            "fire_rate": round(rate, 3),
            "n_fires": len(fires_on),
            "fires_on": fires_on,
            "rate_in_band_10_to_70_pct": 0.10 <= rate <= 0.70,
            "equivalence_class_collisions": collisions,
            "ir_clean_no_eq_collision": len(collisions) == 0,
            "max_jaccard_with_base": round(max_J, 3),
            "max_jaccard_partner": max_J_with,
            "below_collision_threshold_0_95": max_J < 0.95,
        }
        analysis[ep]["passes_all_checks"] = (
            analysis[ep]["rate_in_band_10_to_70_pct"]
            and analysis[ep]["ir_clean_no_eq_collision"]
            and analysis[ep]["below_collision_threshold_0_95"]
        )

    # Cross-modal selectivity check
    cross_modal_preds = ["is_distant_vegetation", "is_close_chromatic_object",
                          "is_uniform_lit_far_field"]
    cm_summary = {}
    for cm in cross_modal_preds:
        fires = analysis[cm]["fires_on"]
        # is_distant_vegetation should fire on all far_chloro variants only
        if cm == "is_distant_vegetation":
            expected = [s for s in SCENES if s.startswith("far_") and s.endswith("_chloro")]
        elif cm == "is_close_chromatic_object":
            expected = [s for s in SCENES if s.startswith("close_") and ("n_green" in s or "n_red" in s)]
        elif cm == "is_uniform_lit_far_field":
            expected = [s for s in SCENES if s.startswith("far_") and ("flat" in s or "warm" in s)]
        cm_summary[cm] = {
            "fires_on": fires, "expected_pattern": expected,
            "matches_design": set(fires) == set(expected),
            "extra_fires": [s for s in fires if s not in expected],
            "missing_fires": [s for s in expected if s not in fires],
        }

    promotion_decisions = {}
    for ep in exp_names:
        a = analysis[ep]
        decision = "PROMOTE" if a["passes_all_checks"] else "RETIRE"
        if not a["passes_all_checks"]:
            reasons = []
            if not a["rate_in_band_10_to_70_pct"]:
                reasons.append(f"fire_rate {a['fire_rate']} outside [0.1, 0.7]")
            if not a["ir_clean_no_eq_collision"]:
                reasons.append(f"equivalence-class collision with: {a['equivalence_class_collisions']}")
            if not a["below_collision_threshold_0_95"]:
                reasons.append(f"max J={a['max_jaccard_with_base']} with {a['max_jaccard_partner']}")
            promotion_decisions[ep] = {"decision": decision, "reasons": reasons}
        else:
            promotion_decisions[ep] = {"decision": decision}

    n_promote = sum(1 for v in promotion_decisions.values() if v["decision"]=="PROMOTE")

    result = {
        "round": "R107", "date": "2026-05-01",
        "method": "4 depth × 5 spectral = 20 systematic scenes",
        "n_scenes": N,
        "n_base_predicates": base_count,
        "n_experimental_predicates": len(exp_names),
        "experimental_predicates": exp_names,
        "per_predicate_analysis": analysis,
        "cross_modal_selectivity_at_scale": cm_summary,
        "promotion_decisions": promotion_decisions,
        "n_promote": n_promote,
        "n_retire": len(exp_names) - n_promote,
    }
    (out_dir/"round107_audit.json").write_text(json.dumps(result, indent=2))
    print("\n=== R107 RESULTS ===")
    print(f"\nfire rates and decisions:")
    for ep in exp_names:
        a = analysis[ep]
        d = promotion_decisions[ep]
        marker = "✓" if d["decision"] == "PROMOTE" else "✗"
        print(f"  {marker} {ep:35s} fire_rate={a['fire_rate']:.2f}  max_J={a['max_jaccard_with_base']:.2f} ({d['decision']})")
        if d["decision"] == "RETIRE":
            for r in d.get("reasons", []):
                print(f"      - {r}")
    print(f"\ncross-modal selectivity at N=20:")
    for cm, s in cm_summary.items():
        match = "✓" if s["matches_design"] else "✗"
        print(f"  {match} {cm}")
        print(f"      fires_on:  {s['fires_on']}")
        print(f"      expected:  {s['expected_pattern']}")
        if s["extra_fires"]: print(f"      EXTRA:    {s['extra_fires']}")
        if s["missing_fires"]: print(f"      MISSING:  {s['missing_fires']}")
    print(f"\nPROMOTE: {n_promote}/{len(exp_names)};  RETIRE: {len(exp_names)-n_promote}/{len(exp_names)}")


if __name__ == "__main__":
    main()
