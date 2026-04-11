"""
Standalone test runner for Raster Law Bridge V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import OperationKind, V1_LAW
from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, BRIDGE_FROZEN,
    CANVAS_WIDTH, CANVAS_HEIGHT, PRIMITIVE_PALETTE, BACKGROUND_COLOR,
    ArtifactPrimitive, ArtifactSpec, BridgeVerdict, BridgeResult,
    render_artifact, parse_artifact, bridge_to_substrate,
    validate_spec, ALL_FIXTURES,
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
    fixture_single_region, fixture_non_adjacent,
)

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


# ═══════ SPEC ═══════
print("\n=== Bridge Spec ===")
check("version", BRIDGE_VERSION == "V1.0")
check("frozen", BRIDGE_FROZEN is True)
check("canvas_size", CANVAS_WIDTH == 400 and CANVAS_HEIGHT == 400)
check("palette_count", len(PRIMITIVE_PALETTE) == 10)
check("bg_white", BACKGROUND_COLOR == (255, 255, 255))

# ═══════ ARTIFACT SPEC VALIDATION ═══════
print("\n=== Spec Validation ===")

# Valid spec
spec_ok = fixture_adjacent_pair()
check("valid_spec", validate_spec(spec_ok) == [])

# Empty spec
spec_empty = ArtifactSpec(primitives=())
errs = validate_spec(spec_empty)
check("empty_spec_invalid", len(errs) > 0)

# Duplicate color
spec_dup = ArtifactSpec(primitives=(
    ArtifactPrimitive(PRIMITIVE_PALETTE[0], 0, 0, 50, 50),
    ArtifactPrimitive(PRIMITIVE_PALETTE[0], 100, 0, 50, 50),
))
errs = validate_spec(spec_dup)
check("dup_color_invalid", len(errs) > 0)

# Off-palette color
spec_bad_color = ArtifactSpec(primitives=(
    ArtifactPrimitive((1, 2, 3), 0, 0, 50, 50),
))
check("bad_color_invalid", len(validate_spec(spec_bad_color)) > 0)

# Out of bounds
spec_oob = ArtifactSpec(primitives=(
    ArtifactPrimitive(PRIMITIVE_PALETTE[0], 380, 380, 50, 50),
))
check("oob_invalid", len(validate_spec(spec_oob)) > 0)

# Zero-size
spec_zero = ArtifactSpec(primitives=(
    ArtifactPrimitive(PRIMITIVE_PALETTE[0], 10, 10, 0, 50),
))
check("zero_size_invalid", len(validate_spec(spec_zero)) > 0)

# ═══════ RENDER + PARSE ROUNDTRIP ═══════
print("\n=== Render + Parse Roundtrip ===")

for name, fixture_fn in ALL_FIXTURES.items():
    spec = fixture_fn()
    png_bytes = render_artifact(spec)
    check(f"render_{name}_nonempty", len(png_bytes) > 100)
    check(f"render_{name}_png_header", png_bytes[:4] == b'\x89PNG')

    parsed = parse_artifact(png_bytes)
    check(f"parse_{name}_count",
          len(parsed) == len(spec.primitives),
          f"expected {len(spec.primitives)}, got {len(parsed)}")

    # Check bbox roundtrip
    spec_bboxes = sorted([(p.x, p.y, p.w, p.h) for p in spec.primitives])
    parsed_bboxes = sorted([tuple(p["bbox"]) for p in parsed])
    check(f"roundtrip_{name}_exact",
          spec_bboxes == parsed_bboxes,
          f"spec={spec_bboxes}, parsed={parsed_bboxes}")

    # Check confidence is always 1.0 (synthetic, no heuristic)
    check(f"confidence_{name}_exact",
          all(p["confidence"] == 1.0 for p in parsed))

# ═══════ RENDER DETERMINISM ═══════
print("\n=== Render Determinism ===")
spec_det = fixture_adjacent_pair()
renders = [render_artifact(spec_det) for _ in range(5)]
check("render_deterministic", all(r == renders[0] for r in renders))

# ═══════ BRIDGE TO SUBSTRATE — ADJACENT (PASS) ═══════
print("\n=== Bridge — Adjacent Pair ===")
br_adj = bridge_to_substrate(fixture_adjacent_pair())
check("bridge_adj_verdict", br_adj.verdict == BridgeVerdict.BRIDGED,
      f"got {br_adj.verdict}")
check("bridge_adj_roundtrip", br_adj.parse_roundtrip_exact)
check("bridge_adj_well_typed", br_adj.type_check_verdict == "WELL_TYPED")
check("bridge_adj_pass", br_adj.execution_verdict == "PASS")
check("bridge_adj_prims", br_adj.parsed_primitives == 2)

# ═══════ BRIDGE TO SUBSTRATE — CONTAINMENT (PASS) ═══════
print("\n=== Bridge — Containment ===")
br_con = bridge_to_substrate(fixture_containment())
check("bridge_con_verdict", br_con.verdict == BridgeVerdict.BRIDGED,
      f"got {br_con.verdict}")
check("bridge_con_pass", br_con.execution_verdict == "PASS")

# ═══════ BRIDGE TO SUBSTRATE — THREE REGIONS ═══════
print("\n=== Bridge — Three Regions ===")
br_three = bridge_to_substrate(fixture_three_regions())
check("bridge_three_verdict", br_three.verdict == BridgeVerdict.BRIDGED,
      f"got {br_three.verdict}")
check("bridge_three_prims", br_three.parsed_primitives == 3)

# ═══════ BRIDGE TO SUBSTRATE — SINGLE REGION ═══════
print("\n=== Bridge — Single Region ===")
br_single = bridge_to_substrate(fixture_single_region())
check("bridge_single_verdict", br_single.verdict == BridgeVerdict.BRIDGED,
      f"got {br_single.verdict}")

# ═══════ BRIDGE TO SUBSTRATE — NON-ADJACENT (FAIL) ═══════
print("\n=== Bridge — Non-Adjacent (expect FAIL or EXEC_FAILED) ===")
br_nonadj = bridge_to_substrate(fixture_non_adjacent())
check("bridge_nonadj_roundtrip", br_nonadj.parse_roundtrip_exact)
check("bridge_nonadj_typed", br_nonadj.type_check_verdict == "WELL_TYPED")
# This should FAIL because the regions are far apart (not adjacent)
check("bridge_nonadj_fail",
      br_nonadj.execution_verdict == "FAIL" or br_nonadj.verdict == BridgeVerdict.EXEC_FAILED,
      f"verdict={br_nonadj.verdict}, exec={br_nonadj.execution_verdict}")

# ═══════ BRIDGE TO SUBSTRATE — INVALID SPEC ═══════
print("\n=== Bridge — Invalid Spec ===")
br_inv = bridge_to_substrate(ArtifactSpec(primitives=()))
check("bridge_inv_verdict", br_inv.verdict == BridgeVerdict.INVALID_SPEC)

# ═══════ BRIDGE RESULT SERIALIZATION ═══════
print("\n=== Bridge Result Serialization ===")
d = br_adj.to_dict()
check("ser_verdict", d["verdict"] == "BRIDGED")
check("ser_roundtrip", d["parse_roundtrip_exact"] is True)
check("ser_version", d["bridge_version"] == BRIDGE_VERSION)
check("ser_prims", d["parsed_primitives"] == 2)

# ═══════ FULL BRIDGE DETERMINISM ═══════
print("\n=== Full Bridge Determinism ===")
results = [bridge_to_substrate(fixture_adjacent_pair()).to_dict() for _ in range(5)]
check("bridge_deterministic", all(r == results[0] for r in results))

# ═══════ CONTAINMENT PARSE — inner not occluded ═══════
print("\n=== Containment Rendering Detail ===")
# The inner rectangle should still be parseable even though it's
# drawn on top of the outer rectangle (later draw wins)
spec_con = fixture_containment()
png_con = render_artifact(spec_con)
parsed_con = parse_artifact(png_con)
# The outer color should have an L-shaped region (minus the inner)
# but parse_artifact finds bounding boxes, so outer bbox is still full
# Inner bbox should be exact
inner_parsed = [p for p in parsed_con if p["_artifact_color"] == list(PRIMITIVE_PALETTE[1])]
check("inner_found", len(inner_parsed) == 1)
if inner_parsed:
    check("inner_bbox",
          tuple(inner_parsed[0]["bbox"]) == (100, 100, 100, 100),
          f"got {inner_parsed[0]['bbox']}")

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
