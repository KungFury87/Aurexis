import warnings; warnings.filterwarnings('ignore')
import json, sys, time
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.visual_intake import _bundle_from_single

R55 = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/round55_corpus_harness/corpus_images')
R85 = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/round85_corpus_growth/images_diverse')
PULL = Path('/tmp/round111_pull')
FP_DIR = Path('/tmp/r111_fps'); FP_DIR.mkdir(exist_ok=True)

corpus = []
for d in [R55, R85]:
    for f in sorted(d.glob('*.npy')): corpus.append(('npy', f.stem, str(f)))
for f in sorted(PULL.glob('*.jpg')): corpus.append(('jpg', f.stem, str(f)))

vision_ops.register_all()
text = (ROOT/'data'/'vision'/'vocab.aurex').read_text()
runtime = Runtime()
for pp in dsl.parse_source(text):
    if pp.ok:
        try: P.type_check(pp.pred); runtime.install(pp.pred)
        except: pass
pred_names = runtime.installed()

budget = 35
tic = time.time()
done = 0; new = 0
for kind, name, path in corpus:
    fp_path = FP_DIR / f'{name}.json'
    if fp_path.exists():
        done += 1; continue
    if time.time() - tic > budget: break
    try:
        rgb = np.load(path) if kind == 'npy' else np.asarray(Image.open(path).convert('RGB'))
        if rgb.ndim != 3 or rgb.shape[-1] != 3: continue
        img = Image.fromarray(rgb); img.thumbnail((320, 320), Image.LANCZOS)
        rgb = np.asarray(img)
        luma = (0.299*rgb[...,0]+0.587*rgb[...,1]+0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, name, patch_size=64, color=color)
        row = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
                for pn in pred_names for rec in [runtime.evaluate(pn, bundle)]}
        fp_path.write_text(json.dumps(row))
        new += 1
    except: pass

print(f'cached {done}, new {new}, total {sum(1 for _ in FP_DIR.glob("*.json"))} / {len(corpus)}')
