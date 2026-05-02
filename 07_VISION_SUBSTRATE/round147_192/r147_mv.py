"""R147 multi-view at image_size=192."""
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

OUT = Path('/tmp/round147_192'); OUT.mkdir(exist_ok=True)
IMG = 192
VIEWS = [0, 90, 180, 270]

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

def train(tf, trgbs, tfps, init, rt, pn, inv, alpha, n_iters=6, eps=0.05, lr=2.0):
    pp = np.array(init, dtype=np.float64); h = []
    t0,p0,s0,J0 = loss_mv(pp, tf, trgbs, tfps, rt, pn, inv, alpha)
    h.append((0, pp.tolist(), float(np.linalg.norm(pp)), t0, p0, s0, J0))
    print(f"  it0 d={float(np.linalg.norm(pp)):.3f} J={J0:.3f}")
    for it in range(1, n_iters+1):
        g = np.zeros(3)
        for i in range(3):
            a = pp.copy(); a[i] += eps; b = pp.copy(); b[i] -= eps
            ta,*_ = loss_mv(a, tf, trgbs, tfps, rt, pn, inv, alpha)
            tb,*_ = loss_mv(b, tf, trgbs, tfps, rt, pn, inv, alpha)
            g[i] = (ta-tb)/(2*eps)
        pp = pp - lr*g
        ti,pi,si,ji = loss_mv(pp, tf, trgbs, tfps, rt, pn, inv, alpha)
        h.append((it, pp.tolist(), float(np.linalg.norm(pp)), ti, pi, si, ji))
        print(f"  it{it} d={float(np.linalg.norm(pp)):.3f} J={ji:.3f}")
    return h

ALPHAS = [float(a) for a in sys.argv[1].split(',')]
cube = make_phoxel_cube(side=0.6, density=10)
sphere = make_phoxel_sphere(radius=0.45, density=18)
tf = combine(cube, sphere, offsets=[(-0.9,0,0),(0.9,0,0)])
print(f"R147 MV-192: alphas={ALPHAS}")
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
init = (1.0, 0.5, 0.0); d0 = float(np.linalg.norm(init))

rf = OUT / "mv_results.json"
prev = json.loads(rf.read_text()) if rf.exists() else {}
for alpha in ALPHAS:
    print(f"\n=== MV alpha={alpha} ===")
    h = train(tf, trgbs, tfps, init, rt, pn, inv, alpha, n_iters=6)
    f = h[-1]
    prev[str(alpha)] = {"alpha": alpha, "history": h, "final_distance": f[2],
                       "final_photo": f[4], "final_J": f[6], "redux_pct": 100*(d0-f[2])/d0}
    rf.write_text(json.dumps(prev, indent=2))
print("\n=== MV-192 results ===")
for k in sorted(prev, key=float):
    r = prev[k]
    print(f"  alpha={r['alpha']}: dist={r['final_distance']:.3f} J={r['final_J']:.3f} redux={r['redux_pct']:.1f}%")
