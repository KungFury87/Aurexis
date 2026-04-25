"""v0.9 failure-attribution / redesign tests."""
from __future__ import annotations

import json
from pathlib import Path

from aurexis_sim.redesign import (
    build_redesign_dossier, write_redesign_reports,
    _rescale_toward, CHALLENGES, REDESIGN_LOOKUP,
)


def test_rescale_compresses_contrast():
    import numpy as np
    pkt = {"image": np.array([[0.0, 0.5, 1.0]], dtype=np.float32),
           "labels": None, "meta": {}}
    out = _rescale_toward(pkt, factor=0.8)
    # after compression toward 0.5 by factor 0.8, range should shrink to
    # 0.2 of original.
    assert abs(out["image"][0, 0] - 0.4) < 1e-5
    assert abs(out["image"][0, 2] - 0.6) < 1e-5


def test_challenges_cover_three_primitives():
    assert set(CHALLENGES.keys()) == {"ordering", "repetition", "role_zone"}


def test_each_primitive_has_baseline_and_3_challenges():
    for name, builder in CHALLENGES.items():
        entries = builder(size=96)
        names = [c for (c, _) in entries]
        assert "baseline" in names
        assert len(names) == 4  # baseline + 3 challenges


def test_dossier_shape():
    dossier = build_redesign_dossier(size=96)
    assert dossier["schema_version"] == "0.9"
    assert set(dossier["per_primitive"].keys()) == set(CHALLENGES.keys())
    for name, rec in dossier["per_primitive"].items():
        for key in ("baseline_survival_under_attribution_capture",
                    "challenge_survivals", "property_sensitivities",
                    "ranked_properties", "dominant_weakness",
                    "suggested_redesign"):
            assert key in rec, (name, key)


def test_redesign_lookup_covers_all_dominant_properties():
    # Every challenge name across all primitives should have an entry
    for name, builder in CHALLENGES.items():
        for (cname, _pkt) in builder(size=96):
            if cname == "baseline":
                continue
            assert cname in REDESIGN_LOOKUP, (name, cname)


def test_at_least_one_primitive_has_nonzero_dominant_sensitivity():
    dossier = build_redesign_dossier(size=96)
    nonzero = False
    for rec in dossier["per_primitive"].values():
        ranked = rec["ranked_properties"]
        if ranked and ranked[0][1] > 0.0:
            nonzero = True
    assert nonzero


def test_write_redesign_reports(tmp_path: Path):
    write_redesign_reports(tmp_path)
    assert (tmp_path / "redesign.json").exists()
    assert (tmp_path / "REDESIGN.md").exists()
    with open(tmp_path / "redesign.json") as f:
        dossier = json.load(f)
    assert "per_primitive" in dossier
