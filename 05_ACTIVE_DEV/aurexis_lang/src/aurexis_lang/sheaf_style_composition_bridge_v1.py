"""
Aurexis Core — Sheaf-Style Composition Bridge V1

Bounded composition proof: a small frozen family of locally consistent
sections can compose into one globally coherent assignment.

What this proves:
  Given that all pairwise overlapping collections agree on their shared
  sequences (verified by the Local Section Consistency Bridge), this module
  constructs a global assignment — a single mapping from every sequence
  name to exactly one structural hash — and proves that every collection's
  local view is compatible with this global assignment.

What this does NOT prove:
  - Full abstract sheaf-theory generality
  - Secure provenance or tamper-proof guarantees
  - General category-theoretic composition
  - Full camera capture robustness
  - Full Aurexis Core completion

Design:
  - A GlobalAssignment maps each sequence contract name to its canonical
    structural hash (computed from the frozen contract data).
  - compose_global_assignment() builds this mapping by iterating over all
    collections and all their sequences.
  - verify_composition() checks that every collection's local sections
    agree with the global assignment.
  - CompositionVerdict: COMPOSABLE, NOT_COMPOSABLE, UNSUPPORTED, ERROR.
  - The composition proof is constructive: it produces the global assignment
    and checks every local section against it.
  - Fabricated contradictions test the NOT_COMPOSABLE path.
  - All operations are deterministic.

This is a bounded executable composition proof, not a general sheaf
gluing theorem or abstract algebraic construction.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.overlap_detection_bridge_v1 import (
    OVERLAP_VERSION, detect_collection_overlaps,
    _get_collection_contract, _get_sequence_contract_by_name,
    _all_collection_names,
)
from aurexis_lang.local_section_consistency_bridge_v1 import (
    LOCAL_SECTION_VERSION, LocalSection, LocalSectionVerdict,
    extract_local_section, compute_structural_hash,
    check_all_overlaps_consistency,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    FROZEN_COLLECTION_CONTRACTS,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

COMPOSITION_VERSION = "V1.0"
COMPOSITION_FROZEN = True


# ════════════════════════════════════════════════════════════
# COMPOSITION VERDICTS
# ════════════════════════════════════════════════════════════

class CompositionVerdict(str, Enum):
    """Outcome of sheaf-style composition check."""
    COMPOSABLE = "COMPOSABLE"
    NOT_COMPOSABLE = "NOT_COMPOSABLE"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# GLOBAL ASSIGNMENT
# ════════════════════════════════════════════════════════════

@dataclass
class GlobalAssignment:
    """
    A mapping from sequence contract name to its canonical structural hash.
    This is the "global section" that all local sections must agree with.
    """
    assignments: Dict[str, str] = field(default_factory=dict)
    version: str = COMPOSITION_VERSION

    @property
    def sequence_count(self) -> int:
        return len(self.assignments)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assignments": dict(self.assignments),
            "sequence_count": self.sequence_count,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# COMPOSITION CHECK RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CompositionCheckResult:
    """Result of checking one collection against the global assignment."""
    collection_name: str = ""
    sequences_checked: int = 0
    sequences_agree: int = 0
    sequences_disagree: int = 0
    disagreements: Tuple[str, ...] = ()
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "sequences_checked": self.sequences_checked,
            "sequences_agree": self.sequences_agree,
            "sequences_disagree": self.sequences_disagree,
            "disagreements": list(self.disagreements),
            "passed": self.passed,
        }


# ════════════════════════════════════════════════════════════
# COMPOSITION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CompositionResult:
    """Complete result of sheaf-style composition verification."""
    verdict: CompositionVerdict = CompositionVerdict.ERROR
    global_assignment: Optional[GlobalAssignment] = None
    local_consistency_verdict: str = ""
    collections_checked: int = 0
    collections_agree: int = 0
    collections_disagree: int = 0
    check_results: Tuple[CompositionCheckResult, ...] = ()
    version: str = COMPOSITION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "global_assignment": self.global_assignment.to_dict() if self.global_assignment else None,
            "local_consistency_verdict": self.local_consistency_verdict,
            "collections_checked": self.collections_checked,
            "collections_agree": self.collections_agree,
            "collections_disagree": self.collections_disagree,
            "check_results": [r.to_dict() for r in self.check_results],
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# GLOBAL ASSIGNMENT CONSTRUCTION
# ════════════════════════════════════════════════════════════

def compose_global_assignment() -> GlobalAssignment:
    """
    Build a global assignment from the frozen contracts.

    For each unique sequence contract, compute its canonical structural hash.
    The global assignment maps sequence_name → structural_hash.
    """
    assignments = {}
    seen = set()

    for coll in FROZEN_COLLECTION_CONTRACTS:
        for seq_name in coll.sequence_contract_names:
            if seq_name in seen:
                continue
            seen.add(seq_name)
            seq = _get_sequence_contract_by_name(seq_name)
            if seq is not None:
                h = compute_structural_hash(
                    seq.name, seq.expected_page_count, seq.page_contract_names,
                )
                assignments[seq_name] = h

    return GlobalAssignment(assignments=assignments)


# ════════════════════════════════════════════════════════════
# COMPOSITION VERIFICATION
# ════════════════════════════════════════════════════════════

def verify_composition(
    global_assignment: Optional[GlobalAssignment] = None,
    override_sections: Optional[Dict[str, Dict[str, LocalSection]]] = None,
) -> CompositionResult:
    """
    Verify that every collection's local sections agree with the global assignment.

    1. First checks local section consistency (all overlaps must agree).
    2. Then checks each collection's sequences against the global assignment.

    override_sections: if provided, maps collection_name → {seq_name: LocalSection}.
    Used for fabricated negative test cases.
    """
    # Step 1: Check local consistency
    local_result = check_all_overlaps_consistency()
    local_verdict_str = local_result.verdict.value

    if override_sections is None and local_result.verdict != LocalSectionVerdict.CONSISTENT:
        return CompositionResult(
            verdict=CompositionVerdict.NOT_COMPOSABLE,
            local_consistency_verdict=local_verdict_str,
        )

    # Step 2: Build global assignment
    if global_assignment is None:
        global_assignment = compose_global_assignment()

    # Step 3: Check each collection against the global assignment
    check_results = []
    total_agree = 0
    total_disagree = 0

    for coll in FROZEN_COLLECTION_CONTRACTS:
        disagreements = []
        agree_count = 0

        for seq_name in coll.sequence_contract_names:
            # Get local section
            if override_sections and coll.name in override_sections and seq_name in override_sections[coll.name]:
                section = override_sections[coll.name][seq_name]
            else:
                section = extract_local_section(coll.name, seq_name)

            if section is None:
                disagreements.append(f"{seq_name}: extraction failed")
                continue

            expected_hash = global_assignment.assignments.get(seq_name)
            if expected_hash is None:
                disagreements.append(f"{seq_name}: not in global assignment")
                continue

            if section.structural_hash == expected_hash:
                agree_count += 1
            else:
                disagreements.append(
                    f"{seq_name}: hash {section.structural_hash[:16]}... != expected {expected_hash[:16]}..."
                )

        checked = agree_count + len(disagreements)
        passed = len(disagreements) == 0

        check_results.append(CompositionCheckResult(
            collection_name=coll.name,
            sequences_checked=checked,
            sequences_agree=agree_count,
            sequences_disagree=len(disagreements),
            disagreements=tuple(disagreements),
            passed=passed,
        ))

        if passed:
            total_agree += 1
        else:
            total_disagree += 1

    verdict = CompositionVerdict.COMPOSABLE if total_disagree == 0 else CompositionVerdict.NOT_COMPOSABLE

    return CompositionResult(
        verdict=verdict,
        global_assignment=global_assignment,
        local_consistency_verdict=local_verdict_str,
        collections_checked=len(check_results),
        collections_agree=total_agree,
        collections_disagree=total_disagree,
        check_results=tuple(check_results),
    )


# ════════════════════════════════════════════════════════════
# FABRICATED NOT_COMPOSABLE CASES
# ════════════════════════════════════════════════════════════

def make_contradictory_override():
    """
    Create an override_sections dict where one collection has a mutated
    structural hash for a shared sequence, causing composition failure.
    """
    sec = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
    if sec is None:
        return None
    mutant = LocalSection(
        collection_name=sec.collection_name,
        sequence_name=sec.sequence_name,
        structural_hash="FABRICATED_WRONG_HASH_" + sec.structural_hash[21:],
        page_count=sec.page_count,
        page_contract_names=sec.page_contract_names,
    )
    return {"two_seq_hv_mixed": {"two_page_mixed_reversed": mutant}}


def make_multi_contradictory_override():
    """
    Create overrides where two collections disagree on different sequences.
    """
    overrides = {}

    sec1 = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
    if sec1:
        mutant1 = LocalSection(
            collection_name=sec1.collection_name,
            sequence_name=sec1.sequence_name,
            structural_hash="AAAA" + sec1.structural_hash[4:],
            page_count=sec1.page_count,
            page_contract_names=sec1.page_contract_names,
        )
        overrides["two_seq_hv_mixed"] = {"two_page_mixed_reversed": mutant1}

    sec2 = extract_local_section("two_seq_all_mixed", "three_page_all_families")
    if sec2:
        mutant2 = LocalSection(
            collection_name=sec2.collection_name,
            sequence_name=sec2.sequence_name,
            structural_hash="BBBB" + sec2.structural_hash[4:],
            page_count=sec2.page_count,
            page_contract_names=sec2.page_contract_names,
        )
        overrides["two_seq_all_mixed"] = {"three_page_all_families": mutant2}

    return overrides


# Predefined case counts
COMPOSABLE_CASE_COUNT = 1    # the frozen contracts compose cleanly
NOT_COMPOSABLE_CASE_COUNT = 2  # single contradiction, multi contradiction
