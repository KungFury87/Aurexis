#!/usr/bin/env python3
"""
Standalone test runner — Cohomological Obstruction Detection Bridge V1

Bounded obstruction detector for composition failures.
32nd bridge, 4th higher-order coherence milestone.

Run:
    python run_v1_cohomological_obstruction_tests.py

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import sys, os

_this = os.path.dirname(os.path.abspath(__file__))
_src = os.path.normpath(os.path.join(_this, "..", "..", "aurexis_lang", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

_passed = 0
_failed = 0

def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {label}")

def section(title):
    print(f"\nSection: {title}")


from aurexis_lang.cohomological_obstruction_bridge_v1 import (
    OBSTRUCTION_VERSION, OBSTRUCTION_FROZEN,
    ObstructionType, ObstructionVerdict,
    Obstruction, ObstructionResult,
    detect_obstructions,
    make_hash_cycle_override, make_page_structure_override,
    make_assignment_contradiction_override,
    CLEAN_CASE_COUNT, OBSTRUCTION_CASE_COUNT,
)


# Section 1: Module metadata
section("1: Module metadata")
check(OBSTRUCTION_VERSION == "V1.0", "OBSTRUCTION_VERSION is V1.0")
check(OBSTRUCTION_FROZEN is True, "OBSTRUCTION_FROZEN is True")
check(CLEAN_CASE_COUNT == 1, "1 clean case")
check(OBSTRUCTION_CASE_COUNT == 3, "3 obstruction cases")


# Section 2: Clean case — no obstructions
section("2: Clean case — frozen contracts have no obstructions")
r = detect_obstructions()
check(r.verdict == ObstructionVerdict.NO_OBSTRUCTIONS, "verdict is NO_OBSTRUCTIONS")
check(r.total_obstructions == 0, "0 obstructions")
check(r.overlap_regions_checked == 3, "3 overlap regions checked")
check(r.sequences_checked > 0, f"sequences checked > 0 (got {r.sequences_checked})")


# Section 3: Hash cycle conflict
section("3: Hash cycle conflict — OBSTRUCTIONS_FOUND")
override1 = make_hash_cycle_override()
check(override1 is not None, "hash cycle override created")
r1 = detect_obstructions(override_sections=override1)
check(r1.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND, "verdict is OBSTRUCTIONS_FOUND")
check(r1.total_obstructions > 0, f"obstructions found (got {r1.total_obstructions})")
types1 = {o.obstruction_type for o in r1.obstructions}
check(ObstructionType.HASH_CYCLE_CONFLICT in types1, "HASH_CYCLE_CONFLICT detected")
# The hash cycle also causes ASSIGNMENT_CONTRADICTION since local != global
check(ObstructionType.ASSIGNMENT_CONTRADICTION in types1, "ASSIGNMENT_CONTRADICTION also detected")
# Verify the conflict involves two_page_mixed_reversed
seqs1 = {o.sequence_name for o in r1.obstructions}
check("two_page_mixed_reversed" in seqs1, "conflict on two_page_mixed_reversed")


# Section 4: Page structure conflict
section("4: Page structure conflict — OBSTRUCTIONS_FOUND")
override2 = make_page_structure_override()
check(override2 is not None, "page structure override created")
r2 = detect_obstructions(override_sections=override2)
check(r2.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND, "verdict is OBSTRUCTIONS_FOUND")
check(r2.total_obstructions > 0, f"obstructions found (got {r2.total_obstructions})")
types2 = {o.obstruction_type for o in r2.obstructions}
check(ObstructionType.PAGE_STRUCTURE_CONFLICT in types2, "PAGE_STRUCTURE_CONFLICT detected")


# Section 5: Assignment contradiction
section("5: Assignment contradiction — OBSTRUCTIONS_FOUND")
override3 = make_assignment_contradiction_override()
check(override3 is not None, "assignment contradiction override created")
r3 = detect_obstructions(override_sections=override3)
check(r3.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND, "verdict is OBSTRUCTIONS_FOUND")
check(r3.total_obstructions > 0, f"obstructions found (got {r3.total_obstructions})")
types3 = {o.obstruction_type for o in r3.obstructions}
check(ObstructionType.ASSIGNMENT_CONTRADICTION in types3, "ASSIGNMENT_CONTRADICTION detected")


# Section 6: Obstruction dataclass
section("6: Obstruction dataclass")
obs = Obstruction(
    obstruction_type=ObstructionType.HASH_CYCLE_CONFLICT,
    collection_a="coll_a", collection_b="coll_b",
    sequence_name="seq_x", detail="test detail",
)
check(obs.obstruction_type == ObstructionType.HASH_CYCLE_CONFLICT, "type correct")
d = obs.to_dict()
check(d["obstruction_type"] == "HASH_CYCLE_CONFLICT", "to_dict type")
check(d["collection_a"] == "coll_a", "to_dict collection_a")
check(d["sequence_name"] == "seq_x", "to_dict sequence_name")
# Frozen
try:
    obs.detail = "mutant"
    check(False, "Obstruction should be frozen")
except (AttributeError, TypeError):
    check(True, "Obstruction is frozen")


# Section 7: ObstructionResult to_dict
section("7: ObstructionResult to_dict")
d_clean = r.to_dict()
check(d_clean["verdict"] == "NO_OBSTRUCTIONS", "clean to_dict verdict")
check(d_clean["total_obstructions"] == 0, "clean to_dict count")
check(len(d_clean["obstructions"]) == 0, "clean to_dict empty list")

d_dirty = r1.to_dict()
check(d_dirty["verdict"] == "OBSTRUCTIONS_FOUND", "dirty to_dict verdict")
check(len(d_dirty["obstructions"]) > 0, "dirty to_dict has obstructions")


# Section 8: Enum values
section("8: Enum values")
check(ObstructionType.HASH_CYCLE_CONFLICT.value == "HASH_CYCLE_CONFLICT", "enum HASH_CYCLE_CONFLICT")
check(ObstructionType.PAGE_STRUCTURE_CONFLICT.value == "PAGE_STRUCTURE_CONFLICT", "enum PAGE_STRUCTURE_CONFLICT")
check(ObstructionType.COVERAGE_GAP.value == "COVERAGE_GAP", "enum COVERAGE_GAP")
check(ObstructionType.ASSIGNMENT_CONTRADICTION.value == "ASSIGNMENT_CONTRADICTION", "enum ASSIGNMENT_CONTRADICTION")
check(ObstructionType.NO_OBSTRUCTION.value == "NO_OBSTRUCTION", "enum NO_OBSTRUCTION")
check(ObstructionVerdict.OBSTRUCTIONS_FOUND.value == "OBSTRUCTIONS_FOUND", "verdict OBSTRUCTIONS_FOUND")
check(ObstructionVerdict.NO_OBSTRUCTIONS.value == "NO_OBSTRUCTIONS", "verdict NO_OBSTRUCTIONS")


# Section 9: Multiple obstructions from single override
section("9: Multiple obstructions from hash cycle override")
# A hash cycle on a universally-shared sequence produces obstructions
# for each overlap region containing that sequence
cycle_obs = [o for o in r1.obstructions if o.obstruction_type == ObstructionType.HASH_CYCLE_CONFLICT]
check(len(cycle_obs) >= 2, f"hash cycle creates >= 2 overlap conflicts (got {len(cycle_obs)})")
# two_page_mixed_reversed is shared by all 3 pairs
involved = {(o.collection_a, o.collection_b) for o in cycle_obs}
check(len(involved) >= 2, f"conflicts span >= 2 collection pairs (got {len(involved)})")


# Section 10: Determinism
section("10: Determinism — repeated detection")
ra = detect_obstructions()
rb = detect_obstructions()
check(ra.verdict == rb.verdict, "verdict deterministic")
check(ra.total_obstructions == rb.total_obstructions, "count deterministic")

r1a = detect_obstructions(override_sections=override1)
r1b = detect_obstructions(override_sections=override1)
check(r1a.total_obstructions == r1b.total_obstructions, "dirty count deterministic")


# Section 11: Each obstruction has required fields
section("11: Each obstruction has required fields")
for o in r1.obstructions:
    check(o.obstruction_type != ObstructionType.NO_OBSTRUCTION, f"type is not NO_OBSTRUCTION")
    check(len(o.sequence_name) > 0, f"sequence_name is not empty")
    check(len(o.detail) > 0, f"detail is not empty")
    check(len(o.collection_a) > 0, f"collection_a is not empty")


# SUMMARY
print(f"\n{'='*60}")
print(f"Cohomological Obstruction Detection Bridge V1 — {_passed + _failed} assertions: {_passed} passed, {_failed} failed")
if _failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_failed}")
sys.exit(0 if _failed == 0 else 1)
