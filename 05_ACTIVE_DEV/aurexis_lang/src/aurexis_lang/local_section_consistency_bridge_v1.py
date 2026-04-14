"""
Aurexis Core — Local Section Consistency Bridge V1

Bounded local-section agreement verification for overlapping collections.
A "local section" is the structural data one collection assigns to a shared
sequence: the sequence contract name, page count, page contract names, and
a deterministic structural hash derived from those fields.

Two collections that share a sequence are locally consistent if they assign
identical structural data to that shared sequence.

What this proves:
  Given two collections that overlap on a sequence (detected by the Overlap
  Detection Bridge), the system can verify that both collections' structural
  views of the shared sequence agree — same sequence name, page count, page
  contract names, and structural hash.  Disagreement is caught and reported
  as a specific inconsistency type.

What this does NOT prove:
  - Global composition (that is the next bridge)
  - Secure provenance or tamper-proof guarantees
  - General sheaf-theoretic section consistency
  - Full camera capture robustness
  - Full Aurexis Core completion

Design:
  - A LocalSection captures one collection's structural view of a shared
    sequence: sequence name, page count, page contract names, structural hash.
  - The structural hash is a deterministic SHA-256 of the canonical fields.
  - check_local_section_consistency() compares two local sections and
    returns a detailed result.
  - check_overlap_consistency() runs all checks for a CollectionOverlapRegion.
  - check_all_overlaps_consistency() runs checks for all collection overlaps.
  - Fabricated inconsistent sections provide negative test cases.
  - All operations are deterministic and lightweight (no full pipeline).

This is a narrow deterministic local-section agreement checker, not a general
section comparison or sheaf-section validator.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import hashlib

from aurexis_lang.overlap_detection_bridge_v1 import (
    OVERLAP_VERSION, OVERLAP_FROZEN,
    CollectionOverlapRegion, detect_collection_overlaps,
    _get_collection_contract, _get_sequence_contract_by_name,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    FROZEN_COLLECTION_CONTRACTS, CollectionContract,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

LOCAL_SECTION_VERSION = "V1.0"
LOCAL_SECTION_FROZEN = True


# ════════════════════════════════════════════════════════════
# VERDICTS
# ════════════════════════════════════════════════════════════

class LocalSectionVerdict(str, Enum):
    """Outcome of local section consistency check."""
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class SectionInconsistencyType(str, Enum):
    """Specific type of local section disagreement."""
    SIGNATURE_MISMATCH = "SIGNATURE_MISMATCH"
    VERDICT_MISMATCH = "VERDICT_MISMATCH"
    PAGE_COUNT_MISMATCH = "PAGE_COUNT_MISMATCH"
    PAGE_NAMES_MISMATCH = "PAGE_NAMES_MISMATCH"
    NO_INCONSISTENCY = "NO_INCONSISTENCY"


# ════════════════════════════════════════════════════════════
# LOCAL SECTION DATACLASS
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LocalSection:
    """
    One collection's structural view of a shared sequence.

    The structural_hash is a deterministic SHA-256 of the canonical fields:
    sequence_name, page_count, and page_contract_names.
    """
    collection_name: str = ""
    sequence_name: str = ""
    structural_hash: str = ""
    page_count: int = 0
    page_contract_names: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "sequence_name": self.sequence_name,
            "structural_hash": self.structural_hash,
            "page_count": self.page_count,
            "page_contract_names": list(self.page_contract_names),
        }


# ════════════════════════════════════════════════════════════
# STRUCTURAL HASH COMPUTATION
# ════════════════════════════════════════════════════════════

def compute_structural_hash(
    sequence_name: str,
    page_count: int,
    page_contract_names: Tuple[str, ...],
) -> str:
    """
    Deterministic SHA-256 hash of the canonical structural fields.
    """
    canonical = f"{sequence_name}|{page_count}|{'|'.join(page_contract_names)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# SECTION CHECK RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class SectionCheckResult:
    """Result of comparing two local sections for one shared sequence."""
    sequence_name: str = ""
    verdict: LocalSectionVerdict = LocalSectionVerdict.ERROR
    inconsistency_type: SectionInconsistencyType = SectionInconsistencyType.NO_INCONSISTENCY
    section_a: Optional[LocalSection] = None
    section_b: Optional[LocalSection] = None
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_name": self.sequence_name,
            "verdict": self.verdict.value,
            "inconsistency_type": self.inconsistency_type.value,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# OVERLAP CONSISTENCY RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class OverlapConsistencyResult:
    """Result of checking all shared sequences for one overlap region."""
    collection_a: str = ""
    collection_b: str = ""
    verdict: LocalSectionVerdict = LocalSectionVerdict.ERROR
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    check_results: Tuple[SectionCheckResult, ...] = ()
    version: str = LOCAL_SECTION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_a": self.collection_a,
            "collection_b": self.collection_b,
            "verdict": self.verdict.value,
            "checks_performed": self.checks_performed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "check_results": [r.to_dict() for r in self.check_results],
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# ALL-OVERLAPS RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class AllOverlapsConsistencyResult:
    """Result of checking all collection overlaps."""
    verdict: LocalSectionVerdict = LocalSectionVerdict.ERROR
    overlap_regions_checked: int = 0
    overlap_regions_consistent: int = 0
    overlap_regions_inconsistent: int = 0
    results: Tuple[OverlapConsistencyResult, ...] = ()
    version: str = LOCAL_SECTION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "overlap_regions_checked": self.overlap_regions_checked,
            "overlap_regions_consistent": self.overlap_regions_consistent,
            "overlap_regions_inconsistent": self.overlap_regions_inconsistent,
            "results": [r.to_dict() for r in self.results],
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# LOCAL SECTION EXTRACTION
# ════════════════════════════════════════════════════════════

def extract_local_section(
    collection_name: str,
    sequence_name: str,
) -> Optional[LocalSection]:
    """
    Extract a collection's local section for a given sequence.

    Uses structural data from frozen contracts — no full pipeline execution.
    """
    coll = _get_collection_contract(collection_name)
    if coll is None:
        return None

    if sequence_name not in coll.sequence_contract_names:
        return None

    seq = _get_sequence_contract_by_name(sequence_name)
    if seq is None:
        return None

    structural_hash = compute_structural_hash(
        seq.name, seq.expected_page_count, seq.page_contract_names,
    )

    return LocalSection(
        collection_name=collection_name,
        sequence_name=sequence_name,
        structural_hash=structural_hash,
        page_count=seq.expected_page_count,
        page_contract_names=seq.page_contract_names,
    )


# ════════════════════════════════════════════════════════════
# LOCAL SECTION COMPARISON
# ════════════════════════════════════════════════════════════

def check_local_section_consistency(
    section_a: LocalSection,
    section_b: LocalSection,
) -> SectionCheckResult:
    """
    Compare two local sections for the same shared sequence.

    Checks (in order): page contract names, page count, structural hash.
    Returns on first inconsistency found.
    """
    seq_name = section_a.sequence_name

    # Check page contract names
    if section_a.page_contract_names != section_b.page_contract_names:
        return SectionCheckResult(
            sequence_name=seq_name,
            verdict=LocalSectionVerdict.INCONSISTENT,
            inconsistency_type=SectionInconsistencyType.PAGE_NAMES_MISMATCH,
            section_a=section_a, section_b=section_b,
            detail=f"Page names differ: {section_a.page_contract_names} vs {section_b.page_contract_names}",
        )

    # Check page count
    if section_a.page_count != section_b.page_count:
        return SectionCheckResult(
            sequence_name=seq_name,
            verdict=LocalSectionVerdict.INCONSISTENT,
            inconsistency_type=SectionInconsistencyType.PAGE_COUNT_MISMATCH,
            section_a=section_a, section_b=section_b,
            detail=f"Page count differs: {section_a.page_count} vs {section_b.page_count}",
        )

    # Check structural hash
    if section_a.structural_hash != section_b.structural_hash:
        return SectionCheckResult(
            sequence_name=seq_name,
            verdict=LocalSectionVerdict.INCONSISTENT,
            inconsistency_type=SectionInconsistencyType.SIGNATURE_MISMATCH,
            section_a=section_a, section_b=section_b,
            detail=f"Structural hash differs: {section_a.structural_hash[:16]}... vs {section_b.structural_hash[:16]}...",
        )

    return SectionCheckResult(
        sequence_name=seq_name,
        verdict=LocalSectionVerdict.CONSISTENT,
        inconsistency_type=SectionInconsistencyType.NO_INCONSISTENCY,
        section_a=section_a, section_b=section_b,
        detail="All section checks passed",
    )


# ════════════════════════════════════════════════════════════
# OVERLAP REGION CONSISTENCY CHECK
# ════════════════════════════════════════════════════════════

def check_overlap_consistency(
    region: CollectionOverlapRegion,
) -> OverlapConsistencyResult:
    """
    Check local section consistency for all shared sequences in an overlap region.
    """
    results = []
    passed = 0
    failed = 0

    for seq_name in region.shared_sequence_names:
        sec_a = extract_local_section(region.collection_a, seq_name)
        sec_b = extract_local_section(region.collection_b, seq_name)

        if sec_a is None or sec_b is None:
            results.append(SectionCheckResult(
                sequence_name=seq_name,
                verdict=LocalSectionVerdict.ERROR,
                detail=f"Could not extract section(s) for {seq_name}",
            ))
            failed += 1
            continue

        r = check_local_section_consistency(sec_a, sec_b)
        results.append(r)
        if r.verdict == LocalSectionVerdict.CONSISTENT:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    verdict = LocalSectionVerdict.CONSISTENT if failed == 0 and total > 0 else (
        LocalSectionVerdict.INCONSISTENT if failed > 0 else LocalSectionVerdict.ERROR
    )

    return OverlapConsistencyResult(
        collection_a=region.collection_a,
        collection_b=region.collection_b,
        verdict=verdict,
        checks_performed=total,
        checks_passed=passed,
        checks_failed=failed,
        check_results=tuple(results),
    )


# ════════════════════════════════════════════════════════════
# ALL-OVERLAPS CONSISTENCY CHECK
# ════════════════════════════════════════════════════════════

def check_all_overlaps_consistency() -> AllOverlapsConsistencyResult:
    """
    Check local section consistency for all collection overlap regions.
    """
    overlaps = detect_collection_overlaps()
    results = []
    consistent_count = 0
    inconsistent_count = 0

    for region in overlaps:
        r = check_overlap_consistency(region)
        results.append(r)
        if r.verdict == LocalSectionVerdict.CONSISTENT:
            consistent_count += 1
        else:
            inconsistent_count += 1

    total = consistent_count + inconsistent_count
    verdict = LocalSectionVerdict.CONSISTENT if inconsistent_count == 0 and total > 0 else (
        LocalSectionVerdict.INCONSISTENT if inconsistent_count > 0 else LocalSectionVerdict.ERROR
    )

    return AllOverlapsConsistencyResult(
        verdict=verdict,
        overlap_regions_checked=total,
        overlap_regions_consistent=consistent_count,
        overlap_regions_inconsistent=inconsistent_count,
        results=tuple(results),
    )


# ════════════════════════════════════════════════════════════
# FABRICATED INCONSISTENT SECTIONS (NEGATIVE TEST CASES)
# ════════════════════════════════════════════════════════════

def make_consistent_pair(sequence_name: str = "two_page_mixed_reversed"):
    """Create two consistent local sections from different collections."""
    sec_a = extract_local_section("two_seq_hv_mixed", sequence_name)
    sec_b = extract_local_section("three_seq_all", sequence_name)
    return sec_a, sec_b


def make_signature_mismatch_pair():
    """Fabricate a pair with different structural hashes."""
    sec_a, sec_b = make_consistent_pair()
    if sec_a is None or sec_b is None:
        return None, None
    mutant = LocalSection(
        collection_name=sec_b.collection_name,
        sequence_name=sec_b.sequence_name,
        structural_hash="0000000000000000" + sec_b.structural_hash[16:],
        page_count=sec_b.page_count,
        page_contract_names=sec_b.page_contract_names,
    )
    return sec_a, mutant


def make_page_count_mismatch_pair():
    """Fabricate a pair with different page counts."""
    sec_a, sec_b = make_consistent_pair()
    if sec_a is None or sec_b is None:
        return None, None
    mutant = LocalSection(
        collection_name=sec_b.collection_name,
        sequence_name=sec_b.sequence_name,
        structural_hash=sec_b.structural_hash,
        page_count=sec_b.page_count + 99,
        page_contract_names=sec_b.page_contract_names,
    )
    return sec_a, mutant


def make_page_names_mismatch_pair():
    """Fabricate a pair with different page contract names."""
    sec_a, sec_b = make_consistent_pair()
    if sec_a is None or sec_b is None:
        return None, None
    mutant = LocalSection(
        collection_name=sec_b.collection_name,
        sequence_name=sec_b.sequence_name,
        structural_hash=sec_b.structural_hash,
        page_count=sec_b.page_count,
        page_contract_names=("fabricated_page_a", "fabricated_page_b"),
    )
    return sec_a, mutant


# Predefined negative test case count
INCONSISTENCY_CASE_COUNT = 3  # sig_mismatch, page_count, page_names
