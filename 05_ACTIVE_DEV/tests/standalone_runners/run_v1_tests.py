"""
Standalone test runner for Visual Grammar V1 — no pytest dependency.
Uses Python's built-in unittest + custom parametrize-style iteration.
"""

import sys
import os
import math
import traceback

# Ensure aurexis_lang is importable
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

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

FLOAT_TOL = 1e-9
passed = 0
failed = 0
errors = []


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        errors.append(f"{name}: {msg}")
        print(f"  FAIL  {name} — {msg}")


def check_close(name, actual, expected, tol=FLOAT_TOL):
    check(name, abs(actual - expected) < tol,
          f"expected {expected}, got {actual}")


# ═══════ GRAMMAR SPEC ═══════
print("\n=== Grammar Spec Tests ===")
check("grammar_version", GRAMMAR_VERSION == "V1.0")
from aurexis_lang.visual_grammar_v1 import GRAMMAR_FROZEN
check("grammar_frozen", GRAMMAR_FROZEN is True)
check("law_adjacent", V1_LAW.adjacent_max_distance_px == 30.0)
check("law_contains", V1_LAW.contains_min_margin_px == 0.0)
check("law_min_area", V1_LAW.min_primitive_area_px2 == 4.0)
check("law_max_prims", V1_LAW.max_primitives_per_frame == 200)

try:
    V1_LAW.adjacent_max_distance_px = 50.0
    check("law_immutable", False, "should have raised AttributeError")
except AttributeError:
    check("law_immutable", True)

check("primitive_kinds_count", len(PrimitiveKind) == 3)
check("operation_kinds_count", len(OperationKind) == 3)
check("fixture_count_adjacent", len(all_adjacent_fixtures()) == FIXTURE_COUNTS["adjacent"])
check("fixture_count_contains", len(all_contains_fixtures()) == FIXTURE_COUNTS["contains"])
check("fixture_count_bind", len(all_bind_fixtures()) == FIXTURE_COUNTS["bind"])
check("fixture_count_validity", len(all_validity_fixtures()) == FIXTURE_COUNTS["validity"])
check("fixture_count_frame", len(all_frame_fixtures()) == FIXTURE_COUNTS["frame"])
total = sum(len(f()) for f in [all_adjacent_fixtures, all_contains_fixtures,
                                all_bind_fixtures, all_validity_fixtures, all_frame_fixtures])
check("fixture_count_total", total == FIXTURE_COUNTS["total"])

# ═══════ BOUNDING BOX ═══════
print("\n=== BoundingBox Tests ===")
bb = BoundingBox(10, 20, 100, 50)
check("bb_x2", bb.x2 == 110)
check("bb_y2", bb.y2 == 70)
check("bb_cx", bb.cx == 60)
check("bb_cy", bb.cy == 45)
check("bb_area", bb.area == 5000)

outer = BoundingBox(0, 0, 200, 200)
inner = BoundingBox(0, 0, 200, 200)
check("bb_contains_exact", outer.contains(inner, margin=0.0))

inner2 = BoundingBox(10, 10, 180, 180)
check("bb_contains_margin_ok", outer.contains(inner2, margin=10.0))
check("bb_contains_margin_fail", not outer.contains(inner2, margin=11.0))

a = BoundingBox(0, 0, 100, 100)
b = BoundingBox(100, 0, 100, 100)
check("bb_edge_dist_touching", a.edge_distance(b) == 0.0)

b2 = BoundingBox(50, 50, 100, 100)
check("bb_edge_dist_overlap", a.edge_distance(b2) == 0.0)

b3 = BoundingBox(120, 0, 100, 100)
check("bb_edge_dist_gap", a.edge_distance(b3) == 20.0)

# ═══════ ADJACENT FIXTURES ═══════
print("\n=== Adjacent Operation Tests ===")
for fixture in all_adjacent_fixtures():
    name = fixture["name"]
    rel = evaluate_adjacent(fixture["operand_a"], fixture["operand_b"])
    check(f"adj_{name}_result", rel.result == fixture["expected_result"],
          f"expected {fixture['expected_result'].name}, got {rel.result.name}")
    check_close(f"adj_{name}_measured", rel.measured_value, fixture["expected_measured_value"])
    check(f"adj_{name}_threshold", rel.law_threshold == fixture["expected_law_threshold"])
    check(f"adj_{name}_status", rel.execution_status == fixture["expected_execution_status"],
          f"expected {fixture['expected_execution_status'].name}, got {rel.execution_status.name}")
    check(f"adj_{name}_version", rel.grammar_version == GRAMMAR_VERSION)

# Symmetry check
print("\n=== Adjacent Symmetry ===")
for fixture in all_adjacent_fixtures():
    a, b = fixture["operand_a"], fixture["operand_b"]
    rel_ab = evaluate_adjacent(a, b)
    rel_ba = evaluate_adjacent(b, a)
    check(f"sym_{fixture['name']}_result", rel_ab.result == rel_ba.result)
    check_close(f"sym_{fixture['name']}_value", rel_ab.measured_value, rel_ba.measured_value)

# Determinism
print("\n=== Adjacent Determinism ===")
for fixture in all_adjacent_fixtures():
    results = [evaluate_adjacent(fixture["operand_a"], fixture["operand_b"]) for _ in range(10)]
    same = all(r.result == results[0].result and r.measured_value == results[0].measured_value for r in results)
    check(f"det_{fixture['name']}", same)

# ═══════ CONTAINS FIXTURES ═══════
print("\n=== Contains Operation Tests ===")
for fixture in all_contains_fixtures():
    name = fixture["name"]
    rel = evaluate_contains(fixture["operand_a"], fixture["operand_b"])
    check(f"cnt_{name}_result", rel.result == fixture["expected_result"],
          f"expected {fixture['expected_result'].name}, got {rel.result.name}")
    check_close(f"cnt_{name}_measured", rel.measured_value, fixture["expected_measured_value"])
    check(f"cnt_{name}_threshold", rel.law_threshold == fixture["expected_law_threshold"])

# ═══════ BIND FIXTURES ═══════
print("\n=== Bind Operation Tests ===")
for fixture in all_bind_fixtures():
    name = fixture["name"]
    binding = evaluate_bind(fixture["bind_name"], fixture["primitive"])
    check(f"bind_{name}_name", binding.name == fixture["expected_binding_name"])
    check(f"bind_{name}_kind", binding.primitive.kind == fixture["expected_primitive_kind"])

# ═══════ VALIDITY FIXTURES ═══════
print("\n=== Validity Tests ===")
for fixture in all_validity_fixtures():
    name = fixture["name"]
    check(f"valid_{name}", fixture["primitive"].is_valid() == fixture["expected_valid"],
          f"expected valid={fixture['expected_valid']}")

# ═══════ FILTERING ═══════
print("\n=== Primitive Filtering Tests ===")
fx = FrameFixtures.max_primitives_exceeded()
kept, dropped = filter_primitives(fx["primitives"])
check("filter_max_kept", len(kept) == fx["expected_kept_count"],
      f"expected {fx['expected_kept_count']}, got {len(kept)}")
check("filter_max_dropped", len(dropped) == fx["expected_dropped_count"],
      f"expected {fx['expected_dropped_count']}, got {len(dropped)}")

prims_mixed = [
    VisualPrimitive(PrimitiveKind.REGION, BoundingBox(0, 0, 10, 10), 1.0),
    VisualPrimitive(PrimitiveKind.POINT, BoundingBox(0, 0, 1, 1), 1.0),
]
kept2, dropped2 = filter_primitives(prims_mixed)
check("filter_invalid_drop", len(kept2) == 1 and len(dropped2) == 1)

# ═══════ FRAME EXECUTION ═══════
print("\n=== Frame Execution Tests ===")
fx3 = FrameFixtures.three_region_frame()
ops = [
    {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
    {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 2},
    {"op": OperationKind.ADJACENT, "a_index": 1, "b_index": 2},
]
frame = execute_frame(0, fx3["primitives"], operations=ops)
check("frame3_rel_count", len(frame.relations) == 3)
for i, expected in enumerate(fx3["expected_relations"]):
    rel = frame.relations[i]
    check(f"frame3_rel{i}_result", rel.result == expected["expected_result"],
          f"expected {expected['expected_result'].name}, got {rel.result.name}")
    check_close(f"frame3_rel{i}_measured", rel.measured_value, expected["expected_measured_value"])

fx_nest = FrameFixtures.nested_containment_frame()
ops_nest = [
    {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1},
    {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 2},
    {"op": OperationKind.CONTAINS, "a_index": 1, "b_index": 2},
    {"op": OperationKind.CONTAINS, "a_index": 1, "b_index": 0},
]
frame_nest = execute_frame(0, fx_nest["primitives"], operations=ops_nest)
check("frame_nest_rel_count", len(frame_nest.relations) == 4)
for i, expected in enumerate(fx_nest["expected_relations"]):
    rel = frame_nest.relations[i]
    check(f"frame_nest_rel{i}_result", rel.result == expected["expected_result"],
          f"expected {expected['expected_result'].name}, got {rel.result.name}")
    check_close(f"frame_nest_rel{i}_measured", rel.measured_value, expected["expected_measured_value"])

# Frame determinism
frames = [execute_frame(0, fx3["primitives"]) for _ in range(5)]
frame_det = all(
    len(f.relations) == len(frames[0].relations) and
    all(r.result == frames[0].relations[j].result for j, r in enumerate(f.relations))
    for f in frames
)
check("frame_determinism", frame_det)

# Frame summary
frame_s = execute_frame(0, fx3["primitives"], bindings=fx3["bindings"])
summary = frame_s.summary()
check("frame_summary_index", summary["frame_index"] == 0)
check("frame_summary_version", summary["grammar_version"] == "V1.0")
check("frame_summary_prims", summary["total_primitives"] == 3)
check("frame_summary_bindings", summary["bindings"] == 3)

# ═══════ PARSER ═══════
print("\n=== Parser Tests ===")
check("parse_kind_region", classify_kind("region") == PrimitiveKind.REGION)
check("parse_kind_edge", classify_kind("edge") == PrimitiveKind.EDGE)
check("parse_kind_keypoint", classify_kind("keypoint") == PrimitiveKind.POINT)
check("parse_kind_case", classify_kind("REGION") == PrimitiveKind.REGION)
check("parse_kind_strip", classify_kind("  Edge  ") == PrimitiveKind.EDGE)
check("parse_kind_unknown", classify_kind("unknown") == PrimitiveKind.REGION)

raw_cv = {"type": "region", "bbox": [10, 20, 100, 80], "confidence": 0.85, "dominant_color": "green"}
prim_cv = parse_primitive(raw_cv)
check("parse_cv_kind", prim_cv.kind == PrimitiveKind.REGION)
check("parse_cv_bbox", prim_cv.bbox.x == 10 and prim_cv.bbox.width == 100)
check("parse_cv_conf", prim_cv.source_confidence == 0.85)
check("parse_cv_attrs", prim_cv.attributes.get("dominant_color") == "green")

raw_zone = {"kind": "EDGE", "x": 0, "y": 50, "width": 200, "height": 3, "confidence": 0.9}
prim_zone = parse_primitive(raw_zone)
check("parse_zone_kind", prim_zone.kind == PrimitiveKind.EDGE)
check("parse_zone_bbox", prim_zone.bbox.width == 200 and prim_zone.bbox.height == 3)

raw_min = {"x": 5, "y": 5, "w": 10, "h": 10}
prim_min = parse_primitive(raw_min)
check("parse_minimal", prim_min is not None and prim_min.kind == PrimitiveKind.REGION)

check("parse_empty_none", parse_primitive({}) is None)
check("parse_nonsense_none", parse_primitive({"nonsense": True}) is None)

raws_frame = [
    {"type": "region", "bbox": [0, 0, 50, 50], "confidence": 1.0},
    {"type": "point", "bbox": [10, 10, 1, 1], "confidence": 1.0},  # invalid
    {"type": "edge", "bbox": [0, 0, 100, 3], "confidence": 0.7},
]
prims_parsed = parse_frame(raws_frame)
check("parse_frame_count", len(prims_parsed) == 2)
check("parse_frame_kinds", prims_parsed[0].kind == PrimitiveKind.REGION and prims_parsed[1].kind == PrimitiveKind.EDGE)

# Roundtrip
raw_rt = {"type": "keypoint", "bbox": [50, 50, 5, 5], "confidence": 0.95}
p1 = parse_primitive(raw_rt)
d = primitive_to_dict(p1)
p2 = parse_primitive(d)
check("roundtrip_kind", p2.kind == p1.kind)
check("roundtrip_bbox", p2.bbox.x == p1.bbox.x and p2.bbox.width == p1.bbox.width)
check("roundtrip_conf", p2.source_confidence == p1.source_confidence)

# Confidence clamping
prim_over = parse_primitive({"type": "region", "bbox": [0, 0, 10, 10], "confidence": 1.5})
check("conf_clamp_high", prim_over.source_confidence == 1.0)
prim_under = parse_primitive({"type": "region", "bbox": [0, 0, 10, 10], "confidence": -0.5})
check("conf_clamp_low", prim_under.source_confidence == 0.0)

# ═══════ INTEGRATION ═══════
print("\n=== Integration Tests ===")
raw_a = {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0}
raw_b = {"type": "region", "bbox": [110, 0, 100, 100], "confidence": 1.0}
ia = parse_primitive(raw_a)
ib = parse_primitive(raw_b)
irel = evaluate_adjacent(ia, ib)
check("integ_adj_result", irel.result == RelationResult.TRUE)
check("integ_adj_measured", irel.measured_value == 10.0)
check("integ_adj_status", irel.execution_status == ExecutionStatus.DETERMINISTIC)

raw_outer = {"type": "region", "bbox": [0, 0, 200, 200], "confidence": 1.0}
raw_inner = {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0}
io = parse_primitive(raw_outer)
ii = parse_primitive(raw_inner)
irel2 = evaluate_contains(io, ii)
check("integ_cnt_result", irel2.result == RelationResult.TRUE)
check("integ_cnt_measured", irel2.measured_value == 50.0)

# Full pipeline determinism
raws_pipe = [
    {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
    {"type": "region", "bbox": [120, 0, 100, 100], "confidence": 1.0},
    {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
]
summaries = []
for _ in range(5):
    pp = parse_frame(raws_pipe)
    ff = execute_frame(0, pp)
    summaries.append(ff.summary())
check("pipeline_determinism", all(s == summaries[0] for s in summaries))

# Relation serialization
fix_ser = AdjacentFixtures.touching_regions()
rel_ser = evaluate_adjacent(fix_ser["operand_a"], fix_ser["operand_b"])
d_ser = rel_ser.to_dict()
check("ser_operation", d_ser["operation"] == "ADJACENT")
check("ser_result", d_ser["result"] == "TRUE")
check("ser_status", d_ser["execution_status"] == "DETERMINISTIC")
check("ser_measured", d_ser["measured_value"] == 0.0)
check("ser_threshold", d_ser["law_threshold"] == 30.0)
check("ser_version", d_ser["grammar_version"] == "V1.0")

# ═══════ SUMMARY ═══════
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
if errors:
    print("\nFAILURES:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("\nALL TESTS PASSED ✓")
    sys.exit(0)
