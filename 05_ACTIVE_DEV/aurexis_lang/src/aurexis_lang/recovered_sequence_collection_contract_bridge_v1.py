"""
Aurexis Core — Recovered Sequence Collection Contract Bridge V1

Bounded ordered multi-sequence validation for the narrow V1 raster bridge.
Proves that a small ordered collection of recovered page sequences can be
validated against a frozen collection-level contract: expected sequence
count, expected sequence order, and expected per-sequence signature match.

What this proves:
  Given two or three ordered page sequences, each already processable
  through the full per-sequence pipeline (per-page recovery → dispatch →
  contract → signature → signature match → sequence contract → sequence
  signature → sequence signature match), the system can validate the
  resulting ordered collection against an explicit frozen collection-level
  contract.

What this does NOT prove:
  - General archive or library management
  - Open-ended workflow engines
  - Arbitrary sequence counts or unknown collection formats
  - Full provenance system
  - Camera-complete behavior
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen CollectionContract specifies: expected sequence count,
    ordered tuple of sequence contract names.
  - A frozen CollectionProfile enumerates the supported collections.
  - validate_collection() runs each sequence through the existing
    sequence signature match pipeline and checks the resulting ordered
    collection of verdicts against the collection contract.
  - Verdicts: COLLECTION_SATISFIED, WRONG_SEQUENCE_COUNT,
    WRONG_SEQUENCE_ORDER, SEQUENCE_MATCH_FAILED,
    UNSUPPORTED_COLLECTION, ERROR.
  - All operations are deterministic.

This is a narrow deterministic recovered-collection proof, not general
archive management or open-ended multi-sequence intelligence.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SEQ_MATCH_VERSION, SEQ_MATCH_FROZEN,
    SeqMatchVerdict, SeqMatchResult,
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
    match_sequence_signature, match_sequence_signature_from_contracts,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceContract, SequenceProfile,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    generate_sequence_host_pngs,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    ExpectedSignatureBaseline, V1_MATCH_BASELINE,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile,
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

COLLECTION_VERSION = "V1.0"
COLLECTION_FROZEN = True


# ════════════════════════════════════════════════════════════
# COLLECTION-LEVEL VERDICTS
# ════════════════════════════════════════════════════════════

class CollectionVerdict(str, Enum):
    """Outcome of a sequence-collection contract validation."""
    COLLECTION_SATISFIED = "COLLECTION_SATISFIED"
    WRONG_SEQUENCE_COUNT = "WRONG_SEQUENCE_COUNT"
    WRONG_SEQUENCE_ORDER = "WRONG_SEQUENCE_ORDER"
    SEQUENCE_MATCH_FAILED = "SEQUENCE_MATCH_FAILED"
    UNSUPPORTED_COLLECTION = "UNSUPPORTED_COLLECTION"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# COLLECTION CONTRACT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CollectionContract:
    """
    A frozen collection-level contract specifying the expected ordered
    multi-sequence validation requirements.

    name: unique identifier for the collection contract
    expected_sequence_count: exact number of sequences expected
    sequence_contract_names: ordered tuple of sequence contract names
    description: human-readable description
    """
    name: str
    expected_sequence_count: int
    sequence_contract_names: Tuple[str, ...]
    description: str = ""

    def get_sequence_contract(self, seq_index: int) -> Optional[SequenceContract]:
        """Look up the SequenceContract for a given position."""
        if seq_index < 0 or seq_index >= self.expected_sequence_count:
            return None
        target_name = self.sequence_contract_names[seq_index]
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            if sc.name == target_name:
                return sc
        return None


@dataclass(frozen=True)
class CollectionProfile:
    """
    Frozen profile enumerating the supported collection contracts.
    Only collections listed here are considered in-bounds.
    """
    contracts: Tuple[CollectionContract, ...]
    version: str = COLLECTION_VERSION


# ════════════════════════════════════════════════════════════
# COLLECTION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CollectionResult:
    """Complete result of a collection contract validation."""
    verdict: CollectionVerdict = CollectionVerdict.ERROR
    collection_contract_name: str = ""
    expected_sequence_count: int = 0
    actual_sequence_count: int = 0
    sequence_match_results: Tuple[SeqMatchResult, ...] = ()
    sequence_signatures: Tuple[str, ...] = ()
    expected_sequence_signatures: Tuple[str, ...] = ()
    failed_sequence_indices: Tuple[int, ...] = ()
    version: str = COLLECTION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "collection_contract_name": self.collection_contract_name,
            "expected_sequence_count": self.expected_sequence_count,
            "actual_sequence_count": self.actual_sequence_count,
            "sequence_match_results": [
                mr.to_dict() for mr in self.sequence_match_results
            ],
            "sequence_signatures": list(self.sequence_signatures),
            "expected_sequence_signatures": list(self.expected_sequence_signatures),
            "failed_sequence_indices": list(self.failed_sequence_indices),
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED COLLECTION SIGNATURES
# ════════════════════════════════════════════════════════════
# For each frozen collection contract, the expected sequence
# signatures are the per-sequence expected signatures from the
# sequence signature match baseline.

_COLLECTION_EXPECTED: Optional[Dict[str, Tuple[str, ...]]] = None


def _build_collection_expected_signatures(
    coll_contract: CollectionContract,
) -> Tuple[str, ...]:
    """
    Build the expected sequence-signature tuple for a collection
    contract by looking up each sequence's expected signature from
    the sequence signature match baseline.
    """
    seq_sigs = _get_expected_seq_sigs()
    result = []
    for name in coll_contract.sequence_contract_names:
        sig = seq_sigs.get(name, "")
        result.append(sig)
    return tuple(result)


def _get_collection_expected() -> Dict[str, Tuple[str, ...]]:
    """Get or build the frozen collection-level expected signatures."""
    global _COLLECTION_EXPECTED
    if _COLLECTION_EXPECTED is None:
        _COLLECTION_EXPECTED = {}
        for cc in FROZEN_COLLECTION_CONTRACTS:
            _COLLECTION_EXPECTED[cc.name] = (
                _build_collection_expected_signatures(cc)
            )
    return _COLLECTION_EXPECTED


# ════════════════════════════════════════════════════════════
# FROZEN COLLECTION CONTRACT DEFINITIONS
# ════════════════════════════════════════════════════════════
# A small frozen family of 3 collection contracts, built from
# the 3 existing frozen sequence contracts.

FROZEN_COLLECTION_CONTRACTS = (
    CollectionContract(
        name="two_seq_hv_mixed",
        expected_sequence_count=2,
        sequence_contract_names=(
            "two_page_horizontal_vertical",
            "two_page_mixed_reversed",
        ),
        description=(
            "Two-sequence collection: seq 0 is two_page_horizontal_vertical, "
            "seq 1 is two_page_mixed_reversed"
        ),
    ),
    CollectionContract(
        name="three_seq_all",
        expected_sequence_count=3,
        sequence_contract_names=(
            "two_page_horizontal_vertical",
            "three_page_all_families",
            "two_page_mixed_reversed",
        ),
        description=(
            "Three-sequence collection: seq 0 is two_page_horizontal_vertical, "
            "seq 1 is three_page_all_families, "
            "seq 2 is two_page_mixed_reversed"
        ),
    ),
    CollectionContract(
        name="two_seq_all_mixed",
        expected_sequence_count=2,
        sequence_contract_names=(
            "three_page_all_families",
            "two_page_mixed_reversed",
        ),
        description=(
            "Two-sequence collection: seq 0 is three_page_all_families, "
            "seq 1 is two_page_mixed_reversed"
        ),
    ),
)

V1_COLLECTION_PROFILE = CollectionProfile(
    contracts=FROZEN_COLLECTION_CONTRACTS,
)


# ════════════════════════════════════════════════════════════
# HOST-IMAGE GROUP GENERATION FOR COLLECTION TESTING
# ════════════════════════════════════════════════════════════

def generate_collection_host_png_groups(
    coll_contract: CollectionContract,
) -> Tuple[Tuple[bytes, ...], ...]:
    """
    Generate the ordered host PNG groups for a collection contract.

    Each group is the ordered host PNGs for one sequence contract.
    The outer tuple is ordered by collection position.

    Deterministic: same coll_contract → identical host PNG groups.
    """
    groups = []
    for seq_name in coll_contract.sequence_contract_names:
        seq_contract = None
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            if sc.name == seq_name:
                seq_contract = sc
                break
        if seq_contract is None:
            raise ValueError(f"No frozen sequence contract: {seq_name}")
        pngs = generate_sequence_host_pngs(seq_contract)
        groups.append(pngs)
    return tuple(groups)


# ════════════════════════════════════════════════════════════
# COLLECTION VALIDATION LOGIC
# ════════════════════════════════════════════════════════════

def validate_collection(
    host_png_groups: Tuple[Tuple[bytes, ...], ...],
    coll_contract: CollectionContract,
    profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> CollectionResult:
    """
    Validate an ordered collection of sequence host-image groups
    against a frozen collection-level contract.

    Steps:
    1. Check if the collection contract is in the profile → UNSUPPORTED
    2. Check sequence count → WRONG_SEQUENCE_COUNT
    3. Run each sequence through the sequence signature match pipeline
    4. Collect per-sequence match results and signatures
    5. Check for sequence-level match failures → SEQUENCE_MATCH_FAILED
    6. Look up expected collection-level signatures
    7. Compare ordered signature sequence → COLLECTION_SATISFIED or
       WRONG_SEQUENCE_ORDER

    Deterministic: same inputs + same contract → identical verdict.
    """
    result = CollectionResult(
        collection_contract_name=coll_contract.name,
        expected_sequence_count=coll_contract.expected_sequence_count,
        actual_sequence_count=len(host_png_groups),
    )

    try:
        # Step 1: Check if collection contract is in profile
        supported_names = tuple(cc.name for cc in profile.contracts)
        if coll_contract.name not in supported_names:
            result.verdict = CollectionVerdict.UNSUPPORTED_COLLECTION
            return result

        # Step 2: Check sequence count
        if len(host_png_groups) != coll_contract.expected_sequence_count:
            result.verdict = CollectionVerdict.WRONG_SEQUENCE_COUNT
            return result

        # Step 3: Run each sequence through sequence signature match
        seq_results: List[SeqMatchResult] = []
        seq_sigs: List[str] = []
        failed_indices: List[int] = []

        for i, host_pngs in enumerate(host_png_groups):
            seq_contract = coll_contract.get_sequence_contract(i)
            if seq_contract is None:
                result.verdict = CollectionVerdict.ERROR
                return result

            mr = match_sequence_signature(
                host_pngs, seq_contract, seq_match_baseline,
                seq_sig_profile, seq_profile,
                match_baseline, layout_profile, tolerance,
                dispatch_profile, signature_profile,
            )
            seq_results.append(mr)
            seq_sigs.append(mr.computed_sequence_signature)

            if mr.verdict != SeqMatchVerdict.MATCH:
                failed_indices.append(i)

        result.sequence_match_results = tuple(seq_results)
        result.sequence_signatures = tuple(seq_sigs)
        result.failed_sequence_indices = tuple(failed_indices)

        # Step 4: Look up expected collection-level signatures
        coll_expected = _get_collection_expected()
        expected_sigs = coll_expected.get(coll_contract.name, ())
        result.expected_sequence_signatures = expected_sigs

        if (not expected_sigs
                or len(expected_sigs) != coll_contract.expected_sequence_count):
            result.verdict = CollectionVerdict.ERROR
            return result

        # Step 5: If all sequences matched, compare ordered signatures
        if not failed_indices:
            if result.sequence_signatures == expected_sigs:
                result.verdict = CollectionVerdict.COLLECTION_SATISFIED
            else:
                # All sequences passed match but signatures differ —
                # should not happen with deterministic pipeline
                result.verdict = CollectionVerdict.SEQUENCE_MATCH_FAILED
            return result

        # Step 6: Some sequences failed. Check for wrong order.
        wrong_order = _detect_wrong_sequence_order(
            host_png_groups, coll_contract,
            seq_match_baseline, seq_sig_profile, seq_profile,
            match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )
        if wrong_order:
            result.verdict = CollectionVerdict.WRONG_SEQUENCE_ORDER
        else:
            result.verdict = CollectionVerdict.SEQUENCE_MATCH_FAILED

        return result

    except Exception:
        result.verdict = CollectionVerdict.ERROR
        return result


def _detect_wrong_sequence_order(
    host_png_groups: Tuple[Tuple[bytes, ...], ...],
    coll_contract: CollectionContract,
    seq_match_baseline: ExpectedSequenceSignatureBaseline,
    seq_sig_profile: SequenceSignatureProfile,
    seq_profile: SequenceProfile,
    match_baseline: ExpectedSignatureBaseline,
    layout_profile: MultiLayoutProfile,
    tolerance: ToleranceProfile,
    dispatch_profile: DispatchProfile,
    signature_profile: SignatureProfile,
) -> bool:
    """
    Check if the provided sequence groups would satisfy the collection
    contract in a different order.

    For each group, try matching against all sequence contracts in the
    collection. If each group matches exactly one contract (not its
    assigned position) and the set of matched contracts covers all
    positions, the groups are in the wrong order.
    """
    n = len(host_png_groups)
    if n != coll_contract.expected_sequence_count:
        return False

    group_matches: List[List[int]] = [[] for _ in range(n)]
    for group_idx in range(n):
        for contract_idx in range(n):
            seq_contract = coll_contract.get_sequence_contract(contract_idx)
            if seq_contract is None:
                continue
            mr = match_sequence_signature(
                host_png_groups[group_idx], seq_contract,
                seq_match_baseline, seq_sig_profile, seq_profile,
                match_baseline, layout_profile, tolerance,
                dispatch_profile, signature_profile,
            )
            if mr.verdict == SeqMatchVerdict.MATCH:
                group_matches[group_idx].append(contract_idx)

    # Check: every group matches at least one contract
    if any(len(m) == 0 for m in group_matches):
        return False

    # Check: each group matches exactly one
    matched_positions = set()
    for group_idx, matches in enumerate(group_matches):
        if len(matches) != 1:
            return False
        matched_positions.add(matches[0])

    # All positions covered?
    if matched_positions != set(range(n)):
        return False

    # Is it NOT the identity mapping?
    identity = all(group_matches[i][0] == i for i in range(n))
    return not identity


def validate_collection_from_contracts(
    coll_contract: CollectionContract,
    profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> CollectionResult:
    """
    Full end-to-end collection validation: generate host PNG groups
    from frozen layouts, then validate the collection.

    Convenience function for testing and verification.
    Deterministic: same coll_contract → identical result.
    """
    host_png_groups = generate_collection_host_png_groups(coll_contract)
    return validate_collection(
        host_png_groups, coll_contract, profile,
        seq_match_baseline, seq_sig_profile, seq_profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen collection contract → COLLECTION_SATISFIED
IN_BOUNDS_CASES = (
    {
        "label": "two_seq_hv_mixed",
        "coll_contract_index": 0,
        "expected_verdict": "COLLECTION_SATISFIED",
    },
    {
        "label": "three_seq_all",
        "coll_contract_index": 1,
        "expected_verdict": "COLLECTION_SATISFIED",
    },
    {
        "label": "two_seq_all_mixed",
        "coll_contract_index": 2,
        "expected_verdict": "COLLECTION_SATISFIED",
    },
)

# Wrong sequence count
WRONG_COUNT_CASES = (
    {
        "label": "two_groups_for_three_contract",
        "description": "Provide 2 sequence groups for a 3-sequence contract",
        "coll_contract_index": 1,
        "provide_count": 2,
        "expected_verdict": "WRONG_SEQUENCE_COUNT",
    },
    {
        "label": "three_groups_for_two_contract",
        "description": "Provide 3 sequence groups for a 2-sequence contract",
        "coll_contract_index": 0,
        "provide_count": 3,
        "expected_verdict": "WRONG_SEQUENCE_COUNT",
    },
)

# Wrong sequence order: correct sequences in wrong order
WRONG_ORDER_CASES = (
    {
        "label": "two_seq_reversed",
        "description": "Provide sequences of two_seq_hv_mixed in reversed order",
        "coll_contract_index": 0,
        "reversed": True,
        "expected_verdict": "WRONG_SEQUENCE_ORDER",
    },
    {
        "label": "three_seq_reversed",
        "description": "Provide sequences of three_seq_all in reversed order",
        "coll_contract_index": 1,
        "reversed": True,
        "expected_verdict": "WRONG_SEQUENCE_ORDER",
    },
)

# Wrong sequence content: sequences from wrong contracts
WRONG_CONTENT_CASES = (
    {
        "label": "wrong_sequence_content",
        "description": "Provide sequence groups from different contract family",
        "coll_contract_index": 0,
        "substitute_seq_indices": (1, 2),
        "expected_verdict": "SEQUENCE_MATCH_FAILED",
    },
)

# Unsupported collection: contract not in profile
UNSUPPORTED_CASES = (
    {
        "label": "unknown_collection",
        "description": "Collection contract not in the frozen profile",
        "contract_name": "nonexistent_collection_contract",
        "expected_verdict": "UNSUPPORTED_COLLECTION",
    },
)
