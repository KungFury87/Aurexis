"""Master Engine-semantics proof index (v0.6).

Aggregates the suite's evidence under the seven proof categories
defined in `proof_taxonomy`. Per category we list:
  - the question the category answers
  - the status (STRONG / PARTIAL / WEAK / STUB)
  - the shipped reports that contribute
  - per-family or per-primitive findings where applicable

Plus a master per-family table that combines:
  - boundary tag (from unlock dossier)
  - validation verdict (from v0.8 validation)
  - confidence state (from v0.6 confidence)
  - semantic-stability verdict where evaluated (cardinality, repetition)

This module does not generate brand-new evidence; it is the
top-level Engine-semantics index a reader sees first.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict

from .proof_taxonomy import (
    PROOF_CATEGORIES, CATEGORY_STATUS,
    REPORT_TO_CATEGORIES, category_index,
)
from .confidence import build_confidence_dossier
from .semantic_stability import build_semantic_stability_dossier


def build_proof_index(seed: int = 0) -> dict:
    cidx = category_index()
    confidence = build_confidence_dossier()
    try:
        semantic = build_semantic_stability_dossier(seed=seed)
    except Exception as e:
        semantic = {"per_primitive": {}, "_error": str(e)}

    # Master per-family table
    family_table: Dict[str, dict] = {}
    for fam, rec in confidence.get("family_states", {}).items():
        family_table[fam] = {
            "boundary_tag":        rec.get("boundary_tag"),
            "validation_verdict":  rec.get("validation_verdict"),
            "confidence_state":    rec.get("confidence_state"),
            "semantic_stability":  None,
        }
    for prim, rec in semantic.get("per_primitive", {}).items():
        if prim not in family_table:
            family_table[prim] = {
                "boundary_tag":        None,
                "validation_verdict":  None,
                "confidence_state":    None,
                "semantic_stability":  rec.get("verdict"),
            }
        else:
            family_table[prim]["semantic_stability"] = rec.get("verdict")

    return {
        "schema_version": "0.6",
        "categories":     PROOF_CATEGORIES,
        "category_status": CATEGORY_STATUS,
        "category_index": cidx,
        "family_table":   family_table,
        "confidence":     confidence,
        "semantic_stability": semantic,
    }


def write_proof_index_reports(out_dir: Path,
                                index: Optional[dict] = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    index = index or build_proof_index()

    # Cleaner json (drop the embedded sub-dossiers' duplicated bits if any)
    with open(out_dir / "proof_index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    L = []
    L.append("# Aurexis Engine-semantics proof index (v0.6)")
    L.append("")
    L.append("This is the top-level Engine-semantics index. The Aurexis")
    L.append("testing suite is an Engine-semantics proof system, not a")
    L.append("simulator product.")
    L.append("")
    L.append("It answers seven proof-category questions; below are status")
    L.append("tags + per-family evidence rolling up boundary tags, validation,")
    L.append("calibrated confidence states, and semantic-stability verdicts.")
    L.append("")
    L.append("## Proof-category status")
    L.append("")
    L.append("| category | status | question |")
    L.append("|---|---|---|")
    for cat, info in PROOF_CATEGORIES.items():
        st = CATEGORY_STATUS.get(cat, "?")
        L.append("| `" + cat + "` | **" + st + "** | "
                 + info["question"] + " |")
    L.append("")

    L.append("## Master per-family Engine-semantics table")
    L.append("")
    L.append("| family | boundary_tag | validation | confidence_state | semantic_stability |")
    L.append("|---|---|---|---|---|")
    for fam, rec in index["family_table"].items():
        L.append("| " + fam
                 + " | " + str(rec.get("boundary_tag") or "-")
                 + " | " + str(rec.get("validation_verdict") or "-")
                 + " | **" + str(rec.get("confidence_state") or "-") + "**"
                 + " | " + str(rec.get("semantic_stability") or "-")
                 + " |")
    L.append("")

    L.append("## Reports per category")
    L.append("")
    cidx = index["category_index"]
    for cat, info in PROOF_CATEGORIES.items():
        L.append("### " + cat + " (" + info["title"] + ")")
        L.append("")
        L.append("- status: **" + CATEGORY_STATUS.get(cat, "?") + "**")
        L.append("- question: _" + info["question"] + "_")
        rs = sorted(cidx.get(cat, []))
        if not rs:
            L.append("- shipped reports: (none)")
        else:
            L.append("- shipped reports:")
            for r in rs:
                L.append("  - `" + r + "`")
        L.append("")

    L.append("## Honest scope (v0.6)")
    L.append("")
    L.append("- VISUAL_RELATIONSHIP / PHYSICAL_SIMULATION /")
    L.append("  LANGUAGE_CONSTRUCTION are STRONG.")
    L.append("- PHOXEL_RASTER_LAW is PARTIAL (binding family covers it).")
    L.append("- SEMANTIC_STABILITY is PARTIAL (v0.6 introduces explicit")
    L.append("  metric; cardinality + repetition only).")
    L.append("- CALIBRATION_CONFIDENCE is PARTIAL (v0.6 introduces explicit")
    L.append("  per-family TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE).")
    L.append("- REAL_EVIDENCE_ANCHORING is STUB (not implemented).")
    L.append("")

    with open(out_dir / "PROOF_INDEX.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return index


def main():
    index = build_proof_index()
    write_proof_index_reports(Path.cwd(), index)
    print("Aurexis Research Sim v0.6 - Engine-semantics proof index")
    print("")
    for cat, info in PROOF_CATEGORIES.items():
        print("  {:<26}  status: {}".format(cat,
            CATEGORY_STATUS.get(cat, "?")))
    print("")
    print("Family table:")
    for fam, rec in index["family_table"].items():
        print("  {:<14}  boundary={:<28} validation={:<14} "
              "confidence={:<22} semantic={}".format(
                fam,
                str(rec.get("boundary_tag") or "-"),
                str(rec.get("validation_verdict") or "-"),
                str(rec.get("confidence_state") or "-"),
                str(rec.get("semantic_stability") or "-")))
    print("")
    print("Wrote proof_index.json and PROOF_INDEX.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
