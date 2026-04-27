"""Authoring-loop CLI.

    python -m aurexis_workbench.cli_intake \
        --intake data/candidates.aurex --report reports/

Reads a candidate intake file, parses + type-checks each block,
runs the IR runner before and after extending the baseline
vocabulary with the accepted candidates, and writes:

  reports/AUTHORING_DOSSIER.md
  reports/authoring_dossier.json
  reports/IR_BEFORE_AFTER.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import intake as IN
from . import vocabulary as V


HERE = Path(__file__).resolve().parent.parent


def _ir_md_block(title: str, summary: dict) -> str:
    L = ["### " + title, ""]
    L.append("Vocabulary: `" + str(summary.get("vocabulary")) + "`")
    L.append("Predicate count: " + str(summary.get("predicate_count")))
    L.append("Tasks: " + str(summary.get("task_count")))
    L.append("- ANSWERED: " + str(summary.get("answered")))
    L.append("- COVERED_BUT_WRONG: "
              + str(summary.get("covered_but_wrong")))
    L.append("- UNCOVERED: " + str(summary.get("uncovered")))
    ir = summary.get("independence_ratio")
    if isinstance(ir, float) and ir == ir:
        L.append("- **IR: {:.2f}**".format(ir))
    else:
        L.append("- **IR: n/a**")
    L.append("")
    return "\n".join(L)


def write_authoring_reports(out_dir: Path, dossier: dict) -> None:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    safe = json.loads(json.dumps(dossier, default=lambda v:
                                    None if isinstance(v, float) and v != v
                                    else v))
    (out_dir / "authoring_dossier.json").write_text(
        json.dumps(safe, indent=2), encoding="utf-8")

    L = ["# Aurexis Workbench v2.1 - Authoring dossier", ""]
    L.append("Intake file: `" + str(dossier.get("intake_path")) + "`")
    L.append("")
    L.append("Candidates parsed: " + str(dossier.get("candidate_count")))
    L.append("Accepted: " + str(len(dossier.get("accepted", []))))
    L.append("Rejected: " + str(len(dossier.get("rejected", []))))
    L.append("")
    L.append("## Accepted candidates")
    L.append("")
    if dossier.get("accepted"):
        L.append("| name | return_type | intent |")
        L.append("|---|---|---|")
        for a in dossier["accepted"]:
            L.append("| " + a["name"]
                      + " | " + str(a.get("return_type"))
                      + " | " + str(a.get("intent")) + " |")
    else:
        L.append("(none)")
    L.append("")
    L.append("## Rejected candidates")
    L.append("")
    if dossier.get("rejected"):
        for r in dossier["rejected"]:
            L.append("- **" + r["name"] + "**")
            for d in r["diagnostics"]:
                L.append("  - " + d)
    else:
        L.append("(none)")
    L.append("")
    L.append("## Independence Ratio — before vs after")
    L.append("")
    L.append(_ir_md_block("Before intake", dossier["ir_before"]))
    L.append(_ir_md_block("After intake",  dossier["ir_after"]))
    delta = dossier.get("ir_delta", {})
    L.append("### Delta")
    L.append("")
    L.append("- ANSWERED:   "
              + str(delta.get("answered_before")) + " -> "
              + str(delta.get("answered_after"))
              + "  (delta " + str(delta.get("answered_delta")) + ")")
    L.append("- UNCOVERED:  "
              + str(delta.get("uncovered_before")) + " -> "
              + str(delta.get("uncovered_after"))
              + "  (delta " + str(delta.get("uncovered_delta")) + ")")
    db = delta.get("ir_before"); da = delta.get("ir_after"); dd = delta.get("ir_delta")
    fb = "n/a" if not (isinstance(db, float) and db == db) else "{:.2f}".format(db)
    fa = "n/a" if not (isinstance(da, float) and da == da) else "{:.2f}".format(da)
    fd = "n/a" if not (isinstance(dd, float) and dd == dd) else "{:+.2f}".format(dd)
    L.append("- **IR: " + fb + " -> " + fa + " (" + fd + ")**")
    L.append("")
    L.append("## Per-task transitions (before -> after)")
    L.append("")
    if dossier.get("transitions"):
        L.append("| scenario | goal_key | before | after |")
        L.append("|---|---|---|---|")
        for t in dossier["transitions"]:
            L.append("| " + t["scenario"]
                      + " | " + t["goal_key"]
                      + " | " + t["before"]
                      + " | " + t["after"] + " |")
    else:
        L.append("(no transitions)")
    L.append("")
    (out_dir / "AUTHORING_DOSSIER.md").write_text(
        "\n".join(L), encoding="utf-8")

    # IR_BEFORE_AFTER.md (compact view)
    M = ["# Aurexis Workbench v2.1 - IR before vs after intake", ""]
    M.append(_ir_md_block("Before", dossier["ir_before"]))
    M.append(_ir_md_block("After",  dossier["ir_after"]))
    M.append("- IR delta: " + fd)
    (out_dir / "IR_BEFORE_AFTER.md").write_text(
        "\n".join(M), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake", default=str(HERE / "data" / "candidates.aurex"),
                     help="Path to a candidate intake file (.aurex).")
    ap.add_argument("--report", default=str(HERE / "reports"),
                     help="Where to write the authoring dossier.")
    args = ap.parse_args()

    dossier = IN.build_intake_dossier(args.intake)
    write_authoring_reports(Path(args.report), dossier)

    print("Aurexis Workbench v2.1 - authoring loop complete")
    print("  intake:    " + args.intake)
    print("  parsed:    " + str(dossier["candidate_count"]))
    print("  accepted:  " + str(len(dossier["accepted"])))
    print("  rejected:  " + str(len(dossier["rejected"])))
    delta = dossier["ir_delta"]
    db = delta.get("ir_before"); da = delta.get("ir_after"); dd = delta.get("ir_delta")
    fb = "n/a" if not (isinstance(db, float) and db == db) else "{:.2f}".format(db)
    fa = "n/a" if not (isinstance(da, float) and da == da) else "{:.2f}".format(da)
    fd = "n/a" if not (isinstance(dd, float) and dd == dd) else "{:+.2f}".format(dd)
    print("  IR: " + fb + " -> " + fa + " (" + fd + ")")
    print("Reports: " + args.report)
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
