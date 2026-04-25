"""v1.3 inferred-binding / image-only proposal tests."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aurexis_sim.inferred_binding import (
    propose_threshold, propose_edges, PROPOSALS,
    build_inferred_binding_dossier, write_inferred_binding_reports,
    _verdict,
)
from aurexis_sim.binding import ROBUST_THR


def test_propose_threshold_returns_bool():
    img = np.zeros((32, 32), dtype=np.float32)
    img[10:14, 10:14] = 1.0
    mask = propose_threshold(img)
    assert mask.dtype == bool
    assert mask.shape == img.shape
    # The bright spot should be covered
    assert mask[12, 12]


def test_propose_edges_detects_contrast():
    img = np.zeros((32, 32), dtype=np.float32)
    img[:, 16:] = 1.0
    mask = propose_edges(img)
    # The edge region near column 16 should be covered
    assert mask[16, 16]


def test_propose_handles_uniform_image():
    img = np.full((32, 32), 0.5, dtype=np.float32)
    m1 = propose_threshold(img)
    m2 = propose_edges(img)
    # Uniform image -> no bright region, no edges. Masks can be empty.
    assert m1.dtype == bool and m2.dtype == bool


def test_proposals_registered():
    assert set(PROPOSALS.keys()) == {"propose_threshold", "propose_edges"}


def test_verdict_function():
    assert _verdict(0.9, {"propose_threshold": 0.9}) == "SURVIVES_WITH_INFERENCE"
    assert _verdict(0.9, {"propose_threshold": 0.3}) == "NEEDS_TIGHT_INFERENCE"
    assert _verdict(0.3, {"propose_threshold": 0.9}) == "FAILS_EVEN_PERFECT"


def test_dossier_shape():
    d = build_inferred_binding_dossier(size=96)
    assert d["schema_version"] == "1.3"
    assert set(d["proposals"]) == {"propose_threshold", "propose_edges"}
    for ck, rec in d["per_composite"].items():
        assert "overall_verdict" in rec
        for sr in rec["sub_relations"]:
            for key in ("sub_primitive", "relation_kind",
                        "unbound", "perfect", "soft_worst",
                        "inferred", "best_inferred", "best_proposal",
                        "verdict"):
                assert key in sr


def test_cardinality_fails_image_proposals_in_composite():
    """Image-only proposals can't isolate the cardinality region in
    composite_repetition_cardinality because the repetition row is
    bright too. Expect NEEDS_TIGHT_INFERENCE or FAILS_EVEN_PERFECT."""
    d = build_inferred_binding_dossier(size=96)
    rec = d["per_composite"]["composite_repetition_cardinality"]
    cards = [sr for sr in rec["sub_relations"]
             if sr["sub_primitive"] == "cardinality"]
    assert cards
    sr = cards[0]
    # Perfect should still be high (from v1.1 semantics)
    assert sr["perfect"] >= ROBUST_THR
    # But best image-only proposal should NOT clear the bar
    bi = sr["best_inferred"]
    assert not (isinstance(bi, float) and bi == bi and bi >= ROBUST_THR)
    assert sr["verdict"] in ("NEEDS_TIGHT_INFERENCE", "FAILS_EVEN_PERFECT")


def test_write_inferred_binding_reports(tmp_path: Path):
    write_inferred_binding_reports(tmp_path)
    assert (tmp_path / "inferred_binding.json").exists()
    assert (tmp_path / "INFERRED_BINDING.md").exists()
    with open(tmp_path / "inferred_binding.json") as f:
        d = json.load(f)
    assert "per_composite" in d
