"""
Tests for Artifact Set Contract Bridge V1.

Proves that a recovered ordered set of artifacts from a multi-artifact
host image can be checked against an explicit page-level contract
with honest acceptance or rejection.

This is a narrow deterministic recovered-set proof, not general
document intelligence or open-ended schema validation.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'aurexis_lang', 'src'))

import pytest

from aurexis_lang.artifact_set_contract_bridge_v1 import (
    CONTRACT_VERSION, CONTRACT_FROZEN,
    V1_CONTRACT_PROFILE, ContractProfile,
    PageContract, FROZEN_CONTRACTS,
    ContractVerdict, ContractResult,
    validate_contract, validate_contract_from_png,
    find_matching_contract,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
)


# ════════════════════════════════════════════════════════════
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

class TestModuleConstants:
    def test_version(self):
        assert CONTRACT_VERSION == "V1.0"

    def test_frozen(self):
        assert CONTRACT_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_CONTRACT_PROFILE, ContractProfile)

    def test_contract_count(self):
        assert len(FROZEN_CONTRACTS) == 5

    def test_in_bounds_count(self):
        assert len(IN_BOUNDS_CASES) == 5

    def test_oob_count(self):
        assert len(OUT_OF_BOUNDS_CASES) == 4


# ════════════════════════════════════════════════════════════
# CONTRACT STRUCTURE
# ════════════════════════════════════════════════════════════

class TestContractStructure:
    def test_unique_names(self):
        names = [c.name for c in FROZEN_CONTRACTS]
        assert len(names) == len(set(names))

    def test_min_count(self):
        assert all(c.expected_count >= 2 for c in FROZEN_CONTRACTS)

    def test_families_match_count(self):
        for c in FROZEN_CONTRACTS:
            assert len(c.expected_families) == c.expected_count

    def test_all_families_known(self):
        valid = {"adjacent_pair", "containment", "three_regions"}
        for c in FROZEN_CONTRACTS:
            for f in c.expected_families:
                assert f in valid

    def test_contract_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            FROZEN_CONTRACTS[0].name = "hacked"  # type: ignore


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

class TestInBounds:
    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_satisfied(self, idx):
        case = IN_BOUNDS_CASES[idx]
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, contract)
        assert cr.verdict == ContractVerdict.SATISFIED, (
            f"{case['label']}: expected SATISFIED, got {cr.verdict}")

    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_count_match(self, idx):
        case = IN_BOUNDS_CASES[idx]
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, contract)
        assert cr.recovered_count == contract.expected_count

    @pytest.mark.parametrize("idx", list(range(len(IN_BOUNDS_CASES))))
    def test_families_match(self, idx):
        case = IN_BOUNDS_CASES[idx]
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, contract)
        assert cr.recovered_families == contract.expected_families


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

class TestOutOfBounds:
    @pytest.mark.parametrize("idx", list(range(len(OUT_OF_BOUNDS_CASES))))
    def test_violation(self, idx):
        case = OUT_OF_BOUNDS_CASES[idx]
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, contract)
        assert cr.verdict.value == case["expected_verdict"], (
            f"{case['label']}: expected {case['expected_verdict']}, "
            f"got {cr.verdict.value}")

    @pytest.mark.parametrize("idx", list(range(len(OUT_OF_BOUNDS_CASES))))
    def test_not_satisfied(self, idx):
        case = OUT_OF_BOUNDS_CASES[idx]
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, contract)
        assert cr.verdict != ContractVerdict.SATISFIED


# ════════════════════════════════════════════════════════════
# RECOVERY FAILURE
# ════════════════════════════════════════════════════════════

class TestRecoveryFailure:
    def test_empty_recovery(self):
        empty = MultiLayoutResult(
            verdict=MultiLayoutVerdict.NO_CANDIDATES,
            dispatched_count=0,
            dispatched_families=(),
        )
        cr = validate_contract(empty, FROZEN_CONTRACTS[0])
        assert cr.verdict == ContractVerdict.RECOVERY_FAILED

    def test_partial_recovery(self):
        partial = MultiLayoutResult(
            verdict=MultiLayoutVerdict.PARTIAL_RECOVERY,
            dispatched_count=1,
            dispatched_families=("adjacent_pair",),
        )
        cr = validate_contract(partial, FROZEN_CONTRACTS[0])
        assert cr.verdict == ContractVerdict.VIOLATED_COUNT


# ════════════════════════════════════════════════════════════
# FIND MATCHING CONTRACT
# ════════════════════════════════════════════════════════════

class TestFindMatching:
    @pytest.mark.parametrize("idx", list(range(len(FROZEN_LAYOUTS))))
    def test_layout_finds_correct_contract(self, idx):
        layout = FROZEN_LAYOUTS[idx]
        spec = build_layout_spec(layout)
        png = generate_multi_artifact_host(spec)
        recovery = multi_artifact_recover_and_dispatch(
            png, expected_families=layout["expected_families"])
        matched = find_matching_contract(recovery)
        assert matched is not None
        assert matched.name == FROZEN_CONTRACTS[idx].name

    def test_empty_no_match(self):
        empty = MultiLayoutResult(
            verdict=MultiLayoutVerdict.NO_CANDIDATES,
            dispatched_count=0,
            dispatched_families=(),
        )
        assert find_matching_contract(empty) is None


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

class TestDeterminism:
    def test_repeated_identical(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        cr1 = validate_contract_from_png(png, FROZEN_CONTRACTS[0])
        cr2 = validate_contract_from_png(png, FROZEN_CONTRACTS[0])
        assert cr1.verdict == cr2.verdict
        assert cr1.recovered_families == cr2.recovered_families
        assert cr1.recovered_count == cr2.recovered_count


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

class TestSerialization:
    def test_result_to_dict(self):
        spec = build_layout_spec(FROZEN_LAYOUTS[0])
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, FROZEN_CONTRACTS[0])
        d = cr.to_dict()
        assert d["verdict"] == "SATISFIED"
        assert d["version"] == "V1.0"
        assert d["expected_count"] == 2
        assert d["recovered_count"] == 2
        assert isinstance(d["expected_families"], list)
        assert isinstance(d["recovered_families"], list)


# ════════════════════════════════════════════════════════════
# CROSS-VALIDATION MATRIX
# ════════════════════════════════════════════════════════════

class TestCrossValidation:
    @pytest.mark.parametrize("i", list(range(len(FROZEN_LAYOUTS))))
    def test_diagonal_satisfied(self, i):
        """Layout i should satisfy contract i."""
        spec = build_layout_spec(FROZEN_LAYOUTS[i])
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, FROZEN_CONTRACTS[i])
        assert cr.verdict == ContractVerdict.SATISFIED

    @pytest.mark.parametrize(
        "i,j",
        [(i, j) for i in range(len(FROZEN_LAYOUTS))
         for j in range(len(FROZEN_CONTRACTS)) if i != j]
    )
    def test_off_diagonal_not_satisfied(self, i, j):
        """Layout i should NOT satisfy contract j (when i != j)."""
        spec = build_layout_spec(FROZEN_LAYOUTS[i])
        png = generate_multi_artifact_host(spec)
        cr = validate_contract_from_png(png, FROZEN_CONTRACTS[j])
        assert cr.verdict != ContractVerdict.SATISFIED
