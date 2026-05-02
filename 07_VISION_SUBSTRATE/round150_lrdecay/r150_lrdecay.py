"""R150 - Adam + lr-decay schedule.

Halve lr every 5 iters past iter 10:
  iters 1-10: lr=0.1 (R148 baseline)
  iters 11-15: lr=0.05
  iters 16-20: lr=0.025

Same fixed eps=0.05 as R148 (adaptive eps was rejected by R149).
Same MV alpha=0.20, image_size=192 setup.
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

OUT = Path('/tmp/round150_lrdecay'); OUT.mkdir(exist_ok=True)
IMG = 192; VIEWS = [0, 90, 180, 270]; ALPHA = 0.20
ADAM_B1 = 0.9; ADAM_B2 = 0.999; ADAM_EPS = 1e-8
EPS = 0.05  # fixed (R149 ruled out adaptive)


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


N_ITERS_THIS_CHUNK = int(sys.argv[1]) if len(sys.argv) > 1 else 5

cube = make_phoxel_cube(side=0.6, density=10)
sphere = make_phoxel_sphere(radius=0.45, density=18)
tf = combine(cube, sphere, offsets=[(-0.9,0,0),(0.9,0,0)])
print(f"R150: Adam + lr-decay, alpha={ALPHA}, image_size={IMG}, fixed eps={EPS}")
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

state_file = OUT / "adam_state.json"
if state_file.exists():
    state = json.loads(state_file.read_text())
    params = np.array(state['params']); m = np.array(state['m']); v = np.array(state['v'])
    history = state['history']; iter_offset = state['iter_count']
    print(f"resuming from iter {iter_offset}, dist={float(np.linalg.norm(params)):.4f}")
else:
    params = np.array([1.0, 0.5, 0.0], dtype=np.float64)
    m = np.zeros(3); v = np.zeros(3); history = []; iter_offset = 0
    t0,p0,s0,J0 = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    history.append((0, params.tolist(), float(np.linalg.norm(params)), t0, p0, s0, J0, 0.1))
    print(f"  it0 d={float(np.linalg.norm(params)):.4f} J={J0:.3f}")

for chunk_iter in range(N_ITERS_THIS_CHUNK):
    t = iter_offset + chunk_iter + 1
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
    history.append((t, params.tolist(), d, ti, pi, si, ji, lr_t))
    print(f"  it{t} d={d:.4f} lr={lr_t:.3f} ph={pi:.4f} sub={si:.3f} J={ji:.3f}")
    state_file.write_text(json.dumps({
        'iter_count': t, 'params': params.tolist(),
        'm': m.tolist(), 'v': v.tolist(), 'history': history,
    }))
