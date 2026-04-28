"""Phoxelis capture-stability benchmark (Plan B from Round 28).

Takes a folder of N captures of the same scene, runs the full vocabulary
on each, and reports per-predicate stability — the fraction of captures
where each predicate's verdict matches its modal (most common) verdict
across the set. A perfectly stable predicate scores 1.0 (always agrees
with itself across captures); a coin-flip predicate scores 0.5.

This is the headline benchmark for the structural claim that Phoxelis's
predicates ride on perceptual structure that survives capture noise.
The expected result is that high-level perceptual predicates (indoor
scene, color dominance, scene type) score near 1.0 while pixel-fragile
ones (motion direction, exact blob counts) score lower. Predicates that
score below ~0.6 are noise-dominated and should either be retired or
have their thresholds widened.

Usage:
    python phoxelis_capture_stability.py /path/to/folder
    python phoxelis_capture_stability.py ~/scene_kitchen --label "kitchen-table"

Folder must contain >= 5 image files (.jpg / .jpeg / .png / .heic).
Captures should all be of the SAME scene under varied conditions
(different angles, distances, exposure, time-of-day) to test the
predicate's robustness.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
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

vision_ops.register_all()


def _luma(arr):
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def load_bundle(path: Path, resize_to: int = 320) -> FieldBundle:
    img = Image.open(path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64) / 255.0
    long_side = max(arr.shape[0], arr.shape[1])
    if long_side > resize_to:
        step = max(1, long_side // resize_to)
        arr = arr[::step, ::step]
    color = arr[..., :3]
    luma = _luma(color)
    burst = luma[None, ...]
    b = FieldBundle(name=path.stem)
    b.add_value("scene", "image", luma, description="luma")
    b.add_value("color_scene", "color_image", color, description="rgb")
    b.add_value("burst", "image_stack", burst, description="single-frame")
    b.add_value("patch_size", "int", 64, description="ROI side")
    b.add_value("row_y", "int", luma.shape[0] // 2,
                  description="autocorr row")
    return b


def load_vocab():
    text = (WB / "data" / "vision" / "vocab.aurex").read_text(encoding="utf-8")
    parsed = dsl.parse_source(text)
    preds = []
    for pp in parsed:
        if not pp.ok:
            continue
        try:
            P.type_check(pp.pred)
            preds.append(pp.pred)
        except Exception:
            continue
    return preds


def run(folder: Path, resize_to: int):
    images = sorted([p for p in folder.iterdir()
                       if p.suffix.lower() in (".jpg", ".jpeg",
                                                  ".png", ".bmp", ".tiff")])
    if len(images) < 5:
        raise ValueError(
            f"Need >= 5 captures of the same scene; got {len(images)} "
            f"in {folder}.")

    preds = load_vocab()
    print(f"Loaded {len(preds)} predicates")
    print(f"Auditing {len(images)} captures from {folder.name}/")

    rt = RT.Runtime()
    for p in preds:
        rt.install(p)

    truth = {p.name: [] for p in preds}
    blocked = {p.name: 0 for p in preds}
    captures: list[str] = []
    t0 = time.time()
    for i, path in enumerate(images):
        bundle = load_bundle(path, resize_to=resize_to)
        captures.append(path.stem)
        for pred in preds:
            rec = rt.evaluate(pred.name, bundle)
            if rec.error:
                truth[pred.name].append(None)
                blocked[pred.name] += 1
            else:
                v = rec.value
                truth[pred.name].append(
                    bool(v) if isinstance(v, (bool, int)) else None)
        if (i + 1) % 5 == 0:
            print(f"  {i+1} / {len(images)} captures audited")
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s")

    stability: dict[str, float] = {}
    modal: dict[str, bool | None] = {}
    minority_count: dict[str, int] = {}
    for pname, row in truth.items():
        valid = [v for v in row if v is not None]
        if not valid:
            stability[pname] = float("nan")
            modal[pname] = None
            minority_count[pname] = 0
            continue
        counts = Counter(valid)
        mode_val, mode_count = counts.most_common(1)[0]
        stability[pname] = mode_count / len(valid)
        modal[pname] = mode_val
        minority_count[pname] = len(valid) - mode_count

    return {
        "folder": str(folder),
        "label": folder.name,
        "n_captures": len(images),
        "n_predicates": len(preds),
        "elapsed_s": elapsed,
        "captures": captures,
        "truth": truth,
        "blocked": blocked,
        "stability": stability,
        "modal": modal,
        "minority_count": minority_count,
    }


def write_report(res, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    n = res["n_captures"]
    label = res["label"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    valid_stab = [s for s in res["stability"].values()
                    if not (s != s)]  # filter NaN
    if valid_stab:
        mean_s = sum(valid_stab) / len(valid_stab)
    else:
        mean_s = 0.0

    rock_solid = [(p, s) for p, s in res["stability"].items() if s == 1.0]
    high       = [(p, s) for p, s in res["stability"].items()
                    if 0.85 <= s < 1.0]
    medium     = [(p, s) for p, s in res["stability"].items()
                    if 0.65 <= s < 0.85]
    fragile    = [(p, s) for p, s in res["stability"].items()
                    if not (s != s) and s < 0.65]

    lines = []
    lines.append("=" * 80)
    lines.append(f"PHOXELIS CAPTURE-STABILITY BENCHMARK — {ts}")
    lines.append(f"scene label: {label}")
    lines.append(f"captures: {n}")
    lines.append(f"vocabulary: {res['n_predicates']} predicates "
                    f"({res['elapsed_s']:.1f}s total)")
    lines.append(f"mean stability across vocabulary: {mean_s:.3f}")
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"ROCK-SOLID (stability == 1.0): {len(rock_solid)}")
    for p, s in sorted(rock_solid):
        lines.append(f"  {p:<48} 1.000  modal={res['modal'][p]}")
    lines.append("")

    lines.append(f"HIGH (0.85 <= stability < 1.0): {len(high)}")
    for p, s in sorted(high, key=lambda kv: -kv[1]):
        lines.append(f"  {p:<48} {s:.3f}  modal={res['modal'][p]}  "
                        f"minority={res['minority_count'][p]}/{n}")
    lines.append("")

    lines.append(f"MEDIUM (0.65 <= stability < 0.85): {len(medium)}")
    for p, s in sorted(medium, key=lambda kv: -kv[1]):
        lines.append(f"  {p:<48} {s:.3f}  modal={res['modal'][p]}  "
                        f"minority={res['minority_count'][p]}/{n}")
    lines.append("")

    lines.append(f"FRAGILE (stability < 0.65 — flapping): {len(fragile)}")
    for p, s in sorted(fragile, key=lambda kv: kv[1]):
        lines.append(f"  {p:<48} {s:.3f}  modal={res['modal'][p]}  "
                        f"minority={res['minority_count'][p]}/{n}")
    lines.append("")

    lines.append("HEADLINE")
    lines.append(f"  rock-solid rate: "
                    f"{len(rock_solid) / max(res['n_predicates'], 1):.3f}")
    lines.append(f"  rock-solid + high rate: "
                    f"{(len(rock_solid)+len(high)) / max(res['n_predicates'], 1):.3f}")
    lines.append(f"  fragile rate:    "
                    f"{len(fragile) / max(res['n_predicates'], 1):.3f}")
    lines.append("")
    lines.append("End of report.")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder of same-scene captures")
    ap.add_argument("--label", default="",
                      help="scene label (default: folder name)")
    ap.add_argument("--resize", type=int, default=320,
                      help="resize long side to this (default 320)")
    ap.add_argument("--out", default="",
                      help="output report path "
                           "(default: timestamped under "
                           "07_VISION_SUBSTRATE/reports/)")
    args = ap.parse_args(argv)

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"ERROR: {folder} is not a directory")
        return 2

    res = run(folder, resize_to=args.resize)
    if args.label:
        res["label"] = args.label

    if args.out:
        out = Path(args.out)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out = CORE / "reports" / f"CAPTURE_STABILITY_{res['label']}_{ts}.md"
    write_report(res, out)

    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps({
        "label": res["label"],
        "n_captures": res["n_captures"],
        "n_predicates": res["n_predicates"],
        "elapsed_s": res["elapsed_s"],
        "stability": res["stability"],
        "modal": {k: (None if v is None else bool(v))
                    for k, v in res["modal"].items()},
        "minority_count": res["minority_count"],
        "captures": res["captures"],
    }, indent=2), encoding="utf-8")
    print(f"Wrote {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
