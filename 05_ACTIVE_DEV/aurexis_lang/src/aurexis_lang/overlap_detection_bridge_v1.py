"""
Aurexis Core — Overlap Detection Bridge V1

Bounded overlap detection across recovered collections, sequences, and pages.
Identifies shared structural elements between collection contracts so that
higher-order coherence checks can verify agreement on overlapping parts.

What this proves:
  Given the frozen family of collection contracts, this module deterministically
  identifies which collections share sequences (by contract name) and which
  sequences share pages (by page contract name).  The resulting OverlapMap is
  the structural input for Local Section Consistency, Sheaf-Style Composition,
  and Cohomological Obstruction Detection.

What this does NOT prove:
  - Content-level agreement (that is the next bridge)
  - Secure provenance or tamper-proof guarantees
  - General graph-theoretic overlap for unbounded structures
  - Full camera capture robustness
  - Full Aurexis Core completion

Design:
  - A frozen OverlapProfile defines which overlap detection rules apply.
  - OverlapRegion: a pair of collection names + their shared sequence names.
  - SequenceOverlapRegion: a pair of sequence names + their shared page names.
  - detect_collection_overlaps(): pairwise collection overlap via shared
    sequence_contract_names.
  - detect_sequence_overlaps(): pairwise sequence overlap via shared
    page_contract_names.
  - detect_full_overlap_map(): combines both levels into a complete map.
  - All operations are deterministic over the frozen contracts.

This is a narrow deterministic structural overlap detector, not a general
graph-matching or set-intersection engine.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List, FrozenSet
from enum import Enum

from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionContract, FROZEN_COLLECTION_CONTRACTS,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    FROZEN_SEQUENCE_CONTRACTS,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

OVERLAP_VERSION = "V1.0"
OVERLAP_FROZEN = True


# ════════════════════════════════════════════════════════════
# OVERLAP VERDICTS
# ════════════════════════════════════════════════════════════

class OverlapVerdict(str, Enum):
    """Outcome of overlap detection."""
    OVERLAPS_FOUND = "OVERLAPS_FOUND"
    NO_OVERLAPS = "NO_OVERLAPS"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# OVERLAP REGION DATACLASSES
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CollectionOverlapRegion:
    """
    A pair of collections that share one or more sequence contract names.
    """
    collection_a: str = ""
    collection_b: str = ""
    shared_sequence_names: Tuple[str, ...] = ()

    @property
    def overlap_count(self) -> int:
        return len(self.shared_sequence_names)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_a": self.collection_a,
            "collection_b": self.collection_b,
            "shared_sequence_names": list(self.shared_sequence_names),
            "overlap_count": self.overlap_count,
        }


@dataclass(frozen=True)
class SequenceOverlapRegion:
    """
    A pair of sequences that share one or more page contract names.
    """
    sequence_a: str = ""
    sequence_b: str = ""
    shared_page_names: Tuple[str, ...] = ()

    @property
    def overlap_count(self) -> int:
        return len(self.shared_page_names)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_a": self.sequence_a,
            "sequence_b": self.sequence_b,
            "shared_page_names": list(self.shared_page_names),
            "overlap_count": self.overlap_count,
        }


# ════════════════════════════════════════════════════════════
# OVERLAP PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OverlapProfile:
    """
    Frozen profile defining overlap detection rules.
    """
    detect_collection_overlaps: bool = True
    detect_sequence_overlaps: bool = True
    require_frozen_contracts_only: bool = True
    version: str = OVERLAP_VERSION


V1_OVERLAP_PROFILE = OverlapProfile()


# ════════════════════════════════════════════════════════════
# OVERLAP MAP (COMBINED RESULT)
# ════════════════════════════════════════════════════════════

@dataclass
class OverlapMap:
    """Complete overlap detection result."""
    verdict: OverlapVerdict = OverlapVerdict.ERROR
    collection_overlaps: Tuple[CollectionOverlapRegion, ...] = ()
    sequence_overlaps: Tuple[SequenceOverlapRegion, ...] = ()
    total_collection_overlap_regions: int = 0
    total_sequence_overlap_regions: int = 0
    collections_analyzed: int = 0
    sequences_analyzed: int = 0
    version: str = OVERLAP_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "collection_overlaps": [r.to_dict() for r in self.collection_overlaps],
            "sequence_overlaps": [r.to_dict() for r in self.sequence_overlaps],
            "total_collection_overlap_regions": self.total_collection_overlap_regions,
            "total_sequence_overlap_regions": self.total_sequence_overlap_regions,
            "collections_analyzed": self.collections_analyzed,
            "sequences_analyzed": self.sequences_analyzed,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN CONTRACT LOOKUP HELPERS
# ════════════════════════════════════════════════════════════

def _get_collection_contract(name: str) -> Optional[CollectionContract]:
    """Look up a frozen collection contract by name."""
    for c in FROZEN_COLLECTION_CONTRACTS:
        if c.name == name:
            return c
    return None


def _get_sequence_contract_by_name(name: str):
    """Look up a frozen sequence contract by name."""
    for s in FROZEN_SEQUENCE_CONTRACTS:
        if s.name == name:
            return s
    return None


def _all_collection_names() -> Tuple[str, ...]:
    """Return all frozen collection contract names in deterministic order."""
    return tuple(c.name for c in FROZEN_COLLECTION_CONTRACTS)


def _all_sequence_names() -> Tuple[str, ...]:
    """Return all frozen sequence contract names in deterministic order."""
    return tuple(s.name for s in FROZEN_SEQUENCE_CONTRACTS)


# ════════════════════════════════════════════════════════════
# COLLECTION-LEVEL OVERLAP DETECTION
# ════════════════════════════════════════════════════════════

def detect_collection_overlaps(
    collection_names: Optional[Tuple[str, ...]] = None,
) -> Tuple[CollectionOverlapRegion, ...]:
    """
    Detect pairwise overlaps among collection contracts.

    Two collections overlap if they share at least one sequence_contract_name.
    Returns all overlapping pairs in deterministic order.

    If collection_names is None, uses all frozen collection contracts.
    """
    if collection_names is None:
        collection_names = _all_collection_names()

    # Resolve contracts
    contracts = []
    for name in collection_names:
        c = _get_collection_contract(name)
        if c is not None:
            contracts.append(c)

    regions = []
    for i in range(len(contracts)):
        for j in range(i + 1, len(contracts)):
            a = contracts[i]
            b = contracts[j]
            shared = tuple(sorted(
                set(a.sequence_contract_names) & set(b.sequence_contract_names)
            ))
            if shared:
                regions.append(CollectionOverlapRegion(
                    collection_a=a.name,
                    collection_b=b.name,
                    shared_sequence_names=shared,
                ))

    return tuple(regions)


# ════════════════════════════════════════════════════════════
# SEQUENCE-LEVEL OVERLAP DETECTION
# ════════════════════════════════════════════════════════════

def detect_sequence_overlaps(
    sequence_names: Optional[Tuple[str, ...]] = None,
) -> Tuple[SequenceOverlapRegion, ...]:
    """
    Detect pairwise overlaps among sequence contracts.

    Two sequences overlap if they share at least one page_contract_name.
    Returns all overlapping pairs in deterministic order.

    If sequence_names is None, uses all frozen sequence contracts.
    """
    if sequence_names is None:
        sequence_names = _all_sequence_names()

    contracts = []
    for name in sequence_names:
        s = _get_sequence_contract_by_name(name)
        if s is not None:
            contracts.append(s)

    regions = []
    for i in range(len(contracts)):
        for j in range(i + 1, len(contracts)):
            a = contracts[i]
            b = contracts[j]
            shared = tuple(sorted(
                set(a.page_contract_names) & set(b.page_contract_names)
            ))
            if shared:
                regions.append(SequenceOverlapRegion(
                    sequence_a=a.name,
                    sequence_b=b.name,
                    shared_page_names=shared,
                ))

    return tuple(regions)


# ════════════════════════════════════════════════════════════
# FULL OVERLAP MAP
# ════════════════════════════════════════════════════════════

def detect_full_overlap_map(
    profile: Optional[OverlapProfile] = None,
    collection_names: Optional[Tuple[str, ...]] = None,
    sequence_names: Optional[Tuple[str, ...]] = None,
) -> OverlapMap:
    """
    Detect all pairwise overlaps at both collection and sequence level.

    Returns a complete OverlapMap with both levels of overlap regions.
    """
    if profile is None:
        profile = V1_OVERLAP_PROFILE

    try:
        coll_names = collection_names if collection_names is not None else _all_collection_names()
        seq_names = sequence_names if sequence_names is not None else _all_sequence_names()

        coll_overlaps = detect_collection_overlaps(coll_names) if profile.detect_collection_overlaps else ()
        seq_overlaps = detect_sequence_overlaps(seq_names) if profile.detect_sequence_overlaps else ()

        has_overlaps = len(coll_overlaps) > 0 or len(seq_overlaps) > 0
        verdict = OverlapVerdict.OVERLAPS_FOUND if has_overlaps else OverlapVerdict.NO_OVERLAPS

        return OverlapMap(
            verdict=verdict,
            collection_overlaps=coll_overlaps,
            sequence_overlaps=seq_overlaps,
            total_collection_overlap_regions=len(coll_overlaps),
            total_sequence_overlap_regions=len(seq_overlaps),
            collections_analyzed=len(coll_names),
            sequences_analyzed=len(seq_names),
            version=profile.version,
        )
    except Exception as exc:
        return OverlapMap(
            verdict=OverlapVerdict.ERROR,
            version=profile.version,
        )


# ════════════════════════════════════════════════════════════
# PREDEFINED OVERLAP CASES
# ════════════════════════════════════════════════════════════

# All 3 frozen collections — rich overlap structure
ALL_COLLECTIONS_CASE = _all_collection_names()

# Just two collections that share sequences
PAIR_CASE_HV_ALL = ("two_seq_hv_mixed", "three_seq_all")
PAIR_CASE_HV_ALLMIXED = ("two_seq_hv_mixed", "two_seq_all_mixed")
PAIR_CASE_ALL_ALLMIXED = ("three_seq_all", "two_seq_all_mixed")

# A single collection — no overlap possible
SINGLE_CASE = ("two_seq_hv_mixed",)

# Expected overlap counts for the frozen contracts
EXPECTED_COLLECTION_OVERLAP_COUNT = 3  # 3 pairwise overlaps among 3 collections
EXPECTED_SEQUENCE_OVERLAP_COUNT = 1    # only two_page_horizontal_vertical ∩ three_page_all_families share pages
