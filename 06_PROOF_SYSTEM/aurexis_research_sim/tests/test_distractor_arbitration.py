"""v1.5 distractor-arbitration / ranking-brittleness tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.distractor_arbitration import (
    composite_cardinality_with_decoy,
    composite_cardinality_ranker_split,
    DISTRACTOR_COMPOSITES, RANKERS,
    rank_by_area, rank_by_mean_intensity,
    rank_by_edge_density, rank_by_compactness,
    _verdict,
    build_distractor_arbitration_dossier,
    write_distractor_arbitration_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_composites_registered():
    assert set(DISTRACTOR_COMPOSITES.keys()) == {
        "composite_cardinality_with_decoy",
        "composite_cardinality_ranker_split",
    }


def test_composite_cardinality_with_decoy_shape():
    pkt = composite_cardinality_with_decoy(size=96)
    assert pkt["image"].shape == (96, 96)
    assert len(pkt["meta"]["composite"]) == 1
    sub = pkt["meta"]["composite"][0]
    assert sub["name"] == "cardinality"
    assert sub["relation"]["count"] == 3


def test_composite_cardinality_ranker_split_shape():
    pkt = composite_cardinality_ranker_split(size=96)
    assert pkt["image"].shape == (96, 96)
    sub = pkt["meta"]["composite"][0]
    assert sub["relation"]["kind"] == "cardinality"
    assert sub["relation"]["count"] == 3


def test_rankers_registered():
    assert set(RANKERS.keys()) == {
        "area", "mean_intensity", "edge_density", "compactness"
    }


def test_rank_by_area_picks_largest():
    big   = np.zeros((20, 20), dtype=bool); big[0:10, 0:10] = True   # 100
    small = np.zeros((20, 20), dtype=bool); small[0:3, 0:3] = True   # 9
    mid   = np.zeros((20, 20), dtype=bool); mid[0:5, 0:5] = True     # 25
    order = rank_by_area([small, big, mid])
    assert order[0] == 1  # big first


def test_rank_by_mean_intensity_uses_captured():
    cap = np.zeros((20, 20), dtype=np.float32)
    cap[0:10, 0:10] = 0.2   # dim region
    cap[10:20, 10:20] = 0.9 # bright region
    dim_mask = np.zeros((20, 20), dtype=bool); dim_mask[0:10, 0:10] = True
    bright_mask = np.zeros((20, 20), dtype=bool); bright_mask[10:20, 10:20] = True
    order = rank_by_mean_intensity([dim_mask, bright_mask], cap)
    assert order[0] == 1  # bright first


def test_rank_by_compactness_prefers_blob():
    # Square blob vs. thin line, same area
    blob = np.zeros((20, 20), dtype=bool); blob[0:4, 0:4] = True  # 4x4=16
    line = np.zeros((20, 20), dtype=bool); line[0, 0:16] = True   # 1x16=16
    order = rank_by_compactness([blob, line])
    assert order[0] == 0  # blob first (more compact)


def test_verdict_boundaries():
    assert _verdict(0.9, {"a": 0.9, "b": 0.9}) == "SURVIVES_UNDER_DISTRACTORS"
    assert _verdict(0.9, {"a": 0.9, "b": 0.3}) == "RANKER_BRITTLE"
    assert _verdict(0.9, {"a": 0.3, "b": 0.3}) == "DISTRACTOR_DOMINATED"
    assert _verdict(0.3, {"a": 0.9, "b": 0.9}) == "FAILS_EVEN_ORACLE"


def test_dossier_shape_and_verdicts():
    d = build_distractor_arbitration_dossier()
    assert d["schema_version"] == "1.5"
    assert set(d["rankers"]) == {"area", "mean_intensity",
                                  "edge_density", "compactness"}
    valid = {"SURVIVES_UNDER_DISTRACTORS", "RANKER_BRITTLE",
             "DISTRACTOR_DOMINATED", "FAILS_EVEN_ORACLE"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
        for sr in rec["sub_relations"]:
            for key in ("sub_primitive", "relation_kind", "n_candidates",
                        "oracle_best", "per_ranker_top1",
                        "ranker_disagreement", "verdict"):
                assert key in sr


def test_with_decoy_is_distractor_dominated():
    """The bigger/brighter decoy should beat every simple ranker."""
    d = build_distractor_arbitration_dossier()
    rec = d["per_composite"]["composite_cardinality_with_decoy"]
    assert rec["overall_verdict"] in ("DISTRACTOR_DOMINATED",
                                       "RANKER_BRITTLE")
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    passes = [v for v in sr["per_ranker_top1"].values()
              if isinstance(v, float) and v == v and v >= ROBUST_THR]
    assert len(passes) < len(sr["per_ranker_top1"])


def test_ranker_split_has_disagreement():
    """The ranker_split composite should produce at least 2 distinct
    top-1 indices across rankers (area vs salience vs compactness)."""
    d = build_distractor_arbitration_dossier()
    rec = d["per_composite"]["composite_cardinality_ranker_split"]
    sr = rec["sub_relations"][0]
    assert sr["ranker_disagreement"] >= 2


def test_write_distractor_arbitration_reports(tmp_path: Path):
    write_distractor_arbitration_reports(tmp_path)
    assert (tmp_path / "distractor_arbitration.json").exists()
    assert (tmp_path / "DISTRACTOR_ARBITRATION.md").exists()
    with open(tmp_path / "distractor_arbitration.json") as f:
        d = json.load(f)
    assert d["schema_version"] == "1.5"
    assert "per_composite" in d
