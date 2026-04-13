"""
Aurexis Core — Cohomological Obstruction Detection Bridge V1

Bounded obstruction detector: identifies specific reasons why a family of
locally consistent sections cannot compose into a globally coherent assignment.

What this proves:
  Given a family of collections with detected overlaps, this module checks
  for specific obstruction types that prevent global composition. When no
  obstructions exist, the sections compose cleanly. When obstructions exist,
  each one is reported as a concrete witness with type, location, and detail.

What this does NOT prove:
  - Full cohomological classification (H¹, H², etc.)
  - General sheaf cohomology computation
  - Secure provenance or tamper-proof guarantees
  - Full camera capture robustness
  - Full Aurexis Core completion

Design:
  - ObstructionType enum: HASH_CYCLE_CONFLICT, PAGE_STRUCTURE_CONFLICT,
    COVERAGE_GAP, ASSIGNMENT_CONTRADICTION, NO_OBSTRUCTION.
  - An Obstruction dataclass captures: type, involved collections,
    involved sequence, detail message.
  - detect_obstructions() checks all overlap regions for specific
    obstruction patterns.
  - For clean data (frozen contracts), no obstructions exist.
  - Fabricated contradictions produce specific obstructions.
  - All operations are deterministic.

This is a bounded executable "cannot glue" detector, not a broad
cohomological computation or abstract theorem prover.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.overlap_detection_bridge_v1 import (
    detect_collection_overlaps, detect_full_overlap_map,
    CollectionOverlapRegion, OverlapMap,
    _get_collection_contract, _get_sequence_contract_by_name,
    _all_collection_names,
)
from aurexis_lang.local_section_consistency_bridge_v1 import (
    LocalSection, LocalSectionVerdict,
    extract_local_section, compute_structural_hash,
    check_local_section_consistency, SectionInconsistencyType,
)
from aurexis_lang.sheaf_style_composition_bridge_v1 import (
    compose_global_assignment, GlobalAssignment,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    FROZEN_COLLECTION_CONTRACTS,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

OBSTRUCTION_VERSION = "V1.0"
OBSTRUCTION_FROZEN = True


# ════════════════════════════════════════════════════════════
# OBSTRUCTION TYPES
# ════════════════════════════════════════════════════════════

class ObstructionType(str, Enum):
    """Specific type of composition obstruction."""
    HASH_CYCLE_CONFLICT = "HASH_CYCLE_CONFLICT"
    PAGE_STRUCTURE_CONFLICT = "PAGE_STRUCTURE_CONFLICT"
    COVERAGE_GAP = "COVERAGE_GAP"
    ASSIGNMENT_CONTRADICTION = "ASSIGNMENT_CONTRADICTION"
    NO_OBSTRUCTION = "NO_OBSTRUCTION"


class ObstructionVerdict(str, Enum):
    """Overall obstruction detection outcome."""
    OBSTRUCTIONS_FOUND = "OBSTRUCTIONS_FOUND"
    NO_OBSTRUCTIONS = "NO_OBSTRUCTIONS"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# OBSTRUCTION DATACLASS
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Obstruction:
    """
    A concrete witness of non-composability.
    """
    obstruction_type: ObstructionType = ObstructionType.NO_OBSTRUCTION
    collection_a: str = ""
    collection_b: str = ""
    sequence_name: str = ""
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obstruction_type": self.obstruction_type.value,
            "collection_a": self.collection_a,
            "collection_b": self.collection_b,
            "sequence_name": self.sequence_name,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# OBSTRUCTION DETECTION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class ObstructionResult:
    """Complete result of obstruction detection."""
    verdict: ObstructionVerdict = ObstructionVerdict.ERROR
    obstructions: Tuple[Obstruction, ...] = ()
    total_obstructions: int = 0
    overlap_regions_checked: int = 0
    sequences_checked: int = 0
    version: str = OBSTRUCTION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "obstructions": [o.to_dict() for o in self.obstructions],
            "total_obstructions": self.total_obstructions,
            "overlap_regions_checked": self.overlap_regions_checked,
            "sequences_checked": self.sequences_checked,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# OBSTRUCTION DETECTION
# ════════════════════════════════════════════════════════════

def detect_obstructions(
    override_sections: Optional[Dict[str, Dict[str, LocalSection]]] = None,
) -> ObstructionResult:
    """
    Detect all composition obstructions across the frozen collection family.

    Checks:
    1. HASH_CYCLE_CONFLICT: two collections assign different structural hashes
       to the same shared sequence.
    2. PAGE_STRUCTURE_CONFLICT: two collections assign different page structures
       (page count or page names) to the same shared sequence.
    3. COVERAGE_GAP: a sequence referenced by a collection is not present in
       the global assignment (missing from all baselines).
    4. ASSIGNMENT_CONTRADICTION: a collection's local section hash disagrees
       with the global assignment.

    override_sections: maps collection_name → {seq_name: LocalSection}.
    Used for fabricated negative test cases.
    """
    overlaps = detect_collection_overlaps()
    global_assignment = compose_global_assignment()
    obstructions: List[Obstruction] = []
    total_seqs_checked = 0

    # Check 1 & 2: pairwise overlap region checks
    for region in overlaps:
        for seq_name in region.shared_sequence_names:
            total_seqs_checked += 1

            # Get sections (with override support)
            if override_sections and region.collection_a in override_sections and seq_name in override_sections[region.collection_a]:
                sec_a = override_sections[region.collection_a][seq_name]
            else:
                sec_a = extract_local_section(region.collection_a, seq_name)

            if override_sections and region.collection_b in override_sections and seq_name in override_sections[region.collection_b]:
                sec_b = override_sections[region.collection_b][seq_name]
            else:
                sec_b = extract_local_section(region.collection_b, seq_name)

            if sec_a is None or sec_b is None:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.COVERAGE_GAP,
                    collection_a=region.collection_a,
                    collection_b=region.collection_b,
                    sequence_name=seq_name,
                    detail=f"Cannot extract section for {seq_name}",
                ))
                continue

            # Check page structure
            if sec_a.page_contract_names != sec_b.page_contract_names:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.PAGE_STRUCTURE_CONFLICT,
                    collection_a=region.collection_a,
                    collection_b=region.collection_b,
                    sequence_name=seq_name,
                    detail=f"Page names differ: {sec_a.page_contract_names} vs {sec_b.page_contract_names}",
                ))
            elif sec_a.page_count != sec_b.page_count:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.PAGE_STRUCTURE_CONFLICT,
                    collection_a=region.collection_a,
                    collection_b=region.collection_b,
                    sequence_name=seq_name,
                    detail=f"Page count differs: {sec_a.page_count} vs {sec_b.page_count}",
                ))

            # Check hash agreement
            if sec_a.structural_hash != sec_b.structural_hash:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.HASH_CYCLE_CONFLICT,
                    collection_a=region.collection_a,
                    collection_b=region.collection_b,
                    sequence_name=seq_name,
                    detail=f"Hash conflict: {sec_a.structural_hash[:16]}... vs {sec_b.structural_hash[:16]}...",
                ))

    # Check 3 & 4: each collection vs global assignment
    for coll in FROZEN_COLLECTION_CONTRACTS:
        for seq_name in coll.sequence_contract_names:
            if override_sections and coll.name in override_sections and seq_name in override_sections[coll.name]:
                section = override_sections[coll.name][seq_name]
            else:
                section = extract_local_section(coll.name, seq_name)

            if section is None:
                continue

            expected = global_assignment.assignments.get(seq_name)
            if expected is None:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.COVERAGE_GAP,
                    collection_a=coll.name,
                    collection_b="(global)",
                    sequence_name=seq_name,
                    detail=f"Sequence {seq_name} not in global assignment",
                ))
            elif section.structural_hash != expected:
                obstructions.append(Obstruction(
                    obstruction_type=ObstructionType.ASSIGNMENT_CONTRADICTION,
                    collection_a=coll.name,
                    collection_b="(global)",
                    sequence_name=seq_name,
                    detail=f"Local hash {section.structural_hash[:16]}... != global {expected[:16]}...",
                ))

    # Determine verdict
    if len(obstructions) > 0:
        verdict = ObstructionVerdict.OBSTRUCTIONS_FOUND
    else:
        verdict = ObstructionVerdict.NO_OBSTRUCTIONS

    return ObstructionResult(
        verdict=verdict,
        obstructions=tuple(obstructions),
        total_obstructions=len(obstructions),
        overlap_regions_checked=len(overlaps),
        sequences_checked=total_seqs_checked,
    )


# ════════════════════════════════════════════════════════════
# FABRICATED OBSTRUCTION CASES
# ════════════════════════════════════════════════════════════

def make_hash_cycle_override():
    """Fabricate a hash cycle conflict: collection A assigns different hash to shared seq."""
    sec = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
    if sec is None:
        return None
    mutant = LocalSection(
        collection_name=sec.collection_name,
        sequence_name=sec.sequence_name,
        structural_hash="CYCLE_CONFLICT_HASH_" + sec.structural_hash[20:],
        page_count=sec.page_count,
        page_contract_names=sec.page_contract_names,
    )
    return {"two_seq_hv_mixed": {"two_page_mixed_reversed": mutant}}


def make_page_structure_override():
    """Fabricate a page structure conflict: different page names for shared seq."""
    sec = extract_local_section("three_seq_all", "two_page_mixed_reversed")
    if sec is None:
        return None
    mutant = LocalSection(
        collection_name=sec.collection_name,
        sequence_name=sec.sequence_name,
        structural_hash=sec.structural_hash,
        page_count=sec.page_count,
        page_contract_names=("wrong_page_a", "wrong_page_b"),
    )
    return {"three_seq_all": {"two_page_mixed_reversed": mutant}}


def make_assignment_contradiction_override():
    """Fabricate an assignment contradiction: local hash != global assignment."""
    sec = extract_local_section("two_seq_all_mixed", "three_page_all_families")
    if sec is None:
        return None
    mutant = LocalSection(
        collection_name=sec.collection_name,
        sequence_name=sec.sequence_name,
        structural_hash="WRONG_GLOBAL_" + sec.structural_hash[12:],
        page_count=sec.page_count,
        page_contract_names=sec.page_contract_names,
    )
    return {"two_seq_all_mixed": {"three_page_all_families": mutant}}


# Predefined case counts
CLEAN_CASE_COUNT = 1     # frozen contracts have no obstructions
OBSTRUCTION_CASE_COUNT = 3  # hash_cycle, page_structure, assignment_contradiction
