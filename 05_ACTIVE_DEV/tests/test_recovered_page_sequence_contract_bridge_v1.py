"""
Pytest tests for Recovered Page Sequence Contract Bridge V1.

Proves that a small ordered sequence of recovered pages can be validated
against a frozen sequence-level contract.

This is a narrow deterministic recovered-sequence proof, not general
document workflow or open-ended multi-page intelligence.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SEQUENCE_VERSION, SEQUENCE_FROZEN,
    SequenceVerdict, SequenceContract, SequenceProfile,
    PageSequenceResult,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    validate_sequence, validate_sequence_from_contracts,
    generate_sequence_host_pngs,
    _get_sequence_expected, _contract_name_to_layout_index,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES, WRONG_ORDER_CASES,
    WRONG_CONTENT_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MatchVerdict, V1_MATCH_BASELINE, _get_expected_signatures,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import FROZEN_CONTRACTS
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    generate_multi_artifact_host, build_layout_spec, FROZEN_LAYOUTS,
)


# ── Module-scoped fixtures ────────────────────────────────

@pytest.fixture(scope="module")
def single_page_sigs():
    return _get_expected_signatures()


@pytest.fixture(scope="module")
def sequence_expected():
    return _get_sequence_expected()


@pytest.fixture(scope="module")
def all_host_pngs():
    """Pre-generate host PNGs for all frozen sequence contracts."""
    return {
        sc.name: generate_sequence_host_pngs(sc)
        for sc in FROZEN_SEQUENCE_CONTRACTS
    }


# ── Module constants ──────────────────────────────────────

class TestModuleConstants:
    def test_version(self):
        assert SEQUENCE_VERSION == "V1.0"

    def test_frozen(self):
        assert SEQUENCE_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_SEQUENCE_PROFILE, SequenceProfile)

    def test_profile_version(self):
        assert V1_SEQUENCE_PROFILE.version == "V1.0"

    def test_frozen_contract_count(self):
        assert len(FROZEN_SEQUENCE_CONTRACTS) == 3

    def test_case_counts(self):
        assert len(IN_BOUNDS_CASES) == 3
        assert len(WRONG_COUNT_CASES) == 2
        assert len(WRONG_ORDER_CASES) == 2
        assert len(WRONG_CONTENT_CASES) == 1
        assert len(UNSUPPORTED_CASES) == 1


# ── Frozen sequence contracts ──────────────────────────────

class TestFrozenContracts:
    def test_two_page_hv(self):
        sc = FROZEN_SEQUENCE_CONTRACTS[0]
        assert sc.name == "two_page_horizontal_vertical"
        assert sc.expected_page_count == 2
        assert sc.page_contract_names == (
            "two_horizontal_adj_cont", "two_vertical_adj_three",
        )

    def test_three_page_all(self):
        sc = FROZEN_SEQUENCE_CONTRACTS[1]
        assert sc.name == "three_page_all_families"
        assert sc.expected_page_count == 3

    def test_two_page_mixed(self):
        sc = FROZEN_SEQUENCE_CONTRACTS[2]
        assert sc.name == "two_page_mixed_reversed"
        assert sc.expected_page_count == 2

    def test_page_contract_lookup(self):
        sc = FROZEN_SEQUENCE_CONTRACTS[0]
        assert sc.get_page_contract(0).name == "two_horizontal_adj_cont"
        assert sc.get_page_contract(1).name == "two_vertical_adj_three"
        assert sc.get_page_contract(2) is None
        assert sc.get_page_contract(-1) is None


# ── Expected signature sequence baseline ───────────────────

class TestExpectedSignatures:
    def test_sequence_expected_count(self, sequence_expected):
        assert len(sequence_expected) == 3

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_sig_count_matches_page_count(self, idx, sequence_expected):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        sigs = sequence_expected[sc.name]
        assert len(sigs) == sc.expected_page_count

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_sigs_match_single_page(self, idx, sequence_expected, single_page_sigs):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        sigs = sequence_expected[sc.name]
        for i, name in enumerate(sc.page_contract_names):
            assert sigs[i] == single_page_sigs[name]

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_sigs_are_valid_hex(self, idx, sequence_expected):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        sigs = sequence_expected[sc.name]
        for sig in sigs:
            assert len(sig) == 64
            assert all(c in "0123456789abcdef" for c in sig)


# ── Host PNG generation ────────────────────────────────────

class TestHostPngGeneration:
    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_png_count(self, idx):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        pngs = generate_sequence_host_pngs(sc)
        assert len(pngs) == sc.expected_page_count

    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_png_headers(self, idx):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        pngs = generate_sequence_host_pngs(sc)
        for png in pngs:
            assert isinstance(png, bytes)
            assert len(png) > 100
            assert png[:8] == b'\x89PNG\r\n\x1a\n'


# ── In-bounds sequence validation ──────────────────────────

class TestInBoundsValidation:
    @pytest.mark.parametrize("case", IN_BOUNDS_CASES,
                             ids=[c["label"] for c in IN_BOUNDS_CASES])
    def test_in_bounds(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        result = validate_sequence_from_contracts(sc)
        assert result.verdict == SequenceVerdict.SEQUENCE_SATISFIED
        assert result.sequence_contract_name == sc.name
        assert result.expected_page_count == sc.expected_page_count
        assert result.actual_page_count == sc.expected_page_count
        assert len(result.page_match_results) == sc.expected_page_count
        assert len(result.failed_page_indices) == 0
        for mr in result.page_match_results:
            assert mr.verdict == MatchVerdict.MATCH


# ── Stability ──────────────────────────────────────────────

class TestStability:
    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_repeated_runs_stable(self, idx):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        r1 = validate_sequence_from_contracts(sc)
        r2 = validate_sequence_from_contracts(sc)
        assert r1.verdict == r2.verdict
        assert r1.page_signatures == r2.page_signatures
        assert r1.expected_signatures == r2.expected_signatures


# ── Wrong page count ───────────────────────────────────────

class TestWrongPageCount:
    @pytest.mark.parametrize("case", WRONG_COUNT_CASES,
                             ids=[c["label"] for c in WRONG_COUNT_CASES])
    def test_wrong_count(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        all_pngs = generate_sequence_host_pngs(sc)
        provide_count = case["provide_page_count"]
        if provide_count < len(all_pngs):
            test_pngs = all_pngs[:provide_count]
        else:
            test_pngs = all_pngs + (all_pngs[-1],) * (provide_count - len(all_pngs))
        result = validate_sequence(test_pngs, sc)
        assert result.verdict == SequenceVerdict.WRONG_PAGE_COUNT


# ── Wrong page order ───────────────────────────────────────

class TestWrongPageOrder:
    @pytest.mark.parametrize("case", WRONG_ORDER_CASES,
                             ids=[c["label"] for c in WRONG_ORDER_CASES])
    def test_wrong_order(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        correct_pngs = generate_sequence_host_pngs(sc)
        reversed_pngs = tuple(reversed(correct_pngs))
        if correct_pngs != reversed_pngs:
            result = validate_sequence(reversed_pngs, sc)
            assert result.verdict == SequenceVerdict.WRONG_PAGE_ORDER
            # Per-position matching naturally fails for wrong-order pages
            assert len(result.failed_page_indices) > 0


# ── Wrong page content ─────────────────────────────────────

class TestWrongPageContent:
    @pytest.mark.parametrize("case", WRONG_CONTENT_CASES,
                             ids=[c["label"] for c in WRONG_CONTENT_CASES])
    def test_wrong_content(self, case):
        sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
        wrong_pngs = []
        for li in case["substitute_layout_indices"]:
            layout = FROZEN_LAYOUTS[li]
            spec = build_layout_spec(layout)
            wrong_pngs.append(generate_multi_artifact_host(spec))
        result = validate_sequence(tuple(wrong_pngs), sc)
        assert result.verdict == SequenceVerdict.PAGE_MATCH_FAILED
        assert len(result.failed_page_indices) > 0


# ── Unsupported sequence ───────────────────────────────────

class TestUnsupportedSequence:
    def test_unsupported(self):
        fake = SequenceContract(
            name="nonexistent_sequence_contract",
            expected_page_count=2,
            page_contract_names=("two_horizontal_adj_cont", "two_vertical_adj_three"),
        )
        pngs = generate_sequence_host_pngs(FROZEN_SEQUENCE_CONTRACTS[0])
        result = validate_sequence(pngs, fake)
        assert result.verdict == SequenceVerdict.UNSUPPORTED_SEQUENCE


# ── Contract-to-layout mapping ─────────────────────────────

class TestContractLayoutMapping:
    @pytest.mark.parametrize("idx", range(5))
    def test_mapping(self, idx):
        assert _contract_name_to_layout_index(FROZEN_CONTRACTS[idx].name) == idx

    def test_unknown(self):
        assert _contract_name_to_layout_index("nonexistent") is None


# ── Serialization ──────────────────────────────────────────

class TestSerialization:
    def test_to_dict(self):
        sc = FROZEN_SEQUENCE_CONTRACTS[0]
        result = validate_sequence_from_contracts(sc)
        d = result.to_dict()
        assert d["verdict"] == "SEQUENCE_SATISFIED"
        assert d["sequence_contract_name"] == sc.name
        assert d["expected_page_count"] == 2
        assert d["actual_page_count"] == 2
        assert len(d["page_match_results"]) == 2
        assert len(d["page_signatures"]) == 2
        assert len(d["failed_page_indices"]) == 0
        assert d["version"] == SEQUENCE_VERSION


# ── E2E cross-validation ──────────────────────────────────

class TestE2ECrossValidation:
    @pytest.mark.parametrize("idx", [0, 1, 2])
    def test_e2e(self, idx, single_page_sigs):
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        result = validate_sequence_from_contracts(sc)
        assert result.verdict == SequenceVerdict.SEQUENCE_SATISFIED
        for i, sig in enumerate(result.page_signatures):
            expected = single_page_sigs[sc.page_contract_names[i]]
            assert sig == expected
