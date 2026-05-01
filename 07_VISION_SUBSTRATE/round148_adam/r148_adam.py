"""R148 - full-convergence Phase 4 training: Adam optimizer + 20 iters at MV alpha=0.20, image_size=192.

Target: drive R147's dist=0.124 (88.9% reduction) toward dist≈0 (near-perfect convergence).
Saves trajectory after every iter so partial run can be resumed.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT)); sys.path.insert(0, '/tmp')
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from r124_phoxel_renderer import render_phoxels, fingerprint, make_phoxel_cube
from r126_sphere_test import make_phoxel_sphere

OUT = Path('/tmp/round148_adam'); OUT.mkdir(exist_ok=True)
IMG = 192
VIEWS = [0, 90, 180, 270]
ALPHA = 0.20

# Adam hyperparameters
ADAM_LR = 0.1
ADAM_B1 = 0.9
ADAM_B2 = 0.999
ADAM_EPS = 1e-8


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


# Argument: number of additional iters to run
N_ITERS_THIS_CHUNK = int(sys.argv[1]) if len(sys.argv) > 1 else 10

cube = make_phoxel_cube(side=0.6, density=10)
sphere = make_phoxel_sphere(radius=0.45, density=18)
tf = combine(cube, sphere, offsets=[(-0.9,0,0),(0.9,0,0)])
print(f"R148: Adam, alpha={ALPHA}, image_size={IMG}, MV 4-view")
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
print(f"invariant subset: {len(inv)} predicates")

# Resume from saved state if available
state_file = OUT / "adam_state.json"
if state_file.exists():
    state = json.loads(state_file.read_text())
    params = np.array(state['params'])
    m = np.array(state['m'])
    v = np.array(state['v'])
    history = state['history']
    iter_offset = state['iter_count']
    print(f"resuming from iter {iter_offset}, params={params.tolist()}, dist={float(np.linalg.norm(params)):.3f}")
else:
    params = np.array([1.0, 0.5, 0.0], dtype=np.float64)
    m = np.zeros(3); v = np.zeros(3); history = []; iter_offset = 0
    t0,p0,s0,J0 = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    history.append((0, params.tolist(), float(np.linalg.norm(params)), t0, p0, s0, J0))
    print(f"  it0 d={float(np.linalg.norm(params)):.3f} ph={p0:.4f} J={J0:.3f}")

eps = 0.05
for chunk_iter in range(N_ITERS_THIS_CHUNK):
    t = iter_offset + chunk_iter + 1
    # finite-diff gradient
    g = np.zeros(3)
    for i in range(3):
        a = params.copy(); a[i] += eps; b = params.copy(); b[i] -= eps
        ta,*_ = loss_mv(a, tf, trgbs, tfps, rt, pn, inv, ALPHA)
        tb,*_ = loss_mv(b, tf, trgbs, tfps, rt, pn, inv, ALPHA)
        g[i] = (ta-tb)/(2*eps)
    # Adam update
    m = ADAM_B1*m + (1-ADAM_B1)*g
    v = ADAM_B2*v + (1-ADAM_B2)*(g**2)
    m_hat = m / (1 - ADAM_B1**t)
    v_hat = v / (1 - ADAM_B2**t)
    params = params - ADAM_LR * m_hat / (np.sqrt(v_hat) + ADAM_EPS)
    # eval
    ti,pi,si,ji = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    d = float(np.linalg.norm(params))
    history.append((t, params.tolist(), d, ti, pi, si, ji))
    print(f"  it{t} d={d:.4f} ph={pi:.4f} sub={si:.3f} J={ji:.3f} grad_norm={float(np.linalg.norm(g)):.4f}")
    # checkpoint
    state_file.write_text(json.dumps({
        'iter_count': t, 'params': params.tolist(),
        'm': m.tolist(), 'v': v.tolist(),
        'history': history,
    }))

print(f"\n=== R148 trajectory (first {iter_offset + N_ITERS_THIS_CHUNK} iters) ===")
for entry in history:
    it, pp, d, t, p, s, j = entry
    print(f"  it{it}: dist={d:.4f} J={j:.3f} redux={100*(1.118-d)/1.118:.1f}%")
