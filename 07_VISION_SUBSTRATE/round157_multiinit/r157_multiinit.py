"""R157 - Multi-init confidence interval at R150 setup (3-DOF Phase 4).

R150 demonstrated lr-decay schedule reaches dist=0.0843 (92.5% reduction)
from init (1.0, 0.5, 0). Multi-init validation: run same setup from 3
additional inits to establish whether that result is robust or
trajectory-specific.

Setup: MV alpha=0.20, image_size=128 (faster than R150's 192 for multi-init
budget), Adam + lr-decay schedule, 20 iters per init, fixed eps=0.05.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT)); sys.path.insert(0, '/tmp')
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from r124_phoxel_renderer import render_phoxels, fingerprint, make_phoxel_cube
from r126_sphere_test import make_phoxel_sphere

OUT = Path('/tmp/round157_multiinit'); OUT.mkdir(exist_ok=True)
IMG = 128; VIEWS = [0, 90, 180, 270]; ALPHA = 0.20
ADAM_B1 = 0.9; ADAM_B2 = 0.999; ADAM_EPS = 1e-8
EPS = 0.05


def lr_at(t):
    if t <= 10: return 0.1
    elif t <= 15: return 0.05
    else: return 0.025


def cam(az):
    rad = np.deg2rad(az)
    return (4.0*np.cos(rad), 4.0*np.sin(rad), 0.6)

def combine(*fs, offsets):
    pts, cols = [], []
    for i, f in enumerate(fs):
        pts.append(f["positions"] + np.array(offsets[i], dtype=np.float64))
        cols.append(f["colors"])
    return {"positions": np.concatenate(pts), "colors": np.concatenate(cols), "n": sum(f["n"] for f in fs)}

def shift(f, t): return {'positions': f['positions']+np.array(t), 'colors': f['colors'], 'n': f['n']}
def render(f, az): return render_phoxels(f, cam(az), image_size=IMG)
def mse(a, b): return float(np.mean((a/255.0 - b/255.0)**2))
def J(a, b, names):
    sa = {k for k in names if a.get(k)}; sb = {k for k in names if b.get(k)}
    return 1.0 if not sa and not sb else len(sa & sb)/len(sa | sb)

def loss_mv(p, tf, trgbs, tfps, rt, pn, inv, alpha):
    f = shift(tf, p)
    photos, substrs, Js = [], [], []
    for i, az in enumerate(VIEWS):
        rgb = render(f, az)
        photos.append(mse(rgb.astype(np.float64), trgbs[i].astype(np.float64)))
        if alpha > 0:
            fp = fingerprint(rgb, f"v{az}", rt, pn)
            j = J(tfps[i], fp, inv); substrs.append(1-j); Js.append(j)
        else: substrs.append(0); Js.append(1.0)
    return float(np.mean(photos))+alpha*float(np.mean(substrs)), float(np.mean(photos)), float(np.mean(substrs)), float(np.mean(Js))


def train_one(init_params, tf, trgbs, tfps, rt, pn, inv, n_iters=20):
    params = np.array(init_params, dtype=np.float64)
    m = np.zeros(3); v = np.zeros(3); history = []
    t0,p0,s0,J0 = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    d0 = float(np.linalg.norm(params))
    history.append((0, params.tolist(), d0, t0, p0, s0, J0))
    for t in range(1, n_iters+1):
        lr_t = lr_at(t)
        g = np.zeros(3)
        for i in range(3):
            a = params.copy(); a[i] += EPS; b = params.copy(); b[i] -= EPS
            ta,*_ = loss_mv(a, tf, trgbs, tfps, rt, pn, inv, ALPHA)
            tb,*_ = loss_mv(b, tf, trgbs, tfps, rt, pn, inv, ALPHA)
            g[i] = (ta-tb)/(2*EPS)
        m = ADAM_B1*m + (1-ADAM_B1)*g
        v = ADAM_B2*v + (1-ADAM_B2)*(g**2)
        m_hat = m / (1 - ADAM_B1**t); v_hat = v / (1 - ADAM_B2**t)
        params = params - lr_t * m_hat / (np.sqrt(v_hat) + ADAM_EPS)
        ti,pi,si,ji = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
        d = float(np.linalg.norm(params))
        history.append((t, params.tolist(), d, ti, pi, si, ji))
    return history


# CLI: arg = init index (0..3 for 4 inits)
INIT_IDX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
INITS = [
    [1.0, 0.5, 0.0],   # R150 baseline
    [0.5, 0.8, 0.3],   # different direction
    [-0.7, 0.4, 0.5],  # negative quadrant
    [0.6, -0.5, -0.4], # mixed signs
]
init = INITS[INIT_IDX]
init_dist = float(np.linalg.norm(init))

cube = make_phoxel_cube(side=0.6, density=10)
sphere = make_phoxel_sphere(radius=0.45, density=18)
tf = combine(cube, sphere, offsets=[(-0.9,0,0),(0.9,0,0)])
print(f"R157 init #{INIT_IDX}: {init} (dist={init_dist:.3f})")
vision_ops.register_all(); rt = Runtime()
text = (ROOT/"data/vision/vocab.aurex").read_text()
for ppx in dsl.parse_source(text):
    if ppx.ok:
        try: P.type_check(ppx.pred); rt.install(ppx.pred)
        except Exception: pass
pn = rt.installed()
trgbs = [render(tf, az) for az in VIEWS]
tfps = [fingerprint(trgbs[i], f"t{az}", rt, pn) for i,az in enumerate(VIEWS)]
inv = [p for p in pn if len({tfps[i][p] for i in range(4)})==1]
print(f"invariant: {len(inv)}")

history = train_one(init, tf, trgbs, tfps, rt, pn, inv, n_iters=20)
final = history[-1]
final_dist = final[2]
final_J = final[6]
redux_pct = 100*(init_dist - final_dist)/init_dist

result = {
    "init_idx": INIT_IDX, "init_params": init, "init_dist": init_dist,
    "final_dist": final_dist, "final_J": final_J, "redux_pct": redux_pct,
    "history": history,
}
all_file = OUT / "all_results.json"
all_results = json.loads(all_file.read_text()) if all_file.exists() else {}
all_results[str(INIT_IDX)] = result
all_file.write_text(json.dumps(all_results, indent=2))

print(f"\n=== INIT #{INIT_IDX} RESULT ===")
print(f"  init dist: {init_dist:.4f}")
print(f"  final dist: {final_dist:.4f} ({redux_pct:.1f}% reduction)")
print(f"  final J: {final_J:.3f}")
