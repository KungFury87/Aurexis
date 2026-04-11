"""
Aurexis Core — Artifact Set Contract Bridge V1

Bounded page-level contract validation for the narrow V1 raster bridge.
Proves that a recovered ordered set of artifacts from a multi-artifact
host image can be checked against a small frozen family of explicit
page-level contracts — expected count, expected artifact families,
expected deterministic order — with honest acceptance or rejection.

What this proves:
  Given a multi-artifact host image and a frozen page-level contract,
  the system can recover the artifact set via the existing multi-artifact
  layout bridge, then deterministically validate whether the recovered
  set satisfies the contract (exact count, exact families, exact order).

What this does NOT prove:
  - Open-ended document understanding
  - Arbitrary page semantics or schema validation
  - Generic validation of unknown layouts
  - Dynamic or user-defined contract schemas
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Page-level contract: frozen dataclass specifying expected_count
    and expected_families (ordered tuple of family names)
  - Contract validation: recover multi-artifact set from host image →
    compare dispatched_count and dispatched_families against contract
  - Five frozen contracts matching the five frozen layouts
  - Four violation modes: RECOVERY_FAILED, VIOLATED_COUNT,
    VIOLATED_FAMILY, VIOLATED_ORDER
  - All operations are deterministic

This is a narrow deterministic recovered-set proof, not general
document intelligence or open-ended schema validation.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile,
    FROZEN_LAYOUTS,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    V1_TOLERANCE_PROFILE, ToleranceProfile,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE, DispatchProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CONTRACT_VERSION = "V1.0"
CONTRACT_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN PAGE-LEVEL CONTRACT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PageContract:
    """
    A frozen page-level contract specifying the expected artifact set.

    name: unique identifier for the contract
    expected_count: exact number of artifacts expected
    expected_families: ordered tuple of expected artifact family names
    description: human-readable description of the contract
    """
    name: str
    expected_count: int
    expected_families: Tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class ContractProfile:
    """
    Frozen profile defining the supported page-level contracts.
    Only contracts listed here are considered in-bounds.
    """
    contracts: Tuple[PageContract, ...]
    version: str = CONTRACT_VERSION


# ════════════════════════════════════════════════════════════
# FROZEN CONTRACT DEFINITIONS
# ════════════════════════════════════════════════════════════

FROZEN_CONTRACTS = (
    PageContract(
        name="two_horizontal_adj_cont",
        expected_count=2,
        expected_families=("adjacent_pair", "containment"),
        description="Two artifacts in horizontal row: adjacent_pair left, containment right",
    ),
    PageContract(
        name="two_vertical_adj_three",
        expected_count=2,
        expected_families=("adjacent_pair", "three_regions"),
        description="Two artifacts in vertical stack: adjacent_pair top, three_regions bottom",
    ),
    PageContract(
        name="three_row_all",
        expected_count=3,
        expected_families=("adjacent_pair", "containment", "three_regions"),
        description="Three artifacts in horizontal row: all three families left to right",
    ),
    PageContract(
        name="two_horizontal_cont_three",
        expected_count=2,
        expected_families=("containment", "three_regions"),
        description="Two artifacts in horizontal row: containment left, three_regions right",
    ),
    PageContract(
        name="two_vertical_three_adj",
        expected_count=2,
        expected_families=("three_regions", "adjacent_pair"),
        description="Two artifacts in vertical stack: three_regions top, adjacent_pair bottom",
    ),
)

V1_CONTRACT_PROFILE = ContractProfile(contracts=FROZEN_CONTRACTS)


# ════════════════════════════════════════════════════════════
# CONTRACT VERDICTS
# ════════════════════════════════════════════════════════════

class ContractVerdict(str, Enum):
    """Outcome of page-level contract validation."""
    SATISFIED = "SATISFIED"                # Recovered set matches contract exactly
    RECOVERY_FAILED = "RECOVERY_FAILED"    # Multi-artifact recovery did not succeed
    VIOLATED_COUNT = "VIOLATED_COUNT"      # Wrong number of dispatched artifacts
    VIOLATED_FAMILY = "VIOLATED_FAMILY"    # Right count but wrong family names
    VIOLATED_ORDER = "VIOLATED_ORDER"      # Right families but wrong order
    UNKNOWN_CONTRACT = "UNKNOWN_CONTRACT"  # Contract not in frozen profile
    ERROR = "ERROR"                        # Unexpected error


@dataclass
class ContractResult:
    """Complete result of page-level contract validation."""
    verdict: ContractVerdict = ContractVerdict.ERROR
    contract_name: str = ""
    expected_count: int = 0
    expected_families: Tuple[str, ...] = ()
    recovered_count: int = 0
    recovered_families: Tuple[str, ...] = ()
    recovery_verdict: str = ""
    version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "contract_name": self.contract_name,
            "expected_count": self.expected_count,
            "expected_families": list(self.expected_families),
            "recovered_count": self.recovered_count,
            "recovered_families": list(self.recovered_families),
            "recovery_verdict": self.recovery_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CONTRACT VALIDATION LOGIC
# ════════════════════════════════════════════════════════════

def validate_contract(
    recovery_result: MultiLayoutResult,
    contract: PageContract,
) -> ContractResult:
    """
    Validate a recovered multi-artifact result against a page-level contract.

    Checks in order:
    1. Recovery must have produced dispatched artifacts
    2. Dispatched count must match contract.expected_count
    3. Dispatched family names must match contract.expected_families
       (both names and order)

    If the families are correct as a set but in wrong order,
    returns VIOLATED_ORDER instead of VIOLATED_FAMILY to provide
    a more specific diagnostic.

    Deterministic: same recovery_result + same contract → identical verdict.
    """
    result = ContractResult(
        contract_name=contract.name,
        expected_count=contract.expected_count,
        expected_families=contract.expected_families,
        recovered_count=recovery_result.dispatched_count,
        recovered_families=recovery_result.dispatched_families,
        recovery_verdict=recovery_result.verdict.value,
    )

    # Step 1: Check that recovery itself succeeded
    if recovery_result.dispatched_count == 0:
        result.verdict = ContractVerdict.RECOVERY_FAILED
        return result

    # Step 2: Check count
    if recovery_result.dispatched_count != contract.expected_count:
        result.verdict = ContractVerdict.VIOLATED_COUNT
        return result

    # Step 3: Check families (exact tuple match = names + order)
    if recovery_result.dispatched_families == contract.expected_families:
        result.verdict = ContractVerdict.SATISFIED
        return result

    # Step 4: Distinguish wrong-order from wrong-family
    if sorted(recovery_result.dispatched_families) == sorted(contract.expected_families):
        result.verdict = ContractVerdict.VIOLATED_ORDER
    else:
        result.verdict = ContractVerdict.VIOLATED_FAMILY

    return result


def validate_contract_from_png(
    host_png: bytes,
    contract: PageContract,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> ContractResult:
    """
    Full end-to-end contract validation from a host image.

      host_png → multi-artifact recovery → contract validation

    Convenience function that chains multi_artifact_recover_and_dispatch
    with validate_contract.

    Deterministic: same host_png + same contract → identical result.
    """
    recovery = multi_artifact_recover_and_dispatch(
        host_png,
        expected_families=contract.expected_families,
        profile=layout_profile,
        tolerance=tolerance,
        dispatch_profile=dispatch_profile,
    )
    return validate_contract(recovery, contract)


def find_matching_contract(
    recovery_result: MultiLayoutResult,
    profile: ContractProfile = V1_CONTRACT_PROFILE,
) -> Optional[PageContract]:
    """
    Find which frozen contract (if any) the recovered set satisfies.

    Iterates through all contracts in the profile and returns the first
    one where validate_contract produces SATISFIED.  Returns None if
    no contract matches.

    Useful for "identify the page type" scenarios within the frozen
    contract family.
    """
    for contract in profile.contracts:
        cr = validate_contract(recovery_result, contract)
        if cr.verdict == ContractVerdict.SATISFIED:
            return contract
    return None


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen layout matched with its correct contract
IN_BOUNDS_CASES = (
    {
        "label": "two_horizontal_matches",
        "layout_index": 0,
        "contract_index": 0,
        "expected_verdict": "SATISFIED",
    },
    {
        "label": "two_vertical_matches",
        "layout_index": 1,
        "contract_index": 1,
        "expected_verdict": "SATISFIED",
    },
    {
        "label": "three_row_matches",
        "layout_index": 2,
        "contract_index": 2,
        "expected_verdict": "SATISFIED",
    },
    {
        "label": "two_horizontal_mixed_matches",
        "layout_index": 3,
        "contract_index": 3,
        "expected_verdict": "SATISFIED",
    },
    {
        "label": "two_vertical_reversed_matches",
        "layout_index": 4,
        "contract_index": 4,
        "expected_verdict": "SATISFIED",
    },
)

# Out-of-bounds: mismatched layout/contract pairs that must fail honestly
OUT_OF_BOUNDS_CASES = (
    {
        "label": "wrong_count_2v3",
        "description": "Two-artifact layout checked against three-artifact contract",
        "layout_index": 0,
        "contract_index": 2,
        "expected_verdict": "VIOLATED_COUNT",
    },
    {
        "label": "wrong_count_3v2",
        "description": "Three-artifact layout checked against two-artifact contract",
        "layout_index": 2,
        "contract_index": 0,
        "expected_verdict": "VIOLATED_COUNT",
    },
    {
        "label": "wrong_family",
        "description": "Two-artifact layout checked against different two-artifact contract",
        "layout_index": 0,
        "contract_index": 3,
        "expected_verdict": "VIOLATED_FAMILY",
    },
    {
        "label": "wrong_order",
        "description": "Vertical reversed layout checked against non-reversed contract",
        "layout_index": 4,
        "contract_index": 1,
        "expected_verdict": "VIOLATED_ORDER",
    },
)
