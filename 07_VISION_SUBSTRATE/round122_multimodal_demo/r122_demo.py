"""R122 — multi-modal grounded demo. Synthesize 5 scenes with paired
RGB + depth + hyperspectral, pass all three to MCP server's
phoxelis_evaluate_image, verify R107 cross-modal predicates fire."""
import warnings; warnings.filterwarnings('ignore')
import json, sys, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image

OUT = Path('/tmp/round122_multimodal_demo'); OUT.mkdir(exist_ok=True)
SCENES_DIR = OUT / 'scenes'; SCENES_DIR.mkdir(exist_ok=True)

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
SERVER = ROOT / 't6_mcp' / 'mcp_server.py'

# Reuse R107 spectral profiles
H = W = 160
N_BANDS = 31
WAVELENGTHS = np.linspace(400, 700, N_BANDS)
RNG = np.random.default_rng(122)


def gauss(c, w):
    g = np.exp(-((WAVELENGTHS - c)**2) / (2*w**2)); return g/g.max()


def chlorophyll_spectrum():
    s = np.full(N_BANDS, 0.15)
    s += 0.25 * gauss(550, 30)
    s -= 0.10 * gauss(670, 20)
    s[WAVELENGTHS > 680] = 0.55
    return np.clip(s, 0, 1)

def green_narrow_spectrum():
    return np.clip(np.full(N_BANDS, 0.10) + 0.55*gauss(540, 20), 0, 1)

def red_narrow_spectrum():
    return np.clip(np.full(N_BANDS, 0.08) + 0.65*gauss(640, 25), 0, 1)

def warm_broad_spectrum():
    return np.clip(0.10 + 0.50 * (WAVELENGTHS - 400) / 300, 0, 1)

def flat_broad_spectrum():
    return np.clip(np.full(N_BANDS, 0.45) + RNG.normal(0, 0.02, N_BANDS), 0, 1)


def depth_far():
    d = np.full((H, W), 0.85, dtype=np.float64)
    d[100:140, 60:100] = 0.7
    return d + RNG.normal(0, 0.005, d.shape)

def depth_close():
    d = np.full((H, W), 0.6, dtype=np.float64)
    d[40:130, 30:120] = 0.20
    return d + RNG.normal(0, 0.005, d.shape)

def depth_uniform():
    return np.full((H, W), 0.6, dtype=np.float64) + RNG.normal(0, 0.005, (H, W))


# Render an RGB approximation from a hyperspectral cube
RED_SENS   = gauss(610, 35)
GREEN_SENS = gauss(540, 35)
BLUE_SENS  = gauss(450, 35)
RGB_BASIS  = np.stack([RED_SENS, GREEN_SENS, BLUE_SENS], axis=0)

def render_rgb(cube):
    flat = cube.reshape(-1, N_BANDS) @ RGB_BASIS.T
    rgb = flat.reshape(H, W, 3)
    rgb = rgb / max(rgb.max(), 1e-6)
    return (rgb * 255).clip(0, 255).astype(np.uint8)

def make_cube(spec_fn):
    cube = np.full((H, W, N_BANDS), 0.05)
    cube[16:144, 16:144] = spec_fn()[None, None, :]
    return np.clip(cube + RNG.normal(0, 0.01, cube.shape), 0, 1)


SCENES = [
    ('vegetation_far',  depth_far,     chlorophyll_spectrum,  'far field with chlorophyll spectrum'),
    ('red_close',       depth_close,   red_narrow_spectrum,   'close subject with narrow red peak'),
    ('green_close',     depth_close,   green_narrow_spectrum, 'close subject with narrow green peak'),
    ('dusk_far',        depth_far,     warm_broad_spectrum,   'far field with broad warm (incandescent) spectrum'),
    ('flat_wall',       depth_uniform, flat_broad_spectrum,   'uniform depth with flat broad spectrum'),
]

# Build files for each scene
for name, df, sf, desc in SCENES:
    cube = make_cube(sf); depth = df()
    rgb = render_rgb(cube)
    Image.fromarray(rgb).save(SCENES_DIR / f'{name}_rgb.png')
    np.save(SCENES_DIR / f'{name}_depth.npy', depth)
    np.save(SCENES_DIR / f'{name}_spectral.npy', cube)
    print(f'built {name}: rgb {rgb.shape} depth {depth.shape} cube {cube.shape}  ({desc})')

# Spawn MCP server, evaluate each scene with all 3 paths
proc = subprocess.Popen(
    [sys.executable, str(SERVER)],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1
)
time.sleep(2.5)

def call(req):
    proc.stdin.write(json.dumps(req) + '\n'); proc.stdin.flush()
    return json.loads(proc.stdout.readline())

call({'jsonrpc':'2.0', 'id':0, 'method':'initialize', 'params':{}})

R107_PREDS = ['has_far_field_dominance', 'has_narrow_spectral_peak',
              'is_distant_vegetation', 'is_close_chromatic_object',
              'is_uniform_lit_far_field']

results = {}
for i, (name, _, _, desc) in enumerate(SCENES):
    args = {
        'image_path':    str(SCENES_DIR / f'{name}_rgb.png'),
        'depth_path':    str(SCENES_DIR / f'{name}_depth.npy'),
        'spectral_path': str(SCENES_DIR / f'{name}_spectral.npy'),
    }
    r = call({'jsonrpc':'2.0', 'id':i+1, 'method':'tools/call',
              'params':{'name':'phoxelis_evaluate_image', 'arguments':args}})
    body = json.loads(r['result']['content'][0]['text']) if 'result' in r else {}
    fp = body.get('fingerprint', {})
    fired = sorted([k for k, v in fp.items() if v is True])
    r107_verdicts = {p: fp.get(p) for p in R107_PREDS}
    results[name] = {
        'design_description': desc,
        'n_fired': body.get('n_fired'),
        'n_evaluated': body.get('n_evaluated'),
        'n_abstained': body.get('n_abstained'),
        'r107_cross_modal_verdicts': r107_verdicts,
        'fired_predicates': fired,
    }

proc.stdin.close()
try: proc.wait(timeout=5)
except: proc.kill()

(OUT/'fingerprints.json').write_text(json.dumps(results, indent=2))
print('\n=== R107 cross-modal predicate firing across 5 multi-modal scenes ===')
print(f'{"scene":18s}  {"far_field":10s} {"narrow_peak":12s} {"distant_veg":12s} {"close_chrom":12s} {"uniform_lit":12s}')
for name, r in results.items():
    v = r['r107_cross_modal_verdicts']
    def fmt(x): return 'FIRE' if x is True else ('-' if x is False else 'abstain')
    print(f'{name:18s}  {fmt(v["has_far_field_dominance"]):10s} {fmt(v["has_narrow_spectral_peak"]):12s} {fmt(v["is_distant_vegetation"]):12s} {fmt(v["is_close_chromatic_object"]):12s} {fmt(v["is_uniform_lit_far_field"]):12s}')

print(f'\nwrote {OUT}/fingerprints.json')
