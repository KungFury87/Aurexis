"""v2.0 blocked-family unlock / ROI-sensitive ordering + symmetry tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.unlock import (
    ordering_survival_bound,
    rank_by_ordering_target,
    symmetry_survival_bound,
    rank_by_symmetry_target,
    composite_ordering_distractor,
    composite_symmetry_distractor,
    UNLOCK_COMPOSITES,
    LABEL_SCOPED_NO_ROI_V20,
    _per_composite_verdict,
    _family_verdict,
    build_unlock_dossier,
    write_unlock_reports,
)
from aurexis_sim.binding import ROBUST_THR


def test_label_scoped_set_v20_excludes_ordering_and_symmetry():
    """v2.0: ordering and symmetry have ROI-aware metrics and are NOT
    in the no-ROI label-scoped set anymore."""
    assert "ordering" not in LABEL_SCOPED_NO_ROI_V20
    assert "symmetry" not in LABEL_SCOPED_NO_ROI_V20
    assert LABEL_SCOPED_NO_ROI_V20 == {"adjacency", "orientation", "hierarchy"}


def test_ordering_survival_returns_zero_when_too_few_components():
    cap = np.full((40, 80), 0.10, dtype=np.float32)
    cap[19:21, 10:13] = 0.95   # only one component
    roi = np.ones((40, 80), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "ordering", "target_count": 5}}}
    s = ordering_survival_bound(pkt, cap, roi, target_count=5)
    assert s == 0.0


def test_ordering_survival_passes_with_monotone_sequence():
    cap = np.full((40, 80), 0.10, dtype=np.float32)
    # 4 markers in a row at increasing brightness
    for i, cx in enumerate((10, 25, 40, 55)):
        cap[19:22, cx-2:cx+3] = 0.40 + 0.15 * i
    roi = np.ones((40, 80), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "ordering", "target_count": 4}}}
    s = ordering_survival_bound(pkt, cap, roi, target_count=4)
    assert s >= 0.80  # all pairs are increasing -> 1.0 monotonicity


def test_ordering_survival_low_for_random_brightness():
    cap = np.full((40, 80), 0.10, dtype=np.float32)
    # 5 markers at non-monotone brightness
    pos_b = [(10, 0.50), (25, 0.95), (40, 0.30), (55, 0.80), (70, 0.55)]
    for cx, b in pos_b:
        cap[19:22, cx-2:cx+3] = b
    roi = np.ones((40, 80), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "ordering", "target_count": 5}}}
    s = ordering_survival_bound(pkt, cap, roi, target_count=5)
    assert s < 0.80


def test_rank_by_ordering_target_handles_empty():
    assert rank_by_ordering_target([], None, 5) == []


def test_symmetry_survival_returns_zero_for_single_component():
    """A single round component must not pass trivially - the metric
    requires >= 2 components inside the ROI."""
    cap = np.full((40, 80), 0.10, dtype=np.float32)
    cap[18:23, 38:43] = 0.95
    roi = np.ones((40, 80), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "symmetry", "axis": "vertical"}}}
    s = symmetry_survival_bound(pkt, cap, roi, target_axis="vertical")
    assert s == 0.0


def test_symmetry_survival_returns_zero_for_narrow_bbox():
    cap = np.full((40, 20), 0.10, dtype=np.float32)
    cap[18:23, 8:11] = 0.95
    cap[18:23, 13:16] = 0.95  # 2 components but bbox width ~10 < 20
    roi = np.zeros((40, 20), dtype=bool); roi[15:25, 5:18] = True
    pkt = {"meta": {"relation": {"kind": "symmetry", "axis": "vertical"}}}
    s = symmetry_survival_bound(pkt, cap, roi, target_axis="vertical")
    assert s == 0.0


def test_symmetry_survival_passes_for_left_right_mirror():
    cap = np.full((40, 80), 0.10, dtype=np.float32)
    # 4 markers arranged exactly symmetrically: i mirrors to (79-i)
    # at bbox width 80.
    pairs = [(15, 64), (25, 54)]
    for x_left, x_right in pairs:
        cap[18:22, x_left-1:x_left+2] = 0.85
        cap[18:22, x_right-1:x_right+2] = 0.85
    roi = np.ones((40, 80), dtype=bool)
    pkt = {"meta": {"relation": {"kind": "symmetry", "axis": "vertical"}}}
    s = symmetry_survival_bound(pkt, cap, roi, target_axis="vertical")
    assert s >= 0.80


def test_rank_by_symmetry_target_handles_empty():
    assert rank_by_symmetry_target([], None, "vertical") == []
    cap = np.zeros((20, 20), dtype=np.float32)
    c = np.ones((20, 20), dtype=bool)
    assert rank_by_symmetry_target([c], cap, None) == []


def test_composite_ordering_distractor_shape():
    pkt = composite_ordering_distractor(size=128)
    assert pkt["image"].shape == (128, 128)
    sub = pkt["meta"]["composite"][0]
    assert sub["name"] == "ordering"
    assert sub["relation"]["kind"] == "ordering"
    assert sub["relation"]["target_count"] >= 2


def test_composite_symmetry_distractor_shape():
    pkt = composite_symmetry_distractor(size=128)
    assert pkt["image"].shape == (128, 128)
    sub = pkt["meta"]["composite"][0]
    assert sub["name"] == "symmetry"
    assert sub["relation"]["kind"] == "symmetry"
    assert sub["relation"]["axis"] in ("vertical", "horizontal")


def test_unlock_composites_includes_new_probes():
    assert "composite_ordering_distractor" in UNLOCK_COMPOSITES
    assert "composite_symmetry_distractor" in UNLOCK_COMPOSITES
    assert "composite_role_zone_decoy" in UNLOCK_COMPOSITES


def test_per_composite_verdict_label_scoped_v20():
    """The remaining label-scoped families produce METRIC_GAP_ROI_INSENSITIVE."""
    for fam in LABEL_SCOPED_NO_ROI_V20:
        v = _per_composite_verdict(0.9, 0.9, 0.9, fam)
        assert v == "METRIC_GAP_ROI_INSENSITIVE"
    # ordering and symmetry are no longer label-scoped
    v = _per_composite_verdict(0.9, 0.3, 0.9, "ordering")
    assert v == "PRIMITIVE_AWARE_HELPS"
    v = _per_composite_verdict(0.9, 0.3, 0.9, "symmetry")
    assert v == "PRIMITIVE_AWARE_HELPS"


def test_dossier_shape_and_keys():
    d = build_unlock_dossier()
    assert d["schema_version"] == "2.0"
    for r in ("ordering_target", "symmetry_target",
              "cardinality_target", "repetition_target_strip",
              "role_zone_target"):
        assert r in d["primitive_aware_rankers"]
    valid = {"GENERIC_FUSION_SUFFICIENT", "ARBITRATION_INVARIANT",
             "METRIC_GAP_ROI_INSENSITIVE", "PRIMITIVE_AWARE_HELPS",
             "PRIMITIVE_AWARE_STILL_FAILS", "PROPOSAL_QUALITY_LIMIT"}
    for ck, rec in d["per_composite"].items():
        assert rec["overall_verdict"] in valid
    assert "family_boundary_map" in d
    fm = d["family_boundary_map"]
    for fam in ("adjacency", "orientation", "hierarchy"):
        assert fam in fm
        assert fm[fam]["boundary_tag"] == "METRIC_GAP_ROI_INSENSITIVE"


def test_five_families_now_help():
    """v2.0 headline: 5 of 8 primitive families now show PRIMITIVE_AWARE_HELPS."""
    d = build_unlock_dossier()
    fm = d["family_boundary_map"]
    for fam in ("cardinality", "repetition", "role_zone",
                "ordering", "symmetry"):
        assert fm[fam]["boundary_tag"] == "PRIMITIVE_AWARE_HELPS", \
            "family {} expected PRIMITIVE_AWARE_HELPS, got {}".format(
                fam, fm[fam]["boundary_tag"])


def test_ordering_distractor_primitive_aware_helps():
    d = build_unlock_dossier()
    rec = d["per_composite"]["composite_ordering_distractor"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    assert sr["best_generic"] < ROBUST_THR
    assert sr["primitive_aware"] >= ROBUST_THR


def test_symmetry_distractor_primitive_aware_helps():
    d = build_unlock_dossier()
    rec = d["per_composite"]["composite_symmetry_distractor"]
    assert rec["overall_verdict"] == "PRIMITIVE_AWARE_HELPS"
    sr = rec["sub_relations"][0]
    assert sr["oracle_best"] >= ROBUST_THR
    assert sr["best_generic"] < ROBUST_THR
    assert sr["primitive_aware"] >= ROBUST_THR


def test_write_unlock_reports(tmp_path: Path):
    write_unlock_reports(tmp_path)
    assert (tmp_path / "unlock.json").exists()
    assert (tmp_path / "UNLOCK.md").exists()
    with open(tmp_path / "unlock.json") as f:
        d = json.load(f)
    assert "family_boundary_map" in d
