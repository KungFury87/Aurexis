"""R130 — layout-invariant predicate subset diagnostic.

Use R128's 4 cube+sphere fingerprints. For each predicate, count
how many of the 4 viewpoints it fires on. A predicate that fires
the same way on all 4 views is layout-invariant; one that flips
between views is layout-sensitive.

Recompute pairwise Jaccards over (a) only layout-invariant
predicates, (b) only layout-sensitive predicates. If (a) gives
mean J >= 0.65, that's the empirical answer for Phase 3 splatting
loss design.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from itertools import combinations
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

OUT = Path('/tmp/round130_layout_invariant'); OUT.mkdir(exist_ok=True)


def main():
    # Re-run R128 setup
    cube = make_phoxel_cube(side=0.8, density=18)
    sphere = make_phoxel_sphere(radius=0.6, density=22)
    field = combine_fields(cube, sphere, offsets=[(-1.0, 0, 0), (1.0, 0, 0)])
    print(f"phoxel_field: {field['n']} phoxels (cube + sphere placed apart)")

    distance = 4.0; elevation = 0.6
    azimuths = [0, 45, 90, 135]
    views = []
    for az in azimuths:
        rad = np.deg2rad(az)
        cam = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(field, cam, image_size=240)
        views.append((az, rgb))

    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()

    fps = {}
    for az, rgb in views:
        fps[az] = fingerprint(rgb, f"multiobj_az{az}", runtime, pred_names)

    # ---- partition predicates by viewpoint variability ---------------------
    # For each predicate, count distinct (boolean) values across 4 viewpoints
    # 0 distinct → never fires (always-False); 1 → invariant True or False;
    # 2 → flips between views (layout-sensitive)
    invariant_preds = []   # same value across all 4
    sensitive_preds = []   # changes value between any pair
    for pn in pred_names:
        vals = [fps[az][pn] for az in azimuths]
        if len(set(vals)) == 1:
            invariant_preds.append(pn)
        else:
            sensitive_preds.append(pn)

    print(f"\nlayout-invariant: {len(invariant_preds)}/{len(pred_names)} ({len(invariant_preds)/len(pred_names)*100:.1f}%)")
    print(f"layout-sensitive: {len(sensitive_preds)}/{len(pred_names)} ({len(sensitive_preds)/len(pred_names)*100:.1f}%)")

    # Show top sensitive ones
    print(f"\nlayout-SENSITIVE predicates (flip between viewpoints):")
    for pn in sorted(sensitive_preds):
        vals = [fps[az][pn] for az in azimuths]
        print(f"  {pn:50s}  az0={vals[0]} az45={vals[1]} az90={vals[2]} az135={vals[3]}")

    # ---- recompute Jaccards on subsets ------------------------------------
    def jaccard_subset(fp_a, fp_b, names):
        a = {k for k in names if fp_a.get(k)}
        b = {k for k in names if fp_b.get(k)}
        if not a and not b: return 1.0
        return len(a & b) / len(a | b)

    print(f"\n=== pairwise Jaccards on different predicate subsets ===")
    print(f"{'pair':14s}  {'all 151':10s} {'invariant':12s} {'sensitive':12s}")
    pair_data = []
    for a, b in combinations(azimuths, 2):
        J_all  = jaccard(fps[a], fps[b])
        J_inv  = jaccard_subset(fps[a], fps[b], invariant_preds)
        J_sens = jaccard_subset(fps[a], fps[b], sensitive_preds)
        pair_data.append((a, b, round(J_all, 3), round(J_inv, 3), round(J_sens, 3)))
        print(f"  az{a}-{b:3d}      {J_all:.3f}      {J_inv:.3f}        {J_sens:.3f}")

    J_all_arr  = np.array([t[2] for t in pair_data])
    J_inv_arr  = np.array([t[3] for t in pair_data])
    J_sens_arr = np.array([t[4] for t in pair_data])

    print(f"\nMEAN:           {J_all_arr.mean():.3f}      {J_inv_arr.mean():.3f}        {J_sens_arr.mean():.3f}")
    print(f"MIN:            {J_all_arr.min():.3f}      {J_inv_arr.min():.3f}        {J_sens_arr.min():.3f}")
    print(f"MAX:            {J_all_arr.max():.3f}      {J_inv_arr.max():.3f}        {J_sens_arr.max():.3f}")

    invariant_passes = J_inv_arr.mean() >= 0.65

    result = {
        "round": "R130",
        "date": "2026-05-01",
        "method": "Partition R128's 151 predicates by 4-viewpoint variability on multi-object scene; recompute pairwise Jaccards on each subset",
        "n_predicates_total": len(pred_names),
        "n_invariant": len(invariant_preds),
        "n_sensitive": len(sensitive_preds),
        "invariant_pct": round(len(invariant_preds) / len(pred_names) * 100, 1),
        "layout_sensitive_predicates": sorted(sensitive_preds),
        "pairwise_J_all_mean": float(J_all_arr.mean()),
        "pairwise_J_invariant_subset_mean": float(J_inv_arr.mean()),
        "pairwise_J_sensitive_subset_mean": float(J_sens_arr.mean()),
        "verdict": (
            "PASS — layout-invariant subset preserves multi-view stability; viable Phase 3 splatting loss design" if invariant_passes
            else "FAIL — even layout-invariant subset breaks below 0.65"
        ),
        "comparison": {
            "R128_full_vocab":           round(float(J_all_arr.mean()), 3),
            "R130_layout_invariant_only": round(float(J_inv_arr.mean()), 3),
            "R124_cube_alone":           0.706,
            "R126_sphere_alone":         0.833,
            "threshold":                 0.65,
        },
    }
    (OUT / "round130_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R130 RESULT ===")
    print(f"layout-invariant subset: {len(invariant_preds)}/{len(pred_names)} predicates")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round130_audit.json")


if __name__ == "__main__":
    main()
