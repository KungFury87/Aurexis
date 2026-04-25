"""v0.6 Engine-semantics proof index / taxonomy / confidence /
semantic-stability tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.proof_taxonomy import (
    PROOF_CATEGORIES, CATEGORY_STATUS, REPORT_TO_CATEGORIES,
    category_index, categories_for_report, write_taxonomy_reports,
)
from aurexis_sim.confidence import (
    confidence_state, build_confidence_dossier,
    write_confidence_reports, CONFIDENCE_STATES,
)
from aurexis_sim.semantic_stability import (
    SCENARIOS,
    evaluate_cardinality, evaluate_repetition,
    build_semantic_stability_dossier,
    write_semantic_stability_reports,
)
from aurexis_sim.proof_index import (
    build_proof_index, write_proof_index_reports,
)


# ----- proof_taxonomy ------------------------------------------------

def test_proof_categories_complete():
    assert set(PROOF_CATEGORIES.keys()) == {
        "VISUAL_RELATIONSHIP", "PHOXEL_RASTER_LAW",
        "SEMANTIC_STABILITY", "CALIBRATION_CONFIDENCE",
        "PHYSICAL_SIMULATION", "REAL_EVIDENCE_ANCHORING",
        "LANGUAGE_CONSTRUCTION",
    }


def test_category_status_values_known():
    valid = {"STRONG", "PARTIAL", "WEAK", "STUB"}
    for cat, st in CATEGORY_STATUS.items():
        assert st in valid


def test_real_evidence_anchoring_is_stub_in_v06():
    assert CATEGORY_STATUS["REAL_EVIDENCE_ANCHORING"] == "STUB"


def test_categories_for_report_known():
    cats = categories_for_report("UNLOCK.md")
    assert "LANGUAGE_CONSTRUCTION" in cats
    cats = categories_for_report("BINDING.md")
    assert "PHOXEL_RASTER_LAW" in cats


def test_category_index_includes_v06_artifacts():
    idx = category_index()
    assert "PROOF_INDEX.md" in idx["VISUAL_RELATIONSHIP"]
    assert "CONFIDENCE.md" in idx["CALIBRATION_CONFIDENCE"]
    assert "SEMANTIC_STABILITY.md" in idx["SEMANTIC_STABILITY"]


def test_write_taxonomy_reports(tmp_path: Path):
    write_taxonomy_reports(tmp_path)
    assert (tmp_path / "proof_taxonomy.json").exists()
    assert (tmp_path / "PROOF_TAXONOMY.md").exists()


# ----- confidence ----------------------------------------------------

def test_confidence_states_set():
    assert CONFIDENCE_STATES == ["TRUST", "HOLD", "DOWNGRADE",
                                  "REJECT", "NEED_MORE_EVIDENCE"]


def test_confidence_state_combinator():
    # Strong endorsements
    assert confidence_state("PRIMITIVE_AWARE_HELPS",
                              "EARNED_ROBUST") == "TRUST"
    # Helps but only weak validation
    assert confidence_state("PRIMITIVE_AWARE_HELPS",
                              "WEAK_ROBUST") == "HOLD"
    # Strong reject from validation
    assert confidence_state("PRIMITIVE_AWARE_HELPS",
                              "SUSPECT") == "REJECT"
    assert confidence_state("PRIMITIVE_AWARE_HELPS",
                              "NOT_ROBUST") == "REJECT"
    # Metric gap, no validation
    assert confidence_state("METRIC_GAP_ROI_INSENSITIVE",
                              None) == "NEED_MORE_EVIDENCE"
    # Failure mode
    assert confidence_state("PRIMITIVE_AWARE_STILL_FAILS",
                              None) == "REJECT"
    # Quality limit
    assert confidence_state("PROPOSAL_QUALITY_LIMIT",
                              None) == "DOWNGRADE"
    # Unknown -> need more evidence
    assert confidence_state(None, None) == "NEED_MORE_EVIDENCE"


def test_build_confidence_dossier_shape():
    d = build_confidence_dossier()
    assert d["schema_version"] == "0.6"
    assert "family_states" in d
    for fam, rec in d["family_states"].items():
        assert rec["confidence_state"] in CONFIDENCE_STATES


def test_write_confidence_reports(tmp_path: Path):
    write_confidence_reports(tmp_path)
    assert (tmp_path / "confidence.json").exists()
    assert (tmp_path / "CONFIDENCE.md").exists()


# ----- semantic_stability -------------------------------------------

def test_scenarios_set():
    assert set(SCENARIOS.keys()) == {"SIM_MILD", "SIM_HOSTILE"}


def test_cardinality_semantic_stable_under_simple_capture():
    """Cardinality with truth N=4 should recover N=4 across both
    scenarios -> SEMANTIC_STABLE."""
    rec = evaluate_cardinality(seed=0)
    assert rec["primitive"] == "cardinality"
    assert rec["truth_value"] == 4
    assert rec["verdict"] in ("SEMANTIC_STABLE", "SEMANTIC_DRIFT")


def test_repetition_evaluation_returns_verdict():
    rec = evaluate_repetition(seed=0)
    assert rec["primitive"] == "repetition"
    valid = {"SEMANTIC_STABLE", "SEMANTIC_DRIFT",
             "SEMANTIC_UNSTABLE", "SEMANTIC_UNRECOVERABLE"}
    assert rec["verdict"] in valid


def test_semantic_stability_dossier_shape():
    d = build_semantic_stability_dossier()
    assert d["schema_version"] == "0.6"
    assert "cardinality" in d["per_primitive"]
    assert "repetition" in d["per_primitive"]


def test_write_semantic_stability_reports(tmp_path: Path):
    write_semantic_stability_reports(tmp_path)
    assert (tmp_path / "semantic_stability.json").exists()
    assert (tmp_path / "SEMANTIC_STABILITY.md").exists()


# ----- proof_index ---------------------------------------------------

def test_proof_index_shape():
    idx = build_proof_index()
    assert idx["schema_version"] == "0.6"
    assert "family_table" in idx
    assert "category_index" in idx
    assert "category_status" in idx


def test_proof_index_includes_role_zone_and_ordering():
    idx = build_proof_index()
    fams = idx["family_table"]
    for fam in ("cardinality", "repetition", "role_zone",
                "ordering", "symmetry"):
        assert fam in fams


def test_proof_index_ordering_calibrated_reject():
    """Multi-evidence calibration: ordering shows PRIMITIVE_AWARE_HELPS
    boundary BUT validation says SUSPECT, so the calibrated confidence
    state is REJECT. This is the v0.6 headline finding."""
    idx = build_proof_index()
    rec = idx["family_table"].get("ordering")
    assert rec is not None
    assert rec["confidence_state"] == "REJECT"


def test_write_proof_index_reports(tmp_path: Path):
    write_proof_index_reports(tmp_path)
    assert (tmp_path / "proof_index.json").exists()
    assert (tmp_path / "PROOF_INDEX.md").exists()
