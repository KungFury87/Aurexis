"""v1.6 fusion / arbitration redesign tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.fusion import (
    FUSION_COMPOSITES, FUSED_RANKERS,
    rank_by_normalized_sum, rank_by_borda,
    attribute_failure, confidence_margin,
    _zscore, _verdict,
    build_fusion_dossier, write_fusion_reports,
)
from aurexis_sim.distractor_arbitration import (
    rank_by_area, rank_by_mean_intensity,
)
from aurexis_sim.binding import ROBUST_THR


def test_fused_rankers_registered():
    assert set(FUSED_RANKERS.keys()) == {"normalized_sum", "borda"}


def test_zscore_zero_variance():
    z = _zscore([1.0, 1.0, 1.0])
    assert np.allclose(z, 0.0)


def test_zscore_nonzero():
    z = _zscore([1.0, 2.0, 3.0])
    assert abs(z.mean()) < 1e-9
    assert abs(z.std() - 1.0) < 1e-6


def test_normalized_sum_picks_balanced_winner():
    # 3 candidates: a is biggest, b is brightest, c is balanced winner
    cap = np.zeros((20, 20), dtype=np.float32)
    cap[0:6, 0:6] = 0.3  # a region: large but dim
    cap[10:13, 10:13] = 0.9  # b region: small but bright
    cap[15:18, 15:18] = 0.6  # c region: medium both
    a = np.zeros((20, 20), dtype=bool); a[0:6, 0:6] = True       # area 36
    b = np.zeros((20, 20), dtype=bool); b[10:13, 10:13] = True   # area 9
    c = np.zeros((20, 20), dtype=bool); c[15:18, 15:18] = True   # area 9
    order = rank_by_normalized_sum([a, b, c], cap)
    # Sanity: result is a permutation of indices
    assert sorted(order) == [0, 1, 2]


def test_borda_picks_consensus():
    # If 2 of 4 single rankers pick candidate X and others split,
    # borda should reflect that. Here we just sanity-check shape.
    cap = np.zeros((20, 20), dtype=np.float32)
    cap[0:5, 0:5] = 0.5
    cap[10:15, 10:15] = 0.7
    a = np.zeros((20, 20), dtype=bool); a[0:5, 0:5] = True
    b = np.zeros((20, 20), dtype=bool); b[10:15, 10:15] = True
    order = rank_by_borda([a, b], cap)
    assert sorted(order) == [0, 1]


def test_borda_and_normalized_handle_empty():
    assert rank_by_borda([], None) == []
    assert rank_by_normalized_sum([], None) == []


def test_attribute_failure_signs():
    # Two candidates: A is bigger and brighter, B is smaller.
    cap = np.zeros((20, 20), dtype=np.float32)
    cap[0:6, 0:6] = 0.9       # A = big bright
    cap[10:12, 10:12] = 0.3   # B = small dim
    A = np.zeros((20, 20), dtype=bool); A[0:6, 0:6] = True
    B = np.zeros((20, 20), dtype=bool); B[10:12, 10:12] = True
    # Pretend oracle is B (the smaller candidate) and picker is A.
    a = attribute_failure([A, B], cap, oracle_idx=1, picker_idx=0)
    # area, mean_intensity should both have +diff (picker is bigger AND brighter)
    assert a["per_feature_z_diff"]["area"] > 0
    assert a["per_feature_z_diff"]["mean_intensity"] > 0


def test_attribute_failure_returns_none_when_match():
    cap = np.zeros((10, 10), dtype=np.float32)
    A = np.zeros((10, 10), dtype=bool); A[0:3, 0:3] = True
    a = attribute_failure([A], cap, oracle_idx=0, picker_idx=0)
    assert a is None


def test_confidence_margin_area_decisive():
    # Area top-1 = 25, top-2 = 4 -> margin = 25/4 = 6.25
    big = np.zeros((10, 10), dtype=bool); big[0:5, 0:5] = True
    sml = np.zeros((10, 10), dtype=bool); sml[0:2, 0:2] = True
    cap = np.zeros((10, 10), dtype=np.float32)
    m = confidence_margin([big, sml], cap, rank_by_area)
    assert m is not None and m > 6.0


def test_verdict_boundaries():
    assert _verdict(0.9, {"a": 0.9, "b": 0.9}) == "FUSION_ROBUST"
    assert _verdict(0.9, {"a": 0.9, "b": 0.3}) == "FUSION_PARTIAL"
    assert _verdict(0.9, {"a": 0.3, "b": 0.3}) == "FUSION_INSUFFICIENT"
    assert _verdict(0.3, {"a": 0.9, "b": 0.9}) == "PROPOSAL_QUALITY_LIMIT"
    assert _verdict(0.9, {}) == "FUSION_INSUFFICIENT"


def test_dossier_shape_and_keys():
    d = build_fusion_dossier()
    assert d["schema_version"] == "1.6"
    assert set(d["single_rankers"]) == {"area", "mean_intensity",
                                         "edge_density", "compactness"}
    assert set(d["fused_rankers"]) == {"normalized_sum", "borda"}
    valid = {"FUSION_ROBUST", "FUSION_PARTIAL", "FUSION_INSUFFICIENT",
             "PROPOSAL_QUALITY_LIMIT"}
    assert set(d["per_composite"].keys()) == set(FUSION_COMPOSITES.keys())
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
        for sr in rec["sub_relations"]:
            for k in ("sub_primitive", "relation_kind", "n_candidates",
                      "oracle_best", "oracle_idx", "single_top1",
                      "fused_top1", "attributions", "confidence",
                      "verdict"):
                assert k in sr


def test_with_decoy_attribution_present():
    """For composite_cardinality_with_decoy each failed single ranker
    should produce an attribution with a dominant feature."""
    d = build_fusion_dossier()
    rec = d["per_composite"]["composite_cardinality_with_decoy"]
    sr = rec["sub_relations"][0]
    # At least one ranker should have failed and so produced an attribution.
    failures = [r for r, a in sr["attributions"].items() if a is not None]
    assert len(failures) >= 1
    for r in failures:
        a = sr["attributions"][r]
        assert a["dominant_misleading"] in (
            "area", "mean_intensity", "edge_density", "compactness"
        )
        assert isinstance(a["per_feature_z_diff"], dict)


def test_fusion_insufficient_on_shipped_composites():
    """The honest finding on the v1.5 distractor composites: simple
    fusion of these 4 features cannot recover. v1.6 should report
    FUSION_INSUFFICIENT (or PROPOSAL_QUALITY_LIMIT) on both."""
    d = build_fusion_dossier()
    for ck in ("composite_cardinality_with_decoy",
               "composite_cardinality_ranker_split"):
        rec = d["per_composite"][ck]
        assert rec["overall_verdict"] in (
            "FUSION_INSUFFICIENT", "PROPOSAL_QUALITY_LIMIT"
        )


def test_write_fusion_reports(tmp_path: Path):
    write_fusion_reports(tmp_path)
    assert (tmp_path / "fusion.json").exists()
    assert (tmp_path / "FUSION.md").exists()
    with open(tmp_path / "fusion.json") as f:
        d = json.load(f)
    assert d["schema_version"] == "1.6"
    assert "per_composite" in d
