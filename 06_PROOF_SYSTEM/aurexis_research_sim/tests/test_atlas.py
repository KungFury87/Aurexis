"""v0.6 atlas synthesis tests."""
from __future__ import annotations

import json
from pathlib import Path

from aurexis_sim.atlas import (
    build_atlas, write_atlas_reports,
    _classify, _find_first_failure,
    MILD_ROBUST, MILD_CONDITIONAL,
    HOSTILE_ROBUST, HOSTILE_CONDITIONAL,
)


def test_classify_buckets():
    assert _classify(0.95, 0.80) == "ROBUST"
    assert _classify(0.85, 0.50) == "CONDITIONAL"
    assert _classify(0.85, 0.20) == "FRAGILE"
    assert _classify(0.30, 0.10) == "FRAGILE"
    assert _classify(float("nan"), 0.9) == "UNKNOWN"


def test_find_first_failure():
    trace = {"s1": 1.0, "s2": 0.9, "s3": 0.7, "s4": 0.4, "s5": 0.2}
    assert _find_first_failure(trace, 0.8) == ("s3", 0.7)
    assert _find_first_failure(trace, 0.5) == ("s4", 0.4)
    assert _find_first_failure({"s1": 1.0}, 0.5) is None


def test_atlas_structure():
    atlas = build_atlas(seed=0)
    assert atlas["schema_version"] == "0.6"
    assert "per_relation" in atlas and len(atlas["per_relation"]) >= 5
    assert "ranked_fragility_under_hostile" in atlas
    assert "hostile_confusion" in atlas and "mild_confusion" in atlas
    # Each per_relation record has expected keys
    for kind, rec in atlas["per_relation"].items():
        for key in ("classification", "mild_hard_survival",
                    "hostile_hard_survival", "stage_first_below_0_8",
                    "stage_first_below_0_5", "right_axis_frontier",
                    "grid_collapse_fraction", "tags", "stage_trace_moderate"):
            assert key in rec, (kind, key)
        assert rec["classification"] in ("ROBUST", "CONDITIONAL",
                                          "FRAGILE", "UNKNOWN")


def test_atlas_ranking_monotone():
    atlas = build_atlas(seed=0)
    ranked = atlas["ranked_fragility_under_hostile"]
    # Sorted ascending by hostile survival
    prev = -1.0
    for _, s in ranked:
        assert s + 1e-9 >= prev
        prev = s


def test_atlas_contains_expected_classes():
    atlas = build_atlas(seed=0)
    buckets = {rec["classification"] for rec in atlas["per_relation"].values()}
    # Given the shipped captures, we expect at least two different buckets to appear.
    assert len(buckets - {"UNKNOWN"}) >= 2


def test_write_atlas_reports(tmp_path: Path):
    write_atlas_reports(tmp_path)
    assert (tmp_path / "atlas.json").exists()
    assert (tmp_path / "ATLAS.md").exists()
    with open(tmp_path / "atlas.json") as f:
        atlas = json.load(f)
    # Survives JSON round-trip
    assert "per_relation" in atlas
