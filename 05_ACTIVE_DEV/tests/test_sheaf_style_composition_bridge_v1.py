"""
Pytest suite — Sheaf-Style Composition Bridge V1

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.sheaf_style_composition_bridge_v1 import (
    COMPOSITION_VERSION, COMPOSITION_FROZEN,
    CompositionVerdict, GlobalAssignment, CompositionCheckResult, CompositionResult,
    compose_global_assignment, verify_composition,
    make_contradictory_override, make_multi_contradictory_override,
    COMPOSABLE_CASE_COUNT, NOT_COMPOSABLE_CASE_COUNT,
)
from aurexis_lang.local_section_consistency_bridge_v1 import extract_local_section


class TestModuleMetadata:
    def test_version(self):
        assert COMPOSITION_VERSION == "V1.0"
    def test_frozen(self):
        assert COMPOSITION_FROZEN is True
    def test_case_counts(self):
        assert COMPOSABLE_CASE_COUNT == 1
        assert NOT_COMPOSABLE_CASE_COUNT == 2

class TestGlobalAssignment:
    def test_sequence_count(self):
        ga = compose_global_assignment()
        assert ga.sequence_count == 3
    def test_contains_all_sequences(self):
        ga = compose_global_assignment()
        assert "two_page_horizontal_vertical" in ga.assignments
        assert "three_page_all_families" in ga.assignments
        assert "two_page_mixed_reversed" in ga.assignments
    def test_hash_length(self):
        ga = compose_global_assignment()
        for h in ga.assignments.values():
            assert len(h) == 64
    def test_deterministic(self):
        a = compose_global_assignment()
        b = compose_global_assignment()
        assert a.assignments == b.assignments
    def test_to_dict(self):
        ga = compose_global_assignment()
        d = ga.to_dict()
        assert d["sequence_count"] == 3
        assert len(d["assignments"]) == 3

class TestComposable:
    def test_verdict(self):
        r = verify_composition()
        assert r.verdict == CompositionVerdict.COMPOSABLE
    def test_local_consistency(self):
        r = verify_composition()
        assert r.local_consistency_verdict == "CONSISTENT"
    def test_all_agree(self):
        r = verify_composition()
        assert r.collections_agree == 3
        assert r.collections_disagree == 0
    def test_check_results(self):
        r = verify_composition()
        for cr in r.check_results:
            assert cr.passed
            assert cr.sequences_disagree == 0

class TestSingleContradiction:
    def test_not_composable(self):
        r = verify_composition(override_sections=make_contradictory_override())
        assert r.verdict == CompositionVerdict.NOT_COMPOSABLE
    def test_at_least_one_disagrees(self):
        r = verify_composition(override_sections=make_contradictory_override())
        assert r.collections_disagree >= 1
    def test_failing_collection(self):
        r = verify_composition(override_sections=make_contradictory_override())
        failing = [cr.collection_name for cr in r.check_results if not cr.passed]
        assert "two_seq_hv_mixed" in failing

class TestMultiContradiction:
    def test_not_composable(self):
        r = verify_composition(override_sections=make_multi_contradictory_override())
        assert r.verdict == CompositionVerdict.NOT_COMPOSABLE
    def test_multiple_disagree(self):
        r = verify_composition(override_sections=make_multi_contradictory_override())
        assert r.collections_disagree >= 2

class TestCompositionResultToDict:
    def test_clean(self):
        r = verify_composition()
        d = r.to_dict()
        assert d["verdict"] == "COMPOSABLE"
        assert d["collections_checked"] == 3
        assert d["global_assignment"] is not None

class TestLocalSectionsMatchGlobal:
    def test_all_match(self):
        ga = compose_global_assignment()
        for coll in ["two_seq_hv_mixed", "three_seq_all", "two_seq_all_mixed"]:
            for seq in ga.assignments:
                sec = extract_local_section(coll, seq)
                if sec is not None:
                    assert sec.structural_hash == ga.assignments[seq]

class TestDeterminism:
    def test_repeated(self):
        a = verify_composition()
        b = verify_composition()
        assert a.verdict == b.verdict
        assert a.collections_agree == b.collections_agree
