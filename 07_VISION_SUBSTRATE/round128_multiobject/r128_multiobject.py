"""R128 — multi-object scene: phoxel cube + phoxel sphere placed apart
in same field, 4-viewpoint stability test. Tests whether substrate
fingerprint stays multi-view stable when spatial layout (which object
is in front, which occludes which) changes between viewpoints."""
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

OUT = Path('/tmp/round128_multiobject'); OUT.mkdir(exist_ok=True)


def combine_fields(*fields, offsets=None):
    """Combine multiple phoxel fields into one with per-field xyz offsets."""
    all_pts = []; all_cols = []
    for i, f in enumerate(fields):
        off = np.array(offsets[i] if offsets else (0, 0, 0), dtype=np.float64)
        all_pts.append(f["positions"] + off)
        all_cols.append(f["colors"])
    return {
        "positions": np.concatenate(all_pts, axis=0),
        "colors": np.concatenate(all_cols, axis=0),
        "n": sum(f["n"] for f in fields),
    }


def main():
    cube = make_phoxel_cube(side=0.8, density=18)
    sphere = make_phoxel_sphere(radius=0.6, density=22)
    # Place cube on the left, sphere on the right
    field = combine_fields(cube, sphere, offsets=[(-1.0, 0, 0), (1.0, 0, 0)])
    print(f"phoxel_field: {field['n']} phoxels (cube + sphere placed apart)")

    distance = 4.0; elevation = 0.6
    azimuths = [0, 45, 90, 135]
    views = []
    for az in azimuths:
        rad = np.deg2rad(az)
        cam = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(field, cam, image_size=240)
        Image.fromarray(rgb).save(OUT / f"multiobj_az{az:03d}.png")
        views.append((az, rgb))
        print(f"  rendered az={az}, fired pixels: {(rgb.sum(axis=-1) > 50).mean()*100:.1f}%")

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
        fp = fingerprint(rgb, f"multiobj_az{az}", runtime, pred_names)
        fps[az] = fp
        n_fired = sum(fp.values())
        print(f"  az={az:3d}: {n_fired}/{len(fp)} predicates fired")

    same_pairs = []
    for a, b in combinations(azimuths, 2):
        J = jaccard(fps[a], fps[b])
        same_pairs.append((a, b, round(J, 3)))
        print(f"  J(az={a}, az={b}) = {J:.3f}")

    Js = np.array([t[2] for t in same_pairs])
    mean_J = float(Js.mean()); min_J = float(Js.min()); max_J = float(Js.max())

    R124_cube = 0.706; R126_sphere = 0.833; R100_2d = 0.758

    result = {
        "round": "R128",
        "date": "2026-05-01",
        "method": "phoxel_field combining cube (left, offset (-1, 0, 0)) + sphere (right, offset (+1, 0, 0)) — 4-viewpoint test",
        "phoxel_field_size": field["n"],
        "viewpoints_azimuth_deg": azimuths,
        "n_predicates": len(pred_names),
        "pairwise_jaccards_same_multiobj": same_pairs,
        "mean_J": mean_J, "min_J": min_J, "max_J": max_J,
        "comparison": {
            "R100_2d_affine":      R100_2d,
            "R124_cube_3d":        R124_cube,
            "R126_sphere_3d":      R126_sphere,
            "R128_cube_plus_sphere_3d": mean_J,
        },
        "verdict": (
            "PASS — multi-view stability holds for multi-object scenes" if mean_J >= 0.65
            else "FAIL — multi-object scenes break the stability claim"
        ),
    }
    (OUT / "round128_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R128 RESULT ===")
    print(f"phoxel_field cube+sphere: {field['n']} phoxels, 4 viewpoints")
    print(f"mean J: {mean_J:.3f}  (R124 cube {R124_cube}, R126 sphere {R126_sphere})")
    print(f"min: {min_J:.3f}  max: {max_J:.3f}")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round128_audit.json")


if __name__ == "__main__":
    main()
