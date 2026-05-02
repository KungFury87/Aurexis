"""R158 - extend corpus from N=226 to N≈426 by adding 200 fresh picsum + re-run IR."""
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

DESK = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved')
R55 = DESK / 'round55_corpus_harness/corpus_images'
R85 = DESK / 'round85_corpus_growth/images_diverse'
R111 = Path('/tmp/round111_pull')
R158 = Path('/tmp/round158_pull')
FP_DIR = Path('/tmp/r111_fps')
NEW_FP_DIR = Path('/tmp/r158_fps'); NEW_FP_DIR.mkdir(exist_ok=True)

vision_ops.register_all()
text = (ROOT/'data'/'vision'/'vocab.aurex').read_text()
runtime = Runtime()
for pp in dsl.parse_source(text):
    if pp.ok:
        try: P.type_check(pp.pred); runtime.install(pp.pred)
        except: pass
pred_names = runtime.installed()
print(f"vocab: {len(pred_names)} predicates")

# Compute fingerprints for new R158 images, save to NEW_FP_DIR
budget = 35
tic = time.time()
new = 0; existing = 0
new_files = sorted(R158.glob('*.jpg'))
print(f"R158 source: {len(new_files)} jpgs")
for path in new_files:
    fp_path = NEW_FP_DIR / f'{path.stem}.json'
    if fp_path.exists():
        existing += 1; continue
    if time.time() - tic > budget: break
    try:
        rgb = np.asarray(Image.open(path).convert('RGB'))
        if rgb.ndim != 3 or rgb.shape[-1] != 3: continue
        img = Image.fromarray(rgb); img.thumbnail((320, 320), Image.LANCZOS)
        rgb = np.asarray(img)
        luma = (0.299*rgb[...,0]+0.587*rgb[...,1]+0.114*rgb[...,2]).astype(np.float64)/255.0
        color = rgb.astype(np.float64)/255.0
        bundle, _ = _bundle_from_single(luma, path.stem, patch_size=64, color=color)
        row = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
                for pn in pred_names for rec in [runtime.evaluate(pn, bundle)]}
        fp_path.write_text(json.dumps(row))
        new += 1
    except Exception as e:
        pass

n_new_total = sum(1 for _ in NEW_FP_DIR.glob('*.json'))
print(f"new fingerprints: {new}, existing R158 cache: {existing}, total R158: {n_new_total}")
