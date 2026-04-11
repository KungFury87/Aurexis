"""
Pytest tests for Recovered Set Signature Match Bridge V1.

Proves that a recovered artifact set's computed signature can be compared
against a frozen expected-signature baseline and return a deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-set match proof, not general
document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    MatchVerdict, MatchResult,
    ExpectedSignatureBaseline, V1_MATCH_BASELINE,
    match_signature, match_from_png,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES, UNSUPPORTED_CASES,
    _get_expected_signatures,
)
from aurexis_lang.recovered_set_signature_bridge_v1 import (
    SignatureVerdict, V1_SIGNATURE_PROFILE,
    sign_recovered_set,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    PageContract, FROZEN_CONTRACTS,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def host_pngs_and_recoveries():
    """Pre-generate host PNGs and recovery results for all frozen layouts."""
    results = []
    for layout in FROZEN_LAYOUTS:
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        recovery = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        results.append((png, recovery))
    return results


# ── Module Constants ──────────────────────────────────────

def test_version():
    assert MATCH_VERSION == "V1.0"

def test_frozen():
    assert MATCH_FROZEN is True

def test_baseline_type():
    assert isinstance(V1_MATCH_BASELINE, ExpectedSignatureBaseline)

def test_baseline_version():
    assert V1_MATCH_BASELINE.version == "V1.0"

def test_baseline_contract_count():
    assert len(V1_MATCH_BASELINE.supported_contracts) == 5

def test_case_counts():
    assert len(IN_BOUNDS_CASES) == 5
    assert len(OUT_OF_BOUNDS_CASES) == 3
    assert len(UNSUPPORTED_CASES) == 1


# ── Expected-Signature Baseline ──────────────────────────

def test_baseline_has_5_signatures():
    sigs = _get_expected_signatures()
    assert len(sigs) == 5

def test_baseline_all_sha256_len():
    sigs = _get_expected_signatures()
    assert all(len(v) == 64 for v in sigs.values())

def test_baseline_all_unique():
    sigs = _get_expected_signatures()
    assert len(set(sigs.values())) == 5

@pytest.mark.parametrize("contract", FROZEN_CONTRACTS,
                         ids=[c.name for c in FROZEN_CONTRACTS])
def test_baseline_supports_contract(contract):
    assert V1_MATCH_BASELINE.is_supported(contract.name)

def test_baseline_rejects_unknown():
    assert not V1_MATCH_BASELINE.is_supported("nonexistent")

def test_baseline_frozen():
    with pytest.raises((AttributeError, TypeError)):
        V1_MATCH_BASELINE.version = "hacked"  # type: ignore


# ── In-Bounds Match ──────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES,
                         ids=[c["label"] for c in IN_BOUNDS_CASES])
def test_in_bounds_match(case, host_pngs_and_recoveries):
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    _, recovery = host_pngs_and_recoveries[idx]
    mr = match_signature(recovery, contract)
    assert mr.verdict == MatchVerdict.MATCH
    assert len(mr.computed_signature) == 64
    assert mr.computed_signature == mr.expected_signature
    assert mr.contract_name == contract.name
    assert mr.sign_verdict == "SIGNED"


# ── Stability ────────────────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES,
                         ids=[c["label"] for c in IN_BOUNDS_CASES])
def test_stability(case, host_pngs_and_recoveries):
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    _, recovery = host_pngs_and_recoveries[idx]
    mr1 = match_signature(recovery, contract)
    mr2 = match_signature(recovery, contract)
    assert mr1.verdict == mr2.verdict
    assert mr1.computed_signature == mr2.computed_signature

def test_stability_from_png(host_pngs_and_recoveries):
    png, _ = host_pngs_and_recoveries[0]
    mr1 = match_from_png(png, FROZEN_CONTRACTS[0])
    mr2 = match_from_png(png, FROZEN_CONTRACTS[0])
    assert mr1.verdict == MatchVerdict.MATCH
    assert mr1.computed_signature == mr2.computed_signature


# ── Out-of-Bounds ────────────────────────────────────────

@pytest.mark.parametrize("case", OUT_OF_BOUNDS_CASES,
                         ids=[c["label"] for c in OUT_OF_BOUNDS_CASES])
def test_out_of_bounds(case, host_pngs_and_recoveries):
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    _, recovery = host_pngs_and_recoveries[idx]
    mr = match_signature(recovery, contract)
    assert mr.verdict == MatchVerdict.SIGN_FAILED
    assert mr.computed_signature == ""

def test_empty_recovery():
    empty = MultiLayoutResult(
        verdict=MultiLayoutVerdict.NO_CANDIDATES,
        dispatched_count=0,
        dispatched_families=(),
    )
    mr = match_signature(empty, FROZEN_CONTRACTS[0])
    assert mr.verdict == MatchVerdict.SIGN_FAILED


# ── Unsupported ──────────────────────────────────────────

@pytest.mark.parametrize("case", UNSUPPORTED_CASES,
                         ids=[c["label"] for c in UNSUPPORTED_CASES])
def test_unsupported(case, host_pngs_and_recoveries):
    unknown_contract = PageContract(
        name=case["contract_name"],
        expected_count=case["expected_count"],
        expected_families=tuple(case["expected_families"]),
    )
    _, recovery = host_pngs_and_recoveries[0]
    mr = match_signature(recovery, unknown_contract)
    assert mr.verdict == MatchVerdict.UNSUPPORTED
    assert mr.computed_signature == ""
    assert mr.expected_signature == ""


# ── End-to-End from PNG ──────────────────────────────────

@pytest.mark.parametrize("case", IN_BOUNDS_CASES,
                         ids=[c["label"] for c in IN_BOUNDS_CASES])
def test_e2e_from_png(case, host_pngs_and_recoveries):
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    png, _ = host_pngs_and_recoveries[idx]
    mr = match_from_png(png, contract)
    assert mr.verdict == MatchVerdict.MATCH

def test_e2e_oob_from_png(host_pngs_and_recoveries):
    png, _ = host_pngs_and_recoveries[0]
    mr = match_from_png(png, FROZEN_CONTRACTS[2])
    assert mr.verdict == MatchVerdict.SIGN_FAILED


# ── Serialization ────────────────────────────────────────

def test_serialization(host_pngs_and_recoveries):
    _, recovery = host_pngs_and_recoveries[0]
    mr = match_signature(recovery, FROZEN_CONTRACTS[0])
    d = mr.to_dict()
    assert d["verdict"] == "MATCH"
    assert len(d["computed_signature"]) == 64
    assert len(d["expected_signature"]) == 64
    assert d["computed_signature"] == d["expected_signature"]
    assert d["contract_name"] == "two_horizontal_adj_cont"
    assert d["version"] == "V1.0"
    assert isinstance(d["dispatched_families"], list)


# ── Cross-Layout Uniqueness ──────────────────────────────

def test_cross_layout_signatures_unique():
    sigs = _get_expected_signatures()
    vals = list(sigs.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert vals[i] != vals[j], f"Sigs {i} and {j} should differ"


# ── Profile Validation ───────────────────────────────────

def test_baseline_contracts_correct():
    assert V1_MATCH_BASELINE.supported_contracts == (
        "two_horizontal_adj_cont",
        "two_vertical_adj_three",
        "three_row_all",
        "two_horizontal_cont_three",
        "two_vertical_three_adj",
    )

@pytest.mark.parametrize("name", V1_MATCH_BASELINE.supported_contracts)
def test_get_expected(name):
    sig = V1_MATCH_BASELINE.get_expected(name)
    assert sig is not None
    assert len(sig) == 64

def test_get_expected_unknown():
    assert V1_MATCH_BASELINE.get_expected("unknown") is None
