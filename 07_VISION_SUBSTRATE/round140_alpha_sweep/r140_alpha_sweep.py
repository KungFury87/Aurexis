"""R140 — α sweep on Phase 4 Option D regularizer weight.

Run R138 setup at α ∈ {0.0, 0.05, 0.2, 1.0} — orders of magnitude coverage.
Track final distance, photo loss, substrate J for each.
Goal: characterize which α gives best convergence + best substrate
J retention, mapping the Phase 4 design parameter space."""
import warnings; warnings.filterwarnings('ignore')
import json, sys, time
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

OUT = Path('/tmp/round140_alpha_sweep'); OUT.mkdir(exist_ok=True)


def translate_field(field, tx, ty, tz):
    return {'positions': field['positions'] + np.array([tx, ty, tz]),
            'colors': field['colors'], 'n': field['n']}

IMAGE_SIZE = 128  # smaller for speed

def render(field):
    return render_phoxels(field, (3.0, 0, 0.5), image_size=IMAGE_SIZE)

def photo_mse(rgb_a, rgb_b):
    a = rgb_a.astype(np.float64) / 255.0
    b = rgb_b.astype(np.float64) / 255.0
    return float(np.mean((a - b) ** 2))

def J_subset(a, b, names):
    sa = {k for k in names if a.get(k)}
    sb = {k for k in names if b.get(k)}
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb)


def train(target_field, fp_target, rgb_target, init_params, runtime,
          pred_names, invariant, alpha, n_iters=6, eps=0.05, lr=2.0):
    params = np.array(init_params, dtype=np.float64)
    history = []

    def total_loss(p):
        rgb = render(translate_field(target_field, *p))
        photo = photo_mse(rgb, rgb_target)
        if alpha > 0:
            fp = fingerprint(rgb, "_", runtime, pred_names)
            substr = 1.0 - J_subset(fp_target, fp, invariant)
        else:
            substr = 0.0
        return photo + alpha * substr, photo, substr

    init_total, init_photo, init_subst = total_loss(params)
    history.append((0, params.tolist(), float(np.linalg.norm(params)),
                    init_total, init_photo, init_subst))

    tic = time.time()
    for it in range(1, n_iters + 1):
        if time.time() - tic > 25: break
        grad = np.zeros(3)
        for i in range(3):
            p_p = params.copy(); p_p[i] += eps
            p_m = params.copy(); p_m[i] -= eps
            t_p, _, _ = total_loss(p_p); t_m, _, _ = total_loss(p_m)
            grad[i] = (t_p - t_m) / (2 * eps)
        params = params - lr * grad
        cur_total, cur_photo, cur_subst = total_loss(params)
        history.append((it, params.tolist(), float(np.linalg.norm(params)),
                         cur_total, cur_photo, cur_subst))
    return history


def main():
    target_field = make_phoxel_cube(side=0.6, density=12)
    print(f"target: {target_field['n']} phoxels (cube at origin)")

    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try: P.type_check(pp.pred); runtime.install(pp.pred)
            except: pass
    pred_names = runtime.installed()

    rgb_target = render(target_field)
    Image.fromarray(rgb_target).save(OUT / "target.png")
    fp_target = fingerprint(rgb_target, "target", runtime, pred_names)

    azimuths = [0, 45, 90, 135]
    target_fps_views = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (3.0 * np.cos(rad), 3.0 * np.sin(rad), 0.5)
        rgb_az = render_phoxels(target_field, cam_az, image_size=IMAGE_SIZE)
        target_fps_views[az] = fingerprint(rgb_az, f"t_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({target_fps_views[az][pn] for az in azimuths}) == 1]
    print(f"invariant subset: {len(invariant)} predicates  (image_size={IMAGE_SIZE})")

    init_params = (1.0, 0.5, 0.0)
    alphas = [0.0, 0.05, 0.2, 1.0]
    sweep = {}
    for alpha in alphas:
        print(f"\n=== α = {alpha} ===")
        h = train(target_field, fp_target, rgb_target, init_params, runtime,
                   pred_names, invariant, alpha, n_iters=6)
        sweep[alpha] = h
        for it, p, d, tot, ph, sb in h:
            print(f"  iter {it}: dist={d:.3f} photo={ph:.4f} substr={sb:.3f} total={tot:.4f}")

    print(f"\n=== α SWEEP SUMMARY ===")
    print(f"{'alpha':8s}  {'final dist':12s}  {'final photo':14s}  {'final substr':14s}  {'final J_inv':12s}")
    summary = []
    for alpha in alphas:
        h = sweep[alpha]
        f = h[-1]
        final_dist = f[2]
        final_photo = f[4]
        final_substr = f[5]
        final_J_inv = 1.0 - f[5]
        summary.append({
            "alpha": alpha,
            "n_iters": len(h) - 1,
            "final_dist": round(final_dist, 4),
            "final_photo": round(final_photo, 5),
            "final_substr_loss": round(final_substr, 4),
            "final_J_invariant": round(final_J_inv, 4),
            "dist_reduction_pct": round((1.118 - final_dist) / 1.118 * 100, 1),
        })
        print(f"  {alpha:6.3f}    {final_dist:.4f}        {final_photo:.5f}        {final_substr:.4f}          {final_J_inv:.4f}")

    # Identify best
    # "best" = lowest final dist, tie-break by highest J_invariant
    sorted_by_dist = sorted(summary, key=lambda x: (x['final_dist'], -x['final_J_invariant']))
    best = sorted_by_dist[0]
    print(f"\nbest alpha by final distance: α={best['alpha']} → dist={best['final_dist']:.4f}, J_inv={best['final_J_invariant']:.4f}")

    result = {
        "round": "R140",
        "date": "2026-05-01",
        "method": "α sweep on Phase 4 Option D regularizer weight; α ∈ {0.0, 0.05, 0.2, 1.0}; 6 iters each; image_size=128",
        "init_params": list(init_params),
        "initial_distance": float(np.linalg.norm(init_params)),
        "alphas_tested": alphas,
        "summary_per_alpha": summary,
        "best_by_distance": best,
        "verdict": (
            f"Best α = {best['alpha']} for this corpus + optimizer; α={best['alpha']} achieves dist={best['final_dist']:.3f} with J_invariant={best['final_J_invariant']:.3f}"
        ),
    }
    (OUT / "round140_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\nwrote {OUT}/round140_audit.json")


if __name__ == "__main__":
    main()
