"""Smoke tests for Aurexis Research Sim (v0.1 contract preserved in v0.2).

    python -m pytest tests -q
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim import truth as truth_mod
from aurexis_sim import metrics as metrics_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.presets import (
    preset_from_ui, save_preset, load_preset, params_from_preset,
    log_run, list_presets,
)


def test_truth_registry_nonempty():
    kinds = truth_mod.list_kinds()
    assert len(kinds) >= 6
    for k in kinds:
        pkt = truth_mod.generate(k, size=64) if k != "grid" else truth_mod.generate(k, size=64, cell=16)
        assert pkt["image"].dtype == np.float32
        # v0.2: accept grayscale (64,64) OR RGB (64,64,3)
        assert pkt["image"].shape in ((64, 64), (64, 64, 3))
        assert 0.0 <= pkt["image"].min() and pkt["image"].max() <= 1.0


def test_chain_clean_is_identity_ish():
    pkt = truth_mod.generate("blocks", size=64, n=8, seed=0)
    result = run_chain(pkt["image"], SimParams(), seed=0)
    m = metrics_mod.compute_all(pkt, result["captured"])
    assert m["psnr_db"] > 40.0
    assert m["edge_survival"] > 0.95
    assert m["ssim_simple"] > 0.95


def test_chain_degrades_under_hostile_params():
    pkt = truth_mod.generate("blocks", size=64, n=8, seed=0)
    clean = run_chain(pkt["image"], SimParams(), seed=0)
    hostile = run_chain(pkt["image"], SimParams(
        blur_sigma=3.0, gauss_noise=0.08, bit_depth=4, gamma=1.8,
    ), seed=0)
    m_clean = metrics_mod.compute_all(pkt, clean["captured"])
    m_hostile = metrics_mod.compute_all(pkt, hostile["captured"])
    assert m_hostile["psnr_db"] < m_clean["psnr_db"]
    assert m_hostile["ssim_simple"] <= m_clean["ssim_simple"]


def test_metrics_with_labels():
    pkt = truth_mod.generate("phoxel_probe", size=64, cell=8, seed=0)
    result = run_chain(pkt["image"], SimParams(blur_sigma=0.5), seed=0)
    m = metrics_mod.compute_all(pkt, result["captured"])
    assert not (m["adjacency_survival"] != m["adjacency_survival"])


def test_corruption_map_shape_and_range():
    pkt = truth_mod.generate("grid", size=64, cell=16, line=1)
    result = run_chain(pkt["image"], SimParams(blur_sigma=1.0), seed=0)
    corr = metrics_mod.local_corruption_map(pkt["image"], result["captured"], block=16)
    assert corr.ndim == 2
    assert 0.0 <= corr.min() and corr.max() <= 1.0 + 1e-6


def test_preset_roundtrip(tmp_path):
    params = SimParams(blur_sigma=1.5, gauss_noise=0.02, bit_depth=7)
    preset = preset_from_ui("unit_preset", "blocks",
                            {"size": 64, "n": 4, "seed": 0}, params, seed=3)
    save_preset(preset, "unit_preset", presets_dir=tmp_path)
    assert "unit_preset" in list_presets(presets_dir=tmp_path)
    loaded = load_preset("unit_preset", presets_dir=tmp_path)
    p2 = params_from_preset(loaded)
    assert abs(p2.blur_sigma - params.blur_sigma) < 1e-9
    assert p2.bit_depth == params.bit_depth


def test_run_logging(tmp_path):
    pkt = truth_mod.generate("blocks", size=64, n=4, seed=0)
    params = SimParams(blur_sigma=0.5)
    result = run_chain(pkt["image"], params, seed=0)
    m = metrics_mod.compute_all(pkt, result["captured"])
    preset = preset_from_ui("log_test", "blocks",
                            {"size": 64, "n": 4, "seed": 0}, params, 0)
    run_dir = log_run(preset, pkt["image"], result["captured"], m, runs_dir=tmp_path)
    assert (run_dir / "preset.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "truth.png").exists()
    assert (run_dir / "captured.png").exists()
    assert (run_dir / "diff.png").exists()
    with open(run_dir / "metrics.json") as f:
        j = json.load(f)
    assert "psnr_db" in j
