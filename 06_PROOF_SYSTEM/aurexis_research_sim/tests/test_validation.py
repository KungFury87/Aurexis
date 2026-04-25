"""v0.8 anti-triviality / validation tests."""
from __future__ import annotations

import json
from pathlib import Path

from aurexis_sim import truth as truth_mod
from aurexis_sim.relations import compute_relation_metrics
from aurexis_sim.validation import (
    validate_promoted_primitives, write_validation_reports,
    PROMOTED, _verdict, ROBUST_THR, CONDITIONAL_THR, NEG_CTRL_MAX,
)


def test_hard_variants_identity_strong():
    for kind in ("role_zone_probe_hard", "repetition_probe_hard"):
        pkt = truth_mod.generate(kind, size=128)
        m = compute_relation_metrics(pkt, pkt["image"])
        assert m["relation_survival"] >= 0.85


def test_negative_controls_score_low_on_identity():
    cases = [
        ("null_relation_probe",        {"size": 128, "relation_kind": "ordering"}),
        ("null_relation_probe",        {"size": 128, "relation_kind": "role_zone"}),
        ("scrambled_ordering_probe",   {"size": 128, "n": 8}),
        ("non_repetition_probe",       {"size": 128, "n": 7}),
        ("equalized_role_zone_probe",  {"size": 128, "n_secondary": 4}),
    ]
    for kind, kw in cases:
        pkt = truth_mod.generate(kind, **kw)
        m = compute_relation_metrics(pkt, pkt["image"])
        assert m["relation_survival"] <= 0.7, (kind, m)


def test_ordering_identity_with_equal_means_is_not_trivially_robust():
    # v0.8 tightening: all-equal means -> 0 score, not spurious 1.0
    pkt = truth_mod.generate("null_relation_probe",
                              size=128, relation_kind="ordering")
    m = compute_relation_metrics(pkt, pkt["image"])
    assert m["relation_survival"] <= 0.05


def test_verdict_function_logic():
    good_base = {"s1": 0.9, "s2": 0.85}
    good_hard = {"s1": 0.7, "s2": 0.6}
    clean_neg = {"n1": 0.2, "n2": 0.1}
    assert _verdict(good_base, good_hard, clean_neg) == "EARNED_ROBUST"
    assert _verdict(good_base, {"s1": 0.3, "s2": 0.6}, clean_neg) == "WEAK_ROBUST"
    assert _verdict(good_base, good_hard, {"n1": 0.7}) == "SUSPECT"
    bad_base = {"s1": 0.5, "s2": 0.85}
    assert _verdict(bad_base, good_hard, clean_neg) == "NOT_ROBUST"


def test_validation_runs_and_emits_expected_shape():
    report = validate_promoted_primitives()
    assert report["schema_version"] == "0.8"
    assert set(report["per_primitive"].keys()) == set(PROMOTED.keys())
    for name, rec in report["per_primitive"].items():
        assert "verdict" in rec
        assert rec["verdict"] in ("EARNED_ROBUST", "WEAK_ROBUST",
                                    "SUSPECT", "NOT_ROBUST")
        assert isinstance(rec["base_survival_per_scenario"], dict)
        assert isinstance(rec["hard_survival_per_scenario"], dict)
        assert isinstance(rec["negative_control_results"], dict)


def test_write_validation_reports(tmp_path: Path):
    write_validation_reports(tmp_path)
    assert (tmp_path / "validation.json").exists()
    assert (tmp_path / "VALIDATION.md").exists()
    with open(tmp_path / "validation.json") as f:
        report = json.load(f)
    assert "per_primitive" in report


def test_at_least_one_v07_promotion_downgraded():
    """v0.7 marked ordering / repetition / role_zone as STABLE_ROBUST.
    v0.8 anti-triviality should downgrade at least one of them from
    EARNED_ROBUST to SUSPECT / WEAK_ROBUST / NOT_ROBUST. That's the
    point of the anti-triviality pass."""
    report = validate_promoted_primitives()
    verdicts = {name: rec["verdict"]
                for name, rec in report["per_primitive"].items()}
    non_earned = [name for name, v in verdicts.items() if v != "EARNED_ROBUST"]
    assert len(non_earned) >= 1, verdicts
