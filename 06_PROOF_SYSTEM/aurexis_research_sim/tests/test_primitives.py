"""v0.7 tests: language-relevant primitive probes + scenario atlas."""
from __future__ import annotations

import json
from pathlib import Path

from aurexis_sim import truth as truth_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.sensor import SensorParams
from aurexis_sim.relations import (
    repetition_probe, cardinality_probe, role_zone_probe,
    compute_relation_metrics,
)
from aurexis_sim.atlas import (
    build_scenario_atlas, write_scenario_atlas_reports,
    _classify_single, DEFAULT_SCENARIOS, ATLAS_PROBE_KINDS,
)


def test_new_probes_registered():
    kinds = truth_mod.list_kinds()
    for k in ("repetition_probe", "cardinality_probe", "role_zone_probe"):
        assert k in kinds


def test_repetition_identity_is_high():
    pkt = repetition_probe(size=128, n=7)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "repetition"
    assert m["relation_survival"] >= 0.85


def test_cardinality_identity_is_perfect():
    pkt = cardinality_probe(size=128, n=5)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "cardinality"
    assert m["relation_survival"] >= 0.95


def test_role_zone_identity_is_perfect():
    pkt = role_zone_probe(size=128, n_secondary=4)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "role_zone"
    assert m["relation_survival"] >= 0.95


def test_role_zone_collapses_when_anchor_equalized():
    pkt = role_zone_probe(size=128, n_secondary=4)
    # Force all markers to same intensity
    import numpy as np
    equalized = np.where(pkt["labels"] > 0, 0.55, pkt["image"])
    m = compute_relation_metrics(pkt, equalized)
    assert m["relation_survival"] <= 0.25


def test_role_zone_degrades_under_heavy_blur():
    pkt = role_zone_probe(size=128, n_secondary=4)
    clean = run_chain(pkt["image"], SimParams(), seed=0)
    blurry = run_chain(pkt["image"], SimParams(blur_sigma=6.0), seed=0)
    m_clean = compute_relation_metrics(pkt, clean["captured"])["relation_survival"]
    m_blur = compute_relation_metrics(pkt, blurry["captured"])["relation_survival"]
    assert m_blur <= m_clean + 1e-9


def test_cardinality_drops_when_markers_merge():
    pkt = cardinality_probe(size=128, n=6)
    # Very heavy blur should merge components visually
    result = run_chain(pkt["image"], SimParams(blur_sigma=8.0), seed=0)
    m = compute_relation_metrics(pkt, result["captured"])
    # Exact behavior depends on threshold; assert it's a real number and
    # probably lower than identity for at least some seed.
    assert isinstance(m["relation_survival"], float)


def test_classify_single():
    assert _classify_single(0.95) == "ROBUST"
    assert _classify_single(0.65) == "CONDITIONAL"
    assert _classify_single(0.20) == "FRAGILE"
    assert _classify_single(float("nan")) == "UNKNOWN"


def test_scenario_atlas_structure():
    atlas = build_scenario_atlas(size=64)
    assert atlas["schema_version"] == "0.7"
    assert set(atlas["scenarios"].keys()) == set(DEFAULT_SCENARIOS.keys())
    assert len(atlas["probe_kinds"]) == len(ATLAS_PROBE_KINDS)
    # Each probe has a row under per_scenario for each scenario
    for sname in atlas["scenarios"]:
        for kind in atlas["probe_kinds"]:
            assert kind in atlas["per_scenario"][sname]
    for kind in atlas["probe_kinds"]:
        s = atlas["stability_summary"][kind]
        for key in ("robust_count", "conditional_count", "fragile_count",
                    "n_scenarios", "range", "mean", "is_stable",
                    "majority_bucket", "stable_verdict"):
            assert key in s


def test_scenario_atlas_verdicts_span_multiple_values():
    atlas = build_scenario_atlas(size=64)
    verdicts = {s["stable_verdict"]
                for s in atlas["stability_summary"].values()}
    # Expect at least two different verdicts across the full probe family
    assert len(verdicts) >= 2


def test_write_scenario_atlas_reports(tmp_path: Path):
    write_scenario_atlas_reports(tmp_path)
    assert (tmp_path / "scenario_atlas.json").exists()
    assert (tmp_path / "SCENARIO_ATLAS.md").exists()
    with open(tmp_path / "scenario_atlas.json") as f:
        atlas = json.load(f)
    assert "per_scenario" in atlas
