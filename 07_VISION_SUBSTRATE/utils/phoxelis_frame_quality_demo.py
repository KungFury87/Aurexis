"""Phoxelis frame-quality gate demo (Round 30).

Scores a folder of images via the Round 30 frame-quality gate and
emits a quality-ranked report. Useful both for proving the gate
works and for empirically choosing the threshold that separates
good frames from bad ones.

Usage:
    python phoxelis_frame_quality_demo.py /path/to/folder
    python phoxelis_frame_quality_demo.py "Phone photos"
    python phoxelis_frame_quality_demo.py --threshold 0.5 /path/to/folder

Output: a markdown report at workspace root + per-image breakdown
including which predicates failed for the rejected frames. The
fragile-by-quality list is the actionable subset for tuning.

Designed to be the empirical step before porting the gate to
JavaScript and inlining it in aurexis_ed_v2_unified.html as a
pre-fusion frame filter (the YELLOW item from the Donald handoff,
"blind averaging bakes in errors from bad frames").
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WB   = ROOT / "Aurexis_Workbench_v2_0"
CORE = ROOT / "Aurexis_Core_WORKING_20260414-1339" / "07_VISION_SUBSTRATE"

sys.path.insert(0, str(WB))
from aurexis_workbench.frame_quality import (        # noqa: E402
    score_bundle, bundle_from_image_path, COMPONENTS)


def run(folder: Path, resize_to: int = 320, threshold: float = 0.5):
    images = sorted([p for p in folder.iterdir()
                       if p.suffix.lower() in (".jpg", ".jpeg", ".png",
                                                  ".bmp", ".tiff")])
    if not images:
        raise ValueError(f"No images in {folder}")

    print(f"Scoring {len(images)} images from {folder.name}/  "
            f"(threshold={threshold})")
    results = []
    t0 = time.time()
    for i, p in enumerate(images):
        bundle = bundle_from_image_path(p, resize_to=resize_to)
        q = score_bundle(bundle)
        results.append({
            "path": p.name,
            "score": q.score,
            "passes": q.score >= threshold,
            "passed": list(q.passed_components),
            "failed": list(q.failed_components),
            "blocked": list(q.blocked_components),
        })
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{len(images)} scored "
                    f"({time.time() - t0:.1f}s)")
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s  ({elapsed/len(images):.2f}s/image)")
    return results, elapsed


def report(results, elapsed: float, label: str, threshold: float, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    n = len(results)
    n_pass = sum(1 for r in results if r["passes"])
    n_fail = n - n_pass
    mean_score = sum(r["score"] for r in results) / n
    rock_solid = [r for r in results if r["score"] == 1.0]
    good       = [r for r in results if 0.7 <= r["score"] < 1.0]
    marginal   = [r for r in results if 0.4 <= r["score"] < 0.7]
    reject     = [r for r in results if r["score"] < 0.4]

    # Failed-component breakdown across all frames
    fail_counts: dict[str, int] = {c["predicate"]: 0 for c in COMPONENTS}
    for r in results:
        for f in r["failed"]:
            fail_counts[f] = fail_counts.get(f, 0) + 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("=" * 80)
    lines.append(f"PHOXELIS FRAME-QUALITY GATE — {ts}")
    lines.append(f"folder: {label}  ({n} images)  threshold={threshold}")
    lines.append(f"elapsed: {elapsed:.1f}s ({elapsed/n:.2f}s/image)")
    lines.append(f"mean score: {mean_score:.3f}  "
                    f"pass: {n_pass}/{n} ({n_pass/n:.1%})  "
                    f"fail: {n_fail}/{n}")
    lines.append("=" * 80)
    lines.append("")

    lines.append("BUCKETS")
    lines.append(f"  rock-solid (1.000): {len(rock_solid):>3}")
    lines.append(f"  good (0.7-1.0):     {len(good):>3}")
    lines.append(f"  marginal (0.4-0.7): {len(marginal):>3}")
    lines.append(f"  reject (<0.4):      {len(reject):>3}")
    lines.append("")

    lines.append("FAILURE BREAKDOWN (predicate -> count of frames that failed it)")
    for pname, count in sorted(fail_counts.items(), key=lambda kv: -kv[1]):
        if count > 0:
            lines.append(f"  {pname:<40} {count:>3}")
    if not any(fail_counts.values()):
        lines.append("  (no failures)")
    lines.append("")

    lines.append("SORTED BY SCORE (best -> worst)")
    for r in sorted(results, key=lambda x: -x["score"]):
        flags = ""
        if r["failed"]:
            flags = "  fails: " + ", ".join(r["failed"])
        lines.append(f"  {r['score']:.3f}  {r['path']:<48}{flags}")
    lines.append("")

    lines.append("REJECT BUCKET DETAILS")
    if not reject:
        lines.append("  (none rejected)")
    for r in reject:
        lines.append(f"  {r['path']}  (score {r['score']:.3f})")
        for fn in r["failed"]:
            lines.append(f"      FAIL: {fn}")
    lines.append("")
    lines.append("End of report.")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="folder of images to score")
    ap.add_argument("--threshold", type=float, default=0.5,
                      help="quality threshold; frames at or above pass")
    ap.add_argument("--resize", type=int, default=320,
                      help="resize long side to this before scoring")
    ap.add_argument("--out", default="",
                      help="output report path (default: timestamped under "
                           "07_VISION_SUBSTRATE/reports/)")
    args = ap.parse_args(argv)

    folder = Path(args.folder)
    if not folder.is_absolute():
        folder = ROOT / args.folder
    if not folder.is_dir():
        print(f"ERROR: {folder} is not a directory")
        return 2

    results, elapsed = run(folder, resize_to=args.resize,
                              threshold=args.threshold)
    label = folder.name

    if args.out:
        out = Path(args.out)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out = CORE / "reports" / f"FRAME_QUALITY_{label}_{ts}.md"

    report(results, elapsed, label, args.threshold, out)

    json_out = out.with_suffix(".json")
    json_out.write_text(json.dumps({
        "label": label,
        "threshold": args.threshold,
        "elapsed_s": elapsed,
        "n_images": len(results),
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"Wrote {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
