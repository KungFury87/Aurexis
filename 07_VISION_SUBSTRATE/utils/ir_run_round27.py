"""IR runner — Round 27.

Runs the Phoxelis vision vocabulary against:
  * the synthetic corpus (vision/synthetic/*.png + synthetic_bursts/*)
  * the real phone-photo corpus (~/Desktop/Aurexis evolved/Phone photos)
  * any .aurex-session.zip dropped under the workspace root

Emits IR_RUN_2026-04-28_round27.md into 07_VISION_SUBSTRATE/reports/
with: per-predicate firing rate, always-False / always-True lists,
empirical equivalence classes, and Round 26 verification numbers.

Designed to run on Vincent's Windows side (where the source files
are intact and the Python module cache works correctly), not the
analysis sandbox (which has mount-staleness issues).
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
WB   = ROOT / "Aurexis_Workbench_v2_0"
CORE = ROOT / "Aurexis_Core_WORKING_20260414-1339" / "07_VISION_SUBSTRATE"

sys.path.insert(0, str(WB))
from aurexis_workbench import dsl, vision_ops, predicates as P
from aurexis_workbench import runtime as RT
from aurexis_workbench.fields import FieldBundle
from aurexis_workbench.vision_bridge import find_sessions, load_session_bundle

vision_ops.register_all()


# ---- corpus loading --------------------------------------------------

def _rgb_to_luma(arr):
    return 0.299*arr[..., 0] + 0.587*arr[..., 1] + 0.114*arr[..., 2]


def load_image_bundle(path: Path, name: str) -> FieldBundle:
    img = Image.open(path); img.load()
    arr = np.asarray(img, dtype=np.float64) / 255.0
    if arr.ndim == 2:
        color = np.stack([arr, arr, arr], axis=-1)
        luma = arr
    else:
        color = arr[..., :3]
        luma = _rgb_to_luma(color)
    # Downsample big images for speed
    long_side = max(luma.shape[0], luma.shape[1])
    if long_side > 320:
        step = max(1, long_side // 320)
        luma = luma[::step, ::step]
        color = color[::step, ::step]
    burst = luma[None, ...]
    bundle = FieldBundle(name=name)
    bundle.add_value("scene", "image", luma, description="luminance")
    bundle.add_value("color_scene", "color_image", color, description="RGB")
    bundle.add_value("burst", "image_stack", burst, description="single-frame")
    bundle.add_value("patch_size", "int", 64, description="ROI side")
    bundle.add_value("row_y", "int", luma.shape[0] // 2,
                       description="default autocorr row")
    return bundle


def collect_corpus():
    bundles = {}

    syn = WB / "data" / "vision" / "synthetic"
    if syn.exists():
        for p in sorted(syn.glob("*.png")):
            bundles[f"syn:{p.stem}"] = load_image_bundle(p, p.stem)

    syn_b = WB / "data" / "vision" / "synthetic_bursts"
    if syn_b.exists():
        for d in sorted([d for d in syn_b.iterdir() if d.is_dir()]):
            frames = sorted(d.glob("*.png"))
            if not frames: continue
            stack = []
            color = None
            for fp in frames[:8]:
                img = Image.open(fp); img.load()
                a = np.asarray(img, dtype=np.float64) / 255.0
                if a.ndim == 3:
                    if color is None:
                        color = a[..., :3]
                    a = _rgb_to_luma(a[..., :3])
                stack.append(a)
            h_min = min(s.shape[0] for s in stack)
            w_min = min(s.shape[1] for s in stack)
            stack = [s[:h_min, :w_min] for s in stack]
            burst = np.stack(stack, axis=0)
            scene = burst[len(burst) // 2]
            if color is None:
                color = np.stack([scene, scene, scene], axis=-1)
            else:
                color = color[:h_min, :w_min]
            bundle = FieldBundle(name=d.name)
            bundle.add_value("scene", "image", scene, description="mid-frame luma")
            bundle.add_value("color_scene", "color_image", color, description="RGB")
            bundle.add_value("burst", "image_stack", burst, description="burst")
            bundle.add_value("patch_size", "int", 64, description="ROI")
            bundle.add_value("row_y", "int", scene.shape[0] // 2,
                              description="autocorr row")
            bundles[f"synb:{d.name}"] = bundle

    photos = ROOT / "Phone photos"
    if photos.exists():
        for p in sorted(photos.glob("*.jpg")):
            bundles[f"real:{p.stem}"] = load_image_bundle(p, p.stem)

    for sp in find_sessions(ROOT):
        try:
            with zipfile.ZipFile(sp, "r") as zf:
                m_name = next((n for n in zf.namelist()
                                  if n.endswith("manifest.json")), None)
                pm = json.loads(zf.read(m_name).decode("utf-8")) if m_name else {}
            max_frames = (len(pm.get("frames", []))
                            if pm.get("protocolId") == "polarization_pair"
                            else 10)
            bundle, _ = load_session_bundle(sp, max_frames=max_frames,
                                              resize_to=256)
            if "row_y" not in bundle.fields:
                bundle.add_value("row_y", "int", 64, description="row")
            bundles[f"sess:{sp.stem}"] = bundle
        except Exception as e:
            print(f"  skipped {sp.name}: {e}", file=sys.stderr)

    return bundles


# ---- vocabulary load -------------------------------------------------

def load_vocab():
    vocab_path = WB / "data" / "vision" / "vocab.aurex"
    text = vocab_path.read_text(encoding="utf-8")
    parsed = dsl.parse_source(text)
    preds, rejected = [], []
    for pp in parsed:
        if not pp.ok:
            rejected.append((pp.name, "; ".join(d.render() for d in pp.diagnostics)))
            continue
        try:
            P.type_check(pp.pred)
            preds.append(pp.pred)
        except Exception as e:
            rejected.append((pp.name, f"TYPE_ERROR: {e}"))
    return preds, rejected


# ---- IR analysis -----------------------------------------------------

def run_ir():
    preds, rejected = load_vocab()
    print(f"Loaded {len(preds)} predicates, rejected {len(rejected)}")
    bundles = collect_corpus()
    print(f"Loaded {len(bundles)} bundles in corpus")

    rt = RT.Runtime()
    for pred in preds:
        rt.install(pred)

    truth_table = {}
    blocked    = {p.name: 0 for p in preds}
    for pname in [p.name for p in preds]:
        truth_table[pname] = []

    bundle_order = list(bundles.keys())
    for bname in bundle_order:
        bundle = bundles[bname]
        for pred in preds:
            rec = rt.evaluate(pred.name, bundle)
            if rec.error:
                truth_table[pred.name].append(None)
                blocked[pred.name] += 1
            else:
                v = rec.value
                truth_table[pred.name].append(bool(v) if isinstance(v, (bool, int)) else None)

    rates = {}
    for pname in truth_table:
        vals = [v for v in truth_table[pname] if v is not None]
        rates[pname] = (sum(vals) / len(vals)) if vals else None

    always_false = [p for p, r in rates.items() if r == 0.0 and blocked[p] < len(bundle_order)]
    always_true  = [p for p, r in rates.items() if r == 1.0]
    fully_blocked = [p for p, b in blocked.items() if b == len(bundle_order)]

    sigs = defaultdict(list)
    for pname, row in truth_table.items():
        if pname in fully_blocked: continue
        sig = tuple(row)
        sigs[sig].append(pname)
    eq_classes = [g for g in sigs.values() if len(g) > 1]

    return {
        "n_preds": len(preds),
        "n_bundles": len(bundle_order),
        "rejected": rejected,
        "rates": rates,
        "blocked": blocked,
        "always_false": always_false,
        "always_true": always_true,
        "fully_blocked": fully_blocked,
        "eq_classes": eq_classes,
        "bundle_order": bundle_order,
        "truth_table": truth_table,
    }


# ---- report ---------------------------------------------------------

def write_report(res):
    out = CORE / "reports" / "IR_RUN_2026-04-28_round27.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("=" * 80)
    lines.append(f"VOCAB IR ANALYSIS round 27 ({res['n_preds']} predicates, "
                    "post-Round-26 narrow-band hue ratios)")
    lines.append(f"corpus: {res['n_bundles']} inputs, "
                    f"vocabulary: {res['n_preds']} predicates")
    lines.append("=" * 80)
    lines.append("")

    lines.append("FIRING RATES (all):")
    for pname, rate in res["rates"].items():
        if pname in res["fully_blocked"]:
            lines.append(f"  {pname:<45}   -    n=0/{res['n_bundles']}")
        else:
            n = res["n_bundles"] - res["blocked"][pname]
            r_str = f"{rate:.2f}" if rate is not None else " - "
            lines.append(f"  {pname:<45} {r_str}   n={n}/{res['n_bundles']}")
    lines.append("")

    lines.append(f"ALWAYS-FALSE PREDICATES: {len(res['always_false'])}")
    for p in res["always_false"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"ALWAYS-TRUE PREDICATES (saturated): {len(res['always_true'])}")
    for p in res["always_true"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"FULLY-BLOCKED PREDICATES (no scene supplies their fields): "
                    f"{len(res['fully_blocked'])}")
    for p in res["fully_blocked"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"EQUIVALENCE CLASSES: {len(res['eq_classes'])}")
    for i, group in enumerate(res["eq_classes"]):
        lines.append(f"  class {i+1}: {' = '.join(group)}")
    lines.append("")

    if res["rejected"]:
        lines.append(f"REJECTED PREDICATES: {len(res['rejected'])}")
        for n, why in res["rejected"]:
            lines.append(f"  {n}: {why}")
        lines.append("")

    lines.append("ROUND 26 VERIFICATION:")
    for new in ("has_vegetation_signature",
                  "has_skin_tone_signature",
                  "has_warm_color_temperature",
                  "has_cool_color_temperature"):
        if new in res["rates"]:
            r = res["rates"][new]
            r_str = f"{r:.2f}" if r is not None else " - "
            n = res["n_bundles"] - res["blocked"][new]
            lines.append(f"  {new:<45} {r_str}   n={n}/{res['n_bundles']}")
        else:
            lines.append(f"  {new:<45}  NOT_LOADED")
    lines.append("")
    lines.append("End of report.")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {out}")
    return out


if __name__ == "__main__":
    res = run_ir()
    print(f"\n=== Headline ===")
    print(f"  predicates evaluated:    {res['n_preds']}")
    print(f"  corpus size:             {res['n_bundles']}")
    print(f"  always-False predicates: {len(res['always_false'])}")
    print(f"  always-True predicates:  {len(res['always_true'])}")
    print(f"  fully-blocked:           {len(res['fully_blocked'])}")
    print(f"  equivalence classes:    {len(res['eq_classes'])}")
    write_report(res)
