"""v1.7 primitive-aware / target-conditioned arbitration tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.primitive_aware import (
    rank_by_cardinality_target,
    rank_by_repetition_target,
    best_generic_top1,
    _verdict, _target_for,
    build_primitive_aware_dossier,
    write_primitive_aware_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_rank_by_cardinality_target_handles_empty():
    assert rank_by_cardinality_target([], None, 3) == []
    assert rank_by_cardinality_target([], None, None) == []


def test_rank_by_cardinality_target_picks_matching_count():
    """Construct a captured image with two candidate ROIs: one
    contains 3 components above threshold; the other contains 5.
    Target count = 3 -> ranker should pick the 3-component candidate."""
    captured = np.full((40, 80), 0.10, dtype=np.float32)
    # 3 bright spots in left half (intended)
    for cx in (8, 18, 28):
        captured[18:22, cx-2:cx+3] = 0.95
    # 5 bright spots in right half (decoy)
    for cx in (45, 51, 57, 63, 69):
        captured[18:22, cx-2:cx+3] = 0.95
    intended = np.zeros((40, 80), dtype=bool); intended[10:30, 0:40] = True
    decoy = np.zeros((40, 80), dtype=bool); decoy[10:30, 40:80] = True
    order = rank_by_cardinality_target([decoy, intended], captured, 3)
    assert order[0] == 1  # intended is index 1; it should be top


def test_rank_by_repetition_target_handles_missing_params():
    assert rank_by_repetition_target([], None, 10.0, 5) == []
    cap = np.zeros((20, 20), dtype=np.float32)
    c = np.ones((20, 20), dtype=bool)
    assert rank_by_repetition_target([c], cap, None, 5) == []
    assert rank_by_repetition_target([c], cap, 10.0, None) == []


def test_target_for_cardinality():
    sub = {"name": "cardinality",
           "relation": {"kind": "cardinality", "count": 4}}
    kind, params = _target_for(sub)
    assert kind == "cardinality"
    assert params["target_count"] == 4


def test_target_for_repetition():
    sub = {"name": "repetition",
           "relation": {"kind": "repetition",
                          "period_px": 12.5, "row_y": 30}}
    kind, params = _target_for(sub)
    assert kind == "repetition"
    assert params["target_period"] == 12.5
    assert params["row_y"] == 30


def test_target_for_other():
    sub = {"name": "ordering", "relation": {"kind": "ordering"}}
    kind, params = _target_for(sub)
    assert kind == "ordering"
    assert params == {}


def test_verdict_boundaries():
    # oracle fails -> proposal quality limit
    assert _verdict(0.3, 0.9, 0.9) == "PROPOSAL_QUALITY_LIMIT"
    # oracle ok, best_generic ok -> generic sufficient
    assert _verdict(0.9, 0.9, 0.9) == "GENERIC_FUSION_SUFFICIENT"
    assert _verdict(0.9, 0.9, 0.3) == "GENERIC_FUSION_SUFFICIENT"
    # oracle ok, generic fails, target ok -> primitive-aware helps
    assert _verdict(0.9, 0.3, 0.9) == "PRIMITIVE_AWARE_HELPS"
    # oracle ok, both fail
    assert _verdict(0.9, 0.3, 0.3) == "PRIMITIVE_AWARE_STILL_FAILS"


def test_best_generic_top1_runs_all_rankers():
    """best_generic_top1 should produce a top-1 score for each of the
    4 single + 2 fused rankers."""
    cap = np.zeros((20, 20), dtype=np.float32)
    cap[0:5, 0:5] = 0.5
    cap[10:13, 10:13] = 0.7
    a = np.zeros((20, 20), dtype=bool); a[0:5, 0:5] = True
    b = np.zeros((20, 20), dtype=bool); b[10:13, 10:13] = True
    scores = [0.7, 0.4]  # candidate A scores 0.7, B scores 0.4
    best, best_name, all_top1 = best_generic_top1([a, b], cap, scores)
    assert isinstance(all_top1, dict)
    assert set(all_top1.keys()) >= {"area", "mean_intensity",
                                      "edge_density", "compactness",
                                      "normalized_sum", "borda"}
    # All values should be within {0.7, 0.4}
    for v in all_top1.values():
        assert v in (0.7, 0.4)
    # Best should be 0.7 (since at least one ranker picks A)
    assert best == 0.7


def test_dossier_shape_and_keys():
    d = build_primitive_aware_dossier()
    assert d["schema_version"] == "1.7"
    assert "cardinality_target" in d["primitive_aware_rankers"]
    valid = {"GENERIC_FUSION_SUFFICIENT", "PRIMITIVE_AWARE_HELPS",
             "PRIMITIVE_AWARE_STILL_FAILS", "PROPOSAL_QUALITY_LIMIT"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
        for sr in rec["sub_relations"]:
            for k in ("sub_primitive", "relation_kind", "n_candidates",
                      "target_params", "oracle_best", "generic_top1",
                      "best_generic", "best_generic_name",
                      "primitive_aware", "verdict"):
                assert k in sr


def test_with_decoy_primitive_aware_helps():
    """The headline v1.7 finding: target-conditioned cardinality
    scoring rescues composite_cardinality_with_decoy where every
    generic single + fused ranker fails."""
    d = build_primitive_aware_dossier()
    rec = d["per_composite"]["composite_cardinality_with_decoy"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    assert sr["best_generic"] < ROBUST_THR
    assert sr["primitive_aware"] >= ROBUST_THR


def test_ranker_split_generic_already_sufficient():
    """In ranker_split the area ranker already passes (v1.5's
    finding); v1.7 should report GENERIC_FUSION_SUFFICIENT and add
    nothing."""
    d = build_primitive_aware_dossier()
    rec = d["per_composite"]["composite_cardinality_ranker_split"]
    assert rec["overall_verdict"] == "GENERIC_FUSION_SUFFICIENT"


def test_write_primitive_aware_reports(tmp_path: Path):
    write_primitive_aware_reports(tmp_path)
    assert (tmp_path / "primitive_aware.json").exists()
    assert (tmp_path / "PRIMITIVE_AWARE.md").exists()
    with open(tmp_path / "primitive_aware.json") as f:
        d = json.load(f)
    assert d["schema_version"] == "1.7"
    assert "per_composite" in d
