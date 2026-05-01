"""R133 — phoxel perturbation-stability test.

Take R131's cube+sphere phoxel field. Apply Gaussian noise to phoxel
positions at σ ∈ {0.005, 0.01, 0.02, 0.05}. Render at fixed viewpoint
(az=0). Compute fingerprints. Measure layout-invariant subset Jaccard
to the original (unperturbed) field.

If invariant subset stays stable (J >= 0.85 at σ=0.01, J >= 0.7 at
σ=0.05), gradient descent on phoxel positions has a smooth-enough
loss landscape — viable Phase 3 R134+.

If J drops fast, gradient descent will fight noise. Phase 3 needs
smoothing or a coarser parameterization.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, '/tmp')
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.visual_intake import _bundle_from_single
from r124_phoxel_renderer import look_at, render_phoxels, fingerprint, jaccard, make_phoxel_cube
from r126_sphere_test import make_phoxel_sphere
from r128_multiobject import combine_fields

OUT = Path('/tmp/round133_perturbation'); OUT.mkdir(exist_ok=True)


def perturb_field(field, sigma, seed=42):
    """Return a copy of field with positions perturbed by Gaussian noise σ."""
    rng = np.random.default_rng(seed)
    new_pos = field['positions'] + rng.normal(0, sigma, field['positions'].shape)
    return {'positions': new_pos, 'colors': field['colors'], 'n': field['n']}


def main():
    cube = make_phoxel_cube(side=0.8, density=18)
    sphere = make_phoxel_sphere(radius=0.6, density=22)
    field = combine_fields(cube, sphere, offsets=[(-1, 0, 0), (1, 0, 0)])
    print(f"baseline phoxel_field: {field['n']} phoxels")

    distance = 4.0; elevation = 0.6
    cam = (distance, 0, elevation)

    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()

    # Re-derive layout-invariant subset (same way as R130)
    azimuths = [0, 45, 90, 135]
    cs_fps_views = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(field, cam_az, image_size=240)
        cs_fps_views[az] = fingerprint(rgb, f"baseline_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({cs_fps_views[az][pn] for az in azimuths}) == 1]
    sensitive = [pn for pn in pred_names if pn not in invariant]
    print(f"layout-invariant subset: {len(invariant)} predicates")

    # Baseline fingerprint (no perturbation, az=0)
    rgb_base = render_phoxels(field, cam, image_size=240)
    Image.fromarray(rgb_base).save(OUT / "perturbed_sigma_0.000.png")
    fp_base = fingerprint(rgb_base, "baseline", runtime, pred_names)

    sigmas = [0.005, 0.01, 0.02, 0.05, 0.10]
    seeds = [42, 43, 44]  # 3 perturbation samples per sigma to average
    perturbation_results = []
    print(f"\nperturbing positions at sigmas {sigmas} (3 seeds each)...")

    def J_subset(a, b, names):
        sa = {k for k in names if a.get(k)}
        sb = {k for k in names if b.get(k)}
        if not sa and not sb: return 1.0
        return len(sa & sb) / len(sa | sb)

    for sigma in sigmas:
        Js_all, Js_inv, Js_sens = [], [], []
        for seed in seeds:
            perturbed = perturb_field(field, sigma, seed=seed)
            rgb_p = render_phoxels(perturbed, cam, image_size=240)
            fp_p = fingerprint(rgb_p, f"perturbed_s{sigma}_seed{seed}", runtime, pred_names)
            J_all  = jaccard(fp_base, fp_p)
            J_inv  = J_subset(fp_base, fp_p, invariant)
            J_sens = J_subset(fp_base, fp_p, sensitive)
            Js_all.append(J_all); Js_inv.append(J_inv); Js_sens.append(J_sens)
            if seed == 42:
                Image.fromarray(rgb_p).save(OUT / f"perturbed_sigma_{sigma:.3f}.png")

        mean_all  = float(np.mean(Js_all))
        mean_inv  = float(np.mean(Js_inv))
        mean_sens = float(np.mean(Js_sens))
        std_inv   = float(np.std(Js_inv))
        perturbation_results.append({
            "sigma": sigma,
            "n_seeds": len(seeds),
            "mean_J_all":         round(mean_all, 3),
            "mean_J_invariant":   round(mean_inv, 3),
            "std_J_invariant":    round(std_inv, 3),
            "mean_J_sensitive":   round(mean_sens, 3),
        })
        print(f"  sigma={sigma:.3f}:  J_all={mean_all:.3f}  J_invariant={mean_inv:.3f} (±{std_inv:.3f})  J_sensitive={mean_sens:.3f}")

    # Verdict criteria: invariant subset J should:
    # - stay >= 0.95 at sigma 0.005 (nearly unchanged on tiny perturbation)
    # - stay >= 0.85 at sigma 0.01
    # - stay >= 0.70 at sigma 0.05
    by_sigma = {r["sigma"]: r for r in perturbation_results}
    pass_005 = by_sigma[0.005]["mean_J_invariant"] >= 0.95
    pass_01  = by_sigma[0.01]["mean_J_invariant"]  >= 0.85
    pass_05  = by_sigma[0.05]["mean_J_invariant"]  >= 0.70
    overall  = pass_005 and pass_01 and pass_05

    result = {
        "round": "R133",
        "date": "2026-05-01",
        "method": "Cube+sphere phoxel field + Gaussian position perturbation at sigmas 0.005-0.10; pairwise Jaccard to baseline at fixed viewpoint az=0",
        "phoxel_field_size": field['n'],
        "n_invariant_predicates": len(invariant),
        "n_sensitive_predicates": len(sensitive),
        "perturbation_sigmas": sigmas,
        "n_seeds_per_sigma": len(seeds),
        "results": perturbation_results,
        "criteria": {
            "sigma_0.005_J_inv >= 0.95": pass_005,
            "sigma_0.010_J_inv >= 0.85": pass_01,
            "sigma_0.050_J_inv >= 0.70": pass_05,
        },
        "verdict": (
            "PASS — substrate fingerprint (layout-invariant subset) is locally smooth under phoxel position perturbations; viable for Phase 3 gradient-descent training"
            if overall
            else "PARTIAL/FAIL — fingerprint loss has jagged regions; Phase 3 needs smoothing or coarser parameterization"
        ),
    }
    (OUT / "round133_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R133 RESULT ===")
    for r in perturbation_results:
        print(f"  sigma={r['sigma']:.3f}: J_invariant = {r['mean_J_invariant']:.3f}")
    print(f"\nverdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round133_audit.json")


if __name__ == "__main__":
    main()
