"""R156 - Staged 7-DOF Phase 4 training (SEQUENTIAL phase unfreeze).

Phase 1 (iters 1-15):  train translation (idx 0-2) only; freeze rot+scale at init
Phase 2 (iters 16-25): train rotations (idx 3-5) only; freeze trans+scale
Phase 3 (iters 26-30): train scale (idx 6) only; freeze trans+rot
Phase 4 (iters 31-40): unfreeze all, fine-tune at lr=0.00625

Tests R155 architectural prediction: SEQUENTIAL > PARALLEL in finite-diff 7-DOF.
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

OUT = Path('/tmp/round156_staged'); OUT.mkdir(exist_ok=True)
IMG = 192; VIEWS = [0, 90, 180, 270]; ALPHA = 0.20
ADAM_B1 = 0.9; ADAM_B2 = 0.999; ADAM_EPS = 1e-8
EPS = 0.05
TARGET = np.array([0, 0, 0, 0, 0, 0, 1.0])
INIT = np.array([1.0, 0.5, 0, 0.2, 0.2, 0.2, 1.1])


def phase_at(t):
    """Return (active_axes, lr) for iteration t."""
    if t <= 5:    return [0,1,2],   0.10  # translation, warmup
    elif t <= 10: return [0,1,2],   0.05  # translation, decay
    elif t <= 15: return [0,1,2],   0.025 # translation, fine
    elif t <= 20: return [3,4,5],   0.05  # rotations, start
    elif t <= 25: return [3,4,5],   0.025 # rotations, fine
    elif t <= 30: return [6],       0.025 # scale only
    elif t <= 35: return [0,1,2,3,4,5,6], 0.0125  # all unfreeze, decay
    else:         return [0,1,2,3,4,5,6], 0.00625 # all unfreeze, fine


def cam(az):
    rad = np.deg2rad(az)
    return (4.0*np.cos(rad), 4.0*np.sin(rad), 0.6)

def combine(*fs, offsets):
    pts, cols = [], []
    for i, f in enumerate(fs):
        pts.append(f["positions"] + np.array(offsets[i], dtype=np.float64))
        cols.append(f["colors"])
    return {"positions": np.concatenate(pts), "colors": np.concatenate(cols), "n": sum(f["n"] for f in fs)}

def rot_matrix(rx, ry, rz):
    cx, sx = np.cos(rx), np.sin(rx); cy, sy = np.cos(ry), np.sin(ry); cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return Rz @ Ry @ Rx

def apply_7dof(field, params):
    tx, ty, tz, rx, ry, rz, s = params
    R = rot_matrix(rx, ry, rz)
    new_pts = (field['positions'] @ R.T) * s + np.array([tx, ty, tz])
    return {'positions': new_pts, 'colors': field['colors'], 'n': field['n']}

def render(f, az): return render_phoxels(f, cam(az), image_size=IMG)
def mse(a, b): return float(np.mean((a/255.0 - b/255.0)**2))
def J(a, b, names):
    sa = {k for k in names if a.get(k)}; sb = {k for k in names if b.get(k)}
    return 1.0 if not sa and not sb else len(sa & sb)/len(sa | sb)

def loss_mv(p, tf, trgbs, tfps, rt, pn, inv, alpha):
    f = apply_7dof(tf, p)
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
print(f"R156 STAGED training: 4-phase sequential unfreeze")
init_dist_7d = float(np.linalg.norm(INIT - TARGET))
print(f"7D init: {init_dist_7d:.4f}")
vision_ops.register_all(); rt = Runtime()
text = (ROOT/"data/vision/vocab.aurex").read_text()
for ppx in dsl.parse_source(text):
    if ppx.ok:
        try: P.type_check(ppx.pred); rt.install(ppx.pred)
        except Exception: pass
pn = rt.installed()
target_field = apply_7dof(tf, TARGET)
trgbs = [render(target_field, az) for az in VIEWS]
tfps = [fingerprint(trgbs[i], f"t{az}", rt, pn) for i,az in enumerate(VIEWS)]
inv = [p for p in pn if len({tfps[i][p] for i in range(4)})==1]
print(f"invariant: {len(inv)}")

state_file = OUT / "adam_state.json"
if state_file.exists():
    state = json.loads(state_file.read_text())
    params = np.array(state['params']); m = np.array(state['m']); v = np.array(state['v'])
    history = state['history']; iter_offset = state['iter_count']
    print(f"resuming from iter {iter_offset}, dist7D={float(np.linalg.norm(params-TARGET)):.4f}")
else:
    params = INIT.copy()
    m = np.zeros(7); v = np.zeros(7); history = []; iter_offset = 0
    t0,p0,s0,J0 = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    history.append((0, params.tolist(), float(np.linalg.norm(params-TARGET)), t0, p0, s0, J0, 0.1, []))
    print(f"  it0 d7D={init_dist_7d:.4f} J={J0:.3f}")

for chunk_iter in range(N_ITERS_THIS_CHUNK):
    t = iter_offset + chunk_iter + 1
    active, lr_t = phase_at(t)
    g = np.zeros(7)
    for i in active:
        a = params.copy(); a[i] += EPS; b = params.copy(); b[i] -= EPS
        ta,*_ = loss_mv(a, tf, trgbs, tfps, rt, pn, inv, ALPHA)
        tb,*_ = loss_mv(b, tf, trgbs, tfps, rt, pn, inv, ALPHA)
        g[i] = (ta-tb)/(2*EPS)
    # Update m, v only for active axes
    for i in active:
        m[i] = ADAM_B1*m[i] + (1-ADAM_B1)*g[i]
        v[i] = ADAM_B2*v[i] + (1-ADAM_B2)*(g[i]**2)
        m_hat = m[i] / (1 - ADAM_B1**t)
        v_hat = v[i] / (1 - ADAM_B2**t)
        params[i] = params[i] - lr_t * m_hat / (np.sqrt(v_hat) + ADAM_EPS)
    ti,pi,si,ji = loss_mv(params, tf, trgbs, tfps, rt, pn, inv, ALPHA)
    d7 = float(np.linalg.norm(params - TARGET))
    history.append((t, params.tolist(), d7, ti, pi, si, ji, lr_t, list(active)))
    phase_label = "T" if active==[0,1,2] else "R" if active==[3,4,5] else "S" if active==[6] else "ALL"
    print(f"  it{t} [{phase_label}] d7D={d7:.4f} lr={lr_t:.4f} ph={pi:.4f} J={ji:.3f} | tx={params[0]:.3f} rx={params[3]:.3f} s={params[6]:.3f}")
    state_file.write_text(json.dumps({
        'iter_count': t, 'params': params.tolist(),
        'm': m.tolist(), 'v': v.tolist(), 'history': history,
    }))
