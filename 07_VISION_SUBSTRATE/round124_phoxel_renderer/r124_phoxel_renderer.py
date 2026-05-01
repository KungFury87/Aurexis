"""R124 — T7 Phase 2 first step. phoxel_field dtype + forward renderer +
4-viewpoint multi-view stability test on a known 3D primitive.

Plan:
  1. Build a phoxel cube (sparse 3D point cloud, colored faces).
  2. Implement pinhole-camera forward renderer (orient camera at pose,
     project, alpha-composite, return 2D RGB image).
  3. Render the cube from 4 viewpoints (azimuth 0/45/90/135 around y-axis,
     elevation 20deg, fixed distance).
  4. Run substrate on each rendering, compute pairwise Jaccards.
  5. Compare to R100's same-scene multi-view ratio (2.33x).

If pairwise Jaccards on the same 3D cube across 4 viewpoints stay high
(say >= 0.65 mean), the substrate's viewpoint stability claim
generalizes from R100's 2D affine to real 3D projection.
"""
from __future__ import annotations
import warnings; warnings.filterwarnings('ignore')
import json, sys, time
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

OUT = Path('/tmp/round124_phoxel_renderer'); OUT.mkdir(exist_ok=True)


# ---- phoxel_field datatype --------------------------------------------------
# A phoxel_field is a dict with:
#   "positions":  (N, 3) float — xyz in world coordinates
#   "colors":     (N, 3) float in [0, 1] — rgb per phoxel
#   "n":          int — number of phoxels

def make_phoxel_cube(side=1.0, density=20, color_faces=True):
    """Colored cube. Each face gets a distinct color so viewpoint changes
    surface up. Surface phoxels only (no interior — fewer to render)."""
    pts = []; colors = []
    n = density
    s = side / 2
    grid = np.linspace(-s, s, n)
    # 6 faces, each a (n*n) grid of phoxels
    face_colors = [
        (1.0, 0.2, 0.2),  # +x: red
        (0.2, 1.0, 0.2),  # -x: green
        (0.2, 0.2, 1.0),  # +y: blue
        (1.0, 1.0, 0.2),  # -y: yellow
        (1.0, 0.2, 1.0),  # +z: magenta
        (0.2, 1.0, 1.0),  # -z: cyan
    ]
    if not color_faces:
        face_colors = [(0.7, 0.7, 0.7)] * 6
    for i, j in [(a, b) for a in grid for b in grid]:
        pts.append([s, i, j]); colors.append(face_colors[0])      # +x
        pts.append([-s, i, j]); colors.append(face_colors[1])     # -x
        pts.append([i, s, j]); colors.append(face_colors[2])      # +y
        pts.append([i, -s, j]); colors.append(face_colors[3])     # -y
        pts.append([i, j, s]); colors.append(face_colors[4])      # +z
        pts.append([i, j, -s]); colors.append(face_colors[5])     # -z
    pts = np.array(pts, dtype=np.float64)
    cols = np.array(colors, dtype=np.float64)
    return {"positions": pts, "colors": cols, "n": len(pts)}


# ---- pinhole-camera forward renderer ---------------------------------------
def look_at(camera_pos, target=(0, 0, 0), up=(0, 0, 1)):
    """Return 4x4 world->camera transform for a camera at camera_pos
    looking at target with given up vector."""
    camera_pos = np.array(camera_pos, dtype=np.float64)
    target = np.array(target, dtype=np.float64)
    up = np.array(up, dtype=np.float64)
    forward = target - camera_pos
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    cam_up = np.cross(right, forward)
    R = np.stack([right, cam_up, -forward], axis=0)
    t = -R @ camera_pos
    M = np.eye(4)
    M[:3, :3] = R; M[:3, 3] = t
    return M


def render_phoxels(field, camera_pos, image_size=240, fov_deg=55.0):
    """Project phoxels through a pinhole camera, depth-sort, paint into
    a 2D RGB image. Each phoxel becomes a small splat.
    """
    M = look_at(camera_pos)
    pts = field["positions"]
    cols = field["colors"]
    # Transform to camera space
    pts_h = np.hstack([pts, np.ones((len(pts), 1))])
    cam = (M @ pts_h.T).T[:, :3]    # (N, 3)
    # Behind-camera cull (z > 0 in our convention since -forward in look_at)
    in_front = cam[:, 2] < -0.01
    cam = cam[in_front]; cols_v = cols[in_front]
    if len(cam) == 0:
        return np.zeros((image_size, image_size, 3), dtype=np.uint8)
    # Perspective projection
    f = (image_size / 2) / np.tan(np.deg2rad(fov_deg / 2))
    z = -cam[:, 2]
    x_proj = cam[:, 0] * (f / z) + image_size / 2
    y_proj = -cam[:, 1] * (f / z) + image_size / 2
    # Depth-sort back-to-front for painter's algorithm
    order = np.argsort(-z)
    img = np.full((image_size, image_size, 3), 0.05, dtype=np.float64)  # near-black bg
    splat_size = 2
    for idx in order:
        xi = int(x_proj[idx]); yi = int(y_proj[idx])
        if 0 <= xi < image_size and 0 <= yi < image_size:
            x0, x1 = max(0, xi-splat_size), min(image_size, xi+splat_size+1)
            y0, y1 = max(0, yi-splat_size), min(image_size, yi+splat_size+1)
            img[y0:y1, x0:x1] = cols_v[idx]
    return (img * 255).clip(0, 255).astype(np.uint8)


# ---- substrate eval helpers (mirrors R100 / R124 path) ----------------------
def fingerprint(rgb_u8, name, runtime, pred_names):
    luma = (0.299*rgb_u8[..., 0] + 0.587*rgb_u8[..., 1]
            + 0.114*rgb_u8[..., 2]).astype(np.float64) / 255.0
    color = rgb_u8.astype(np.float64) / 255.0
    bundle, _ = _bundle_from_single(luma, name, patch_size=64, color=color)
    fp = {}
    for pn in pred_names:
        rec = runtime.evaluate(pn, bundle)
        fp[pn] = bool(rec.value) if (rec.error is None and rec.value is not None) else False
    return fp


def jaccard(a, b):
    aset = {k for k, v in a.items() if v}
    bset = {k for k, v in b.items() if v}
    if not aset and not bset: return 1.0
    return len(aset & bset) / len(aset | bset)


# ---- main -------------------------------------------------------------------
def main():
    # Build phoxel cube + render 4 viewpoints
    field = make_phoxel_cube(side=1.0, density=24)
    print(f"phoxel_field: {field['n']} phoxels (cube, density 24)")

    distance = 3.5; elevation = 0.6  # camera height (z)
    azimuths = [0, 45, 90, 135]      # degrees rotation around z axis
    views = []
    for az in azimuths:
        rad = np.deg2rad(az)
        cam = (distance * np.cos(rad), distance * np.sin(rad), elevation)
        rgb = render_phoxels(field, cam, image_size=240)
        Image.fromarray(rgb).save(OUT / f"cube_az{az:03d}.png")
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
    print(f"\nsubstrate: {len(pred_names)} predicates installed")

    # Fingerprint each view
    fps = {}
    for az, rgb in views:
        fp = fingerprint(rgb, f"cube_az{az}", runtime, pred_names)
        fps[az] = fp
        n_fired = sum(fp.values())
        print(f"  az={az:3d}: {n_fired}/{len(fp)} predicates fired")

    # Pairwise Jaccards
    same_cube_pairs = []
    for a, b in combinations(azimuths, 2):
        J = jaccard(fps[a], fps[b])
        same_cube_pairs.append((a, b, round(J, 3)))
        print(f"  J(az={a}, az={b}) = {J:.3f}")

    Js = np.array([t[2] for t in same_cube_pairs])
    mean_J = float(Js.mean())
    min_J = float(Js.min())
    max_J = float(Js.max())

    # R100 baseline for comparison
    R100_same_scene_J_mean = 0.758
    R100_diff_scene_J_mean = 0.325

    result = {
        "round": "R124",
        "date": "2026-05-01",
        "method": "phoxel_field datatype + pinhole forward renderer + 4-viewpoint test",
        "phoxel_field_size": field["n"],
        "viewpoints_azimuth_deg": azimuths,
        "n_predicates": len(pred_names),
        "pairwise_jaccards_same_cube": same_cube_pairs,
        "mean_J": mean_J, "min_J": min_J, "max_J": max_J,
        "R100_baseline": {
            "same_scene_J_mean": R100_same_scene_J_mean,
            "diff_scene_J_mean": R100_diff_scene_J_mean,
        },
        "verdict": (
            "PASS — multi-view stable on real 3D projection" if mean_J >= 0.65
            else "FAIL — viewpoint stability breaks under real 3D projection"
        ),
        "comparison_note": (
            f"R124 mean J {mean_J:.3f} vs R100 same-scene J {R100_same_scene_J_mean}; "
            f"R100 used 2D affine viewpoint proxy, R124 uses real 3D pinhole projection."
        ),
    }
    (OUT / "round124_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R124 RESULT ===")
    print(f"phoxel_field cube: {field['n']} phoxels across 4 viewpoints")
    print(f"mean Jaccard same-cube multi-view: {mean_J:.3f}  (R100 was {R100_same_scene_J_mean})")
    print(f"min: {min_J:.3f}  max: {max_J:.3f}")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round124_audit.json")


if __name__ == "__main__":
    main()
