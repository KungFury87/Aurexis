#!/usr/bin/env python3
"""
Standalone test runner — Local Section Consistency Bridge V1

Bounded local-section agreement verification for overlapping collections.
30th bridge milestone, 2nd higher-order coherence milestone.

Run:
    python run_v1_local_section_consistency_tests.py

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


from aurexis_lang.local_section_consistency_bridge_v1 import (
    LOCAL_SECTION_VERSION, LOCAL_SECTION_FROZEN,
    LocalSectionVerdict, SectionInconsistencyType,
    LocalSection, SectionCheckResult, OverlapConsistencyResult, AllOverlapsConsistencyResult,
    extract_local_section, check_local_section_consistency,
    check_overlap_consistency, check_all_overlaps_consistency,
    compute_structural_hash,
    make_consistent_pair, make_signature_mismatch_pair,
    make_page_count_mismatch_pair, make_page_names_mismatch_pair,
    INCONSISTENCY_CASE_COUNT,
)
from aurexis_lang.overlap_detection_bridge_v1 import (
    detect_collection_overlaps, CollectionOverlapRegion,
)


# Section 1: Module metadata
section("1: Module metadata")
check(LOCAL_SECTION_VERSION == "V1.0", "LOCAL_SECTION_VERSION is V1.0")
check(LOCAL_SECTION_FROZEN is True, "LOCAL_SECTION_FROZEN is True")
check(INCONSISTENCY_CASE_COUNT == 3, "3 predefined inconsistency cases")


# Section 2: Structural hash determinism
section("2: Structural hash determinism")
h1 = compute_structural_hash("test_seq", 2, ("page_a", "page_b"))
h2 = compute_structural_hash("test_seq", 2, ("page_a", "page_b"))
h3 = compute_structural_hash("test_seq", 3, ("page_a", "page_b"))
h4 = compute_structural_hash("test_seq", 2, ("page_a", "page_c"))
check(h1 == h2, "same inputs → same hash")
check(h1 != h3, "different page_count → different hash")
check(h1 != h4, "different page_names → different hash")
check(len(h1) == 64, "hash is 64-char hex (SHA-256)")


# Section 3: Local section extraction
section("3: Local section extraction")
sec = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
check(sec is not None, "extraction succeeds for valid collection/sequence")
if sec:
    check(sec.collection_name == "two_seq_hv_mixed", "correct collection name")
    check(sec.sequence_name == "two_page_mixed_reversed", "correct sequence name")
    check(sec.page_count == 2, "correct page count")
    check(len(sec.page_contract_names) == 2, "correct page contract names count")
    check(len(sec.structural_hash) == 64, "structural hash is 64-char hex")

check(extract_local_section("nonexistent", "two_page_mixed_reversed") is None, "nonexistent collection returns None")
check(extract_local_section("two_seq_hv_mixed", "nonexistent") is None, "nonexistent sequence returns None")


# Section 4: Consistent pair
section("4: Consistent pair — same sequence from different collections")
a, b = make_consistent_pair()
check(a is not None and b is not None, "consistent pair extracted")
if a and b:
    check(a.sequence_name == b.sequence_name, "same sequence name")
    check(a.collection_name != b.collection_name, "different collection names")
    check(a.structural_hash == b.structural_hash, "same structural hash")
    check(a.page_count == b.page_count, "same page count")
    check(a.page_contract_names == b.page_contract_names, "same page contract names")
    r = check_local_section_consistency(a, b)
    check(r.verdict == LocalSectionVerdict.CONSISTENT, "consistent pair → CONSISTENT")
    check(r.inconsistency_type == SectionInconsistencyType.NO_INCONSISTENCY, "no inconsistency type")


# Section 5: Signature mismatch
section("5: Fabricated signature mismatch")
a, b = make_signature_mismatch_pair()
check(a is not None and b is not None, "mismatch pair fabricated")
if a and b:
    r = check_local_section_consistency(a, b)
    check(r.verdict == LocalSectionVerdict.INCONSISTENT, "verdict is INCONSISTENT")
    check(r.inconsistency_type == SectionInconsistencyType.SIGNATURE_MISMATCH, "type is SIGNATURE_MISMATCH")


# Section 6: Page count mismatch
section("6: Fabricated page count mismatch")
a, b = make_page_count_mismatch_pair()
check(a is not None and b is not None, "page count pair fabricated")
if a and b:
    r = check_local_section_consistency(a, b)
    check(r.verdict == LocalSectionVerdict.INCONSISTENT, "verdict is INCONSISTENT")
    check(r.inconsistency_type == SectionInconsistencyType.PAGE_COUNT_MISMATCH, "type is PAGE_COUNT_MISMATCH")


# Section 7: Page names mismatch
section("7: Fabricated page names mismatch")
a, b = make_page_names_mismatch_pair()
check(a is not None and b is not None, "page names pair fabricated")
if a and b:
    r = check_local_section_consistency(a, b)
    check(r.verdict == LocalSectionVerdict.INCONSISTENT, "verdict is INCONSISTENT")
    check(r.inconsistency_type == SectionInconsistencyType.PAGE_NAMES_MISMATCH, "type is PAGE_NAMES_MISMATCH")


# Section 8: Overlap region consistency — all 3 pairs
section("8: Overlap region consistency — all 3 pairs")
overlaps = detect_collection_overlaps()
for region in overlaps:
    r = check_overlap_consistency(region)
    check(r.verdict == LocalSectionVerdict.CONSISTENT,
          f"{region.collection_a} ∩ {region.collection_b} CONSISTENT")
    check(r.checks_passed == r.checks_performed,
          f"all {r.checks_performed} checks passed")
    check(r.checks_failed == 0, "no failed checks")


# Section 9: All overlaps consistency
section("9: All overlaps consistency")
all_r = check_all_overlaps_consistency()
check(all_r.verdict == LocalSectionVerdict.CONSISTENT, "all overlaps CONSISTENT")
check(all_r.overlap_regions_checked == 3, "3 overlap regions checked")
check(all_r.overlap_regions_consistent == 3, "3 regions consistent")
check(all_r.overlap_regions_inconsistent == 0, "0 regions inconsistent")


# Section 10: LocalSection frozen and to_dict
section("10: LocalSection frozen and to_dict")
if sec:
    try:
        sec.collection_name = "mutant"
        check(False, "LocalSection should be frozen")
    except (AttributeError, TypeError):
        check(True, "LocalSection is frozen")
    d = sec.to_dict()
    check(d["collection_name"] == "two_seq_hv_mixed", "to_dict collection_name")
    check(d["sequence_name"] == "two_page_mixed_reversed", "to_dict sequence_name")
    check(len(d["structural_hash"]) == 64, "to_dict structural_hash")


# Section 11: SectionCheckResult to_dict
section("11: SectionCheckResult and OverlapConsistencyResult to_dict")
a, b = make_consistent_pair()
if a and b:
    r = check_local_section_consistency(a, b)
    d = r.to_dict()
    check(d["verdict"] == "CONSISTENT", "to_dict verdict")
    check(d["inconsistency_type"] == "NO_INCONSISTENCY", "to_dict inconsistency_type")

all_d = all_r.to_dict()
check(all_d["verdict"] == "CONSISTENT", "all to_dict verdict")
check(all_d["overlap_regions_checked"] == 3, "all to_dict regions count")


# Section 12: Determinism
section("12: Determinism — repeated calls produce identical results")
r_a = check_all_overlaps_consistency()
r_b = check_all_overlaps_consistency()
check(r_a.verdict == r_b.verdict, "verdict deterministic")
check(r_a.overlap_regions_checked == r_b.overlap_regions_checked, "regions count deterministic")
check(r_a.overlap_regions_consistent == r_b.overlap_regions_consistent, "consistent count deterministic")


# Section 13: Cross-collection section extraction for all shared sequences
section("13: Cross-collection section extraction for all shared sequences")
# two_page_mixed_reversed is shared by all 3 collections
for cname in ["two_seq_hv_mixed", "three_seq_all", "two_seq_all_mixed"]:
    s = extract_local_section(cname, "two_page_mixed_reversed")
    check(s is not None, f"{cname} has section for two_page_mixed_reversed")
    if s:
        check(s.structural_hash == sec.structural_hash, f"{cname} hash matches")


# SUMMARY
print(f"\n{'='*60}")
print(f"Local Section Consistency Bridge V1 — {_passed + _failed} assertions: {_passed} passed, {_failed} failed")
if _failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_failed}")
sys.exit(0 if _failed == 0 else 1)
