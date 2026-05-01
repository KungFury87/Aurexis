"""R146 - Single-view fine-grained alpha sweep at 96/128/160.

Same setup as R143/R144/R145 except 1 view (az=0) instead of 4. Tests
whether view count is subsumed by the resolution-tracking law or is a
separate dimension.
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

OUT = Path('/tmp/round146_singleview'); OUT.mkdir(exist_ok=True)
SINGLE_AZ = 0  # only one view


def cam(az, radius=4.0, height=0.6):
    rad = np.deg2rad(az)
    return (radius*np.cos(rad), radius*np.sin(rad), height)


def combine(*fields, offsets):
    pts, cols = [], []
    for i, f in enumerate(fields):
        off = np.array(offsets[i], dtype=np.float64)
        pts.append(f["positions"] + off); cols.append(f["colors"])
    return {"positions": np.concatenate(pts), "colors": np.concatenate(cols),
            "n": sum(f["n"] for f in fields)}


def shift(f, t): return {'positions': f['positions']+np.array(t), 'colors': f['colors'], 'n': f['n']}
def render(f, image_size): return render_phoxels(f, cam(SINGLE_AZ), image_size=image_size)
def mse(a, b): return float(np.mean((a/255.0 - b/255.0)**2))
def J(a, b, names):
    sa = {k for k in names if a.get(k)}; sb = {k for k in names if b.get(k)}
    return 1.0 if not sa and not sb else len(sa & sb)/len(sa | sb)


def loss(p, tf, trgb, tfp, rt, pn, image_size, all_preds, alpha):
    f = shift(tf, p)
    rgb = render(f, image_size)
    photo = mse(rgb.astype(np.float64), trgb.astype(np.float64))
    if alpha > 0:
        fp = fingerprint(rgb, "v", rt, pn)
        # single-view: use FULL vocabulary (no layout-invariant filter; it's degenerate at 1 view)
        j = J(tfp, fp, all_preds); substr = 1 - j
    else:
        substr = 0; j = 1.0
    return photo + alpha*substr, photo, substr, j


def train(tf, trgb, tfp, init, rt, pn, image_size, all_preds, alpha,
          n_iters=6, eps=0.05, lr=2.0):
    pp = np.array(init, dtype=np.float64); h = []
    t0,p0,s0,J0 = loss(pp, tf, trgb, tfp, rt, pn, image_size, all_preds, alpha)
    h.append((0, pp.tolist(), float(np.linalg.norm(pp)), t0, p0, s0, J0))
    print(f"  it0 d={float(np.linalg.norm(pp)):.3f} ph={p0:.4f} J={J0:.3f}")
    for it in range(1, n_iters+1):
        g = np.zeros(3)
        for i in range(3):
            a = pp.copy(); a[i] += eps; b = pp.copy(); b[i] -= eps
            ta,*_ = loss(a, tf, trgb, tfp, rt, pn, image_size, all_preds, alpha)
            tb,*_ = loss(b, tf, trgb, tfp, rt, pn, image_size, all_preds, alpha)
            g[i] = (ta-tb)/(2*eps)
        pp = pp - lr*g
        ti,pi,si,ji = loss(pp, tf, trgb, tfp, rt, pn, image_size, all_preds, alpha)
        h.append((it, pp.tolist(), float(np.linalg.norm(pp)), ti, pi, si, ji))
        print(f"  it{it} d={float(np.linalg.norm(pp)):.3f} ph={pi:.4f} J={ji:.3f}")
    return h


# Args: image_size,alpha[,alpha,...]
image_size = int(sys.argv[1])
ALPHAS_THIS_RUN = [float(a) for a in sys.argv[2].split(',')]
print(f"image_size={image_size}, alphas={ALPHAS_THIS_RUN}")

cube = make_phoxel_cube(side=0.6, density=10)
sphere = make_phoxel_sphere(radius=0.45, density=18)
tf = combine(cube, sphere, offsets=[(-0.9,0,0),(0.9,0,0)])
print(f"target: {tf['n']} phoxels (single view az=0)")
vision_ops.register_all(); rt = Runtime()
text = (ROOT/"data/vision/vocab.aurex").read_text()
for ppx in dsl.parse_source(text):
    if ppx.ok:
        try: P.type_check(ppx.pred); rt.install(ppx.pred)
        except Exception: pass
pn = rt.installed()
trgb = render(tf, image_size)
tfp = fingerprint(trgb, "t", rt, pn)
init = (1.0, 0.5, 0.0); d0 = float(np.linalg.norm(init))

results_file = OUT / f"results_size{image_size}.json"
prev = {}
if results_file.exists():
    prev = json.loads(results_file.read_text())

for alpha in ALPHAS_THIS_RUN:
    print(f"\n=== alpha={alpha} (size={image_size}) ===")
    h = train(tf, trgb, tfp, init, rt, pn, image_size, pn, alpha, n_iters=6)
    f = h[-1]
    prev[str(alpha)] = {
        "alpha": alpha, "history": h, "final_distance": f[2],
        "final_photo": f[4], "final_J": f[6],
        "redux_pct": 100*(d0-f[2])/d0,
    }
    results_file.write_text(json.dumps(prev, indent=2))

print(f"\n=== current results (size={image_size}, single view) ===")
for k in sorted(prev, key=float):
    r = prev[k]
    print(f"  alpha={r['alpha']}: dist={r['final_distance']:.3f} J={r['final_J']:.3f} redux={r['redux_pct']:.1f}%")
