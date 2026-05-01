"""R126 — replicate R124's multi-view phoxel-renderer test on a SPHERE.
If sphere also passes (mean J >= 0.65), R124's result generalizes
across primitive shapes; if not, the cube was special and Phase 2
needs more work."""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from itertools import combinations
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.visual_intake import _bundle_from_single

# reuse renderer infrastructure from r124
sys.path.insert(0, '/tmp')
from r124_phoxel_renderer import look_at, render_phoxels, fingerprint, jaccard

OUT = Path('/tmp/round126_sphere_test'); OUT.mkdir(exist_ok=True)


def make_phoxel_sphere(radius=1.0, density=24, color_by_normal=True):
    """Phoxel sphere: surface points sampled spherically, colored by
    surface normal so viewpoint changes are visible.

    Color encodes (nx, ny, nz) mapped to (r, g, b) via 0.5*(n+1) so
    each direction shows distinctly across viewpoints.
    """
    # sample roughly density^2 points with Fibonacci spiral
    n_total = density * density
    indices = np.arange(n_total) + 0.5
    phi   = np.arccos(1 - 2 * indices / n_total)
    theta = np.pi * (1 + 5 ** 0.5) * indices
    x = radius * np.cos(theta) * np.sin(phi)
    y = radius * np.sin(theta) * np.sin(phi)
    z = radius * np.cos(phi)
    pts = np.stack([x, y, z], axis=-1)
    if color_by_normal:
        normals = pts / np.linalg.norm(pts, axis=-1, keepdims=True)
        colors = 0.5 * (normals + 1.0)  # in [0, 1]
    else:
        colors = np.full_like(pts, 0.7)
    return {"positions": pts, "colors": colors, "n": len(pts)}


def main():
    field = make_phoxel_sphere(radius=1.0, density=28)
    print(f"phoxel_field: {field['n']} phoxels (sphere, density 28)")

    distance = 3.5; elevation = 0.6
    azimuths = [0, 45, 90, 135]
    views = []
    for az in azimuths:
        rad = np.deg2rad(az)
        cam = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(field, cam, image_size=240)
        Image.fromarray(rgb).save(OUT / f"sphere_az{az:03d}.png")
        views.append((az, rgb))
        print(f"  rendered az={az}, fired pixels: {(rgb.sum(axis=-1) > 50).mean()*100:.1f}%")

    # Setup substrate
    vision_ops.register_all()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    runtime = Runtime()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()

    fps = {}
    for az, rgb in views:
        fp = fingerprint(rgb, f"sphere_az{az}", runtime, pred_names)
        fps[az] = fp
        n_fired = sum(fp.values())
        print(f"  az={az:3d}: {n_fired}/{len(fp)} predicates fired")

    same_pairs = []
    for a, b in combinations(azimuths, 2):
        J = jaccard(fps[a], fps[b])
        same_pairs.append((a, b, round(J, 3)))
        print(f"  J(az={a}, az={b}) = {J:.3f}")

    Js = np.array([t[2] for t in same_pairs])
    mean_J = float(Js.mean())
    min_J = float(Js.min())
    max_J = float(Js.max())

    R124_cube_mean_J = 0.706
    R100_2d_proxy_mean_J = 0.758

    result = {
        "round": "R126",
        "date": "2026-05-01",
        "method": "phoxel_field SPHERE (Fibonacci-spiral surface, normal-colored) + 4-viewpoint test",
        "phoxel_field_size": field["n"],
        "viewpoints_azimuth_deg": azimuths,
        "n_predicates": len(pred_names),
        "pairwise_jaccards_same_sphere": same_pairs,
        "mean_J": mean_J, "min_J": min_J, "max_J": max_J,
        "comparison": {
            "R100_2d_affine_proxy_mean_J": R100_2d_proxy_mean_J,
            "R124_cube_3d_proj_mean_J":    R124_cube_mean_J,
            "R126_sphere_3d_proj_mean_J":  mean_J,
        },
        "verdict": (
            "PASS — multi-view stability generalizes across primitive shapes" if mean_J >= 0.65
            else "FAIL — cube result was shape-specific"
        ),
    }
    (OUT / "round126_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R126 RESULT ===")
    print(f"phoxel_field sphere: {field['n']} phoxels across 4 viewpoints")
    print(f"mean Jaccard: {mean_J:.3f}  (R124 cube: {R124_cube_mean_J}, R100 2D affine: {R100_2d_proxy_mean_J})")
    print(f"min: {min_J:.3f}  max: {max_J:.3f}")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round126_audit.json")


if __name__ == "__main__":
    main()
