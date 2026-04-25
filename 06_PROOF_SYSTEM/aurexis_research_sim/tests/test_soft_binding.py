"""v1.2 soft-binding / imperfect ROI tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.soft_binding import (
    _dilate, _erode, _shift, _noisy,
    build_soft_modes, build_soft_binding_dossier,
    write_soft_binding_reports, _verdict,
)
from aurexis_sim.binding import roi_from_labels, ROBUST_THR


def test_dilate_grows_mask():
    m = np.zeros((10, 10), dtype=bool); m[5, 5] = True
    d = _dilate(m, 2)
    assert d[5, 5] and d[3, 5] and d[7, 5] and d[5, 3] and d[5, 7]
    assert d.sum() > m.sum()


def test_erode_shrinks_mask():
    m = np.zeros((10, 10), dtype=bool); m[4:7, 4:7] = True
    e = _erode(m, 1)
    assert e.sum() < m.sum()
    # Center survives one erosion
    assert e[5, 5]


def test_shift_translates_mask():
    m = np.zeros((10, 10), dtype=bool); m[5, 5] = True
    s = _shift(m, 0, 2)
    assert s[5, 7] and not s[5, 5]


def test_noisy_flips_some_pixels():
    m = np.zeros((20, 20), dtype=bool)
    n = _noisy(m, 0.5, seed=0)
    # Expect roughly 50% True
    assert 0.3 < n.mean() < 0.7


def test_build_soft_modes_has_expected_names():
    lab = np.zeros((32, 32), dtype=np.int32); lab[10:14, 10:14] = 1
    perfect = roi_from_labels(lab, dilate=2)
    modes = build_soft_modes(perfect, size_hint=32, seed=0)
    assert set(modes.keys()) == {"perfect", "dilate_extra", "erode",
                                  "shift_px", "noisy_10pct"}


def test_verdict_function():
    assert _verdict(0.9, 0.9, {"perfect": 0.9, "dilate_extra": 0.9,
                                "erode": 0.85, "shift_px": 0.9,
                                "noisy_10pct": 0.9}) == "ROBUST_TO_SOFT_BINDING"
    assert _verdict(0.3, 0.9, {"perfect": 0.9, "dilate_extra": 0.9,
                                "erode": 0.3, "shift_px": 0.9,
                                "noisy_10pct": 0.9}) == "NEEDS_TIGHT_BINDING"
    assert _verdict(0.3, 0.3, {"perfect": 0.3}) == "FAILS_EVEN_PERFECT"


def test_dossier_shape():
    d = build_soft_binding_dossier(size=96)
    assert d["schema_version"] == "1.2"
    for ck, rec in d["per_composite"].items():
        assert "overall_verdict" in rec
        for sr in rec["sub_relations"]:
            assert "mode_survival" in sr
            assert set(sr["mode_survival"].keys()) == set(d["soft_modes"])
            assert sr["verdict"] in ("ROBUST_TO_SOFT_BINDING",
                                       "NEEDS_TIGHT_BINDING",
                                       "FAILS_EVEN_PERFECT")


def test_cardinality_degrades_under_noisy_mask():
    """The v1.1 NEEDS_BINDING case should be re-classified here as
    NEEDS_TIGHT_BINDING because the noisy mask knocks cardinality back
    down even though perfect ROI restores it."""
    d = build_soft_binding_dossier(size=96)
    rec = d["per_composite"]["composite_repetition_cardinality"]
    cards = [sr for sr in rec["sub_relations"]
             if sr["sub_primitive"] == "cardinality"]
    assert cards
    sr = cards[0]
    assert sr["mode_survival"]["perfect"] >= 0.8
    # At least one soft mode should drop it below the robust threshold
    drops = [v for m, v in sr["mode_survival"].items()
             if m != "perfect" and isinstance(v, float) and v == v
             and v < ROBUST_THR]
    assert len(drops) >= 1
    assert sr["verdict"] in ("NEEDS_TIGHT_BINDING", "FAILS_EVEN_PERFECT")


def test_write_soft_binding_reports(tmp_path: Path):
    write_soft_binding_reports(tmp_path)
    assert (tmp_path / "soft_binding.json").exists()
    assert (tmp_path / "SOFT_BINDING.md").exists()
    with open(tmp_path / "soft_binding.json") as f:
        d = json.load(f)
    assert "per_composite" in d
