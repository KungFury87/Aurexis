"""Vision CLI: parse the vision vocabulary, run it against every
.aurex-session zip under a given root, print verdicts as a table.

Usage:
    python -m aurexis_workbench.cli_vision [SEARCH_ROOT]

Default SEARCH_ROOT is the parent of this project.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import dsl, vision_ops, predicates as P
from . import runtime as RT
from .vision_bridge import find_sessions, load_session_bundle


DEFAULT_VOCAB = Path(__file__).resolve().parent.parent / "data" / "vision" / "vocab.aurex"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("search_root", nargs="?",
                     default=str(Path(__file__).resolve().parent.parent.parent))
    ap.add_argument("--vocab", default=str(DEFAULT_VOCAB))
    ap.add_argument("--max-frames", type=int, default=10)
    ap.add_argument("--resize-to", type=int, default=256)
    args = ap.parse_args(argv)

    vision_ops.register_all()
    text = Path(args.vocab).read_text()
    parsed = dsl.parse_source(text)
    preds = []
    for pp in parsed:
        if not pp.ok:
            print(f"REJECT {pp.name}: " + "; ".join(d.render()
                                                       for d in pp.diagnostics))
            continue
        try:
            P.type_check(pp.pred)
            preds.append(pp.pred)
        except Exception as e:
            print(f"TYPE ERROR {pp.name}: {e}")
    print(f"loaded {len(preds)} vision predicates from {args.vocab}")
    print()

    rt = RT.Runtime()
    for pred in preds:
        rt.install(pred)

    sessions = find_sessions(args.search_root)
    if not sessions:
        print(f"no .aurex-session.zip files under {args.search_root}")
        return 1
    pred_names = [p.name for p in preds]
    col_w = max(len(n) for n in pred_names) + 2

    for sp in sessions:
        # Polarization-pair sessions need both axes loaded; default
        # max-frames=10 only catches the first axis. Auto-bump.
        peek_max = args.max_frames
        try:
            import zipfile, json
            with zipfile.ZipFile(sp, "r") as zf:
                m_name = next((n for n in zf.namelist()
                                  if n.endswith("manifest.json")), None)
                if m_name:
                    pm = json.loads(zf.read(m_name).decode("utf-8"))
                    if pm.get("protocolId") == "polarization_pair":
                        peek_max = max(peek_max, len(pm.get("frames", [])))
        except Exception:
            pass
        bundle, meta = load_session_bundle(sp,
                                             max_frames=peek_max,
                                             resize_to=args.resize_to)
        # Default row_y so row-based predicates can run on sessions too
        if "row_y" not in bundle.fields:
            bundle.add_value("row_y", "int", 64,
                              description="default row index for autocorr predicates")
        print(f"--- {sp.name}")
        print(f"    protocol={meta.protocol_id} lux={meta.light_lux_median} fields={sorted(bundle.names())}")
        for pred in preds:
            rec = rt.evaluate(pred.name, bundle)
            if rec.error:
                msg = "BLOCKED"
            else:
                msg = repr(rec.value)
            print(f"    {pred.name:<{col_w}} {msg}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
