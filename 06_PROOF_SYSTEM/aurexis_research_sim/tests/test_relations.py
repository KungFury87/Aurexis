"""Relation-probe + relation-metric smoke tests (v0.3).

    python -m pytest tests -q
"""
from __future__ import annotations

import numpy as np

from aurexis_sim import truth as truth_mod
from aurexis_sim import metrics as metrics_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.sensor import SensorParams
from aurexis_sim.relations import (
    ordering_probe, adjacency_probe, symmetry_probe,
    orientation_probe, hierarchy_probe,
    compute_relation_metrics, relation_report,
)


def test_probes_registered():
    kinds = truth_mod.list_kinds()
    for k in ("ordering_probe", "adjacency_probe", "symmetry_probe",
              "orientation_probe", "hierarchy_probe"):
        assert k in kinds, "missing probe kind " + k


def test_probe_meta_advertises_relation():
    for kind in ("ordering_probe", "adjacency_probe", "symmetry_probe",
                 "orientation_probe", "hierarchy_probe"):
        pkt = truth_mod.generate(kind, size=96)
        rel = pkt["meta"].get("relation")
        assert isinstance(rel, dict)
        assert "kind" in rel


def test_ordering_identity_is_perfect():
    pkt = ordering_probe(size=96, n=6)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "ordering"
    assert m["relation_survival"] >= 0.99


def test_adjacency_identity_is_perfect():
    pkt = adjacency_probe(size=96, n_pairs=3)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "adjacency"
    assert m["relation_survival"] >= 0.99


def test_symmetry_identity_is_perfect():
    pkt = symmetry_probe(size=96, axis="vertical")
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "symmetry"
    assert m["relation_survival"] >= 0.95


def test_orientation_identity_is_perfect():
    pkt = orientation_probe(size=128, n=4)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "orientation"
    assert m["relation_survival"] >= 0.75  # tolerance on cardinal angles


def test_hierarchy_identity_is_perfect():
    pkt = hierarchy_probe(size=96)
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_kind"] == "hierarchy"
    assert m["relation_survival"] >= 0.99


def test_ordering_survives_mild_capture():
    pkt = ordering_probe(size=128, n=6)
    p = SimParams(blur_sigma=0.8, gauss_noise=0.01)
    out = run_chain(pkt["image"], p, seed=0)
    m = compute_relation_metrics(pkt, out["captured"])
    assert m["relation_survival"] >= 0.8


def test_compute_all_includes_relation_for_probe():
    pkt = ordering_probe(size=96, n=5)
    p = SimParams()
    out = run_chain(pkt["image"], p, seed=0)
    m = metrics_mod.compute_all(pkt, out["captured"])
    assert "relation_kind" in m and "relation_survival" in m
    assert m["relation_kind"] == "ordering"


def test_relation_report_has_every_stage():
    pkt = ordering_probe(size=96, n=5)
    p = SimParams(blur_sigma=0.5)
    rep = relation_report(pkt, p, seed=0)
    # Expect at minimum these keys
    for stage in ("source", "geometric", "optical_blur", "photometric",
                  "noise", "quantize", "captured"):
        assert stage in rep, "missing stage " + stage


def test_hostile_degrades_ordering_vs_clean():
    pkt = ordering_probe(size=128, n=8)
    clean = run_chain(pkt["image"], SimParams(), seed=0)["captured"]
    hostile = run_chain(pkt["image"], SimParams(
        blur_sigma=4.0, gauss_noise=0.15, bit_depth=3, gamma=2.2,
    ), seed=0)["captured"]
    m_clean = compute_relation_metrics(pkt, clean)["relation_survival"]
    m_hostile = compute_relation_metrics(pkt, hostile)["relation_survival"]
    assert m_hostile <= m_clean + 1e-9


def test_hierarchy_degrades_under_heavy_blur():
    pkt = hierarchy_probe(size=128, seed=0)
    clean = run_chain(pkt["image"], SimParams(), seed=0)["captured"]
    blurry = run_chain(pkt["image"],
                       SimParams(blur_sigma=6.0), seed=0)["captured"]
    m_clean = compute_relation_metrics(pkt, clean)["relation_survival"]
    m_blur = compute_relation_metrics(pkt, blurry)["relation_survival"]
    assert m_blur <= m_clean + 1e-9
