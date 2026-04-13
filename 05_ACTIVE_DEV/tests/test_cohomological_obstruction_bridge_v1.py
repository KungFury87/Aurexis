"""
Pytest suite — Cohomological Obstruction Detection Bridge V1

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import pytest
from aurexis_lang.cohomological_obstruction_bridge_v1 import (
    OBSTRUCTION_VERSION, OBSTRUCTION_FROZEN,
    ObstructionType, ObstructionVerdict,
    Obstruction, ObstructionResult,
    detect_obstructions,
    make_hash_cycle_override, make_page_structure_override,
    make_assignment_contradiction_override,
    CLEAN_CASE_COUNT, OBSTRUCTION_CASE_COUNT,
)


class TestModuleMetadata:
    def test_version(self):
        assert OBSTRUCTION_VERSION == "V1.0"
    def test_frozen(self):
        assert OBSTRUCTION_FROZEN is True
    def test_case_counts(self):
        assert CLEAN_CASE_COUNT == 1
        assert OBSTRUCTION_CASE_COUNT == 3

class TestCleanCase:
    def test_no_obstructions(self):
        r = detect_obstructions()
        assert r.verdict == ObstructionVerdict.NO_OBSTRUCTIONS
        assert r.total_obstructions == 0
    def test_overlap_regions_checked(self):
        r = detect_obstructions()
        assert r.overlap_regions_checked == 3
    def test_sequences_checked(self):
        r = detect_obstructions()
        assert r.sequences_checked > 0

class TestHashCycleConflict:
    def test_found(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        assert r.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND
    def test_type(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        types = {o.obstruction_type for o in r.obstructions}
        assert ObstructionType.HASH_CYCLE_CONFLICT in types
    def test_sequence(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        seqs = {o.sequence_name for o in r.obstructions}
        assert "two_page_mixed_reversed" in seqs

class TestPageStructureConflict:
    def test_found(self):
        r = detect_obstructions(override_sections=make_page_structure_override())
        assert r.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND
    def test_type(self):
        r = detect_obstructions(override_sections=make_page_structure_override())
        types = {o.obstruction_type for o in r.obstructions}
        assert ObstructionType.PAGE_STRUCTURE_CONFLICT in types

class TestAssignmentContradiction:
    def test_found(self):
        r = detect_obstructions(override_sections=make_assignment_contradiction_override())
        assert r.verdict == ObstructionVerdict.OBSTRUCTIONS_FOUND
    def test_type(self):
        r = detect_obstructions(override_sections=make_assignment_contradiction_override())
        types = {o.obstruction_type for o in r.obstructions}
        assert ObstructionType.ASSIGNMENT_CONTRADICTION in types

class TestObstructionDataclass:
    def test_fields(self):
        o = Obstruction(
            obstruction_type=ObstructionType.HASH_CYCLE_CONFLICT,
            collection_a="a", collection_b="b",
            sequence_name="s", detail="d",
        )
        assert o.obstruction_type == ObstructionType.HASH_CYCLE_CONFLICT
    def test_frozen(self):
        o = Obstruction()
        with pytest.raises((AttributeError, TypeError)):
            o.detail = "mutant"
    def test_to_dict(self):
        o = Obstruction(
            obstruction_type=ObstructionType.COVERAGE_GAP,
            collection_a="ca", collection_b="cb",
            sequence_name="sn", detail="dd",
        )
        d = o.to_dict()
        assert d["obstruction_type"] == "COVERAGE_GAP"
        assert d["collection_a"] == "ca"

class TestObstructionResultToDict:
    def test_clean(self):
        r = detect_obstructions()
        d = r.to_dict()
        assert d["verdict"] == "NO_OBSTRUCTIONS"
        assert d["total_obstructions"] == 0
    def test_dirty(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        d = r.to_dict()
        assert d["verdict"] == "OBSTRUCTIONS_FOUND"
        assert len(d["obstructions"]) > 0

class TestEnumValues:
    def test_obstruction_types(self):
        assert ObstructionType.HASH_CYCLE_CONFLICT.value == "HASH_CYCLE_CONFLICT"
        assert ObstructionType.PAGE_STRUCTURE_CONFLICT.value == "PAGE_STRUCTURE_CONFLICT"
        assert ObstructionType.COVERAGE_GAP.value == "COVERAGE_GAP"
        assert ObstructionType.ASSIGNMENT_CONTRADICTION.value == "ASSIGNMENT_CONTRADICTION"
        assert ObstructionType.NO_OBSTRUCTION.value == "NO_OBSTRUCTION"
    def test_verdicts(self):
        assert ObstructionVerdict.OBSTRUCTIONS_FOUND.value == "OBSTRUCTIONS_FOUND"
        assert ObstructionVerdict.NO_OBSTRUCTIONS.value == "NO_OBSTRUCTIONS"

class TestMultipleObstructions:
    def test_cycle_creates_multiple(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        cycle = [o for o in r.obstructions if o.obstruction_type == ObstructionType.HASH_CYCLE_CONFLICT]
        assert len(cycle) >= 2
    def test_involved_pairs(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        cycle = [o for o in r.obstructions if o.obstruction_type == ObstructionType.HASH_CYCLE_CONFLICT]
        pairs = {(o.collection_a, o.collection_b) for o in cycle}
        assert len(pairs) >= 2

class TestDeterminism:
    def test_clean(self):
        a = detect_obstructions()
        b = detect_obstructions()
        assert a.verdict == b.verdict
        assert a.total_obstructions == b.total_obstructions
    def test_dirty(self):
        ov = make_hash_cycle_override()
        a = detect_obstructions(override_sections=ov)
        b = detect_obstructions(override_sections=ov)
        assert a.total_obstructions == b.total_obstructions

class TestObstructionFields:
    def test_all_have_fields(self):
        r = detect_obstructions(override_sections=make_hash_cycle_override())
        for o in r.obstructions:
            assert o.obstruction_type != ObstructionType.NO_OBSTRUCTION
            assert len(o.sequence_name) > 0
            assert len(o.detail) > 0
            assert len(o.collection_a) > 0
