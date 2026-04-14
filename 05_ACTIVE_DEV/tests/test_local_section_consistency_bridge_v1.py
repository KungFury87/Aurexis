"""
Pytest suite — Local Section Consistency Bridge V1

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
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
from aurexis_lang.overlap_detection_bridge_v1 import detect_collection_overlaps


class TestModuleMetadata:
    def test_version(self):
        assert LOCAL_SECTION_VERSION == "V1.0"
    def test_frozen(self):
        assert LOCAL_SECTION_FROZEN is True
    def test_case_count(self):
        assert INCONSISTENCY_CASE_COUNT == 3

class TestStructuralHash:
    def test_deterministic(self):
        h1 = compute_structural_hash("s", 2, ("a", "b"))
        h2 = compute_structural_hash("s", 2, ("a", "b"))
        assert h1 == h2
    def test_different_count(self):
        h1 = compute_structural_hash("s", 2, ("a", "b"))
        h2 = compute_structural_hash("s", 3, ("a", "b"))
        assert h1 != h2
    def test_different_names(self):
        h1 = compute_structural_hash("s", 2, ("a", "b"))
        h2 = compute_structural_hash("s", 2, ("a", "c"))
        assert h1 != h2
    def test_sha256_length(self):
        h = compute_structural_hash("test", 1, ("p",))
        assert len(h) == 64

class TestLocalSectionExtraction:
    def test_valid(self):
        s = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
        assert s is not None
        assert s.collection_name == "two_seq_hv_mixed"
        assert s.sequence_name == "two_page_mixed_reversed"
        assert s.page_count == 2
    def test_nonexistent_collection(self):
        assert extract_local_section("nonexistent", "two_page_mixed_reversed") is None
    def test_nonexistent_sequence(self):
        assert extract_local_section("two_seq_hv_mixed", "nonexistent") is None
    def test_frozen(self):
        s = extract_local_section("two_seq_hv_mixed", "two_page_mixed_reversed")
        with pytest.raises((AttributeError, TypeError)):
            s.collection_name = "mutant"

class TestConsistentPair:
    def test_same_hash(self):
        a, b = make_consistent_pair()
        assert a.structural_hash == b.structural_hash
    def test_different_collections(self):
        a, b = make_consistent_pair()
        assert a.collection_name != b.collection_name
    def test_verdict(self):
        a, b = make_consistent_pair()
        r = check_local_section_consistency(a, b)
        assert r.verdict == LocalSectionVerdict.CONSISTENT
        assert r.inconsistency_type == SectionInconsistencyType.NO_INCONSISTENCY

class TestSignatureMismatch:
    def test_verdict(self):
        a, b = make_signature_mismatch_pair()
        r = check_local_section_consistency(a, b)
        assert r.verdict == LocalSectionVerdict.INCONSISTENT
        assert r.inconsistency_type == SectionInconsistencyType.SIGNATURE_MISMATCH

class TestPageCountMismatch:
    def test_verdict(self):
        a, b = make_page_count_mismatch_pair()
        r = check_local_section_consistency(a, b)
        assert r.verdict == LocalSectionVerdict.INCONSISTENT
        assert r.inconsistency_type == SectionInconsistencyType.PAGE_COUNT_MISMATCH

class TestPageNamesMismatch:
    def test_verdict(self):
        a, b = make_page_names_mismatch_pair()
        r = check_local_section_consistency(a, b)
        assert r.verdict == LocalSectionVerdict.INCONSISTENT
        assert r.inconsistency_type == SectionInconsistencyType.PAGE_NAMES_MISMATCH

class TestOverlapRegionConsistency:
    def test_all_pairs_consistent(self):
        for region in detect_collection_overlaps():
            r = check_overlap_consistency(region)
            assert r.verdict == LocalSectionVerdict.CONSISTENT
            assert r.checks_failed == 0

class TestAllOverlapsConsistency:
    def test_all_consistent(self):
        r = check_all_overlaps_consistency()
        assert r.verdict == LocalSectionVerdict.CONSISTENT
        assert r.overlap_regions_checked == 3
        assert r.overlap_regions_consistent == 3
    def test_to_dict(self):
        r = check_all_overlaps_consistency()
        d = r.to_dict()
        assert d["verdict"] == "CONSISTENT"
        assert d["overlap_regions_checked"] == 3

class TestSectionCheckResultToDict:
    def test_consistent(self):
        a, b = make_consistent_pair()
        r = check_local_section_consistency(a, b)
        d = r.to_dict()
        assert d["verdict"] == "CONSISTENT"
        assert d["inconsistency_type"] == "NO_INCONSISTENCY"

class TestDeterminism:
    def test_repeated(self):
        a = check_all_overlaps_consistency()
        b = check_all_overlaps_consistency()
        assert a.verdict == b.verdict
        assert a.overlap_regions_consistent == b.overlap_regions_consistent

class TestCrossCollectionExtraction:
    def test_all_share_mixed_reversed(self):
        secs = []
        for c in ["two_seq_hv_mixed", "three_seq_all", "two_seq_all_mixed"]:
            s = extract_local_section(c, "two_page_mixed_reversed")
            assert s is not None
            secs.append(s)
        assert secs[0].structural_hash == secs[1].structural_hash == secs[2].structural_hash
