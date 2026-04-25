"""v1.9 arbitration-boundary mapping / ROI-sensitive role_zone tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.boundary import (
    role_zone_survival_bound,
    rank_by_role_zone_target,
    composite_role_zone_decoy,
    BOUNDARY_COMPOSITES,
    LABEL_SCOPED_NO_ROI,
    _per_composite_verdict,
    _family_verdict,
    build_boundary_dossier,
    write_boundary_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_label_scoped_set_excludes_role_zone():
    """v1.9: role_zone has an ROI-aware metric and is NOT in
    LABEL_SCOPED_NO_ROI."""
    assert "role_zone" not in LABEL_SCOPED_NO_ROI
    assert LABEL_SCOPED_NO_ROI == {"ordering", "adjacency", "symmetry",
                                     "orientation", "hierarchy"}


def test_role_zone_survival_returns_zero_when_no_components():
    captured = np.full((20, 20), 0.10, dtype=np.float32)
    roi = np.ones((20, 20), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "role_zone",
                                   "target_satellites": 4}}}
    s = role_zone_survival_bound(pkt, captured, roi, target_satellites=4)
    assert s == 0.0


def test_role_zone_survival_returns_zero_when_anchor_not_clear():
    """If the brightest component is not >= 10% above the next
    brightest, no clear anchor -> score 0."""
    captured = np.full((40, 40), 0.10, dtype=np.float32)
    captured[10:13, 10:13] = 0.80   # marker A
    captured[10:13, 25:28] = 0.81   # marker B (basically tied)
    captured[25:28, 10:13] = 0.80   # marker C
    roi = np.ones((40, 40), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "role_zone",
                                   "target_satellites": 2}}}
    s = role_zone_survival_bound(pkt, captured, roi, target_satellites=2)
    assert s == 0.0


def test_role_zone_survival_passes_with_clear_anchor():
    captured = np.full((40, 40), 0.10, dtype=np.float32)
    captured[10:14, 10:14] = 0.95   # bright anchor
    captured[20:23, 10:13] = 0.50
    captured[10:13, 20:23] = 0.50
    captured[25:28, 25:28] = 0.50
    captured[6:9, 25:28]   = 0.50
    roi = np.ones((40, 40), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "role_zone",
                                   "target_satellites": 4}}}
    s = role_zone_survival_bound(pkt, captured, roi, target_satellites=4)
    assert s == 1.0


def test_rank_by_role_zone_target_handles_empty():
    assert rank_by_role_zone_target([], None, 4) == []
    cap = np.zeros((20, 20), dtype=np.float32)
    c = np.ones((20, 20), dtype=bool)
    assert rank_by_role_zone_target([c], cap, None) == []


def test_composite_role_zone_decoy_shape():
    pkt = composite_role_zone_decoy(size=128)
    assert pkt["image"].shape == (128, 128)
    sub = pkt["meta"]["composite"][0]
    assert sub["name"] == "role_zone"
    assert sub["relation"]["kind"] == "role_zone"
    assert sub["relation"]["target_satellites"] == 4


def test_boundary_composites_includes_role_zone():
    assert "composite_cardinality_with_decoy" in BOUNDARY_COMPOSITES
    assert "composite_cardinality_ranker_split" in BOUNDARY_COMPOSITES
    assert "composite_repetition_distractor" in BOUNDARY_COMPOSITES
    assert "composite_role_zone_decoy" in BOUNDARY_COMPOSITES


def test_per_composite_verdict_label_scoped_metric_gap():
    """A relation_kind in LABEL_SCOPED_NO_ROI should produce
    METRIC_GAP_ROI_INSENSITIVE regardless of generic/target scores."""
    v = _per_composite_verdict(0.9, 0.9, 0.9, "ordering")
    assert v == "METRIC_GAP_ROI_INSENSITIVE"
    v = _per_composite_verdict(0.9, 0.0, 0.0, "ordering")
    assert v == "METRIC_GAP_ROI_INSENSITIVE"


def test_per_composite_verdict_proposal_quality():
    v = _per_composite_verdict(0.3, 0.9, 0.9, "cardinality")
    assert v == "PROPOSAL_QUALITY_LIMIT"


def test_per_composite_verdict_primitive_aware_helps():
    v = _per_composite_verdict(0.9, 0.3, 0.9, "cardinality")
    assert v == "PRIMITIVE_AWARE_HELPS"
    v = _per_composite_verdict(0.9, 0.3, 0.9, "role_zone")
    assert v == "PRIMITIVE_AWARE_HELPS"


def test_family_verdict_picks_best_news():
    """Family verdict should pick the most favorable per-composite
    verdict (priority order: PRIMITIVE_AWARE_HELPS > GENERIC > etc.)."""
    assert _family_verdict(["GENERIC_FUSION_SUFFICIENT",
                              "PRIMITIVE_AWARE_HELPS"]) == "PRIMITIVE_AWARE_HELPS"
    assert _family_verdict(["METRIC_GAP_ROI_INSENSITIVE"]) == "METRIC_GAP_ROI_INSENSITIVE"
    assert _family_verdict([]) == "METRIC_GAP_ROI_INSENSITIVE"


def test_dossier_shape_and_keys():
    d = build_boundary_dossier()
    assert d["schema_version"] == "1.9"
    assert "role_zone_target" in d["primitive_aware_rankers"]
    valid = {"GENERIC_FUSION_SUFFICIENT", "ARBITRATION_INVARIANT",
             "METRIC_GAP_ROI_INSENSITIVE", "PRIMITIVE_AWARE_HELPS",
             "PRIMITIVE_AWARE_STILL_FAILS", "PROPOSAL_QUALITY_LIMIT"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
    assert "family_boundary_map" in d
    assert "role_zone" in d["family_boundary_map"]
    for fam in ("ordering", "adjacency", "symmetry",
                "orientation", "hierarchy"):
        assert fam in d["family_boundary_map"]
        assert (d["family_boundary_map"][fam]["boundary_tag"]
                == "METRIC_GAP_ROI_INSENSITIVE")


def test_role_zone_decoy_primitive_aware_helps():
    """v1.9 headline: target-conditioned role_zone scoring rescues
    composite_role_zone_decoy where every generic ranker fails."""
    d = build_boundary_dossier()
    rec = d["per_composite"]["composite_role_zone_decoy"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    assert sr["best_generic"] < ROBUST_THR
    assert sr["primitive_aware"] >= ROBUST_THR


def test_three_families_help():
    """v1.9: three primitive families now show PRIMITIVE_AWARE_HELPS."""
    d = build_boundary_dossier()
    fm = d["family_boundary_map"]
    for fam in ("cardinality", "repetition", "role_zone"):
        assert fm[fam]["boundary_tag"] == "PRIMITIVE_AWARE_HELPS"


def test_write_boundary_reports(tmp_path: Path):
    write_boundary_reports(tmp_path)
    assert (tmp_path / "boundary.json").exists()
    assert (tmp_path / "BOUNDARY.md").exists()
    with open(tmp_path / "boundary.json") as f:
        d = json.load(f)
    assert d["schema_version"] == "1.9"
    assert "family_boundary_map" in d
