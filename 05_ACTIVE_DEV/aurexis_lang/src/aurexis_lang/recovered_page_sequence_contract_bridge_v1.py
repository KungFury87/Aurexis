"""
Aurexis Core — Recovered Page Sequence Contract Bridge V1

Bounded ordered multi-page validation for the narrow V1 raster bridge.
Proves that a small ordered sequence of recovered pages can be validated
against a frozen sequence-level contract: expected page count, expected
page order, expected page signature sequence.

What this proves:
  Given two or three host images processed as an ordered sequence, the
  system can run each through the existing single-page recovery pipeline
  (recovery → dispatch → contract → signature → signature-match), then
  validate the resulting ordered signature sequence against an explicit
  frozen sequence-level contract.

What this does NOT prove:
  - General document workflow
  - Open-ended multi-page intelligence
  - Arbitrary page counts or unknown sequence formats
  - Full provenance system
  - Camera-complete behavior
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen SequenceContract specifies: expected page count, ordered
    list of per-page contract names, and the expected signature for
    each page position.
  - A frozen SequenceProfile enumerates the supported sequence contracts.
  - validate_sequence() runs each host PNG through the existing
    single-page match pipeline and checks the resulting ordered
    signature sequence against the sequence contract.
  - Verdicts: SEQUENCE_SATISFIED, WRONG_PAGE_COUNT, WRONG_PAGE_ORDER,
    PAGE_MATCH_FAILED, UNSUPPORTED_SEQUENCE, ERROR.
  - All operations are deterministic.

This is a narrow deterministic recovered-sequence proof, not general
document workflow or open-ended multi-page intelligence.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    MatchVerdict, MatchResult,
    ExpectedSignatureBaseline, V1_MATCH_BASELINE,
    match_from_png,
    _get_expected_signatures,
    IN_BOUNDS_CASES as MATCH_IN_BOUNDS_CASES,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    PageContract, FROZEN_CONTRACTS, V1_CONTRACT_PROFILE,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutProfile, V1_MULTI_LAYOUT_PROFILE,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    V1_TOLERANCE_PROFILE, ToleranceProfile,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE, DispatchProfile,
)
from aurexis_lang.recovered_set_signature_bridge_v1 import (
    V1_SIGNATURE_PROFILE, SignatureProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

SEQUENCE_VERSION = "V1.0"
SEQUENCE_FROZEN = True


# ════════════════════════════════════════════════════════════
# SEQUENCE-LEVEL VERDICTS
# ════════════════════════════════════════════════════════════

class SequenceVerdict(str, Enum):
    """Outcome of a page-sequence contract validation."""
    SEQUENCE_SATISFIED = "SEQUENCE_SATISFIED"        # All pages match in order
    WRONG_PAGE_COUNT = "WRONG_PAGE_COUNT"            # Input count != expected
    WRONG_PAGE_ORDER = "WRONG_PAGE_ORDER"            # Right pages, wrong order
    PAGE_MATCH_FAILED = "PAGE_MATCH_FAILED"          # One or more pages failed match
    UNSUPPORTED_SEQUENCE = "UNSUPPORTED_SEQUENCE"    # Sequence contract not in profile
    ERROR = "ERROR"                                  # Unexpected error


# ════════════════════════════════════════════════════════════
# SEQUENCE CONTRACT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SequenceContract:
    """
    A frozen sequence-level contract specifying the expected ordered
    multi-page validation requirements.

    name: unique identifier for the sequence contract
    expected_page_count: exact number of pages expected
    page_contract_names: ordered tuple of per-page contract names
    expected_signatures: ordered tuple of expected SHA-256 signatures
        for each page position (computed lazily from the deterministic
        pipeline)
    description: human-readable description
    """
    name: str
    expected_page_count: int
    page_contract_names: Tuple[str, ...]
    description: str = ""

    def get_page_contract(self, page_index: int) -> Optional[PageContract]:
        """Look up the PageContract for a given page position."""
        if page_index < 0 or page_index >= self.expected_page_count:
            return None
        target_name = self.page_contract_names[page_index]
        for c in FROZEN_CONTRACTS:
            if c.name == target_name:
                return c
        return None


@dataclass(frozen=True)
class SequenceProfile:
    """
    Frozen profile enumerating the supported page-sequence contracts.
    Only sequences listed here are considered in-bounds.
    """
    contracts: Tuple[SequenceContract, ...]
    version: str = SEQUENCE_VERSION


# ════════════════════════════════════════════════════════════
# SEQUENCE RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class PageSequenceResult:
    """Complete result of a page-sequence contract validation."""
    verdict: SequenceVerdict = SequenceVerdict.ERROR
    sequence_contract_name: str = ""
    expected_page_count: int = 0
    actual_page_count: int = 0
    page_match_results: Tuple[MatchResult, ...] = ()
    page_signatures: Tuple[str, ...] = ()
    expected_signatures: Tuple[str, ...] = ()
    failed_page_indices: Tuple[int, ...] = ()
    version: str = SEQUENCE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "sequence_contract_name": self.sequence_contract_name,
            "expected_page_count": self.expected_page_count,
            "actual_page_count": self.actual_page_count,
            "page_match_results": [mr.to_dict() for mr in self.page_match_results],
            "page_signatures": list(self.page_signatures),
            "expected_signatures": list(self.expected_signatures),
            "failed_page_indices": list(self.failed_page_indices),
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED-SIGNATURE SEQUENCE BASELINE
# ════════════════════════════════════════════════════════════
# These are the canonical per-page expected signatures for each
# frozen sequence contract.  They are drawn from the same
# deterministic single-page pipeline used by the match bridge.

def _build_sequence_expected_signatures(
    seq_contract: SequenceContract,
) -> Tuple[str, ...]:
    """
    Build the expected signature tuple for a sequence contract
    by looking up each page's expected signature from the
    single-page match baseline.
    """
    sigs = _get_expected_signatures()
    result = []
    for name in seq_contract.page_contract_names:
        sig = sigs.get(name, "")
        result.append(sig)
    return tuple(result)


# Lazy cache for sequence-level expected signatures
_SEQUENCE_EXPECTED: Optional[Dict[str, Tuple[str, ...]]] = None


def _get_sequence_expected() -> Dict[str, Tuple[str, ...]]:
    """Get or build the frozen sequence-level expected signatures."""
    global _SEQUENCE_EXPECTED
    if _SEQUENCE_EXPECTED is None:
        _SEQUENCE_EXPECTED = {}
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            _SEQUENCE_EXPECTED[sc.name] = _build_sequence_expected_signatures(sc)
    return _SEQUENCE_EXPECTED


# ════════════════════════════════════════════════════════════
# FROZEN SEQUENCE CONTRACT DEFINITIONS
# ════════════════════════════════════════════════════════════
# A small frozen family: one two-page and one three-page sequence.
# These reuse the existing 5 frozen layout×contract pairs.

FROZEN_SEQUENCE_CONTRACTS = (
    SequenceContract(
        name="two_page_horizontal_vertical",
        expected_page_count=2,
        page_contract_names=(
            "two_horizontal_adj_cont",
            "two_vertical_adj_three",
        ),
        description=(
            "Two-page sequence: page 0 is two_horizontal_adj_cont, "
            "page 1 is two_vertical_adj_three"
        ),
    ),
    SequenceContract(
        name="three_page_all_families",
        expected_page_count=3,
        page_contract_names=(
            "two_horizontal_adj_cont",
            "two_vertical_adj_three",
            "three_row_all",
        ),
        description=(
            "Three-page sequence: page 0 is two_horizontal_adj_cont, "
            "page 1 is two_vertical_adj_three, "
            "page 2 is three_row_all"
        ),
    ),
    SequenceContract(
        name="two_page_mixed_reversed",
        expected_page_count=2,
        page_contract_names=(
            "two_horizontal_cont_three",
            "two_vertical_three_adj",
        ),
        description=(
            "Two-page sequence: page 0 is two_horizontal_cont_three, "
            "page 1 is two_vertical_three_adj"
        ),
    ),
)

V1_SEQUENCE_PROFILE = SequenceProfile(contracts=FROZEN_SEQUENCE_CONTRACTS)


# ════════════════════════════════════════════════════════════
# HOST-IMAGE GENERATION FOR SEQUENCE TESTING
# ════════════════════════════════════════════════════════════

def generate_sequence_host_pngs(
    seq_contract: SequenceContract,
) -> Tuple[bytes, ...]:
    """
    Generate the ordered host PNG images for a sequence contract.

    Each page's host image is generated from the frozen layout that
    matches the page's contract (same layout_index as contract_index
    in the existing frozen family).

    Deterministic: same seq_contract → identical host PNG sequence.
    """
    host_pngs = []
    for page_name in seq_contract.page_contract_names:
        # Find the layout index that matches this contract name
        layout_idx = _contract_name_to_layout_index(page_name)
        if layout_idx is None:
            raise ValueError(f"No frozen layout for contract: {page_name}")
        layout = FROZEN_LAYOUTS[layout_idx]
        spec = build_layout_spec(layout)
        host_png = generate_multi_artifact_host(spec)
        host_pngs.append(host_png)
    return tuple(host_pngs)


def _contract_name_to_layout_index(contract_name: str) -> Optional[int]:
    """Map a contract name to its frozen layout index."""
    for i, c in enumerate(FROZEN_CONTRACTS):
        if c.name == contract_name:
            return i
    return None


# ════════════════════════════════════════════════════════════
# SEQUENCE VALIDATION LOGIC
# ════════════════════════════════════════════════════════════

def validate_sequence(
    host_pngs: Tuple[bytes, ...],
    seq_contract: SequenceContract,
    profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> PageSequenceResult:
    """
    Validate an ordered sequence of host images against a frozen
    sequence-level contract.

    Steps:
    1. Check if the sequence contract is in the profile → UNSUPPORTED
    2. Check page count → WRONG_PAGE_COUNT
    3. Run each page through the single-page match pipeline
    4. Collect per-page signatures and match results
    5. Check for page-level match failures → PAGE_MATCH_FAILED
    6. Look up expected sequence signatures
    7. Compare ordered signature sequence → SEQUENCE_SATISFIED or
       WRONG_PAGE_ORDER

    Deterministic: same host_pngs + same seq_contract → identical verdict.
    """
    result = PageSequenceResult(
        sequence_contract_name=seq_contract.name,
        expected_page_count=seq_contract.expected_page_count,
        actual_page_count=len(host_pngs),
    )

    # Step 1: Check if sequence contract is in profile
    supported_names = tuple(sc.name for sc in profile.contracts)
    if seq_contract.name not in supported_names:
        result.verdict = SequenceVerdict.UNSUPPORTED_SEQUENCE
        return result

    # Step 2: Check page count
    if len(host_pngs) != seq_contract.expected_page_count:
        result.verdict = SequenceVerdict.WRONG_PAGE_COUNT
        return result

    # Step 3: Run each page through single-page match pipeline
    page_results: List[MatchResult] = []
    page_signatures: List[str] = []
    failed_indices: List[int] = []

    for i, host_png in enumerate(host_pngs):
        page_contract = seq_contract.get_page_contract(i)
        if page_contract is None:
            result.verdict = SequenceVerdict.ERROR
            return result

        mr = match_from_png(
            host_png,
            page_contract,
            baseline=match_baseline,
            layout_profile=layout_profile,
            tolerance=tolerance,
            dispatch_profile=dispatch_profile,
            signature_profile=signature_profile,
        )
        page_results.append(mr)
        page_signatures.append(mr.computed_signature)

        if mr.verdict != MatchVerdict.MATCH:
            failed_indices.append(i)

    result.page_match_results = tuple(page_results)
    result.page_signatures = tuple(page_signatures)
    result.failed_page_indices = tuple(failed_indices)

    # Step 4: Look up expected signature sequence
    seq_expected = _get_sequence_expected()
    expected_sigs = seq_expected.get(seq_contract.name, ())
    result.expected_signatures = expected_sigs

    if not expected_sigs or len(expected_sigs) != seq_contract.expected_page_count:
        result.verdict = SequenceVerdict.ERROR
        return result

    # Step 5: If all pages matched, compare ordered signature sequences
    if not failed_indices:
        if result.page_signatures == expected_sigs:
            result.verdict = SequenceVerdict.SEQUENCE_SATISFIED
        else:
            # All pages matched their per-position contracts but signatures
            # differ — shouldn't happen with deterministic pipeline, but
            # handle defensively
            result.verdict = SequenceVerdict.PAGE_MATCH_FAILED
        return result

    # Step 6: Some pages failed their per-position match.
    # Check if the pages are correct but in the wrong order by trying
    # each page against ALL contracts in the sequence.
    wrong_order = _detect_wrong_order(
        host_pngs, seq_contract,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )
    if wrong_order:
        result.verdict = SequenceVerdict.WRONG_PAGE_ORDER
    else:
        result.verdict = SequenceVerdict.PAGE_MATCH_FAILED

    return result


def _detect_wrong_order(
    host_pngs: Tuple[bytes, ...],
    seq_contract: SequenceContract,
    match_baseline: ExpectedSignatureBaseline,
    layout_profile: MultiLayoutProfile,
    tolerance: ToleranceProfile,
    dispatch_profile: DispatchProfile,
    signature_profile: SignatureProfile,
) -> bool:
    """
    Check if the provided pages would satisfy the sequence contract
    in a different order.

    For each page, try matching against all contracts in the sequence.
    If each page matches exactly one contract (not its assigned position)
    and the set of matched contracts covers all positions, the pages
    are in the wrong order.

    Returns True if wrong order detected, False otherwise.
    """
    n = len(host_pngs)
    if n != seq_contract.expected_page_count:
        return False

    # For each page, find which contract(s) it matches
    page_matches: List[List[int]] = [[] for _ in range(n)]
    for page_idx in range(n):
        for contract_idx in range(n):
            contract = seq_contract.get_page_contract(contract_idx)
            if contract is None:
                continue
            mr = match_from_png(
                host_pngs[page_idx], contract,
                baseline=match_baseline,
                layout_profile=layout_profile,
                tolerance=tolerance,
                dispatch_profile=dispatch_profile,
                signature_profile=signature_profile,
            )
            if mr.verdict == MatchVerdict.MATCH:
                page_matches[page_idx].append(contract_idx)

    # Check: every page matches at least one contract
    if any(len(m) == 0 for m in page_matches):
        return False

    # Check: the matched contracts cover all positions but not in
    # the identity mapping (which would mean correct order)
    matched_positions = set()
    for page_idx, matches in enumerate(page_matches):
        if len(matches) != 1:
            # Ambiguous — more than one match — not a clean reordering
            # For the frozen family, each page should match exactly one
            return False
        matched_positions.add(matches[0])

    # All positions covered?
    if matched_positions != set(range(n)):
        return False

    # Is it NOT the identity mapping? (identity = correct order)
    identity = all(page_matches[i][0] == i for i in range(n))
    return not identity


def validate_sequence_from_contracts(
    seq_contract: SequenceContract,
    profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> PageSequenceResult:
    """
    Full end-to-end sequence validation: generate host PNGs from
    frozen layouts, then validate the sequence.

    Convenience function for testing and verification.

    Deterministic: same seq_contract → identical result.
    """
    host_pngs = generate_sequence_host_pngs(seq_contract)
    return validate_sequence(
        host_pngs, seq_contract, profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen sequence contract → SEQUENCE_SATISFIED
IN_BOUNDS_CASES = (
    {
        "label": "two_page_hv",
        "seq_contract_index": 0,
        "expected_verdict": "SEQUENCE_SATISFIED",
    },
    {
        "label": "three_page_all",
        "seq_contract_index": 1,
        "expected_verdict": "SEQUENCE_SATISFIED",
    },
    {
        "label": "two_page_mixed",
        "seq_contract_index": 2,
        "expected_verdict": "SEQUENCE_SATISFIED",
    },
)

# Wrong page count: correct pages but wrong number
WRONG_COUNT_CASES = (
    {
        "label": "two_pages_for_three_contract",
        "description": "Provide 2 host PNGs for a 3-page sequence contract",
        "seq_contract_index": 1,
        "provide_page_count": 2,
        "expected_verdict": "WRONG_PAGE_COUNT",
    },
    {
        "label": "three_pages_for_two_contract",
        "description": "Provide 3 host PNGs for a 2-page sequence contract",
        "seq_contract_index": 0,
        "provide_page_count": 3,
        "expected_verdict": "WRONG_PAGE_COUNT",
    },
)

# Wrong page order: correct pages in wrong order
WRONG_ORDER_CASES = (
    {
        "label": "two_page_reversed",
        "description": "Provide pages of two_page_horizontal_vertical in reversed order",
        "seq_contract_index": 0,
        "reversed": True,
        "expected_verdict": "WRONG_PAGE_ORDER",
    },
    {
        "label": "three_page_reversed",
        "description": "Provide pages of three_page_all_families in reversed order",
        "seq_contract_index": 1,
        "reversed": True,
        "expected_verdict": "WRONG_PAGE_ORDER",
    },
)

# Wrong page content: pages from wrong contracts
WRONG_CONTENT_CASES = (
    {
        "label": "wrong_page_content",
        "description": "Provide pages from a different contract family",
        "seq_contract_index": 0,
        "substitute_layout_indices": (3, 4),
        "expected_verdict": "PAGE_MATCH_FAILED",
    },
)

# Unsupported sequence: contract not in profile
UNSUPPORTED_CASES = (
    {
        "label": "unknown_sequence",
        "description": "Sequence contract not in the frozen profile",
        "contract_name": "nonexistent_sequence_contract",
        "expected_verdict": "UNSUPPORTED_SEQUENCE",
    },
)
