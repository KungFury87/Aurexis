"""v1.8 primitive-aware coverage / repetition strip-fix tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.coverage import (
    _largest_contiguous_strip,
    repetition_survival_bound_strip,
    rank_by_repetition_target_strip,
    composite_repetition_distractor,
    COVERAGE_COMPOSITES,
    LABEL_SCOPED_KINDS,
    _verdict,
    build_coverage_dossier,
    write_coverage_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_largest_contiguous_strip_full():
    m = np.ones(20, dtype=bool)
    assert _largest_contiguous_strip(m) == (0, 20)


def test_largest_contiguous_strip_empty():
    m = np.zeros(20, dtype=bool)
    assert _largest_contiguous_strip(m) == (0, 0)


def test_largest_contiguous_strip_picks_longest():
    m = np.zeros(40, dtype=bool)
    m[2:6] = True       # length 4
    m[10:24] = True     # length 14 (longest)
    m[30:32] = True     # length 2
    s, e = _largest_contiguous_strip(m)
    assert (s, e) == (10, 24)


def test_largest_contiguous_strip_at_end():
    m = np.zeros(20, dtype=bool)
    m[14:20] = True
    assert _largest_contiguous_strip(m) == (14, 20)


def test_repetition_strip_returns_zero_when_strip_too_short():
    """If col_mask at row_y has no run of length >= 2*period, the
    strip metric returns 0 rather than falling back to the full row."""
    captured = np.full((40, 80), 0.20, dtype=np.float32)
    # Periodic pattern at row 20, period 10
    for cx in range(5, 80, 10):
        captured[19:21, cx-1:cx+2] = 0.95
    pkt = {"meta": {"relation": {"kind": "repetition",
                                   "period_px": 10.0, "row_y": 20}}}
    # ROI is far from row 20 -> col_mask at row 20 is all False
    roi_far = np.zeros((40, 80), dtype=bool); roi_far[0:5, 0:80] = True
    assert repetition_survival_bound_strip(pkt, captured, roi_far) == 0.0


def test_repetition_strip_detects_period_when_strip_long():
    captured = np.full((40, 80), 0.20, dtype=np.float32)
    for cx in range(5, 80, 10):
        captured[19:21, cx-1:cx+2] = 0.95
    pkt = {"meta": {"relation": {"kind": "repetition",
                                   "period_px": 10.0, "row_y": 20}}}
    roi = np.zeros((40, 80), dtype=bool); roi[15:25, 0:80] = True
    s = repetition_survival_bound_strip(pkt, captured, roi)
    assert s >= 0.80


def test_rank_by_repetition_target_strip_handles_empty():
    assert rank_by_repetition_target_strip([], None, 10.0, 5) == []
    cap = np.zeros((20, 20), dtype=np.float32)
    c = np.ones((20, 20), dtype=bool)
    assert rank_by_repetition_target_strip([c], cap, None, 5) == []
    assert rank_by_repetition_target_strip([c], cap, 10.0, None) == []


def test_composite_repetition_distractor_shape():
    pkt = composite_repetition_distractor(size=128)
    assert pkt["image"].shape == (128, 128)
    sub = pkt["meta"]["composite"][0]
    assert sub["name"] == "repetition"
    assert sub["relation"]["kind"] == "repetition"
    assert sub["relation"]["period_px"] >= 10
    assert "row_y" in sub["relation"]


def test_coverage_composites_includes_distractor_set():
    """COVERAGE_COMPOSITES must include the v1.5 distractor composites
    plus the new repetition distractor."""
    assert "composite_cardinality_with_decoy" in COVERAGE_COMPOSITES
    assert "composite_cardinality_ranker_split" in COVERAGE_COMPOSITES
    assert "composite_repetition_distractor" in COVERAGE_COMPOSITES


def test_label_scoped_set():
    assert LABEL_SCOPED_KINDS == {"ordering", "adjacency", "symmetry",
                                    "orientation", "hierarchy", "role_zone"}


def test_verdict_boundaries():
    # oracle fails
    assert _verdict(0.3, 0.9, 0.9) == "PROPOSAL_QUALITY_LIMIT"
    # label-scoped: invariant regardless of generic / target
    assert _verdict(0.9, 0.3, 0.3, label_scoped=True) == "ARBITRATION_INVARIANT"
    # generic ok
    assert _verdict(0.9, 0.9, 0.9) == "GENERIC_FUSION_SUFFICIENT"
    # only target ok
    assert _verdict(0.9, 0.3, 0.9) == "PRIMITIVE_AWARE_HELPS"
    # both fail
    assert _verdict(0.9, 0.3, 0.3) == "PRIMITIVE_AWARE_STILL_FAILS"


def test_dossier_shape_and_keys():
    d = build_coverage_dossier()
    assert d["schema_version"] == "1.8"
    assert "cardinality_target" in d["primitive_aware_rankers"]
    assert "repetition_target_strip" in d["primitive_aware_rankers"]
    valid = {"GENERIC_FUSION_SUFFICIENT", "ARBITRATION_INVARIANT",
             "PRIMITIVE_AWARE_HELPS", "PRIMITIVE_AWARE_STILL_FAILS",
             "PROPOSAL_QUALITY_LIMIT"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
        for sr in rec["sub_relations"]:
            for k in ("sub_primitive", "relation_kind", "n_candidates",
                      "target_params", "label_scoped",
                      "oracle_best", "generic_top1",
                      "best_generic", "best_generic_name",
                      "primitive_aware", "verdict"):
                assert k in sr


def test_repetition_distractor_primitive_aware_helps():
    """v1.8 headline: target-conditioned repetition scoring rescues
    composite_repetition_distractor where every generic ranker fails."""
    d = build_coverage_dossier()
    rec = d["per_composite"]["composite_repetition_distractor"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    assert sr["best_generic"] < ROBUST_THR
    assert sr["primitive_aware"] >= ROBUST_THR


def test_cardinality_with_decoy_still_helps_under_v18():
    """v1.7's cardinality result must still hold under v1.8."""
    d = build_coverage_dossier()
    rec = d["per_composite"]["composite_cardinality_with_decoy"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"


def test_write_coverage_reports(tmp_path: Path):
    write_coverage_reports(tmp_path)
    assert (tmp_path / "coverage.json").exists()
    assert (tmp_path / "COVERAGE.md").exists()
    with open(tmp_path / "coverage.json") as f:
        d = json.load(f)
    assert d["schema_version"] == "1.8"
    assert "per_composite" in d
