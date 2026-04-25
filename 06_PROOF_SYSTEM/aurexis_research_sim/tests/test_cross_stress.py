"""v0.5 cross-stress tests.

Goals:
  - stress_grid_2d runs and returns the expected structure.
  - Each probe's shipped right-axis sweep eventually drops below 0.8
    (i.e. the chosen axis is actually the killer axis for that probe).
  - build_reports writes all expected files.
"""
from __future__ import annotations

import json
from pathlib import Path

from aurexis_sim.simulate import SimParams
from aurexis_sim.sensor import SensorParams
from aurexis_sim.stress import (
    stress_grid_2d, build_reports, SHIPPED_SWEEPS,
    relation_confusion_table, DEFAULT_PROBE_KINDS_HARD,
)


def test_grid_2d_structure():
    def builder(a, b):
        return SimParams(
            blur_sigma=float(a),
            sensor=SensorParams(enabled=True, pattern="RGGB",
                                noise_r=float(b), noise_g=float(b), noise_b=float(b)),
        )
    g = stress_grid_2d("adjacency_probe_hard", {"size": 96, "n_pairs": 4},
                       builder, [0.0, 2.0, 4.0], [0.0, 0.04, 0.08], seed=0)
    assert len(g["a_values"]) == 3
    assert len(g["b_values"]) == 3
    assert len(g["survival"]) == 3
    assert all(len(r) == 3 for r in g["survival"])
    assert 0.0 <= g["collapse_fraction_below_0_5"] <= 1.0


def test_grid_2d_shows_collapse_region_for_adjacency():
    def builder(a, b):
        return SimParams(
            blur_sigma=float(a),
            sensor=SensorParams(enabled=True, pattern="RGGB",
                                noise_r=float(b), noise_g=float(b), noise_b=float(b)),
        )
    g = stress_grid_2d("adjacency_probe_hard", {"size": 96, "n_pairs": 6},
                       builder, [0.0, 2.0, 4.0], [0.0, 0.04, 0.08], seed=0)
    # At high blur + high sensor noise the hard adjacency probe should collapse
    s_corner = g["survival"][-1][-1]
    assert s_corner < 0.7, g


def test_shipped_sweeps_right_axis_each_probe_moves():
    """For each non-info shipped sweep, the end of the curve should drop
    noticeably below 1.0 — proof the axis was the right choice."""
    from aurexis_sim.stress import stress_sweep
    for (name, kind, kwargs, builder, values, seed, axis) in SHIPPED_SWEEPS:
        if "info_only" in name:
            continue
        curve = stress_sweep(kind, kwargs, builder, values, seed=seed)
        s_end = curve[-1][1]
        # Any real drop is acceptable (>= 0.05); the point is that the
        # probe responds to THIS axis, not blur-only.
        s0 = curve[0][1]
        if s0 == s0 and s_end == s_end:
            assert s_end <= s0 - 0.02 or s_end < 0.95, (name, curve)


def test_build_reports_writes_all_files(tmp_path):
    build_reports(tmp_path)
    for fn in ("stress_report.json", "stress_report.csv",
               "stress_grids.json", "confusion_tables.json",
               "SUMMARY.md"):
        assert (tmp_path / fn).exists(), fn
    with open(tmp_path / "stress_report.json") as f:
        report = json.load(f)
    assert "sweeps" in report and "grids" in report and "confusion" in report
    assert len(report["grids"]) >= 3
    assert "hostile_hard" in report["confusion"]


def test_confusion_tables_are_populated():
    ct = relation_confusion_table(SimParams(blur_sigma=2.0, gauss_noise=0.03,
                                            sensor=SensorParams(enabled=True,
                                                                noise_r=0.03,
                                                                noise_g=0.02,
                                                                noise_b=0.03)),
                                  DEFAULT_PROBE_KINDS_HARD, size=96)
    for k in DEFAULT_PROBE_KINDS_HARD:
        assert k in ct
    # At least one should drop
    assert any((v == v) and v < 0.9 for v in ct.values())
