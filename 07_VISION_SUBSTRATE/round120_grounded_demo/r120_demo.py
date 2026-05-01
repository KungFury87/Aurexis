"""R120 — pick 10 representative images, fingerprint each via MCP server,
write the fingerprints + image-source-types to disk for the LLM to read."""
import warnings; warnings.filterwarnings('ignore')
import json, sys, subprocess, time
from pathlib import Path

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/'
            'Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
SERVER = ROOT / 't6_mcp' / 'mcp_server.py'
OUT = Path('/tmp/round120_grounded_demo'); OUT.mkdir(exist_ok=True)

# 10 representative images covering different content types
R55 = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/round55_corpus_harness/corpus_images')
R85 = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/round85_corpus_growth/images_diverse')
PULL = Path('/tmp/round111_pull')

# Curated to cover diverse content; the LLM will NOT see image content
SAMPLES = [
    ('inat_335031177', R55 / 'inat_335031177.npy', 'iNaturalist nature photo'),
    ('met_437287', R55 / 'met_437287.npy', 'MET artwork'),
    ('osm_5_15_21', R55 / 'osm_5_15_21.npy', 'OpenStreetMap raster tile'),
    ('histo_14-0855-F1.jpg', R85 / 'histo_14-0855-F1.jpg.npy', 'histopathology slide'),
    ('paintings_first', None, 'painting'),  # filled below
    ('microscopy_first', None, 'microscopy'),
    ('sat_first', None, 'satellite imagery'),
    ('diagrams_first', None, 'diagram'),
    ('picsum_a', PULL / 'picsum_r111_0001.jpg', 'random natural photo'),
    ('picsum_b', PULL / 'picsum_r111_0030.jpg', 'random natural photo'),
]
# Fill in source-type representatives
def first_npy(d, prefix):
    for f in sorted(d.glob(f'{prefix}*.npy')): return f
for i, (label, path, src_type) in enumerate(SAMPLES):
    if path is None:
        prefix = label.split('_first')[0]
        SAMPLES[i] = (label, first_npy(R85, prefix), src_type)

# Spawn MCP server, send tools/call evaluate_image for each
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

results = {}
for i, (label, path, src_type) in enumerate(SAMPLES):
    if path is None or not path.exists():
        print(f'SKIP {label}: no file')
        continue
    r = call({'jsonrpc':'2.0', 'id':i+1, 'method':'tools/call',
              'params':{'name':'phoxelis_evaluate_image',
                        'arguments':{'image_path':str(path)}}})
    body = json.loads(r['result']['content'][0]['text']) if 'result' in r else {}
    fp = body.get('fingerprint', {})
    fired = sorted([k for k, v in fp.items() if v is True])
    results[label] = {
        'source_type_label': src_type,
        'n_fired': body.get('n_fired'),
        'n_evaluated': body.get('n_evaluated'),
        'fired_predicates': fired,
    }
    print(f'{label}: {len(fired)} fired')

proc.stdin.close()
try: proc.wait(timeout=5)
except: proc.kill()

(OUT/'fingerprints.json').write_text(json.dumps(results, indent=2))
print(f'\nwrote {OUT}/fingerprints.json — {len(results)} images')
