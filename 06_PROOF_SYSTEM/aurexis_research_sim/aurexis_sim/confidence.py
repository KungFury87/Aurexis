"""Calibration / confidence-state evaluator (v0.6).

Combines per-family evidence into a calibrated confidence state.
This module answers a single Engine-semantics question per primitive
family:

    "Given everything the suite has tested, what is our calibrated
     confidence state for this primitive family?"

States:

    TRUST                  Strong evidence the primitive works:
                           PRIMITIVE_AWARE_HELPS at family level AND
                           validation says EARNED_ROBUST.
    HOLD                   Passes but with limited evidence:
                           generic-fusion sufficient OR primitive-aware
                           helps but validation only WEAK_ROBUST.
    DOWNGRADE              Passes only under tight conditions:
                           PROPOSAL_QUALITY_LIMIT or
                           ROI/proposal pressure.
    REJECT                 Fails strongly:
                           PRIMITIVE_AWARE_STILL_FAILS or validation
                           says NOT_ROBUST / SUSPECT.
    NEED_MORE_EVIDENCE     Inputs incomplete:
                           METRIC_GAP_ROI_INSENSITIVE; metric is not
                           ROI-aware; arbitration test not possible
                           AND no validation result available.

Inputs come from:
  - aurexis_sim.unlock.build_unlock_dossier() (boundary tag per family)
  - aurexis_sim.validation.validate_promoted_primitives() (validation
    verdict per primitive)

Honest scope:
  - The combinator is a small deterministic table, not a learned
    classifier.
  - For families with no boundary entry (truly unmapped), the state
    is NEED_MORE_EVIDENCE.
  - For families whose boundary tag is NOT in the well-known set,
    the state is also NEED_MORE_EVIDENCE.
  - This module produces confidence STATES, not confidence numbers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


CONFIDENCE_STATES = ["TRUST", "HOLD", "DOWNGRADE", "REJECT",
                      "NEED_MORE_EVIDENCE"]


def confidence_state(boundary_tag: Optional[str],
                      validation_verdict: Optional[str]) -> str:
    """Combine per-family boundary tag + validation verdict into a
    calibrated confidence state."""
    if boundary_tag is None:
        return "NEED_MORE_EVIDENCE"

    # Strong reject
    if boundary_tag == "PRIMITIVE_AWARE_STILL_FAILS":
        return "REJECT"
    if validation_verdict in ("NOT_ROBUST", "SUSPECT"):
        return "REJECT"

    # Strong trust: arbitration helps + validation strongly endorses
    if boundary_tag == "PRIMITIVE_AWARE_HELPS":
        if validation_verdict == "EARNED_ROBUST":
            return "TRUST"
        if validation_verdict in ("WEAK_ROBUST",):
            return "HOLD"
        # No validation entry: hold pending more evidence
        return "HOLD"

    if boundary_tag == "GENERIC_FUSION_SUFFICIENT":
        if validation_verdict == "EARNED_ROBUST":
            return "TRUST"
        return "HOLD"

    if boundary_tag == "PROPOSAL_QUALITY_LIMIT":
        return "DOWNGRADE"

    if boundary_tag == "METRIC_GAP_ROI_INSENSITIVE":
        if validation_verdict == "EARNED_ROBUST":
            return "HOLD"
        return "NEED_MORE_EVIDENCE"

    if boundary_tag == "ARBITRATION_INVARIANT":
        if validation_verdict == "EARNED_ROBUST":
            return "TRUST"
        return "HOLD"

    return "NEED_MORE_EVIDENCE"


def build_confidence_dossier() -> dict:
    """Run the boundary + validation evidence and produce per-family
    confidence states."""
    from .unlock import build_unlock_dossier
    from .validation import validate_promoted_primitives

    boundary = build_unlock_dossier()
    try:
        validation = validate_promoted_primitives()
    except Exception:
        validation = {"per_primitive": {}}

    family_states: Dict[str, dict] = {}
    boundary_map = boundary.get("family_boundary_map", {})
    val_per = validation.get("per_primitive", {})

    for fam, rec in boundary_map.items():
        boundary_tag = rec.get("boundary_tag")
        val_v = None
        if fam in val_per:
            val_v = val_per[fam].get("verdict")
        state = confidence_state(boundary_tag, val_v)
        family_states[fam] = {
            "boundary_tag":      boundary_tag,
            "validation_verdict": val_v,
            "confidence_state":  state,
        }

    # Also include any validation-only families not in boundary map
    for fam, rec in val_per.items():
        if fam in family_states:
            continue
        family_states[fam] = {
            "boundary_tag":       None,
            "validation_verdict": rec.get("verdict"),
            "confidence_state":
                confidence_state(None, rec.get("verdict")),
        }

    return {
        "schema_version": "0.6",
        "states": CONFIDENCE_STATES,
        "family_states": family_states,
    }


def write_confidence_reports(out_dir: Path,
                              dossier: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    dossier = dossier or build_confidence_dossier()

    with open(out_dir / "confidence.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v0.6 - Calibration / confidence dossier")
    L.append("")
    L.append("Per-family calibrated confidence state combining boundary tag")
    L.append("(from unlock dossier) and validation verdict (from v0.8 validation).")
    L.append("")
    L.append("States: " + ", ".join("`" + s + "`" for s in CONFIDENCE_STATES))
    L.append("")
    L.append("## Family confidence states")
    L.append("")
    L.append("| family | boundary_tag | validation_verdict | confidence_state |")
    L.append("|---|---|---|---|")
    for fam, rec in dossier["family_states"].items():
        L.append("| " + fam
                 + " | " + str(rec.get("boundary_tag") or "-")
                 + " | " + str(rec.get("validation_verdict") or "-")
                 + " | **" + rec["confidence_state"] + "** |")
    L.append("")

    with open(out_dir / "CONFIDENCE.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return dossier


def main():
    dossier = build_confidence_dossier()
    write_confidence_reports(Path.cwd(), dossier)
    print("Aurexis Research Sim v0.6 - Confidence dossier")
    print("")
    for fam, rec in dossier["family_states"].items():
        print("  {:<14} boundary={:<28} validation={:<14} -> {}".format(
            fam,
            str(rec.get("boundary_tag") or "-"),
            str(rec.get("validation_verdict") or "-"),
            rec["confidence_state"]))
    print("")
    print("Wrote confidence.json and CONFIDENCE.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
