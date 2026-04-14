"""
Pytest suite — Overlap Detection Bridge V1

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
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


class TestModuleMetadata:
    def test_version(self):
        assert OVERLAP_VERSION == "V1.0"
    def test_frozen(self):
        assert OVERLAP_FROZEN is True
    def test_profile_version(self):
        assert V1_OVERLAP_PROFILE.version == "V1.0"
    def test_profile_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            V1_OVERLAP_PROFILE.version = "V2.0"

class TestFrozenContractDiscovery:
    def test_collection_count(self):
        assert len(_all_collection_names()) == 3
    def test_sequence_count(self):
        assert len(_all_sequence_names()) == 3
    def test_collection_names(self):
        names = _all_collection_names()
        assert "two_seq_hv_mixed" in names
        assert "three_seq_all" in names
        assert "two_seq_all_mixed" in names
    def test_sequence_names(self):
        names = _all_sequence_names()
        assert "two_page_horizontal_vertical" in names
        assert "three_page_all_families" in names
        assert "two_page_mixed_reversed" in names

class TestCollectionOverlaps:
    def test_all_three_count(self):
        overlaps = detect_collection_overlaps()
        assert len(overlaps) == 3
    def test_hv_all_pair(self):
        overlaps = detect_collection_overlaps()
        m = {(r.collection_a, r.collection_b): r for r in overlaps}
        p = m[("two_seq_hv_mixed", "three_seq_all")]
        assert set(p.shared_sequence_names) == {"two_page_horizontal_vertical", "two_page_mixed_reversed"}
    def test_hv_allmixed_pair(self):
        overlaps = detect_collection_overlaps()
        m = {(r.collection_a, r.collection_b): r for r in overlaps}
        p = m[("two_seq_hv_mixed", "two_seq_all_mixed")]
        assert set(p.shared_sequence_names) == {"two_page_mixed_reversed"}
    def test_all_allmixed_pair(self):
        overlaps = detect_collection_overlaps()
        m = {(r.collection_a, r.collection_b): r for r in overlaps}
        p = m[("three_seq_all", "two_seq_all_mixed")]
        assert set(p.shared_sequence_names) == {"three_page_all_families", "two_page_mixed_reversed"}

class TestSequenceOverlaps:
    def test_count(self):
        overlaps = detect_sequence_overlaps()
        assert len(overlaps) == EXPECTED_SEQUENCE_OVERLAP_COUNT
    def test_shared_pages(self):
        overlaps = detect_sequence_overlaps()
        if overlaps:
            r = overlaps[0]
            assert set(r.shared_page_names) == {"two_horizontal_adj_cont", "two_vertical_adj_three"}

class TestFullOverlapMap:
    def test_verdict(self):
        m = detect_full_overlap_map()
        assert m.verdict == OverlapVerdict.OVERLAPS_FOUND
    def test_counts(self):
        m = detect_full_overlap_map()
        assert m.total_collection_overlap_regions == 3
        assert m.total_sequence_overlap_regions == 1
    def test_analyzed(self):
        m = detect_full_overlap_map()
        assert m.collections_analyzed == 3
        assert m.sequences_analyzed == 3

class TestPairCases:
    def test_hv_all(self):
        r = detect_collection_overlaps(PAIR_CASE_HV_ALL)
        assert len(r) == 1 and r[0].overlap_count == 2
    def test_hv_allmixed(self):
        r = detect_collection_overlaps(PAIR_CASE_HV_ALLMIXED)
        assert len(r) == 1 and r[0].overlap_count == 1
    def test_all_allmixed(self):
        r = detect_collection_overlaps(PAIR_CASE_ALL_ALLMIXED)
        assert len(r) == 1 and r[0].overlap_count == 2

class TestSingleCase:
    def test_no_overlap(self):
        r = detect_collection_overlaps(SINGLE_CASE)
        assert len(r) == 0
    def test_no_overlap_map(self):
        m = detect_full_overlap_map(collection_names=SINGLE_CASE, sequence_names=("two_page_horizontal_vertical",))
        assert m.verdict == OverlapVerdict.NO_OVERLAPS

class TestDataclasses:
    def test_collection_overlap_region(self):
        c = CollectionOverlapRegion(collection_a="a", collection_b="b", shared_sequence_names=("s1", "s2"))
        assert c.overlap_count == 2
        d = c.to_dict()
        assert d["overlap_count"] == 2
    def test_sequence_overlap_region(self):
        s = SequenceOverlapRegion(sequence_a="sa", sequence_b="sb", shared_page_names=("p1",))
        assert s.overlap_count == 1
    def test_overlap_map_to_dict(self):
        m = detect_full_overlap_map()
        d = m.to_dict()
        assert d["verdict"] == "OVERLAPS_FOUND"
        assert len(d["collection_overlaps"]) == 3

class TestLookupHelpers:
    def test_valid_collection(self):
        assert _get_collection_contract("two_seq_hv_mixed") is not None
    def test_invalid_collection(self):
        assert _get_collection_contract("nonexistent") is None
    def test_valid_sequence(self):
        assert _get_sequence_contract_by_name("two_page_horizontal_vertical") is not None
    def test_invalid_sequence(self):
        assert _get_sequence_contract_by_name("nonexistent") is None

class TestProfileDisabled:
    def test_no_collection_detection(self):
        p = OverlapProfile(detect_collection_overlaps=False)
        m = detect_full_overlap_map(profile=p)
        assert m.total_collection_overlap_regions == 0
    def test_no_sequence_detection(self):
        p = OverlapProfile(detect_sequence_overlaps=False)
        m = detect_full_overlap_map(profile=p)
        assert m.total_sequence_overlap_regions == 0

class TestDeterminism:
    def test_repeated_calls(self):
        a = detect_full_overlap_map()
        b = detect_full_overlap_map()
        assert a.verdict == b.verdict
        assert a.total_collection_overlap_regions == b.total_collection_overlap_regions

class TestUniversalSharedSequence:
    def test_all_pairs_share_mixed_reversed(self):
        for r in detect_collection_overlaps():
            assert "two_page_mixed_reversed" in r.shared_sequence_names

class TestPredefinedCounts:
    def test_expected_collection(self):
        assert EXPECTED_COLLECTION_OVERLAP_COUNT == 3
    def test_expected_sequence(self):
        assert EXPECTED_SEQUENCE_OVERLAP_COUNT == 1
