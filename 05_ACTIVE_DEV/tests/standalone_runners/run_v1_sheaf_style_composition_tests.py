#!/usr/bin/env python3
"""
Standalone test runner — Sheaf-Style Composition Bridge V1

Bounded composition proof: locally consistent sections compose into a
globally coherent assignment. 31st bridge, 3rd higher-order coherence.

Run:
    python run_v1_sheaf_style_composition_tests.py

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


from aurexis_lang.sheaf_style_composition_bridge_v1 import (
    COMPOSITION_VERSION, COMPOSITION_FROZEN,
    CompositionVerdict, GlobalAssignment, CompositionCheckResult, CompositionResult,
    compose_global_assignment, verify_composition,
    make_contradictory_override, make_multi_contradictory_override,
    COMPOSABLE_CASE_COUNT, NOT_COMPOSABLE_CASE_COUNT,
)
from aurexis_lang.local_section_consistency_bridge_v1 import (
    extract_local_section, LocalSection,
)


# Section 1: Module metadata
section("1: Module metadata")
check(COMPOSITION_VERSION == "V1.0", "COMPOSITION_VERSION is V1.0")
check(COMPOSITION_FROZEN is True, "COMPOSITION_FROZEN is True")
check(COMPOSABLE_CASE_COUNT == 1, "1 composable case")
check(NOT_COMPOSABLE_CASE_COUNT == 2, "2 not-composable cases")


# Section 2: Global assignment construction
section("2: Global assignment construction")
ga = compose_global_assignment()
check(ga.sequence_count == 3, f"3 sequences in global assignment (got {ga.sequence_count})")
check("two_page_horizontal_vertical" in ga.assignments, "two_page_horizontal_vertical in assignment")
check("three_page_all_families" in ga.assignments, "three_page_all_families in assignment")
check("two_page_mixed_reversed" in ga.assignments, "two_page_mixed_reversed in assignment")
for name, h in ga.assignments.items():
    check(len(h) == 64, f"{name} hash is 64-char hex")


# Section 3: Global assignment determinism
section("3: Global assignment determinism")
ga2 = compose_global_assignment()
check(ga.assignments == ga2.assignments, "same assignments on repeated call")


# Section 4: Composable verification — frozen contracts
section("4: Composable verification — frozen contracts")
r = verify_composition()
check(r.verdict == CompositionVerdict.COMPOSABLE, "verdict is COMPOSABLE")
check(r.local_consistency_verdict == "CONSISTENT", "local consistency is CONSISTENT")
check(r.collections_checked == 3, "3 collections checked")
check(r.collections_agree == 3, "3 collections agree")
check(r.collections_disagree == 0, "0 collections disagree")
check(r.global_assignment is not None, "global assignment present")
if r.global_assignment:
    check(r.global_assignment.sequence_count == 3, "global has 3 sequences")
for cr in r.check_results:
    check(cr.passed, f"{cr.collection_name} passed")
    check(cr.sequences_disagree == 0, f"{cr.collection_name} no disagreements")


# Section 5: Single contradiction
section("5: Single contradiction — NOT_COMPOSABLE")
override = make_contradictory_override()
check(override is not None, "contradictory override created")
r2 = verify_composition(override_sections=override)
check(r2.verdict == CompositionVerdict.NOT_COMPOSABLE, "verdict is NOT_COMPOSABLE")
check(r2.collections_disagree >= 1, "at least 1 collection disagrees")
# Find the failing collection
failing = [cr for cr in r2.check_results if not cr.passed]
check(len(failing) >= 1, "at least 1 failing check result")
if failing:
    check("two_seq_hv_mixed" in [f.collection_name for f in failing],
          "two_seq_hv_mixed is the failing collection")


# Section 6: Multi contradiction
section("6: Multi contradiction — NOT_COMPOSABLE")
override2 = make_multi_contradictory_override()
check(override2 is not None and len(override2) == 2, "multi override has 2 collections")
r3 = verify_composition(override_sections=override2)
check(r3.verdict == CompositionVerdict.NOT_COMPOSABLE, "verdict is NOT_COMPOSABLE")
check(r3.collections_disagree >= 2, f"at least 2 collections disagree (got {r3.collections_disagree})")


# Section 7: GlobalAssignment to_dict
section("7: GlobalAssignment to_dict")
d = ga.to_dict()
check(d["sequence_count"] == 3, "to_dict sequence_count")
check(len(d["assignments"]) == 3, "to_dict assignments count")
check(d["version"] == "V1.0", "to_dict version")


# Section 8: CompositionResult to_dict
section("8: CompositionResult to_dict")
d2 = r.to_dict()
check(d2["verdict"] == "COMPOSABLE", "to_dict verdict")
check(d2["collections_checked"] == 3, "to_dict collections_checked")
check(d2["global_assignment"] is not None, "to_dict has global_assignment")
check(len(d2["check_results"]) == 3, "to_dict has 3 check_results")


# Section 9: CompositionCheckResult details
section("9: CompositionCheckResult details for clean case")
for cr in r.check_results:
    check(cr.sequences_checked > 0, f"{cr.collection_name} checked sequences")
    check(cr.sequences_agree == cr.sequences_checked, f"{cr.collection_name} all sequences agree")
    d3 = cr.to_dict()
    check(d3["passed"] is True, f"{cr.collection_name} to_dict passed")


# Section 10: Local sections match global assignment
section("10: Local sections match global assignment")
for coll_name in ["two_seq_hv_mixed", "three_seq_all", "two_seq_all_mixed"]:
    for seq_name in ga.assignments:
        sec = extract_local_section(coll_name, seq_name)
        if sec is not None:
            check(sec.structural_hash == ga.assignments[seq_name],
                  f"{coll_name}/{seq_name} matches global")


# Section 11: Determinism
section("11: Determinism — repeated verification")
ra = verify_composition()
rb = verify_composition()
check(ra.verdict == rb.verdict, "verdict deterministic")
check(ra.collections_agree == rb.collections_agree, "agree count deterministic")


# SUMMARY
print(f"\n{'='*60}")
print(f"Sheaf-Style Composition Bridge V1 — {_passed + _failed} assertions: {_passed} passed, {_failed} failed")
if _failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_failed}")
sys.exit(0 if _failed == 0 else 1)
