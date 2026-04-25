"""Proof-category taxonomy for the Aurexis Engine-semantics proof system (v0.6).

The Aurexis testing suite is not "simulate everything" and not
"generate fake camera wins." It is an Engine-semantics proof system:
controlled evidence, exposed failure modes, mapped limits, and
information that helps decide which Engine law or semantic rule
needs to change.

This module organizes the suite's existing reports + probes around
seven proof categories. It does not generate new evidence by itself
- it is a registry that lets the rest of the suite (proof_index)
present evidence under Engine-semantics framing.

Proof categories:

  VISUAL_RELATIONSHIP    Tests of visual relationship survival and
                          discriminability under capture (ordering,
                          adjacency, symmetry, orientation,
                          hierarchy, repetition, cardinality,
                          role_zone).
  PHOXEL_RASTER_LAW       Tests of how primitive evaluation depends
                          on ROI / phoxel-cell choice (binding,
                          soft_binding, inferred_binding).
  SEMANTIC_STABILITY      Tests of whether the SEMANTIC VALUE
                          recovered (count, period_px, axis) is
                          stable across capture scenarios. New in
                          v0.6.
  CALIBRATION_CONFIDENCE  Calibrated trust state per primitive
                          family (TRUST / HOLD / DOWNGRADE / REJECT
                          / NEED_MORE_EVIDENCE). New in v0.6.
  PHYSICAL_SIMULATION     Tests that exercise the display/capture
                          chain (stress sweeps, scenario atlas,
                          per-stage relation report).
  REAL_EVIDENCE_ANCHORING Real-image intake and comparison against
                          synthetic predictions. NOT YET IMPLEMENTED;
                          listed for boundary mapping only.
  LANGUAGE_CONSTRUCTION   Outputs that inform whether a primitive is
                          worth promoting, redesigning, or rejecting
                          in a visual language (validation, redesign,
                          arbitration, fusion, primitive_aware,
                          coverage, boundary, unlock).

Honest scope:
  - This module does NOT compute new evidence. It maps existing
    reports to proof categories and provides a category index.
  - Each proof category is a question. Reports are answers (or
    partial answers) to that question.
  - REAL_EVIDENCE_ANCHORING is intentionally listed but unimplemented;
    the registry says so.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


# Question each proof category answers in plain English.
PROOF_CATEGORIES: Dict[str, Dict[str, str]] = {
    "VISUAL_RELATIONSHIP": {
        "title": "Visual relationship proofs",
        "question": (
            "Does each visual relationship primitive survive the "
            "display/capture chain, and by how much?"
        ),
    },
    "PHOXEL_RASTER_LAW": {
        "title": "Phoxel/raster law proofs",
        "question": (
            "Does primitive evaluation depend on ROI/phoxel-cell "
            "choice? When does ROI matter, when does it not, and "
            "how does inferred ROI compare to oracle ROI?"
        ),
    },
    "SEMANTIC_STABILITY": {
        "title": "Semantic stability proofs",
        "question": (
            "Is the SEMANTIC VALUE recovered (cardinality count, "
            "repetition period, ordering axis, symmetry axis, etc.) "
            "stable across capture scenarios, or does it drift?"
        ),
    },
    "CALIBRATION_CONFIDENCE": {
        "title": "Calibration and confidence proofs",
        "question": (
            "What is the calibrated trust state per primitive family "
            "given all available evidence: TRUST / HOLD / DOWNGRADE / "
            "REJECT / NEED_MORE_EVIDENCE?"
        ),
    },
    "PHYSICAL_SIMULATION": {
        "title": "Simulator-supported physical proofs",
        "question": (
            "How do primitive scores change under display/capture "
            "stress (blur, motion blur, rolling shutter, sensor "
            "Bayer, noise, quantize)?"
        ),
    },
    "REAL_EVIDENCE_ANCHORING": {
        "title": "Real-evidence anchoring",
        "question": (
            "Does synthetic prediction match real captured imagery "
            "for the same primitives?"
        ),
    },
    "LANGUAGE_CONSTRUCTION": {
        "title": "Language-construction proofs",
        "question": (
            "Should this primitive be promoted, redesigned, or "
            "rejected as a visual-language unit? Does target-"
            "conditioned arbitration help, or is generic enough?"
        ),
    },
}


# Map shipped reports to proof categories. A report can serve more
# than one category. This is the canonical mapping.
REPORT_TO_CATEGORIES: Dict[str, List[str]] = {
    # v0.5 stress / 1D and 2D physical-stress + relation discriminability
    "SUMMARY.md": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],
    "stress_report.json": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],
    "stress_grids.json": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],
    "confusion_tables.json": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],

    # v0.6 / v0.7 atlas + scenario atlas
    "ATLAS.md": ["VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],
    "atlas.json": ["VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION"],
    "SCENARIO_ATLAS.md": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION",
        "SEMANTIC_STABILITY"],
    "scenario_atlas.json": [
        "VISUAL_RELATIONSHIP", "PHYSICAL_SIMULATION",
        "SEMANTIC_STABILITY"],

    # v0.8 / v0.9 validation + redesign
    "VALIDATION.md": [
        "VISUAL_RELATIONSHIP", "CALIBRATION_CONFIDENCE"],
    "validation.json": [
        "VISUAL_RELATIONSHIP", "CALIBRATION_CONFIDENCE"],
    "REDESIGN.md": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],
    "redesign.json": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],

    # v1.0 interaction (composite primitives)
    "INTERACTION.md": [
        "VISUAL_RELATIONSHIP", "SEMANTIC_STABILITY"],
    "interaction.json": [
        "VISUAL_RELATIONSHIP", "SEMANTIC_STABILITY"],

    # v1.1 / v1.2 / v1.3 binding family (phoxel/raster law)
    "BINDING.md":           ["PHOXEL_RASTER_LAW"],
    "binding.json":         ["PHOXEL_RASTER_LAW"],
    "SOFT_BINDING.md":      ["PHOXEL_RASTER_LAW"],
    "soft_binding.json":    ["PHOXEL_RASTER_LAW"],
    "INFERRED_BINDING.md":  ["PHOXEL_RASTER_LAW"],
    "inferred_binding.json":["PHOXEL_RASTER_LAW"],

    # v1.4 / v1.5 arbitration and distractor
    "ARBITRATION.md": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],
    "arbitration.json": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],
    "DISTRACTOR_ARBITRATION.md": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],
    "distractor_arbitration.json": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],

    # v1.6 fusion (arbitration redesign signals)
    "FUSION.md":  ["LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],
    "fusion.json":["LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE"],

    # v1.7 / v1.8 / v1.9 / v2.0 primitive-aware & boundary
    "PRIMITIVE_AWARE.md":  [
        "LANGUAGE_CONSTRUCTION", "VISUAL_RELATIONSHIP"],
    "primitive_aware.json":[
        "LANGUAGE_CONSTRUCTION", "VISUAL_RELATIONSHIP"],
    "COVERAGE.md":   [
        "LANGUAGE_CONSTRUCTION", "VISUAL_RELATIONSHIP",
        "PHOXEL_RASTER_LAW"],
    "coverage.json": [
        "LANGUAGE_CONSTRUCTION", "VISUAL_RELATIONSHIP",
        "PHOXEL_RASTER_LAW"],
    "BOUNDARY.md":   [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE",
        "VISUAL_RELATIONSHIP"],
    "boundary.json": [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE",
        "VISUAL_RELATIONSHIP"],
    "UNLOCK.md":     [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE",
        "VISUAL_RELATIONSHIP"],
    "unlock.json":   [
        "LANGUAGE_CONSTRUCTION", "CALIBRATION_CONFIDENCE",
        "VISUAL_RELATIONSHIP"],

    # v0.6 (THIS PASS) - new artifacts
    "SEMANTIC_STABILITY.md":      ["SEMANTIC_STABILITY"],
    "semantic_stability.json":    ["SEMANTIC_STABILITY"],
    "CONFIDENCE.md":              ["CALIBRATION_CONFIDENCE"],
    "confidence.json":            ["CALIBRATION_CONFIDENCE"],
    "PROOF_INDEX.md":             list(PROOF_CATEGORIES.keys()),
    "proof_index.json":           list(PROOF_CATEGORIES.keys()),
}


# Status of each proof category in v0.6. "STRONG" = multiple shipped
# reports; "PARTIAL" = some evidence; "WEAK" = limited; "STUB" = no
# real evidence yet.
CATEGORY_STATUS: Dict[str, str] = {
    "VISUAL_RELATIONSHIP":     "STRONG",
    "PHYSICAL_SIMULATION":     "STRONG",
    "PHOXEL_RASTER_LAW":       "PARTIAL",
    "SEMANTIC_STABILITY":      "PARTIAL",  # v0.6 introduces explicit metric
    "CALIBRATION_CONFIDENCE":  "PARTIAL",  # v0.6 introduces explicit state
    "LANGUAGE_CONSTRUCTION":   "STRONG",
    "REAL_EVIDENCE_ANCHORING": "STUB",     # not implemented in v0.6
}


def category_index() -> Dict[str, List[str]]:
    """Return per-category list of supporting reports."""
    out: Dict[str, List[str]] = {cat: [] for cat in PROOF_CATEGORIES}
    for rep, cats in REPORT_TO_CATEGORIES.items():
        for cat in cats:
            if cat in out:
                out[cat].append(rep)
    return out


def categories_for_report(report_name: str) -> List[str]:
    return list(REPORT_TO_CATEGORIES.get(report_name, []))


def write_taxonomy_reports(out_dir: Path) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    idx = category_index()
    payload = {
        "schema_version": "0.6",
        "categories": PROOF_CATEGORIES,
        "category_status": CATEGORY_STATUS,
        "category_index": idx,
        "report_to_categories": REPORT_TO_CATEGORIES,
    }
    with open(out_dir / "proof_taxonomy.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    L = []
    L.append("# Aurexis Research Sim v0.6 - Proof-category taxonomy")
    L.append("")
    L.append("Engine-semantics proof system. Each category is a question; "
              "shipped reports are answers (or partial answers) to that question.")
    L.append("")
    L.append("## Category index")
    L.append("")
    L.append("| category | status | question |")
    L.append("|---|---|---|")
    for cat, info in PROOF_CATEGORIES.items():
        status = CATEGORY_STATUS.get(cat, "?")
        L.append("| `" + cat + "` | " + status + " | " + info["question"] + " |")
    L.append("")
    L.append("## Supporting reports per category")
    L.append("")
    for cat, info in PROOF_CATEGORIES.items():
        L.append("### " + cat + " (" + info["title"] + ")")
        L.append("")
        L.append("Status: **" + CATEGORY_STATUS.get(cat, "?") + "**")
        L.append("")
        L.append("Question: _" + info["question"] + "_")
        L.append("")
        reports = idx.get(cat, [])
        if not reports:
            L.append("(no shipped reports)")
        else:
            L.append("Shipped reports:")
            for r in sorted(reports):
                L.append("- `" + r + "`")
        L.append("")
    with open(out_dir / "PROOF_TAXONOMY.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return payload


def main():
    write_taxonomy_reports(Path.cwd())
    idx = category_index()
    print("Aurexis Research Sim v0.6 - Proof-category taxonomy")
    print("")
    for cat, info in PROOF_CATEGORIES.items():
        print("  {:<26} [{}]".format(cat, CATEGORY_STATUS.get(cat, "?")))
        print("    Q: " + info["question"])
        for r in sorted(idx.get(cat, [])):
            print("    - " + r)
        print("")
    print("Wrote proof_taxonomy.json and PROOF_TAXONOMY.md into CWD.")
    return 0


def _entry():
    return main()


if __name__ == "__main__":
    raise SystemExit(_entry())
# end of file padding
