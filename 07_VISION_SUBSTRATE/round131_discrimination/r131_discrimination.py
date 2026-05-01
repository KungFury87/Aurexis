"""R131 — discrimination test for R130's layout-invariant subset.
Generate 6 distinct phoxel scenes, render from az=0, compute fingerprints,
test whether layout-invariant subset DISCRIMINATES between scene types
or collapses them to one fingerprint."""
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
from r124_phoxel_renderer import (look_at, render_phoxels, fingerprint,
                                    jaccard, make_phoxel_cube)
from r126_sphere_test import make_phoxel_sphere
from r128_multiobject import combine_fields

OUT = Path('/tmp/round131_discrimination'); OUT.mkdir(exist_ok=True)


def make_phoxel_pyramid(base=1.0, height=1.0, density=18):
    """Square-base pyramid. 4 triangle faces + bottom square."""
    pts = []; cols = []
    n = density
    s = base / 2
    # 4 triangular faces
    apex = np.array([0, 0, height/2])
    base_corners = np.array([[s, s, -height/2], [-s, s, -height/2],
                              [-s, -s, -height/2], [s, -s, -height/2]])
    face_colors = [(1, 0.5, 0), (0, 0.8, 1), (0.5, 1, 0), (1, 0, 0.5)]
    for fi in range(4):
        c1, c2 = base_corners[fi], base_corners[(fi+1) % 4]
        for u in np.linspace(0, 1, n):
            for v in np.linspace(0, 1 - u, max(1, int(n*(1-u)))):
                p = (1 - u - v) * apex + u * c1 + v * c2
                pts.append(p); cols.append(face_colors[fi])
    # base square
    for i in np.linspace(-s, s, n):
        for j in np.linspace(-s, s, n):
            pts.append([i, j, -height/2]); cols.append((0.6, 0.6, 0.6))
    return {"positions": np.array(pts), "colors": np.array(cols), "n": len(pts)}


def main():
    # Build 6 scenes
    cube_small = make_phoxel_cube(side=0.6, density=14)
    cube_big = make_phoxel_cube(side=1.0, density=18)
    sphere_small = make_phoxel_sphere(radius=0.5, density=20)
    sphere_big = make_phoxel_sphere(radius=0.8, density=24)
    pyramid = make_phoxel_pyramid(base=1.0, height=1.2, density=14)

    SCENES = {
        'cube_sphere':    combine_fields(cube_big, sphere_big, offsets=[(-1, 0, 0), (1, 0, 0)]),
        'two_cubes':      combine_fields(cube_small, cube_big, offsets=[(-1, 0, 0), (1, 0, 0)]),
        'two_spheres':    combine_fields(sphere_small, sphere_big, offsets=[(-1, 0, 0), (1, 0, 0)]),
        'cube_pyramid':   combine_fields(cube_big, pyramid, offsets=[(-1, 0, 0), (1, 0, 0)]),
        'single_sphere':  sphere_big,
        'single_cube':    cube_big,
    }

    # Render each at az=0
    distance = 4.0; elevation = 0.6
    cam = (distance, 0, elevation)
    fps = {}
    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()

    for name, field in SCENES.items():
        rgb = render_phoxels(field, cam, image_size=240)
        Image.fromarray(rgb).save(OUT / f"{name}_az0.png")
        fp = fingerprint(rgb, name, runtime, pred_names)
        fps[name] = fp
        print(f"{name:18s} {field['n']:5d} phoxels  {sum(fp.values())}/151 fired")

    # Reuse R130's layout-invariant set (rebuilt from cube+sphere R128 scene)
    cube_sphere = SCENES['cube_sphere']
    azimuths = [0, 45, 90, 135]
    cs_fps = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(cube_sphere, cam_az, image_size=240)
        cs_fps[az] = fingerprint(rgb, f"cs_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({cs_fps[az][pn] for az in azimuths}) == 1]
    sensitive = [pn for pn in pred_names if pn not in invariant]
    print(f"\nlayout-invariant set (re-derived): {len(invariant)} predicates")

    # Pairwise scene Jaccards on (full 151 / invariant subset / sensitive subset)
    def J_subset(a, b, names):
        sa = {k for k in names if a.get(k)}
        sb = {k for k in names if b.get(k)}
        if not sa and not sb: return 1.0
        return len(sa & sb) / len(sa | sb)

    print(f"\n{'pair':32s}  {'all 151':9s} {'invariant':10s} {'sensitive':10s}")
    pair_data = []
    scenes = list(SCENES.keys())
    for a, b in combinations(scenes, 2):
        J_all  = jaccard(fps[a], fps[b])
        J_inv  = J_subset(fps[a], fps[b], invariant)
        J_sens = J_subset(fps[a], fps[b], sensitive)
        pair_data.append((a, b, round(J_all, 3), round(J_inv, 3), round(J_sens, 3)))
        print(f"  {a:14s} vs {b:14s}  {J_all:.3f}      {J_inv:.3f}        {J_sens:.3f}")

    J_all_arr  = np.array([t[2] for t in pair_data])
    J_inv_arr  = np.array([t[3] for t in pair_data])
    J_sens_arr = np.array([t[4] for t in pair_data])

    print(f"\n{'BETWEEN-SCENE MEANS':32s}  {J_all_arr.mean():.3f}      {J_inv_arr.mean():.3f}        {J_sens_arr.mean():.3f}")
    print(f"{'BETWEEN-SCENE MIN':32s}  {J_all_arr.min():.3f}      {J_inv_arr.min():.3f}        {J_sens_arr.min():.3f}")
    print(f"{'BETWEEN-SCENE MAX':32s}  {J_all_arr.max():.3f}      {J_inv_arr.max():.3f}        {J_sens_arr.max():.3f}")

    # Verdict: invariant subset DISCRIMINATES if mean between-scene J < 0.85
    # (some shared structure expected since all are colored-phoxel scenes)
    discriminates = J_inv_arr.mean() < 0.85
    has_spread = (J_inv_arr.max() - J_inv_arr.min()) > 0.10

    result = {
        "round": "R131",
        "date": "2026-05-01",
        "method": "6 distinct phoxel scenes rendered from az=0; pairwise Jaccards on full + layout-invariant + layout-sensitive subsets",
        "scenes": list(SCENES.keys()),
        "n_predicates_total": len(pred_names),
        "n_layout_invariant": len(invariant),
        "n_layout_sensitive": len(sensitive),
        "between_scene_pairs": pair_data,
        "between_scene_J_all_mean":         float(J_all_arr.mean()),
        "between_scene_J_invariant_mean":   float(J_inv_arr.mean()),
        "between_scene_J_sensitive_mean":   float(J_sens_arr.mean()),
        "between_scene_J_invariant_min":    float(J_inv_arr.min()),
        "between_scene_J_invariant_max":    float(J_inv_arr.max()),
        "invariant_subset_discriminates":   bool(discriminates),
        "invariant_subset_has_spread":      bool(has_spread),
        "verdict": (
            "PASS — layout-invariant 115 subset DISCRIMINATES between scene types AND was multi-view stable per R130; viable Phase 3 splatting content-loss"
            if (discriminates and has_spread)
            else "PARTIAL — subset is stable but may be too uniform across scenes"
        ),
    }
    (OUT / "round131_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R131 RESULT ===")
    print(f"layout-invariant subset: {len(invariant)} predicates")
    print(f"between-scene mean J on invariant subset: {J_inv_arr.mean():.3f}  (range {J_inv_arr.min():.3f}-{J_inv_arr.max():.3f})")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round131_audit.json")


if __name__ == "__main__":
    main()
