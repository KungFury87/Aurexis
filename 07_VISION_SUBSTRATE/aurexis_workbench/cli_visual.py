"""Generic visual CLI: run the vision vocabulary against ANY visual input.

Usage:
    python -m aurexis_workbench.cli_visual <PATH>
    python -m aurexis_workbench.cli_visual <PATH_axis_0> <PATH_axis_90>

Where PATH can be:
    a single image (jpg/png/bmp/tiff/webp/heic/...)
    a directory of images (treated as image_stack)
    a video file (mp4/mov/avi/...)
    two paths (treated as a polarization-pair: axis 0 and axis 90)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import dsl, vision_ops, predicates as P
from . import runtime as RT
from .visual_intake import bundle_from_path, bundle_from_pair


DEFAULT_VOCAB = Path(__file__).resolve().parent.parent / "data" / "vision" / "vocab.aurex"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+",
                     help="1 path (image/dir/video) or 2 paths (axis pair)")
    ap.add_argument("--vocab", default=str(DEFAULT_VOCAB))
    ap.add_argument("--max-frames", type=int, default=16)
    ap.add_argument("--resize-to", type=int, default=512)
    ap.add_argument("--row-y", type=int, default=128,
                     help="row index for repetition predicate")
    args = ap.parse_args(argv)

    vision_ops.register_all()
    text = Path(args.vocab).read_text()
    parsed = dsl.parse_source(text)
    preds = []
    for pp in parsed:
        if not pp.ok:
            continue
        try:
            P.type_check(pp.pred)
            preds.append(pp.pred)
        except Exception:
            pass
    print(f"loaded {len(preds)} predicates")

    rt = RT.Runtime()
    for pred in preds:
        rt.install(pred)

    if len(args.paths) == 2:
        bundle, meta = bundle_from_pair(args.paths[0], args.paths[1],
                                          resize_to=args.resize_to)
    else:
        bundle, meta = bundle_from_path(args.paths[0],
                                          max_frames=args.max_frames,
                                          resize_to=args.resize_to)
    if "row_y" not in bundle.fields:
        bundle.add_value("row_y", "int", int(args.row_y),
                          description="reference row for autocorr predicate")

    print(f"--- input: {meta.source}")
    print(f"    kind={meta.kind} n_frames={meta.n_frames} "
            f"resolution={meta.resolution}")
    print(f"    fields: {sorted(bundle.names())}")
    col_w = max(len(p.name) for p in preds) + 2
    for pred in preds:
        rec = rt.evaluate(pred.name, bundle)
        if rec.error:
            msg = "BLOCKED  (" + rec.error.split("required")[0].strip() + ")"
        else:
            msg = repr(rec.value)
        print(f"    {pred.name:<{col_w}} {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
