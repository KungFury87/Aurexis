"""Phoxelis corpus audit at scale (Plan A from Round 28).

Pulls N images per source from the live source router, runs the full
vocabulary on each, and emits a structured IR report. The headline
output is the curve of how the firing-rate / equivalence-class /
always-False statistics scale as the corpus grows from 57 (the prior
local set) to 1000+ heterogeneous real-world images.

Designed to run on the user's Windows machine where the file system
is intact. Output lands in 07_VISION_SUBSTRATE/reports/.

Usage (defaults to a moderate run):
    python phoxelis_corpus_audit.py
    python phoxelis_corpus_audit.py --per-source 50 --resize 320
    python phoxelis_corpus_audit.py --stages stage_0_synthetic,stage_1_easy

The runner is checkpoint-friendly: it writes intermediate results
every 25 images so a long batch can be killed and resumed (the
URL dedup file already carries the fetched-set forward).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
WB   = ROOT / "Aurexis_Workbench_v2_0"
CORE = ROOT / "Aurexis_Core_WORKING_20260414-1339" / "07_VISION_SUBSTRATE"

sys.path.insert(0, str(WB))
from aurexis_workbench import dsl, vision_ops, predicates as P  # noqa: E402
from aurexis_workbench import runtime as RT                       # noqa: E402
from aurexis_workbench.fields import FieldBundle                  # noqa: E402
from aurexis_workbench.eval_split import assign_split             # noqa: E402
from aurexis_workbench import sources as SRC                      # noqa: E402

vision_ops.register_all()


# ---- bundle from PIL ---------------------------------------------------

def _luma(arr):
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def pil_to_bundle(img: Image.Image, name: str, resize_to: int = 320
                    ) -> FieldBundle:
    arr = np.asarray(img.convert("RGB"), dtype=np.float64) / 255.0
    long_side = max(arr.shape[0], arr.shape[1])
    if long_side > resize_to:
        step = max(1, long_side // resize_to)
        arr = arr[::step, ::step]
    color = arr[..., :3]
    luma = _luma(color)
    burst = luma[None, ...]
    b = FieldBundle(name=name)
    b.add_value("scene", "image", luma, description="luma")
    b.add_value("color_scene", "color_image", color, description="rgb")
    b.add_value("burst", "image_stack", burst, description="single-frame")
    b.add_value("patch_size", "int", 64, description="ROI side")
    b.add_value("row_y", "int", luma.shape[0] // 2,
                  description="autocorr row")
    return b


# ---- vocabulary --------------------------------------------------------

def load_vocab():
    text = (WB / "data" / "vision" / "vocab.aurex").read_text(encoding="utf-8")
    parsed = dsl.parse_source(text)
    preds = []
    rejected = []
    for pp in parsed:
        if not pp.ok:
            rejected.append((pp.name, "; ".join(d.render()
                                                  for d in pp.diagnostics)))
            continue
        try:
            P.type_check(pp.pred)
            preds.append(pp.pred)
        except Exception as e:
            rejected.append((pp.name, f"TYPE_ERROR: {e}"))
    return preds, rejected


# ---- runner ------------------------------------------------------------

def run(per_source: int, resize_to: int, stages: list[str] | None,
          archive_dir: Path):
    preds, rejected = load_vocab()
    print(f"Loaded {len(preds)} predicates, rejected {len(rejected)}")
    rt = RT.Runtime()
    for p in preds:
        rt.install(p)

    archive_dir.mkdir(parents=True, exist_ok=True)
    SRC.init_dedup(archive_dir)

    truth_table: dict[str, list] = {p.name: [] for p in preds}
    blocked = {p.name: 0 for p in preds}
    sources_seen = Counter()
    splits = Counter()
    aliases: list[str] = []

    t0 = time.time()
    n_done = 0
    for stage_name, lst in SRC.SOURCES.items():
        if stages and stage_name not in stages:
            continue
        for label, fn in lst:
            print(f"\n[{stage_name}] {label}")
            try:
                for img, alias, src in fn(per_source):
                    bundle = pil_to_bundle(img, alias, resize_to=resize_to)
                    for pred in preds:
                        rec = rt.evaluate(pred.name, bundle)
                        if rec.error:
                            truth_table[pred.name].append(None)
                            blocked[pred.name] += 1
                        else:
                            v = rec.value
                            truth_table[pred.name].append(
                                bool(v) if isinstance(v, (bool, int)) else None)
                    aliases.append(alias)
                    sources_seen[src] += 1
                    splits[assign_split(alias)] += 1
                    n_done += 1
                    if n_done % 25 == 0:
                        print(f"    {n_done} images audited "
                              f"({time.time() - t0:.1f}s elapsed)")
                        SRC.flush_dedup()
            except Exception as e:
                print(f"    {label} crashed: {type(e).__name__}: {e}")

    SRC.flush_dedup()
    elapsed = time.time() - t0
    print(f"\n--- {n_done} images audited in {elapsed:.1f}s "
            f"({elapsed/max(n_done,1):.2f}s / image) ---")

    return {
        "n_images": n_done,
        "elapsed_s": elapsed,
        "preds": [p.name for p in preds],
        "rejected": rejected,
        "truth_table": truth_table,
        "blocked": blocked,
        "sources_seen": dict(sources_seen),
        "splits": dict(splits),
        "aliases": aliases,
    }


# ---- analysis ----------------------------------------------------------

def analyse(res):
    n = res["n_images"]
    rates = {}
    for pname, row in res["truth_table"].items():
        vals = [v for v in row if v is not None]
        rates[pname] = (sum(vals) / len(vals)) if vals else None

    fully_blocked = [p for p, b in res["blocked"].items() if b == n]
    always_false = [p for p, r in rates.items()
                      if r == 0.0 and p not in fully_blocked]
    always_true  = [p for p, r in rates.items() if r == 1.0]

    sigs = defaultdict(list)
    for pname, row in res["truth_table"].items():
        if pname in fully_blocked:
            continue
        sigs[tuple(row)].append(pname)
    eq_classes = [g for g in sigs.values() if len(g) > 1]

    return {
        "rates": rates,
        "fully_blocked": fully_blocked,
        "always_false": always_false,
        "always_true": always_true,
        "eq_classes": eq_classes,
    }


# ---- report ------------------------------------------------------------

def write_report(res, ana, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    n = res["n_images"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("=" * 80)
    lines.append(f"PHOXELIS CORPUS AUDIT AT SCALE — {ts}")
    lines.append(f"corpus: {n} images from "
                    f"{len(res['sources_seen'])} live sources")
    lines.append(f"vocabulary: {len(res['preds'])} predicates, "
                    f"{res['elapsed_s']:.1f}s total "
                    f"({res['elapsed_s']/max(n,1):.2f}s/image)")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"SOURCES SEEN ({len(res['sources_seen'])}):")
    for src, count in sorted(res['sources_seen'].items(),
                                key=lambda kv: -kv[1]):
        lines.append(f"  {src:<24} {count:>4}")
    lines.append("")

    lines.append(f"SPLIT DISTRIBUTION:")
    for split, count in res["splits"].items():
        lines.append(f"  {split:<8} {count}")
    lines.append("")

    lines.append("FIRING RATES (sorted descending):")
    sorted_rates = sorted(ana["rates"].items(),
                            key=lambda kv: (kv[1] if kv[1] is not None else -1),
                            reverse=True)
    for pname, rate in sorted_rates:
        if pname in ana["fully_blocked"]:
            lines.append(f"  {pname:<48}    -    n=0/{n}")
        else:
            cnt = n - res["blocked"][pname]
            r_str = f"{rate:.3f}" if rate is not None else " -- "
            lines.append(f"  {pname:<48} {r_str}   n={cnt}/{n}")
    lines.append("")

    lines.append(f"ALWAYS-FALSE PREDICATES: {len(ana['always_false'])}")
    for p in ana["always_false"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"ALWAYS-TRUE PREDICATES (saturated): "
                    f"{len(ana['always_true'])}")
    for p in ana["always_true"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"FULLY-BLOCKED PREDICATES: {len(ana['fully_blocked'])}")
    for p in ana["fully_blocked"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append(f"EQUIVALENCE CLASSES: {len(ana['eq_classes'])}")
    for i, group in enumerate(ana["eq_classes"]):
        lines.append(f"  class {i+1}: {' = '.join(group)}")
    lines.append("")

    if res["rejected"]:
        lines.append(f"REJECTED AT VOCAB LOAD: {len(res['rejected'])}")
        for nm, why in res["rejected"]:
            lines.append(f"  {nm}: {why}")
        lines.append("")

    lines.append(f"INDEPENDENCE RATIO HEADLINE")
    lines.append(f"  predicates fully blocked: {len(ana['fully_blocked'])}")
    lines.append(f"  predicates that did real work: "
                    f"{len(res['preds']) - len(ana['fully_blocked'])}")
    lines.append(f"  always-False rate: "
                    f"{len(ana['always_false']) / max(len(res['preds']), 1):.3f}")
    lines.append(f"  always-True rate:  "
                    f"{len(ana['always_true']) / max(len(res['preds']), 1):.3f}")
    lines.append(f"  EQ-class rate:     "
                    f"{len(ana['eq_classes']) / max(len(res['preds']), 1):.3f}")
    lines.append("")
    lines.append("End of report.")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


# ---- entrypoint --------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-source", type=int, default=20,
                      help="images to fetch per source (default 20)")
    ap.add_argument("--resize", type=int, default=320,
                      help="resize long side to this (default 320)")
    ap.add_argument("--stages", default="",
                      help="comma-separated stage names to include "
                           "(default: all)")
    ap.add_argument("--archive", default=str(ROOT / "_audit_archive"),
                      help="dedup archive dir")
    ap.add_argument("--out", default="",
                      help="output report path (default: timestamped under "
                           "07_VISION_SUBSTRATE/reports/)")
    args = ap.parse_args(argv)

    stages = [s.strip() for s in args.stages.split(",") if s.strip()] or None
    res = run(per_source=args.per_source, resize_to=args.resize,
                stages=stages, archive_dir=Path(args.archive))
    ana = analyse(res)

    if args.out:
        out = Path(args.out)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out = CORE / "reports" / f"IR_AT_SCALE_{ts}.md"
    write_report(res, ana, out)

    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps({
        "rates": ana["rates"],
        "fully_blocked": ana["fully_blocked"],
        "always_false": ana["always_false"],
        "always_true": ana["always_true"],
        "eq_classes": ana["eq_classes"],
        "sources_seen": res["sources_seen"],
        "n_images": res["n_images"],
        "elapsed_s": res["elapsed_s"],
        "splits": res["splits"],
    }, indent=2), encoding="utf-8")
    print(f"Wrote {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
