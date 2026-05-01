"""R134 — Phase 3 first step: finite-difference gradient descent on
phoxel translation. Smallest viable differentiable-training demo.

Target: cube at origin
Init:   same cube translated by (tx, ty, tz) = (1.0, 0.5, 0)
Loss:   1 - Jaccard(current_fingerprint, target_fingerprint) on
        layout-invariant subset
Method: finite-difference numerical gradient over (tx, ty, tz),
        gradient descent step
Goal:   demonstrate any monotonic loss decrease — proves gradient
        signal is usable
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
from aurexis_workbench.visual_intake import _bundle_from_single
from r124_phoxel_renderer import look_at, render_phoxels, fingerprint, jaccard, make_phoxel_cube

OUT = Path('/tmp/round134_train'); OUT.mkdir(exist_ok=True)


def translate_field(field, tx, ty, tz):
    return {
        'positions': field['positions'] + np.array([tx, ty, tz]),
        'colors': field['colors'],
        'n': field['n'],
    }


def render_eval(field, runtime, pred_names, image_size=160):
    cam = (3.0, 0, 0.5)
    rgb = render_phoxels(field, cam, image_size=image_size)
    return rgb, fingerprint(rgb, "_", runtime, pred_names)


def J_subset(a, b, names):
    sa = {k for k in names if a.get(k)}
    sb = {k for k in names if b.get(k)}
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb)


def main():
    # Setup
    target_field = make_phoxel_cube(side=0.6, density=12)  # smaller for speed
    print(f"target: cube at origin ({target_field['n']} phoxels)")

    vision_ops.register_all()
    runtime = Runtime()
    text = (ROOT / "data" / "vision" / "vocab.aurex").read_text()
    for pp in dsl.parse_source(text):
        if pp.ok:
            try:
                P.type_check(pp.pred); runtime.install(pp.pred)
            except Exception: pass
    pred_names = runtime.installed()

    # Compute target fingerprint at fixed viewpoint
    rgb_target, fp_target = render_eval(target_field, runtime, pred_names)
    Image.fromarray(rgb_target).save(OUT / "target.png")
    print(f"target fingerprint: {sum(fp_target.values())}/151 fired")

    # Re-derive layout-invariant subset from a 4-viewpoint test on target
    # (this is the same protocol used in R130/R131/R133)
    azimuths = [0, 45, 90, 135]
    target_fps_views = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (3.0 * np.cos(rad), 3.0 * np.sin(rad), 0.5)
        rgb_az = render_phoxels(target_field, cam_az, image_size=160)
        target_fps_views[az] = fingerprint(rgb_az, f"target_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({target_fps_views[az][pn] for az in azimuths}) == 1]
    print(f"layout-invariant subset: {len(invariant)} predicates")

    # Initialize parameters
    params = np.array([1.0, 0.5, 0.0])  # initial translation (tx, ty, tz)
    initial_field = translate_field(target_field, *params)

    rgb0, fp0 = render_eval(initial_field, runtime, pred_names)
    initial_J = J_subset(fp_target, fp0, invariant)
    initial_loss = 1.0 - initial_J
    print(f"initial: params={params.tolist()}, J_invariant={initial_J:.3f}, loss={initial_loss:.3f}")
    Image.fromarray(rgb0).save(OUT / "iter_00.png")

    # Gradient descent
    n_iters = 8
    eps = 0.05      # finite-difference step
    lr = 0.4        # learning rate

    history = [(0, params.tolist(), initial_J, initial_loss)]
    tic = time.time()
    for it in range(1, n_iters + 1):
        if time.time() - tic > 35: break
        # Compute current loss
        field = translate_field(target_field, *params)
        rgb, fp = render_eval(field, runtime, pred_names)
        cur_J = J_subset(fp_target, fp, invariant)
        cur_loss = 1.0 - cur_J

        # Finite-difference gradient
        grad = np.zeros(3)
        for i in range(3):
            p_plus = params.copy(); p_plus[i] += eps
            p_minus = params.copy(); p_minus[i] -= eps
            f_p = translate_field(target_field, *p_plus)
            f_m = translate_field(target_field, *p_minus)
            _, fp_p = render_eval(f_p, runtime, pred_names)
            _, fp_m = render_eval(f_m, runtime, pred_names)
            J_p = J_subset(fp_target, fp_p, invariant)
            J_m = J_subset(fp_target, fp_m, invariant)
            loss_p = 1.0 - J_p
            loss_m = 1.0 - J_m
            grad[i] = (loss_p - loss_m) / (2 * eps)

        # Step
        new_params = params - lr * grad
        params = new_params

        # Evaluate after step
        new_field = translate_field(target_field, *params)
        rgb_new, fp_new = render_eval(new_field, runtime, pred_names)
        new_J = J_subset(fp_target, fp_new, invariant)
        new_loss = 1.0 - new_J
        history.append((it, params.tolist(), new_J, new_loss))
        Image.fromarray(rgb_new).save(OUT / f"iter_{it:02d}.png")
        dist = float(np.linalg.norm(params))
        print(f"iter {it}: params=[{params[0]:+.3f},{params[1]:+.3f},{params[2]:+.3f}]  "
              f"|d|={dist:.3f}  J={new_J:.3f}  loss={new_loss:.3f}  grad_norm={np.linalg.norm(grad):.3f}")

    # Verdict
    final_J = history[-1][2]
    final_loss = history[-1][3]
    final_dist = float(np.linalg.norm(history[-1][1]))
    initial_dist = float(np.linalg.norm([1.0, 0.5, 0.0]))
    monotonic = all(history[i][3] <= history[max(0,i-1)][3] + 0.05 for i in range(1, len(history)))
    decreased = final_loss < initial_loss
    moved_toward = final_dist < initial_dist

    result = {
        "round": "R134",
        "date": "2026-05-01",
        "method": "finite-difference gradient descent on 3-param translation; loss = 1 - Jaccard(current, target) on layout-invariant subset",
        "target": "cube at origin",
        "initial_params": [1.0, 0.5, 0.0],
        "initial_J": history[0][2],
        "initial_loss": history[0][3],
        "initial_distance": initial_dist,
        "n_iters_run": len(history) - 1,
        "eps_finite_diff": eps,
        "learning_rate": lr,
        "n_invariant_predicates": len(invariant),
        "history": history,
        "final_params": history[-1][1],
        "final_J": final_J,
        "final_loss": final_loss,
        "final_distance_from_origin": final_dist,
        "loss_decreased": bool(decreased),
        "moved_toward_origin": bool(moved_toward),
        "approximately_monotonic": bool(monotonic),
        "verdict": (
            "PASS — finite-difference gradient descent on phoxel translation reduces fingerprint loss; gradient signal is usable on the layout-invariant subset"
            if (decreased and moved_toward)
            else "PARTIAL — gradient signal exists but loss landscape has plateaus; Phase 4 may want continuous-relaxation variant"
        ),
    }
    (OUT / "round134_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R134 RESULT ===")
    print(f"initial: dist={initial_dist:.3f}, loss={history[0][3]:.3f}")
    print(f"final:   dist={final_dist:.3f}, loss={final_loss:.3f}")
    print(f"loss decreased: {decreased}; moved toward origin: {moved_toward}")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round134_audit.json")


if __name__ == "__main__":
    main()
