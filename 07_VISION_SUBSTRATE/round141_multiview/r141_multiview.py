"""R141 - Multi-view Phase 4 training: does alpha sweet spot shift?

R138 + R140 used a single fixed viewpoint (az=0). Real splatting trains
against multiple views. R141 tests how Phase 4's alpha sweet spot shifts
when photometric + substrate losses are summed across 4 viewpoints.

Hypothesis: more viewpoints = more photometric signal, so optimal alpha
should shift LOWER (less regularization needed when photo gradient is
stronger).
"""
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
from r124_phoxel_renderer import render_phoxels, fingerprint, jaccard, make_phoxel_cube

OUT = Path('/tmp/round141_multiview'); OUT.mkdir(exist_ok=True)
IMAGE_SIZE = 128
VIEW_AZIMUTHS = [0, 90, 180, 270]


def cam_for_az(az_deg, radius=3.0, height=0.5):
    rad = np.deg2rad(az_deg)
    return (radius * np.cos(rad), radius * np.sin(rad), height)


def translate_field(field, tx, ty, tz):
    return {'positions': field['positions'] + np.array([tx, ty, tz]),
            'colors': field['colors'], 'n': field['n']}


def render_view(field, az):
    return render_phoxels(field, cam_for_az(az), image_size=IMAGE_SIZE)


def photo_mse(a, b):
    a = a.astype(np.float64) / 255.0
    b = b.astype(np.float64) / 255.0
    return float(np.mean((a - b) ** 2))


def J_subset(a, b, names):
    sa = {k for k in names if a.get(k)}
    sb = {k for k in names if b.get(k)}
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb)


def multiview_loss(params, target_field, target_rgbs, target_fps,
                   runtime, pred_names, invariant, alpha):
    f = translate_field(target_field, *params)
    photos, substrs, Js = [], [], []
    for i, az in enumerate(VIEW_AZIMUTHS):
        rgb = render_view(f, az)
        p = photo_mse(rgb, target_rgbs[i])
        if alpha > 0:
            fp = fingerprint(rgb, f"v{az}", runtime, pred_names)
            J = J_subset(target_fps[i], fp, invariant)
            s = 1.0 - J
        else:
            s = 0.0; J = 1.0
        photos.append(p); substrs.append(s); Js.append(J)
    photo_avg = float(np.mean(photos))
    substr_avg = float(np.mean(substrs))
    J_avg = float(np.mean(Js))
    total = photo_avg + alpha * substr_avg
    return total, photo_avg, substr_avg, J_avg


def train(target_field, target_rgbs, target_fps, init_params, runtime,
          pred_names, invariant, alpha, n_iters=6, eps=0.05, lr=2.0):
    params = np.array(init_params, dtype=np.float64)
    history = []
    t0, p0, s0, J0 = multiview_loss(params, target_field, target_rgbs,
                                     target_fps, runtime, pred_names,
                                     invariant, alpha)
    d0 = float(np.linalg.norm(params))
    history.append((0, params.tolist(), d0, t0, p0, s0, J0))
    print(f"  iter 0: dist={d0:.3f} photo={p0:.4f} substr={s0:.3f} J={J0:.3f}")
    tic = time.time()
    for it in range(1, n_iters + 1):
        if time.time() - tic > 90: break
        grad = np.zeros(3)
        for i in range(3):
            pp = params.copy(); pp[i] += eps
            pm = params.copy(); pm[i] -= eps
            tp, *_ = multiview_loss(pp, target_field, target_rgbs,
                                     target_fps, runtime, pred_names,
                                     invariant, alpha)
            tm, *_ = multiview_loss(pm, target_field, target_rgbs,
                                     target_fps, runtime, pred_names,
                                     invariant, alpha)
            grad[i] = (tp - tm) / (2 * eps)
        params = params - lr * grad
        ti, pi, si, Ji = multiview_loss(params, target_field, target_rgbs,
                                         target_fps, runtime, pred_names,
                                         invariant, alpha)
        d = float(np.linalg.norm(params))
        history.append((it, params.tolist(), d, ti, pi, si, Ji))
        print(f"  iter {it}: dist={d:.3f} photo={pi:.4f} substr={si:.3f} J={Ji:.3f}")
    return history


def main():
    target_field = make_phoxel_cube(side=0.6, density=12)
    print(f"target: cube at origin ({target_field['n']} phoxels)")
    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception:
                pass
    pred_names = runtime.installed()
    print(f"\nrendering {len(VIEW_AZIMUTHS)} target views...")
    target_rgbs = []; target_fps = []
    for az in VIEW_AZIMUTHS:
        rgb = render_view(target_field, az)
        target_rgbs.append(rgb)
        Image.fromarray(rgb).save(OUT / f"target_az{az}.png")
        fp = fingerprint(rgb, f"t_az{az}", runtime, pred_names)
        target_fps.append(fp)
    invariant = [pn for pn in pred_names
                 if len({target_fps[i][pn] for i in range(len(VIEW_AZIMUTHS))}) == 1]
    print(f"layout-invariant subset across {len(VIEW_AZIMUTHS)} views: {len(invariant)} predicates")
    init_params = (1.0, 0.5, 0.0)
    initial_dist = float(np.linalg.norm(init_params))
    print(f"\ninit translation {init_params}, distance {initial_dist:.3f}\n")
    alphas = [0.0, 0.05, 0.2, 0.5]
    results = []
    for alpha in alphas:
        print(f"=== alpha = {alpha} ===")
        hist = train(target_field, target_rgbs, target_fps, init_params,
                     runtime, pred_names, invariant, alpha=alpha,
                     n_iters=6, eps=0.05, lr=2.0)
        final = hist[-1]
        results.append({
            "alpha": alpha, "history": hist,
            "final_distance": final[2], "final_photo": final[4],
            "final_substr": final[5], "final_J": final[6],
            "dist_reduction_pct": 100.0 * (initial_dist - final[2]) / initial_dist,
        })
        print()
    print("=== R141 SUMMARY (multi-view) ===")
    print(f"{'alpha':<8}{'dist':<10}{'photo':<10}{'substr':<10}{'J_avg':<10}{'redux%':<10}")
    for r in results:
        print(f"{r['alpha']:<8}{r['final_distance']:<10.3f}"
              f"{r['final_photo']:<10.4f}{r['final_substr']:<10.3f}"
              f"{r['final_J']:<10.3f}{r['dist_reduction_pct']:<10.1f}")
    best = min(results, key=lambda r: r['final_distance'])
    print(f"\nbest alpha (multi-view) = {best['alpha']} (dist={best['final_distance']:.3f}, J={best['final_J']:.3f})")
    print(f"compare to R140 single-view best alpha = 0.2 (dist=0.240)")
    audit = {
        "round": "R141", "date": "2026-05-01",
        "method": ("Multi-view Phase 4 training. Loss = (1/4) sum_views "
                   "[photo_MSE_v + alpha * (1 - J_invariant_v)] over 4 cameras "
                   "at azimuths 0,90,180,270. Finite-diff gradient on 3-param translation. "
                   "Sweep alpha in {0.0, 0.05, 0.2, 0.5}, 6 iters, lr=2.0, eps=0.05."),
        "n_views": len(VIEW_AZIMUTHS), "view_azimuths": VIEW_AZIMUTHS,
        "image_size": IMAGE_SIZE, "init_params": list(init_params),
        "initial_distance": initial_dist,
        "n_invariant_predicates_multiview": len(invariant),
        "alphas_tested": alphas, "results": results,
        "best_alpha_multiview": best['alpha'],
        "best_dist_multiview": best['final_distance'],
        "single_view_best_alpha_R140": 0.2,
        "single_view_best_dist_R140": 0.240,
    }
    (OUT / "round141_audit.json").write_text(json.dumps(audit, indent=2))
    print(f"\nwrote {OUT}/round141_audit.json")


if __name__ == "__main__":
    main()
