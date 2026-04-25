"""v1.0 composite / interaction tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim import truth as truth_mod
from aurexis_sim.interaction import (
    COMPOSITES, build_interaction_dossier, write_interaction_reports,
    _flag, _worst_flag,
)


def test_composite_probes_registered():
    kinds = truth_mod.list_kinds()
    for k in COMPOSITES.keys():
        assert k in kinds


def test_composite_probes_expose_subrelations():
    for kind, builder in COMPOSITES.items():
        pkt = builder(size=128)
        comp = pkt["meta"].get("composite")
        assert isinstance(comp, list) and len(comp) >= 2
        for sub in comp:
            assert "name" in sub and "labels" in sub and "relation" in sub
            assert isinstance(sub["labels"], np.ndarray)


def test_flag_function():
    assert _flag(0.01) == "BINDING_OK"
    assert _flag(0.15) == "CROWDING"
    assert _flag(0.50) == "BINDING_FAILURE"
    assert _flag(float("nan")) == "UNKNOWN"


def test_worst_flag_picks_severest():
    assert _worst_flag(["BINDING_OK", "CROWDING"]) == "CROWDING"
    assert _worst_flag(["BINDING_OK", "BINDING_FAILURE", "CROWDING"]) == "BINDING_FAILURE"
    assert _worst_flag(["BINDING_OK", "BINDING_OK"]) == "BINDING_OK"
    assert _worst_flag([]) == "UNKNOWN"


def test_dossier_shape():
    dossier = build_interaction_dossier(size=96)
    assert dossier["schema_version"] == "1.0"
    assert set(dossier["per_composite"].keys()) == set(COMPOSITES.keys())
    for ck, rec in dossier["per_composite"].items():
        assert "overall_flag" in rec
        assert "sub_relations" in rec
        assert len(rec["sub_relations"]) >= 2
        for sr in rec["sub_relations"]:
            for key in ("sub_primitive", "survival_in_composite",
                        "survival_alone", "interference", "flag"):
                assert key in sr


def test_at_least_one_composite_shows_interference():
    dossier = build_interaction_dossier(size=96)
    any_nontrivial = False
    for rec in dossier["per_composite"].values():
        for sr in rec["sub_relations"]:
            it = sr["interference"]
            if isinstance(it, float) and it == it and it > 0.05:
                any_nontrivial = True
    assert any_nontrivial


def test_write_interaction_reports(tmp_path: Path):
    write_interaction_reports(tmp_path)
    assert (tmp_path / "interaction.json").exists()
    assert (tmp_path / "INTERACTION.md").exists()
    with open(tmp_path / "interaction.json") as f:
        dossier = json.load(f)
    assert "per_composite" in dossier
