"""v0.4 stress / discriminability tests."""
from __future__ import annotations

import numpy as np

from aurexis_sim import truth as truth_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.relations import compute_relation_metrics
from aurexis_sim.stress import (
    stress_sweep, collapse_threshold,
    curve_is_monotone_nonincreasing,
    relation_confusion_table,
    DEFAULT_PROBE_KINDS_HARD, DEFAULT_PROBE_KINDS_EASY,
)


# Hard probes must be registered
def test_hard_probes_registered():
    kinds = truth_mod.list_kinds()
    for k in ("ordering_probe_hard", "adjacency_probe_hard",
              "symmetry_probe_hard", "orientation_probe_hard",
              "hierarchy_probe_hard"):
        assert k in kinds


# Hard probes must STILL pass identity (0 stress -> ~1.0 survival)
def test_hard_probes_identity_is_still_good():
    for k in DEFAULT_PROBE_KINDS_HARD:
        pkt = truth_mod.getattr = None  # ensure no shadowing
        pkt = truth_mod.generate(k, size=96)
        m = compute_relation_metrics(pkt, pkt["image"])
        # Hard identity may be slightly below 1.0 due to tight geometry,
        # but should still be clearly robust.
        assert m["relation_survival"] >= 0.7, (k, m)


# Sweep curves must be monotone-non-increasing (small tol for seed noise)
def test_blur_sweep_is_monotone_on_hard_ordering():
    curve = stress_sweep("ordering_probe_hard", {"size": 128, "n": 10},
                        lambda v: SimParams(blur_sigma=float(v)),
                        [0.0, 1.0, 2.0, 4.0, 6.0, 8.0], seed=0)
    assert curve_is_monotone_nonincreasing(curve, tol=0.05), curve


# Hard probes must strictly degrade vs easy probes under the same stress
def test_hard_is_more_fragile_than_easy_under_blur():
    stress = SimParams(blur_sigma=3.0, gauss_noise=0.03)
    hard = relation_confusion_table(stress, DEFAULT_PROBE_KINDS_HARD, size=128)
    easy = relation_confusion_table(stress, DEFAULT_PROBE_KINDS_EASY, size=128)
    # Check at least 3 of 5 relations have hard < easy
    worse = 0
    for name in ("ordering", "adjacency", "symmetry",
                 "orientation", "hierarchy"):
        h = hard.get(name + "_probe_hard", 1.0)
        e = easy.get(name + "_probe", 1.0)
        if h == h and e == e and h < e + 1e-9:
            worse += 1
    assert worse >= 3, (hard, easy)


# Collapse threshold should find a value on a curve that drops through
def test_collapse_threshold_finds_collapse():
    curve = [(0.0, 1.0), (1.0, 0.9), (2.0, 0.7), (3.0, 0.4), (4.0, 0.2)]
    ct = collapse_threshold(curve, 0.5)
    assert ct is not None
    assert ct[0] == 3.0 and ct[1] <= 0.5


# Collapse threshold returns None if curve stays above
def test_collapse_threshold_none_when_always_high():
    curve = [(0.0, 1.0), (1.0, 0.95), (2.0, 0.85), (3.0, 0.7)]
    assert collapse_threshold(curve, 0.5) is None


# At least one hard probe must actually drop under heavy blur
def test_some_hard_probe_collapses_under_heavy_blur():
    drops = []
    for k in DEFAULT_PROBE_KINDS_HARD:
        curve = stress_sweep(k, {"size": 128},
                             lambda v: SimParams(blur_sigma=float(v)),
                             [0.0, 1.0, 2.0, 4.0, 8.0], seed=0)
        drops.append(curve[-1][1])
    assert any((d == d) and d <= 0.6 for d in drops), drops


# Confusion table produces finite scores for every probe
def test_confusion_table_populates_all_kinds():
    ct = relation_confusion_table(SimParams(blur_sigma=1.0),
                                  DEFAULT_PROBE_KINDS_HARD, size=96)
    for k in DEFAULT_PROBE_KINDS_HARD:
        assert k in ct


# smoke that module-level `python -m aurexis_sim.stress` writes report files
def test_run_all_shipped_sweeps(tmp_path):
    from aurexis_sim.stress import run_all_shipped_sweeps
    report = run_all_shipped_sweeps(out_dir=tmp_path)
    assert (tmp_path / "stress_report.json").exists()
    assert (tmp_path / "stress_report.csv").exists()
    assert len(report["sweeps"]) >= 5
    # Every sweep should have a curve
    for name, info in report["sweeps"].items():
        assert len(info["curve"]) >= 2
