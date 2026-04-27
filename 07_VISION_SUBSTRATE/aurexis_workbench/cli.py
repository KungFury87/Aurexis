"""Workbench CLI entry point.

    python -m aurexis_workbench.cli                  # default IR run
    python -m aurexis_workbench.cli --vocab VOCAB    # named vocab
    python -m aurexis_workbench.cli --report REPORTS # output dir
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import scenarios as S
from . import vocabulary as V
from . import independence as I
from .starter import build_starter_vocabulary, build_runtime_tasks


HERE = Path(__file__).resolve().parent.parent


def write_independence_reports(out_dir: Path, summary: dict) -> None:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "independence_ratio.json", "w",
               encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=lambda v:
                    None if isinstance(v, float) and v != v else v)

    L = []
    L.append("# Aurexis Workbench v2.0 - Independence Ratio")
    L.append("")
    L.append("Vocabulary: `" + str(summary.get("vocabulary")) + "`")
    L.append("Predicates installed: "
              + str(summary.get("predicate_count")))
    L.append("Runtime tasks: " + str(summary.get("task_count")))
    L.append("")
    L.append("- ANSWERED:           " + str(summary.get("answered")))
    L.append("- COVERED_BUT_WRONG:  " + str(summary.get("covered_but_wrong")))
    L.append("- UNCOVERED:          " + str(summary.get("uncovered")))
    L.append("")
    ir = summary.get("independence_ratio")
    if isinstance(ir, float) and ir == ir:
        L.append("**Independence Ratio: {:.2f}**".format(ir))
    else:
        L.append("**Independence Ratio: n/a**")
    L.append("")
    L.append("## Per-task results")
    L.append("")
    L.append("| scenario | goal_key | status | predicate | expected | actual | error |")
    L.append("|---|---|---|---|---|---|---|")
    for r in summary.get("results", []):
        L.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            r.get("scenario"), r.get("goal_key"),
            r.get("status"),
            r.get("predicate") or "-",
            r.get("expected"),
            r.get("actual") if r.get("actual") is not None else "-",
            r.get("error") or ""))
    L.append("")
    (out_dir / "INDEPENDENCE_RATIO.md").write_text(
        "\n".join(L), encoding="utf-8")


def write_vocabulary_report(out_dir: Path,
                              vocab: V.Vocabulary) -> None:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    L = []
    L.append("# Aurexis Workbench v2.0 - Vocabulary")
    L.append("")
    L.append("Vocabulary: `" + vocab.name + "`")
    L.append("Predicates: " + str(len(vocab.items)))
    L.append("")
    L.append("| name | intent | return_type | expects |")
    L.append("|---|---|---|---|")
    for nm in vocab.list_names():
        p = vocab.items[nm]
        ex = ", ".join(k + ":" + v for k, v in p.expects.items())
        L.append("| " + nm
                  + " | " + (p.intent or "-")
                  + " | " + str(p.return_type)
                  + " | " + (ex or "-") + " |")
    L.append("")
    (out_dir / "VOCABULARY.md").write_text("\n".join(L),
                                             encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", default=None,
                     help="Path to a saved vocabulary JSON. If omitted, the starter vocabulary is used.")
    ap.add_argument("--report", default=str(HERE / "reports"),
                     help="Where to write the IR + vocabulary reports.")
    args = ap.parse_args()

    if args.vocab:
        vocab = V.Vocabulary.load(args.vocab)
    else:
        vocab = build_starter_vocabulary()

    bundles = S.build_all()
    bundle_by_name = {b.name: b for b in bundles}
    tasks = build_runtime_tasks()

    summary = I.run_independence(vocab, tasks, bundle_by_name)
    out_dir = Path(args.report)
    write_independence_reports(out_dir, summary)
    write_vocabulary_report(out_dir, vocab)
    # Also save a serialized vocabulary so the run is reproducible
    vocab.save(out_dir / "vocabulary.json")

    print("Aurexis Workbench v2.0 - IR run complete")
    print("  vocabulary:        " + vocab.name)
    print("  predicate count:   " + str(len(vocab.items)))
    print("  tasks:             " + str(summary["task_count"]))
    print("  answered:          " + str(summary["answered"]))
    print("  covered_but_wrong: " + str(summary["covered_but_wrong"]))
    print("  uncovered:         " + str(summary["uncovered"]))
    ir = summary["independence_ratio"]
    if isinstance(ir, float) and ir == ir:
        print("  IR:                {:.2f}".format(ir))
    print("Reports written to " + str(out_dir))
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
