"""R137 — does the layout-SENSITIVE subset gradient-train where the
invariant subset couldn't?

Same R134 setup: cube target at origin, init translation (1.0, 0.5, 0).
Loss = 1 - Jaccard(current, target) on the 36 layout-SENSITIVE predicates.
If this converges where R134's invariant subset plateaued, the partition
has both content-loss AND position-loss building blocks for Phase 4."""
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

OUT = Path('/tmp/round137_sensitive'); OUT.mkdir(exist_ok=True)


def translate_field(field, tx, ty, tz):
    return {'positions': field['positions'] + np.array([tx, ty, tz]),
            'colors': field['colors'], 'n': field['n']}


def render(field, image_size=160):
    return render_phoxels(field, (3.0, 0, 0.5), image_size=image_size)


def J_subset(a, b, names):
    sa = {k for k in names if a.get(k)}
    sb = {k for k in names if b.get(k)}
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb)


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
            except Exception: pass
    pred_names = runtime.installed()

    # Target fingerprint at fixed viewpoint
    rgb_target = render(target_field)
    Image.fromarray(rgb_target).save(OUT / "target.png")
    fp_target = fingerprint(rgb_target, "target", runtime, pred_names)

    # Re-derive layout partition from a 4-viewpoint test on TARGET alone
    azimuths = [0, 45, 90, 135]
    target_fps_views = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (3.0 * np.cos(rad), 3.0 * np.sin(rad), 0.5)
        rgb_az = render_phoxels(target_field, cam_az, image_size=160)
        target_fps_views[az] = fingerprint(rgb_az, f"target_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({target_fps_views[az][pn] for az in azimuths}) == 1]
    sensitive = [pn for pn in pred_names if pn not in invariant]
    print(f"layout-invariant: {len(invariant)}; layout-sensitive: {len(sensitive)}")

    # Initialize at offset position
    params = np.array([1.0, 0.5, 0.0])
    field0 = translate_field(target_field, *params)
    rgb0 = render(field0)
    fp0 = fingerprint(rgb0, "init", runtime, pred_names)
    Image.fromarray(rgb0).save(OUT / "iter_00.png")

    initial_J_sens = J_subset(fp_target, fp0, sensitive)
    initial_J_inv  = J_subset(fp_target, fp0, invariant)
    initial_loss = 1.0 - initial_J_sens
    initial_dist = float(np.linalg.norm(params))
    print(f"\ninitial: params={params.tolist()}, dist={initial_dist:.3f}")
    print(f"  J_sensitive={initial_J_sens:.3f}, loss={initial_loss:.3f}")
    print(f"  J_invariant={initial_J_inv:.3f}  (for comparison)")

    n_iters = 10
    eps = 0.05
    lr = 0.4
    history = [(0, params.tolist(), initial_dist, initial_J_sens, initial_loss)]
    tic = time.time()
    for it in range(1, n_iters + 1):
        if time.time() - tic > 35: break
        grad = np.zeros(3)
        for i in range(3):
            p_plus = params.copy(); p_plus[i] += eps
            p_minus = params.copy(); p_minus[i] -= eps
            f_p = translate_field(target_field, *p_plus)
            f_m = translate_field(target_field, *p_minus)
            fp_p = fingerprint(render(f_p), "_p", runtime, pred_names)
            fp_m = fingerprint(render(f_m), "_m", runtime, pred_names)
            loss_p = 1.0 - J_subset(fp_target, fp_p, sensitive)
            loss_m = 1.0 - J_subset(fp_target, fp_m, sensitive)
            grad[i] = (loss_p - loss_m) / (2 * eps)
        params = params - lr * grad
        new_field = translate_field(target_field, *params)
        rgb_new = render(new_field)
        fp_new = fingerprint(rgb_new, "new", runtime, pred_names)
        Image.fromarray(rgb_new).save(OUT / f"iter_{it:02d}.png")
        new_J_sens = J_subset(fp_target, fp_new, sensitive)
        new_loss = 1.0 - new_J_sens
        new_dist = float(np.linalg.norm(params))
        history.append((it, params.tolist(), new_dist, new_J_sens, new_loss))
        print(f"iter {it}: params=[{params[0]:+.3f},{params[1]:+.3f},{params[2]:+.3f}]  "
              f"|d|={new_dist:.3f}  J_sens={new_J_sens:.3f}  loss={new_loss:.3f}  "
              f"grad_norm={np.linalg.norm(grad):.3f}")

    final_dist = history[-1][2]
    final_J_sens = history[-1][3]
    final_loss = history[-1][4]

    R134_initial_dist = 1.118; R134_final_dist = 0.891

    converged = final_dist < 0.30
    moved_substantially = (initial_dist - final_dist) / initial_dist > 0.30

    result = {
        "round": "R137",
        "date": "2026-05-01",
        "method": "Same R134 setup but loss = 1 - Jaccard(current, target) on layout-SENSITIVE 36-predicate subset",
        "n_invariant_predicates": len(invariant),
        "n_sensitive_predicates": len(sensitive),
        "initial_params": [1.0, 0.5, 0.0],
        "initial_distance": initial_dist,
        "initial_J_sensitive": initial_J_sens,
        "initial_loss": initial_loss,
        "n_iters": len(history) - 1,
        "history": history,
        "final_params": history[-1][1],
        "final_distance": final_dist,
        "final_J_sensitive": final_J_sens,
        "final_loss": final_loss,
        "loss_reduction_pct": round((initial_loss - final_loss) / max(initial_loss, 1e-6) * 100, 1),
        "distance_reduction_pct": round((initial_dist - final_dist) / initial_dist * 100, 1),
        "comparison_to_R134_invariant": {
            "R134_invariant_initial_dist": R134_initial_dist,
            "R134_invariant_final_dist": R134_final_dist,
            "R134_dist_reduction_pct": 20.3,
            "R137_sensitive_dist_reduction_pct": round((initial_dist - final_dist) / initial_dist * 100, 1),
        },
        "converged": bool(converged),
        "moved_substantially": bool(moved_substantially),
        "verdict": (
            "PASS — layout-sensitive subset gradient-trains cleanly toward target; partition has both content-loss (invariant, R130-R131) AND position-loss (sensitive, R137) building blocks for Phase 4"
            if (final_dist < initial_dist * 0.6)
            else "PARTIAL — sensitive subset still struggles; finite-diff on phoxel translation is intrinsically hard"
        ),
    }
    (OUT / "round137_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R137 RESULT ===")
    print(f"R134 invariant subset: dist 1.118 -> 0.891 (20% reduction); plateaued at gradient=0")
    print(f"R137 sensitive subset: dist {initial_dist:.3f} -> {final_dist:.3f} ({(initial_dist-final_dist)/initial_dist*100:.0f}% reduction)")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round137_audit.json")


if __name__ == "__main__":
    main()
