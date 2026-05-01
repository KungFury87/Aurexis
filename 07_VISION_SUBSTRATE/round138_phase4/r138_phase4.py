"""R138 — Phase 4 Option D first concrete training pipeline.

Loss = per-pixel MSE (photometric primary) + α × (1 - J_invariant) (substrate regularizer)

Test: train 3-param translation on a known cube target.
- Photometric-only baseline converges cleanly to ~(0,0,0)?
- Combined loss also converges? Validates regularizer doesn't break primary signal."""
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

OUT = Path('/tmp/round138_phase4'); OUT.mkdir(exist_ok=True)


def translate_field(field, tx, ty, tz):
    return {'positions': field['positions'] + np.array([tx, ty, tz]),
            'colors': field['colors'], 'n': field['n']}


def render(field, image_size=160):
    return render_phoxels(field, (3.0, 0, 0.5), image_size=image_size)


def photometric_mse(rgb_a, rgb_b):
    a = rgb_a.astype(np.float64) / 255.0
    b = rgb_b.astype(np.float64) / 255.0
    return float(np.mean((a - b) ** 2))


def J_subset(a, b, names):
    sa = {k for k in names if a.get(k)}
    sb = {k for k in names if b.get(k)}
    if not sa and not sb: return 1.0
    return len(sa & sb) / len(sa | sb)


def train_run(target_field, init_params, runtime, pred_names, invariant,
              fp_target, rgb_target, alpha, n_iters=10, eps=0.05, lr=2.0,
              tag="run"):
    """One training run with given alpha (regularizer weight)."""
    params = np.array(init_params, dtype=np.float64)
    history = []
    initial_dist = float(np.linalg.norm(params))

    def total_loss(p):
        f = translate_field(target_field, *p)
        rgb = render(f)
        photo = photometric_mse(rgb, rgb_target)
        if alpha > 0:
            fp = fingerprint(rgb, "_", runtime, pred_names)
            J = J_subset(fp_target, fp, invariant)
            substr = 1.0 - J
        else:
            substr = 0.0
            J = 1.0
        total = photo + alpha * substr
        return total, photo, substr, J

    init_total, init_photo, init_subst, init_J = total_loss(params)
    history.append((0, params.tolist(), float(np.linalg.norm(params)),
                    init_total, init_photo, init_subst, init_J))
    print(f"  iter 0: dist={initial_dist:.3f} photo={init_photo:.4f} substr={init_subst:.3f} total={init_total:.4f}")

    tic = time.time()
    for it in range(1, n_iters + 1):
        if time.time() - tic > 30: break
        # Finite-diff gradient on total loss
        grad = np.zeros(3)
        for i in range(3):
            p_plus = params.copy(); p_plus[i] += eps
            p_minus = params.copy(); p_minus[i] -= eps
            t_p, _, _, _ = total_loss(p_plus)
            t_m, _, _, _ = total_loss(p_minus)
            grad[i] = (t_p - t_m) / (2 * eps)
        params = params - lr * grad
        cur_total, cur_photo, cur_subst, cur_J = total_loss(params)
        d = float(np.linalg.norm(params))
        history.append((it, params.tolist(), d, cur_total, cur_photo, cur_subst, cur_J))
        print(f"  iter {it}: dist={d:.3f} photo={cur_photo:.4f} substr={cur_subst:.3f} total={cur_total:.4f} grad={np.linalg.norm(grad):.4f}")

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
            except Exception: pass
    pred_names = runtime.installed()

    rgb_target = render(target_field)
    Image.fromarray(rgb_target).save(OUT / "target.png")
    fp_target = fingerprint(rgb_target, "target", runtime, pred_names)

    azimuths = [0, 45, 90, 135]
    target_fps_views = {}
    for az in azimuths:
        rad = np.deg2rad(az)
        cam_az = (3.0 * np.cos(rad), 3.0 * np.sin(rad), 0.5)
        rgb_az = render_phoxels(target_field, cam_az, image_size=160)
        target_fps_views[az] = fingerprint(rgb_az, f"t_az{az}", runtime, pred_names)
    invariant = [pn for pn in pred_names
                  if len({target_fps_views[az][pn] for az in azimuths}) == 1]
    print(f"layout-invariant subset: {len(invariant)} predicates")

    init_params = (1.0, 0.5, 0.0)
    initial_dist = float(np.linalg.norm(init_params))
    print(f"\ninit translation: {init_params}, distance={initial_dist:.3f}\n")

    # Photometric-only baseline (alpha=0) — short
    print(f"=== Run 1: photometric-only (alpha=0) ===")
    h_baseline = train_run(target_field, init_params, runtime, pred_names,
                            invariant, fp_target, rgb_target, alpha=0.0,
                            n_iters=8, lr=2.0, tag="baseline")

    # Combined loss (alpha=0.05 — small regularizer)
    print(f"\n=== Run 2: photometric + 0.05 × substrate (alpha=0.05) ===")
    h_combined = train_run(target_field, init_params, runtime, pred_names,
                            invariant, fp_target, rgb_target, alpha=0.05,
                            n_iters=8, lr=2.0, tag="combined")

    # Save final renders
    final_baseline = translate_field(target_field, *h_baseline[-1][1])
    Image.fromarray(render(final_baseline)).save(OUT / "final_baseline.png")
    final_combined = translate_field(target_field, *h_combined[-1][1])
    Image.fromarray(render(final_combined)).save(OUT / "final_combined.png")

    # Verdict
    final_dist_baseline = h_baseline[-1][2]
    final_dist_combined = h_combined[-1][2]
    final_J_baseline = h_baseline[-1][6]
    final_J_combined = h_combined[-1][6]

    baseline_converged = final_dist_baseline < 0.30
    combined_converged = final_dist_combined < 0.30
    regularizer_doesnt_break = abs(final_dist_baseline - final_dist_combined) < 0.4
    substrate_J_improves = final_J_combined >= final_J_baseline - 0.05

    result = {
        "round": "R138",
        "date": "2026-05-01",
        "method": "Phase 4 Option D — photometric primary loss + α × substrate fingerprint regularizer; finite-difference gradient descent on 3-param translation",
        "target": "cube at origin",
        "init_params": list(init_params),
        "initial_distance": initial_dist,
        "n_invariant_predicates": len(invariant),
        "alpha_combined": 0.05,
        "baseline_history": h_baseline,
        "combined_history": h_combined,
        "baseline_final_distance": final_dist_baseline,
        "baseline_final_J_invariant": final_J_baseline,
        "combined_final_distance": final_dist_combined,
        "combined_final_J_invariant": final_J_combined,
        "baseline_converged": bool(baseline_converged),
        "combined_converged": bool(combined_converged),
        "regularizer_compatible_with_baseline": bool(regularizer_doesnt_break),
        "substrate_J_does_not_degrade": bool(substrate_J_improves),
        "verdict": (
            "PASS — Phase 4 Option D operational; photometric primary converges; substrate regularizer compatible without breaking convergence"
            if (baseline_converged and combined_converged and regularizer_doesnt_break)
            else (
                "PARTIAL — photometric works but regularizer interferes (or photometric alone doesn't converge in this setup)"
            )
        ),
    }
    (OUT / "round138_audit.json").write_text(json.dumps(result, indent=2))
    print(f"\n=== R138 RESULT ===")
    print(f"baseline (photo only):    dist {initial_dist:.3f} -> {final_dist_baseline:.3f}, J_inv={final_J_baseline:.3f}")
    print(f"combined (photo + 0.05×sub): dist {initial_dist:.3f} -> {final_dist_combined:.3f}, J_inv={final_J_combined:.3f}")
    print(f"verdict: {result['verdict']}")
    print(f"\nwrote {OUT}/round138_audit.json")


if __name__ == "__main__":
    main()
