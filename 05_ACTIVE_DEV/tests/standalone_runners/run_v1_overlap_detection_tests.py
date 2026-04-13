#!/usr/bin/env python3
"""
Standalone test runner — Overlap Detection Bridge V1

Bounded overlap detection across recovered collections, sequences, and pages.
29th bridge milestone, 1st higher-order coherence milestone.

Run:
    python run_v1_overlap_detection_tests.py

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import sys, os, traceback

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


# ════════════════════════════════════════════════════════════
# IMPORTS
# ════════════════════════════════════════════════════════════

from aurexis_lang.overlap_detection_bridge_v1 import (
    OVERLAP_VERSION, OVERLAP_FROZEN,
    OverlapVerdict, OverlapProfile, V1_OVERLAP_PROFILE,
    CollectionOverlapRegion, SequenceOverlapRegion, OverlapMap,
    detect_collection_overlaps, detect_sequence_overlaps,
    detect_full_overlap_map,
    ALL_COLLECTIONS_CASE, SINGLE_CASE,
    PAIR_CASE_HV_ALL, PAIR_CASE_HV_ALLMIXED, PAIR_CASE_ALL_ALLMIXED,
    EXPECTED_COLLECTION_OVERLAP_COUNT, EXPECTED_SEQUENCE_OVERLAP_COUNT,
    _all_collection_names, _all_sequence_names,
    _get_collection_contract, _get_sequence_contract_by_name,
)


# ════════════════════════════════════════════════════════════
# Section 1: Module metadata
# ════════════════════════════════════════════════════════════

section("1: Module metadata")
check(OVERLAP_VERSION == "V1.0", "OVERLAP_VERSION is V1.0")
check(OVERLAP_FROZEN is True, "OVERLAP_FROZEN is True")
check(V1_OVERLAP_PROFILE.version == "V1.0", "V1_OVERLAP_PROFILE version")
check(V1_OVERLAP_PROFILE.detect_collection_overlaps is True, "profile detects collection overlaps")
check(V1_OVERLAP_PROFILE.detect_sequence_overlaps is True, "profile detects sequence overlaps")
check(V1_OVERLAP_PROFILE.require_frozen_contracts_only is True, "profile requires frozen contracts")


# ════════════════════════════════════════════════════════════
# Section 2: Frozen contract discovery
# ════════════════════════════════════════════════════════════

section("2: Frozen contract discovery")
coll_names = _all_collection_names()
seq_names = _all_sequence_names()
check(len(coll_names) == 3, f"3 frozen collection contracts (got {len(coll_names)})")
check(len(seq_names) == 3, f"3 frozen sequence contracts (got {len(seq_names)})")
check("two_seq_hv_mixed" in coll_names, "two_seq_hv_mixed in collections")
check("three_seq_all" in coll_names, "three_seq_all in collections")
check("two_seq_all_mixed" in coll_names, "two_seq_all_mixed in collections")
check("two_page_horizontal_vertical" in seq_names, "two_page_horizontal_vertical in sequences")
check("three_page_all_families" in seq_names, "three_page_all_families in sequences")
check("two_page_mixed_reversed" in seq_names, "two_page_mixed_reversed in sequences")


# ════════════════════════════════════════════════════════════
# Section 3: Collection-level overlap detection — all 3
# ════════════════════════════════════════════════════════════

section("3: Collection-level overlap — all 3 frozen collections")
coll_overlaps = detect_collection_overlaps()
check(len(coll_overlaps) == 3, f"3 pairwise collection overlaps (got {len(coll_overlaps)})")

# Verify each expected overlap pair
overlap_map_coll = {(r.collection_a, r.collection_b): r for r in coll_overlaps}

pair1 = overlap_map_coll.get(("two_seq_hv_mixed", "three_seq_all"))
check(pair1 is not None, "overlap: two_seq_hv_mixed ∩ three_seq_all exists")
if pair1:
    check(set(pair1.shared_sequence_names) == {"two_page_horizontal_vertical", "two_page_mixed_reversed"},
          "two_seq_hv_mixed ∩ three_seq_all shares 2 sequences")
    check(pair1.overlap_count == 2, "overlap count is 2")

pair2 = overlap_map_coll.get(("two_seq_hv_mixed", "two_seq_all_mixed"))
check(pair2 is not None, "overlap: two_seq_hv_mixed ∩ two_seq_all_mixed exists")
if pair2:
    check(set(pair2.shared_sequence_names) == {"two_page_mixed_reversed"},
          "two_seq_hv_mixed ∩ two_seq_all_mixed shares 1 sequence")
    check(pair2.overlap_count == 1, "overlap count is 1")

pair3 = overlap_map_coll.get(("three_seq_all", "two_seq_all_mixed"))
check(pair3 is not None, "overlap: three_seq_all ∩ two_seq_all_mixed exists")
if pair3:
    check(set(pair3.shared_sequence_names) == {"three_page_all_families", "two_page_mixed_reversed"},
          "three_seq_all ∩ two_seq_all_mixed shares 2 sequences")
    check(pair3.overlap_count == 2, "overlap count is 2")


# ════════════════════════════════════════════════════════════
# Section 4: Sequence-level overlap detection
# ════════════════════════════════════════════════════════════

section("4: Sequence-level overlap — all 3 frozen sequences")
seq_overlaps = detect_sequence_overlaps()
check(len(seq_overlaps) == EXPECTED_SEQUENCE_OVERLAP_COUNT,
      f"expected {EXPECTED_SEQUENCE_OVERLAP_COUNT} sequence overlap(s) (got {len(seq_overlaps)})")
if seq_overlaps:
    r = seq_overlaps[0]
    check(r.sequence_a == "two_page_horizontal_vertical", "seq overlap pair a")
    check(r.sequence_b == "three_page_all_families", "seq overlap pair b")
    check(set(r.shared_page_names) == {"two_horizontal_adj_cont", "two_vertical_adj_three"},
          "shared pages: two_horizontal_adj_cont + two_vertical_adj_three")
    check(r.overlap_count == 2, "sequence overlap count is 2")


# ════════════════════════════════════════════════════════════
# Section 5: Full overlap map
# ════════════════════════════════════════════════════════════

section("5: Full overlap map")
full_map = detect_full_overlap_map()
check(full_map.verdict == OverlapVerdict.OVERLAPS_FOUND, "verdict is OVERLAPS_FOUND")
check(full_map.total_collection_overlap_regions == 3, "3 collection overlap regions")
check(full_map.total_sequence_overlap_regions == 1, "1 sequence overlap region")
check(full_map.collections_analyzed == 3, "3 collections analyzed")
check(full_map.sequences_analyzed == 3, "3 sequences analyzed")
check(full_map.version == "V1.0", "map version is V1.0")


# ════════════════════════════════════════════════════════════
# Section 6: Pair-specific cases
# ════════════════════════════════════════════════════════════

section("6: Pair-specific overlap cases")
r1 = detect_collection_overlaps(PAIR_CASE_HV_ALL)
check(len(r1) == 1, "PAIR_CASE_HV_ALL: 1 overlap")
if r1:
    check(r1[0].overlap_count == 2, "shares 2 sequences")

r2 = detect_collection_overlaps(PAIR_CASE_HV_ALLMIXED)
check(len(r2) == 1, "PAIR_CASE_HV_ALLMIXED: 1 overlap")
if r2:
    check(r2[0].overlap_count == 1, "shares 1 sequence")

r3 = detect_collection_overlaps(PAIR_CASE_ALL_ALLMIXED)
check(len(r3) == 1, "PAIR_CASE_ALL_ALLMIXED: 1 overlap")
if r3:
    check(r3[0].overlap_count == 2, "shares 2 sequences")


# ════════════════════════════════════════════════════════════
# Section 7: Single collection — no overlap possible
# ════════════════════════════════════════════════════════════

section("7: Single collection — no overlap")
r_single = detect_collection_overlaps(SINGLE_CASE)
check(len(r_single) == 0, "single collection has no overlaps")
m_single = detect_full_overlap_map(collection_names=SINGLE_CASE, sequence_names=("two_page_horizontal_vertical",))
check(m_single.verdict == OverlapVerdict.NO_OVERLAPS, "single collection verdict is NO_OVERLAPS")


# ════════════════════════════════════════════════════════════
# Section 8: CollectionOverlapRegion dataclass
# ════════════════════════════════════════════════════════════

section("8: CollectionOverlapRegion dataclass")
cor = CollectionOverlapRegion(
    collection_a="test_a", collection_b="test_b",
    shared_sequence_names=("seq1", "seq2", "seq3"),
)
check(cor.overlap_count == 3, "overlap_count property works")
d = cor.to_dict()
check(d["collection_a"] == "test_a", "to_dict collection_a")
check(d["overlap_count"] == 3, "to_dict overlap_count")
check(len(d["shared_sequence_names"]) == 3, "to_dict shared_sequence_names length")


# ════════════════════════════════════════════════════════════
# Section 9: SequenceOverlapRegion dataclass
# ════════════════════════════════════════════════════════════

section("9: SequenceOverlapRegion dataclass")
sor = SequenceOverlapRegion(
    sequence_a="seqA", sequence_b="seqB",
    shared_page_names=("page1",),
)
check(sor.overlap_count == 1, "sequence overlap_count property works")
d2 = sor.to_dict()
check(d2["sequence_a"] == "seqA", "to_dict sequence_a")
check(d2["overlap_count"] == 1, "to_dict overlap_count")


# ════════════════════════════════════════════════════════════
# Section 10: OverlapMap to_dict
# ════════════════════════════════════════════════════════════

section("10: OverlapMap to_dict")
fd = full_map.to_dict()
check(fd["verdict"] == "OVERLAPS_FOUND", "to_dict verdict string")
check(len(fd["collection_overlaps"]) == 3, "to_dict collection_overlaps count")
check(len(fd["sequence_overlaps"]) == 1, "to_dict sequence_overlaps count")
check(fd["collections_analyzed"] == 3, "to_dict collections_analyzed")
check(fd["version"] == "V1.0", "to_dict version")


# ════════════════════════════════════════════════════════════
# Section 11: Contract lookup helpers
# ════════════════════════════════════════════════════════════

section("11: Contract lookup helpers")
c1 = _get_collection_contract("two_seq_hv_mixed")
check(c1 is not None, "lookup two_seq_hv_mixed succeeds")
check(c1.name == "two_seq_hv_mixed", "correct contract returned")
check(_get_collection_contract("nonexistent") is None, "nonexistent returns None")

s1 = _get_sequence_contract_by_name("two_page_horizontal_vertical")
check(s1 is not None, "lookup two_page_horizontal_vertical succeeds")
check(s1.name == "two_page_horizontal_vertical", "correct sequence contract returned")
check(_get_sequence_contract_by_name("nonexistent") is None, "nonexistent seq returns None")


# ════════════════════════════════════════════════════════════
# Section 12: OverlapProfile frozen
# ════════════════════════════════════════════════════════════

section("12: OverlapProfile frozen")
try:
    V1_OVERLAP_PROFILE.version = "V2.0"
    check(False, "profile should be frozen")
except (AttributeError, TypeError, Exception):
    check(True, "profile is frozen (immutable)")


# ════════════════════════════════════════════════════════════
# Section 13: Profile with detection disabled
# ════════════════════════════════════════════════════════════

section("13: Profile with collection detection disabled")
no_coll_profile = OverlapProfile(detect_collection_overlaps=False, detect_sequence_overlaps=True)
m_nc = detect_full_overlap_map(profile=no_coll_profile)
check(m_nc.total_collection_overlap_regions == 0, "no collection overlaps when disabled")
check(m_nc.total_sequence_overlap_regions > 0, "sequence overlaps still detected")

no_seq_profile = OverlapProfile(detect_collection_overlaps=True, detect_sequence_overlaps=False)
m_ns = detect_full_overlap_map(profile=no_seq_profile)
check(m_ns.total_collection_overlap_regions > 0, "collection overlaps still detected")
check(m_ns.total_sequence_overlap_regions == 0, "no sequence overlaps when disabled")


# ════════════════════════════════════════════════════════════
# Section 14: Determinism
# ════════════════════════════════════════════════════════════

section("14: Determinism — repeated calls produce identical results")
m_a = detect_full_overlap_map()
m_b = detect_full_overlap_map()
check(m_a.verdict == m_b.verdict, "verdict deterministic")
check(m_a.total_collection_overlap_regions == m_b.total_collection_overlap_regions, "coll overlap count deterministic")
check(m_a.total_sequence_overlap_regions == m_b.total_sequence_overlap_regions, "seq overlap count deterministic")
for i in range(len(m_a.collection_overlaps)):
    check(m_a.collection_overlaps[i].collection_a == m_b.collection_overlaps[i].collection_a, f"coll overlap {i} a deterministic")
    check(m_a.collection_overlaps[i].shared_sequence_names == m_b.collection_overlaps[i].shared_sequence_names, f"coll overlap {i} shared deterministic")


# ════════════════════════════════════════════════════════════
# Section 15: Universal shared sequence
# ════════════════════════════════════════════════════════════

section("15: Universal shared sequence — two_page_mixed_reversed")
# All 3 collection pairs share two_page_mixed_reversed
for r in coll_overlaps:
    check("two_page_mixed_reversed" in r.shared_sequence_names,
          f"{r.collection_a} ∩ {r.collection_b} shares two_page_mixed_reversed")


# ════════════════════════════════════════════════════════════
# Section 16: Expected predefined counts
# ════════════════════════════════════════════════════════════

section("16: Expected predefined counts")
check(EXPECTED_COLLECTION_OVERLAP_COUNT == 3, "EXPECTED_COLLECTION_OVERLAP_COUNT == 3")
check(EXPECTED_SEQUENCE_OVERLAP_COUNT == 1, "EXPECTED_SEQUENCE_OVERLAP_COUNT == 1")
check(len(ALL_COLLECTIONS_CASE) == 3, "ALL_COLLECTIONS_CASE has 3 names")
check(len(SINGLE_CASE) == 1, "SINGLE_CASE has 1 name")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"Overlap Detection Bridge V1 — {_passed + _failed} assertions: {_passed} passed, {_failed} failed")
if _failed == 0:
    print("ALL PASS ✓")
else:
    print(f"FAILURES: {_failed}")
sys.exit(0 if _failed == 0 else 1)
