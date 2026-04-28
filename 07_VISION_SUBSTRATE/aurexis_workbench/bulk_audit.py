"""Bulk corpus audit.

Points the full Phoxelis Vision Vocabulary at a folder of images
and produces:
  - CSV with one row per image, one column per predicate
  - Markdown summary: per-predicate firing rates, notable photos,
    narrator outputs for each
  - Per-photo narration paragraph

Usage:
    python -m aurexis_workbench.bulk_audit <FOLDER> [--out report.md]
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Dict, List

from . import dsl, vision_ops, predicates as P, runtime as RT
from .visual_intake import bundle_from_path, IMAGE_EXTS
from .narrator import narrate

VOCAB_PATH = (Path(__file__).resolve().parent.parent
                / "data" / "vision" / "vocab.aurex")


def install_vocab(rt: RT.Runtime):
    vision_ops.register_all()
    parsed = dsl.parse_source(VOCAB_PATH.read_text())
    preds = []
    for pp in parsed:
        if not pp.ok:
            continue
        try:
            P.type_check(pp.pred)
            rt.install(pp.pred)
            preds.append(pp.pred)
        except Exception:
            pass
    return preds


def audit_folder(folder: str | Path,
                  out_md: str | Path,
                  out_csv: str | Path | None = None) -> Dict:
    folder = Path(folder)
    files = sorted([f for f in folder.iterdir()
                     if f.suffix.lower() in IMAGE_EXTS])
    if not files:
        print(f"no images in {folder}")
        return {"folder": str(folder), "n_images": 0}
    rt = RT.Runtime()
    preds = install_vocab(rt)
    print(f"loaded {len(preds)} predicates")
    print(f"auditing {len(files)} images...")

    rows: List[Dict] = []
    narratives: Dict[str, str] = {}
    for i, f in enumerate(files):
        t0 = time.time()
        try:
            bundle, _ = bundle_from_path(f)
        except Exception as e:
            print(f"  [{i+1}/{len(files)}] FAIL load: {f.name} ({e})")
            continue
        if "row_y" not in bundle.fields:
            bundle.add_value("row_y", "int", 128, "default row")
        verdicts = {}
        for pred in preds:
            rec = rt.evaluate(pred.name, bundle)
            verdicts[pred.name] = (
                "" if rec.error else ("T" if rec.value else "F"))
        narrative = narrate(bundle)
        narratives[f.name] = narrative
        verdicts["__file"] = f.name
        rows.append(verdicts)
        elapsed = time.time() - t0
        print(f"  [{i+1}/{len(files)}] {f.name}  ({elapsed:.2f}s)")

    # Per-predicate firing rate
    pred_names = [p.name for p in preds]
    fired = {n: 0 for n in pred_names}
    n_total = {n: 0 for n in pred_names}
    for row in rows:
        for n in pred_names:
            v = row.get(n, "")
            if v == "T":
                fired[n] += 1; n_total[n] += 1
            elif v == "F":
                n_total[n] += 1

    rates = {n: (fired[n] / n_total[n] if n_total[n] else None)
              for n in pred_names}

    # Write CSV
    if out_csv:
        out_csv = Path(out_csv)
        with out_csv.open("w", newline="", encoding="utf-8") as fh:
            cols = ["__file"] + pred_names
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in cols})
        print(f"wrote CSV: {out_csv}")

    # Write markdown report
    L = []
    L.append(f"# Phoxelis Vision Language - Bulk Audit Report")
    L.append("")
    L.append(f"**Folder:** `{folder}`  ")
    L.append(f"**Images:** {len(rows)} / {len(files)} loaded successfully  ")
    L.append(f"**Vocabulary:** {len(preds)} predicates from "
              f"`{VOCAB_PATH.name}`  ")
    L.append("")
    L.append("## Per-predicate firing rate")
    L.append("")
    L.append("| predicate | rate | fired |")
    L.append("|---|---|---|")
    for n in sorted(pred_names, key=lambda nm: -(rates.get(nm) or -1)):
        r = rates.get(n)
        rs = f"{r:.0%}" if r is not None else "-"
        fs = f"{fired[n]} / {n_total[n]}"
        L.append(f"| `{n}` | {rs} | {fs} |")
    L.append("")

    L.append("## Narrator output per image")
    L.append("")
    for f in files:
        nv = narratives.get(f.name, "(narration failed)")
        L.append(f"### `{f.name}`")
        L.append("")
        L.append(nv)
        L.append("")

    # Notable findings: predicates that fire on small subsets of photos
    L.append("## Notable findings (predicates firing on 5-50% of photos)")
    L.append("")
    interesting = []
    for n in pred_names:
        r = rates.get(n)
        if r is None:
            continue
        if 0.05 <= r <= 0.50:
            interesting.append((n, r))
    interesting.sort(key=lambda x: x[1])
    for n, r in interesting:
        # Find which files fired this predicate
        firing_files = [row["__file"] for row in rows
                         if row.get(n) == "T"]
        L.append(f"- **`{n}`** ({r:.0%} = {len(firing_files)} photos): "
                  + ", ".join(f"`{f}`" for f in firing_files[:6])
                  + (" ..." if len(firing_files) > 6 else ""))
    L.append("")
    out_md = Path(out_md)
    out_md.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote markdown report: {out_md}")
    return {
        "folder": str(folder),
        "n_images_loaded": len(rows),
        "n_images_total": len(files),
        "n_predicates": len(preds),
        "rates": rates,
    }


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python -m aurexis_workbench.bulk_audit <FOLDER> "
                "[--out report.md] [--csv report.csv]")
        return 1
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", default="audit_report.md")
    ap.add_argument("--csv", default="audit_report.csv")
    args = ap.parse_args(argv)
    audit_folder(args.folder, args.out, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
