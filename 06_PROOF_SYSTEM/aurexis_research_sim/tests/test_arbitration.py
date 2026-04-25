"""v1.4 arbitration / proposal-competition tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.arbitration import (
    candidates_from_mask,
    rank_candidates,
    _components,
    _verdict,
    build_arbitration_dossier,
    write_arbitration_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_components_splits_disjoint_blobs():
    m = np.zeros((20, 20), dtype=bool)
    m[2:5, 2:5] = True
    m[10:13, 10:13] = True
    comps = _components(m)
    assert len(comps) == 2
    assert comps[0].sum() == 9 or comps[1].sum() == 9


def test_candidates_from_mask_drops_small_noise():
    m = np.zeros((20, 20), dtype=bool)
    m[2:5, 2:5] = True            # area 9
    m[18, 18] = True              # area 1 (noise)
    cands = candidates_from_mask(m, min_area=4, dilate=0)
    assert len(cands) == 1


def test_candidates_dilated():
    m = np.zeros((20, 20), dtype=bool)
    m[10, 10] = True
    m[10, 11] = True
    m[11, 10] = True
    m[11, 11] = True  # area 4
    cands = candidates_from_mask(m, min_area=4, dilate=2)
    assert len(cands) == 1
    # After 2-step dilation the candidate must be larger than the seed.
    assert cands[0].sum() > 4


def test_rank_candidates_by_area():
    c_small = np.zeros((10, 10), dtype=bool); c_small[0:2, 0:2] = True   # 4
    c_big   = np.zeros((10, 10), dtype=bool); c_big[0:5, 0:5] = True     # 25
    c_mid   = np.zeros((10, 10), dtype=bool); c_mid[0:3, 0:3] = True     # 9
    order = rank_candidates([c_small, c_big, c_mid])
    # Largest first -> c_big (index 1), then c_mid (index 2), then c_small
    assert order[0] == 1
    assert order[1] == 2
    assert order[2] == 0


def test_rank_empty():
    assert rank_candidates([]) == []


def test_verdict_boundaries():
    assert _verdict(0.9, 0.9) == "SURVIVES_WITH_TOP1"
    assert _verdict(0.9, 0.3) == "NEEDS_ORACLE_ARBITRATION"
    assert _verdict(0.3, 0.9) == "FAILS_UNDER_COMPETITION"
    # NaN oracle -> fails
    assert _verdict(float("nan"), 0.9) == "FAILS_UNDER_COMPETITION"


def test_dossier_shape_and_verdicts():
    d = build_arbitration_dossier(size=96)
    assert d["schema_version"] == "1.4"
    assert d["ranker"] == "largest_area"
    assert set(d["proposals"]) == {"propose_threshold", "propose_edges"}
    valid = {"SURVIVES_WITH_TOP1", "NEEDS_ORACLE_ARBITRATION",
             "FAILS_UNDER_COMPETITION"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
        for sr in rec["sub_relations"]:
            for key in ("sub_primitive", "relation_kind",
                        "per_method", "n_candidates_total",
                        "oracle_best", "top1", "worst",
                        "spread", "verdict"):
                assert key in sr
            assert sr["verdict"] in valid


def test_write_arbitration_reports(tmp_path: Path):
    write_arbitration_reports(tmp_path)
    assert (tmp_path / "arbitration.json").exists()
    assert (tmp_path / "ARBITRATION.md").exists()
    with open(tmp_path / "arbitration.json") as f:
        d = json.load(f)
    assert "per_composite" in d
    assert d["schema_version"] == "1.4"


def test_cardinality_fails_under_competition_in_mixed_scene():
    """In composite_repetition_cardinality, image-only proposals split
    into many candidates and the largest-area top1 does not line up with
    the small counted items. Expect NEEDS_ORACLE_ARBITRATION or
    FAILS_UNDER_COMPETITION for the cardinality sub-primitive."""
    d = build_arbitration_dossier(size=96)
    rec = d["per_composite"]["composite_repetition_cardinality"]
    cards = [sr for sr in rec["sub_relations"]
             if sr["sub_primitive"] == "cardinality"]
    assert cards
    sr = cards[0]
    t1 = sr["top1"]
    # top1 should NOT pass the robust threshold
    assert not (isinstance(t1, float) and t1 == t1 and t1 >= ROBUST_THR)
    assert sr["verdict"] in ("NEEDS_ORACLE_ARBITRATION",
                             "FAILS_UNDER_COMPETITION")
