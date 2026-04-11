"""
Aurexis Core — Visual Grammar V1 Deterministic Test Suite

Tests every canonical fixture against the V1 executor.
Every test asserts exact expected values — no tolerance, no approximation
(except for floating point comparison where noted).

If any test fails, the grammar or executor is broken — not the fixture.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os
import math
import pytest

# Ensure aurexis_lang is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarLaw, V1_LAW, BoundingBox, VisualPrimitive, Binding,
    Relation, GrammarFrame, GRAMMAR_VERSION,
)
from aurexis_lang.visual_grammar_v1_fixtures import (
    AdjacentFixtures, ContainsFixtures, BindFixtures, ValidityFixtures,
    FrameFixtures, all_adjacent_fixtures, all_contains_fixtures,
    all_bind_fixtures, all_validity_fixtures, all_frame_fixtures,
    FIXTURE_COUNTS,
)
from aurexis_lang.visual_executor_v1 import (
    evaluate_adjacent, evaluate_contains, evaluate_bind,
    filter_primitives, execute_frame,
)
from aurexis_lang.visual_parser_v1 import (
    parse_primitive, parse_frame, classify_kind,
    primitive_to_dict, frame_to_dicts,
)


FLOAT_TOL = 1e-9  # Tolerance for floating point comparison


# ════════════════════════════════════════════════════════════
# GRAMMAR SPEC TESTS — frozen values
# ════════════════════════════════════════════════════════════

class TestGrammarSpec:
    """Verify the grammar spec is frozen and correct."""

    def test_grammar_version(self):
        assert GRAMMAR_VERSION == "V1.0"

    def test_law_frozen(self):
        from aurexis_lang.visual_grammar_v1 import GRAMMAR_FROZEN
        assert GRAMMAR_FROZEN is True

    def test_law_thresholds(self):
        assert V1_LAW.adjacent_max_distance_px == 30.0
        assert V1_LAW.contains_min_margin_px == 0.0
        assert V1_LAW.min_primitive_area_px2 == 4.0
        assert V1_LAW.max_primitives_per_frame == 200

    def test_law_immutable(self):
        """GrammarLaw is a frozen dataclass — cannot be mutated."""
        with pytest.raises(AttributeError):
            V1_LAW.adjacent_max_distance_px = 50.0

    def test_primitive_kinds(self):
        assert len(PrimitiveKind) == 3
        assert PrimitiveKind.REGION is not None
        assert PrimitiveKind.EDGE is not None
        assert PrimitiveKind.POINT is not None

    def test_operation_kinds(self):
        assert len(OperationKind) == 3
        assert OperationKind.ADJACENT is not None
        assert OperationKind.CONTAINS is not None
        assert OperationKind.BIND is not None

    def test_fixture_counts(self):
        assert len(all_adjacent_fixtures()) == FIXTURE_COUNTS["adjacent"]
        assert len(all_contains_fixtures()) == FIXTURE_COUNTS["contains"]
        assert len(all_bind_fixtures()) == FIXTURE_COUNTS["bind"]
        assert len(all_validity_fixtures()) == FIXTURE_COUNTS["validity"]
        assert len(all_frame_fixtures()) == FIXTURE_COUNTS["frame"]
        total = (
            len(all_adjacent_fixtures())
            + len(all_contains_fixtures())
            + len(all_bind_fixtures())
            + len(all_validity_fixtures())
            + len(all_frame_fixtures())
        )
        assert total == FIXTURE_COUNTS["total"]


# ════════════════════════════════════════════════════════════
# BOUNDING BOX TESTS
# ════════════════════════════════════════════════════════════

class TestBoundingBox:

    def test_properties(self):
        bb = BoundingBox(10, 20, 100, 50)
        assert bb.x2 == 110
        assert bb.y2 == 70
        assert bb.cx == 60
        assert bb.cy == 45
        assert bb.area == 5000

    def test_contains_exact(self):
        outer = BoundingBox(0, 0, 200, 200)
        inner = BoundingBox(0, 0, 200, 200)
        assert outer.contains(inner, margin=0.0) is True

    def test_contains_with_margin(self):
        outer = BoundingBox(0, 0, 200, 200)
        inner = BoundingBox(10, 10, 180, 180)
        assert outer.contains(inner, margin=10.0) is True
        assert outer.contains(inner, margin=11.0) is False

    def test_edge_distance_touching(self):
        a = BoundingBox(0, 0, 100, 100)
        b = BoundingBox(100, 0, 100, 100)
        assert a.edge_distance(b) == 0.0

    def test_edge_distance_overlapping(self):
        a = BoundingBox(0, 0, 100, 100)
        b = BoundingBox(50, 50, 100, 100)
        assert a.edge_distance(b) == 0.0

    def test_edge_distance_gap(self):
        a = BoundingBox(0, 0, 100, 100)
        b = BoundingBox(120, 0, 100, 100)
        assert a.edge_distance(b) == 20.0


# ════════════════════════════════════════════════════════════
# ADJACENT OPERATION TESTS — all 10 fixtures
# ════════════════════════════════════════════════════════════

class TestAdjacentOperation:

    @pytest.mark.parametrize("fixture", all_adjacent_fixtures(),
                             ids=[f["name"] for f in all_adjacent_fixtures()])
    def test_adjacent_fixture(self, fixture):
        rel = evaluate_adjacent(fixture["operand_a"], fixture["operand_b"])

        assert rel.operation == OperationKind.ADJACENT
        assert rel.result == fixture["expected_result"], (
            f"Fixture '{fixture['name']}': expected {fixture['expected_result'].name}, "
            f"got {rel.result.name} (measured={rel.measured_value})"
        )
        assert abs(rel.measured_value - fixture["expected_measured_value"]) < FLOAT_TOL, (
            f"Fixture '{fixture['name']}': expected measured={fixture['expected_measured_value']}, "
            f"got {rel.measured_value}"
        )
        assert rel.law_threshold == fixture["expected_law_threshold"]
        assert rel.execution_status == fixture["expected_execution_status"]
        assert rel.grammar_version == GRAMMAR_VERSION

    def test_adjacent_symmetry(self):
        """ADJACENT must be symmetric: ADJACENT(a,b) == ADJACENT(b,a)."""
        for fixture in all_adjacent_fixtures():
            a, b = fixture["operand_a"], fixture["operand_b"]
            rel_ab = evaluate_adjacent(a, b)
            rel_ba = evaluate_adjacent(b, a)
            assert rel_ab.result == rel_ba.result, (
                f"Symmetry violation in '{fixture['name']}'"
            )
            assert abs(rel_ab.measured_value - rel_ba.measured_value) < FLOAT_TOL

    def test_determinism(self):
        """Same input must produce exactly the same output every time."""
        for fixture in all_adjacent_fixtures():
            a, b = fixture["operand_a"], fixture["operand_b"]
            results = [evaluate_adjacent(a, b) for _ in range(10)]
            for r in results:
                assert r.result == results[0].result
                assert r.measured_value == results[0].measured_value
                assert r.execution_status == results[0].execution_status


# ════════════════════════════════════════════════════════════
# CONTAINS OPERATION TESTS — all 6 fixtures
# ════════════════════════════════════════════════════════════

class TestContainsOperation:

    @pytest.mark.parametrize("fixture", all_contains_fixtures(),
                             ids=[f["name"] for f in all_contains_fixtures()])
    def test_contains_fixture(self, fixture):
        rel = evaluate_contains(fixture["operand_a"], fixture["operand_b"])

        assert rel.operation == OperationKind.CONTAINS
        assert rel.result == fixture["expected_result"], (
            f"Fixture '{fixture['name']}': expected {fixture['expected_result'].name}, "
            f"got {rel.result.name} (measured={rel.measured_value})"
        )
        assert abs(rel.measured_value - fixture["expected_measured_value"]) < FLOAT_TOL, (
            f"Fixture '{fixture['name']}': expected measured={fixture['expected_measured_value']}, "
            f"got {rel.measured_value}"
        )
        assert rel.law_threshold == fixture["expected_law_threshold"]
        assert rel.grammar_version == GRAMMAR_VERSION

    def test_determinism(self):
        """Same input must produce exactly the same output every time."""
        for fixture in all_contains_fixtures():
            a, b = fixture["operand_a"], fixture["operand_b"]
            results = [evaluate_contains(a, b) for _ in range(10)]
            for r in results:
                assert r.result == results[0].result
                assert r.measured_value == results[0].measured_value


# ════════════════════════════════════════════════════════════
# BIND OPERATION TESTS — all 3 fixtures
# ════════════════════════════════════════════════════════════

class TestBindOperation:

    @pytest.mark.parametrize("fixture", all_bind_fixtures(),
                             ids=[f["name"] for f in all_bind_fixtures()])
    def test_bind_fixture(self, fixture):
        binding = evaluate_bind(fixture["bind_name"], fixture["primitive"])

        assert binding.name == fixture["expected_binding_name"]
        assert binding.primitive.kind == fixture["expected_primitive_kind"]
        assert binding.primitive is fixture["primitive"]

    def test_determinism(self):
        for fixture in all_bind_fixtures():
            bindings = [
                evaluate_bind(fixture["bind_name"], fixture["primitive"])
                for _ in range(10)
            ]
            for b in bindings:
                assert b.name == bindings[0].name
                assert b.primitive.kind == bindings[0].primitive.kind


# ════════════════════════════════════════════════════════════
# VALIDITY TESTS — all 4 fixtures
# ════════════════════════════════════════════════════════════

class TestValidity:

    @pytest.mark.parametrize("fixture", all_validity_fixtures(),
                             ids=[f["name"] for f in all_validity_fixtures()])
    def test_validity_fixture(self, fixture):
        assert fixture["primitive"].is_valid() == fixture["expected_valid"], (
            f"Fixture '{fixture['name']}': expected valid={fixture['expected_valid']}"
        )


# ════════════════════════════════════════════════════════════
# PRIMITIVE FILTERING TESTS
# ════════════════════════════════════════════════════════════

class TestPrimitiveFiltering:

    def test_max_primitives_exceeded(self):
        fixture = FrameFixtures.max_primitives_exceeded()
        kept, dropped = filter_primitives(fixture["primitives"])
        assert len(kept) == fixture["expected_kept_count"]
        assert len(dropped) == fixture["expected_dropped_count"]

    def test_invalid_primitives_dropped(self):
        prims = [
            VisualPrimitive(PrimitiveKind.REGION, BoundingBox(0, 0, 10, 10), 1.0),
            VisualPrimitive(PrimitiveKind.POINT, BoundingBox(0, 0, 1, 1), 1.0),  # area=1 < 4
        ]
        kept, dropped = filter_primitives(prims)
        assert len(kept) == 1
        assert len(dropped) == 1
        assert kept[0].kind == PrimitiveKind.REGION

    def test_all_valid_no_drop(self):
        prims = [
            VisualPrimitive(PrimitiveKind.REGION, BoundingBox(0, 0, 10, 10), 1.0),
            VisualPrimitive(PrimitiveKind.REGION, BoundingBox(20, 0, 10, 10), 1.0),
        ]
        kept, dropped = filter_primitives(prims)
        assert len(kept) == 2
        assert len(dropped) == 0


# ════════════════════════════════════════════════════════════
# FRAME EXECUTION TESTS
# ════════════════════════════════════════════════════════════

class TestFrameExecution:

    def test_three_region_frame(self):
        fixture = FrameFixtures.three_region_frame()
        prims = fixture["primitives"]

        ops = [
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
            {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 2},
            {"op": OperationKind.ADJACENT, "a_index": 1, "b_index": 2},
        ]

        frame = execute_frame(0, prims, operations=ops)

        assert len(frame.relations) == 3
        for i, expected in enumerate(fixture["expected_relations"]):
            rel = frame.relations[i]
            assert rel.result == expected["expected_result"], (
                f"Relation {i}: expected {expected['expected_result'].name}, got {rel.result.name}"
            )
            assert abs(rel.measured_value - expected["expected_measured_value"]) < FLOAT_TOL

    def test_nested_containment_frame(self):
        fixture = FrameFixtures.nested_containment_frame()
        prims = fixture["primitives"]

        ops = [
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1},
            {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 2},
            {"op": OperationKind.CONTAINS, "a_index": 1, "b_index": 2},
            {"op": OperationKind.CONTAINS, "a_index": 1, "b_index": 0},
        ]

        frame = execute_frame(0, prims, operations=ops)

        assert len(frame.relations) == 4
        for i, expected in enumerate(fixture["expected_relations"]):
            rel = frame.relations[i]
            assert rel.result == expected["expected_result"], (
                f"Relation {i}: expected {expected['expected_result'].name}, got {rel.result.name}"
            )
            assert abs(rel.measured_value - expected["expected_measured_value"]) < FLOAT_TOL

    def test_frame_summary(self):
        fixture = FrameFixtures.three_region_frame()
        prims = fixture["primitives"]
        bindings = fixture["bindings"]

        frame = execute_frame(0, prims, bindings=bindings)
        summary = frame.summary()

        assert summary["frame_index"] == 0
        assert summary["grammar_version"] == "V1.0"
        assert summary["total_primitives"] == 3
        assert summary["valid_primitives"] == 3
        assert summary["bindings"] == 3

    def test_frame_determinism(self):
        """Same frame input → same frame output every time."""
        fixture = FrameFixtures.three_region_frame()
        prims = fixture["primitives"]

        frames = [execute_frame(0, prims) for _ in range(5)]
        for f in frames:
            assert len(f.relations) == frames[0].relations.__len__()
            for i, rel in enumerate(f.relations):
                assert rel.result == frames[0].relations[i].result
                assert rel.measured_value == frames[0].relations[i].measured_value


# ════════════════════════════════════════════════════════════
# PARSER TESTS
# ════════════════════════════════════════════════════════════

class TestParser:

    def test_classify_kind_known(self):
        assert classify_kind("region") == PrimitiveKind.REGION
        assert classify_kind("edge") == PrimitiveKind.EDGE
        assert classify_kind("keypoint") == PrimitiveKind.POINT
        assert classify_kind("REGION") == PrimitiveKind.REGION
        assert classify_kind("  Edge  ") == PrimitiveKind.EDGE

    def test_classify_kind_unknown(self):
        assert classify_kind("unknown_thing") == PrimitiveKind.REGION
        assert classify_kind("") == PrimitiveKind.REGION

    def test_parse_cv_format(self):
        raw = {
            "type": "region",
            "bbox": [10, 20, 100, 80],
            "confidence": 0.85,
            "dominant_color": "green",
        }
        prim = parse_primitive(raw)
        assert prim is not None
        assert prim.kind == PrimitiveKind.REGION
        assert prim.bbox.x == 10
        assert prim.bbox.y == 20
        assert prim.bbox.width == 100
        assert prim.bbox.height == 80
        assert prim.source_confidence == 0.85
        assert prim.attributes["dominant_color"] == "green"

    def test_parse_zone_manifest_format(self):
        raw = {
            "kind": "EDGE",
            "x": 0, "y": 50,
            "width": 200, "height": 3,
            "confidence": 0.9,
            "orientation_deg": 0.0,
        }
        prim = parse_primitive(raw)
        assert prim is not None
        assert prim.kind == PrimitiveKind.EDGE
        assert prim.bbox.width == 200
        assert prim.bbox.height == 3

    def test_parse_minimal_format(self):
        raw = {"x": 5, "y": 5, "w": 10, "h": 10}
        prim = parse_primitive(raw)
        assert prim is not None
        assert prim.kind == PrimitiveKind.REGION  # default
        assert prim.bbox.width == 10

    def test_parse_invalid_returns_none(self):
        assert parse_primitive({}) is None
        assert parse_primitive({"nonsense": True}) is None

    def test_parse_frame_filters_invalid(self):
        raws = [
            {"type": "region", "bbox": [0, 0, 50, 50], "confidence": 1.0},
            {"type": "point", "bbox": [10, 10, 1, 1], "confidence": 1.0},  # area=1 < 4
            {"type": "edge", "bbox": [0, 0, 100, 3], "confidence": 0.7},
        ]
        prims = parse_frame(raws)
        assert len(prims) == 2  # second one invalid
        assert prims[0].kind == PrimitiveKind.REGION
        assert prims[1].kind == PrimitiveKind.EDGE

    def test_roundtrip_serialization(self):
        """primitive → dict → primitive must produce equivalent result."""
        raw = {
            "type": "keypoint",
            "bbox": [50, 50, 5, 5],
            "confidence": 0.95,
        }
        prim1 = parse_primitive(raw)
        d = primitive_to_dict(prim1)
        prim2 = parse_primitive(d)

        assert prim2 is not None
        assert prim2.kind == prim1.kind
        assert prim2.bbox.x == prim1.bbox.x
        assert prim2.bbox.y == prim1.bbox.y
        assert prim2.bbox.width == prim1.bbox.width
        assert prim2.bbox.height == prim1.bbox.height
        assert prim2.source_confidence == prim1.source_confidence

    def test_confidence_clamping(self):
        raw = {"type": "region", "bbox": [0, 0, 10, 10], "confidence": 1.5}
        prim = parse_primitive(raw)
        assert prim.source_confidence == 1.0

        raw2 = {"type": "region", "bbox": [0, 0, 10, 10], "confidence": -0.5}
        prim2 = parse_primitive(raw2)
        assert prim2.source_confidence == 0.0


# ════════════════════════════════════════════════════════════
# INTEGRATION — parser + executor end-to-end
# ════════════════════════════════════════════════════════════

class TestIntegration:

    def test_parse_then_execute_adjacent(self):
        """Parse raw CV dicts → evaluate ADJACENT → verify result."""
        raw_a = {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0}
        raw_b = {"type": "region", "bbox": [110, 0, 100, 100], "confidence": 1.0}

        a = parse_primitive(raw_a)
        b = parse_primitive(raw_b)
        rel = evaluate_adjacent(a, b)

        assert rel.result == RelationResult.TRUE
        assert rel.measured_value == 10.0
        assert rel.execution_status == ExecutionStatus.DETERMINISTIC

    def test_parse_then_execute_contains(self):
        """Parse raw CV dicts → evaluate CONTAINS → verify result."""
        raw_outer = {"type": "region", "bbox": [0, 0, 200, 200], "confidence": 1.0}
        raw_inner = {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0}

        outer = parse_primitive(raw_outer)
        inner = parse_primitive(raw_inner)
        rel = evaluate_contains(outer, inner)

        assert rel.result == RelationResult.TRUE
        assert rel.measured_value == 50.0

    def test_full_pipeline_determinism(self):
        """
        Full pipeline: raw dicts → parse → execute_frame → verify.
        Run 5 times to prove determinism.
        """
        raws = [
            {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
            {"type": "region", "bbox": [120, 0, 100, 100], "confidence": 1.0},
            {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
        ]

        summaries = []
        for _ in range(5):
            prims = parse_frame(raws)
            frame = execute_frame(0, prims)
            summaries.append(frame.summary())

        for s in summaries:
            assert s == summaries[0]


# ════════════════════════════════════════════════════════════
# RELATION SERIALIZATION TEST
# ════════════════════════════════════════════════════════════

class TestRelationSerialization:

    def test_to_dict(self):
        fixture = AdjacentFixtures.touching_regions()
        rel = evaluate_adjacent(fixture["operand_a"], fixture["operand_b"])
        d = rel.to_dict()

        assert d["operation"] == "ADJACENT"
        assert d["result"] == "TRUE"
        assert d["execution_status"] == "DETERMINISTIC"
        assert d["measured_value"] == 0.0
        assert d["law_threshold"] == 30.0
        assert d["grammar_version"] == "V1.0"
        assert d["operand_a_kind"] == "REGION"
        assert d["operand_b_kind"] == "REGION"
