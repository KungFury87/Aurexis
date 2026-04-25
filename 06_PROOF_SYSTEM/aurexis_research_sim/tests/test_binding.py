"""v1.1 scene-scoped binding / ROI-aware evaluation tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.binding import (
    roi_from_labels, build_binding_dossier, write_binding_reports,
    _verdict, _scene_ambiguity,
    compute_relation_metric_unbound, compute_relation_metric_bound,
    cardinality_survival_bound, repetition_survival_bound,
    ROBUST_THR, BINDING_BOOST,
)
from aurexis_sim import truth as truth_mod


def test_roi_from_labels_dilates():
    lab = np.zeros((10, 10), dtype=np.int32)
    lab[5, 5] = 1
    roi = roi_from_labels(lab, dilate=2)
    assert roi[5, 5]
    assert roi[3, 5] and roi[7, 5] and roi[5, 3] and roi[5, 7]
    # Corners still False
    assert not roi[0, 0]


def test_verdict_logic():
    assert _verdict(0.9, 0.9) == "SURVIVES_GLOBAL"
    assert _verdict(0.3, 0.9) == "NEEDS_BINDING"
    assert _verdict(0.2, 0.2) == "FAILS_EVEN_BOUND"
    assert _verdict(float("nan"), 0.9) == "UNKNOWN"


def test_scene_ambiguity_tag():
    assert _scene_ambiguity(0.2, 0.9) is True
    assert _scene_ambiguity(0.9, 0.95) is False


def test_cardinality_bound_restores_count_in_composite():
    """The v1.0 BINDING_FAILURE on cardinality should flip to
    SURVIVES_GLOBAL or NEEDS_BINDING when ROI binding is applied."""
    dossier = build_binding_dossier(size=96)
    rec = dossier["per_composite"]["composite_repetition_cardinality"]
    cards = [sr for sr in rec["sub_relations"]
             if sr["sub_primitive"] == "cardinality"]
    assert cards, "no cardinality sub_relation"
    sr = cards[0]
    # Unbound should be poor (<= 0.5), bound should be high
    assert sr["unbound_survival"] <= 0.5
    assert sr["bound_survival"] >= 0.8
    assert sr["verdict"] in ("NEEDS_BINDING", "SURVIVES_GLOBAL")
    # And scene ambiguity tag should fire
    assert "SCENE_AMBIGUITY" in sr["tags"]


def test_dossier_schema():
    d = build_binding_dossier(size=96)
    assert d["schema_version"] == "1.1"
    assert set(d["per_composite"].keys())  # non-empty
    for ck, rec in d["per_composite"].items():
        assert "overall_verdict" in rec
        assert len(rec["sub_relations"]) >= 2
        for sr in rec["sub_relations"]:
            for key in ("sub_primitive", "relation_kind",
                        "unbound_survival", "bound_survival",
                        "binding_boost", "verdict", "tags"):
                assert key in sr


def test_write_binding_reports(tmp_path: Path):
    write_binding_reports(tmp_path)
    assert (tmp_path / "binding.json").exists()
    assert (tmp_path / "BINDING.md").exists()
    with open(tmp_path / "binding.json") as f:
        dossier = json.load(f)
    assert "per_composite" in dossier


def test_label_based_relations_equal_bound_unbound():
    """For ordering / adjacency / role_zone (label-scoped), bound and
    unbound should agree."""
    from aurexis_sim.interaction import composite_ordering_role_zone
    from aurexis_sim.interaction import INTERACTION_CAPTURE
    from aurexis_sim.simulate import run_chain
    pkt = composite_ordering_role_zone(size=96)
    capture = INTERACTION_CAPTURE()
    result = run_chain(pkt["image"], capture, seed=0)
    captured = result["captured"]
    for sub in pkt["meta"]["composite"]:
        roi = roi_from_labels(sub["labels"], dilate=3)
        u = compute_relation_metric_unbound(sub, captured)
        b = compute_relation_metric_bound(sub, captured, roi)
        assert abs(b - u) < 1e-6
