"""
Pytest-format tests for Raster Law Bridge V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "aurexis_lang", "src"
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


# ═══════ SPEC ═══════

class TestBridgeSpec:
    def test_version(self):
        assert BRIDGE_VERSION == "V1.0"

    def test_frozen(self):
        assert BRIDGE_FROZEN is True

    def test_canvas_size(self):
        assert CANVAS_WIDTH == 400
        assert CANVAS_HEIGHT == 400

    def test_palette_count(self):
        assert len(PRIMITIVE_PALETTE) == 10

    def test_bg_white(self):
        assert BACKGROUND_COLOR == (255, 255, 255)


# ═══════ SPEC VALIDATION ═══════

class TestSpecValidation:
    def test_valid_spec(self):
        assert validate_spec(fixture_adjacent_pair()) == []

    def test_empty_spec_invalid(self):
        assert len(validate_spec(ArtifactSpec(primitives=()))) > 0

    def test_duplicate_color_invalid(self):
        spec = ArtifactSpec(primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 0, 0, 50, 50),
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 100, 0, 50, 50),
        ))
        assert len(validate_spec(spec)) > 0

    def test_bad_color_invalid(self):
        spec = ArtifactSpec(primitives=(
            ArtifactPrimitive((1, 2, 3), 0, 0, 50, 50),
        ))
        assert len(validate_spec(spec)) > 0

    def test_out_of_bounds_invalid(self):
        spec = ArtifactSpec(primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 380, 380, 50, 50),
        ))
        assert len(validate_spec(spec)) > 0

    def test_zero_size_invalid(self):
        spec = ArtifactSpec(primitives=(
            ArtifactPrimitive(PRIMITIVE_PALETTE[0], 10, 10, 0, 50),
        ))
        assert len(validate_spec(spec)) > 0


# ═══════ RENDER + PARSE ROUNDTRIP ═══════

class TestRenderParseRoundtrip:
    @pytest.mark.parametrize("name,fixture_fn", list(ALL_FIXTURES.items()))
    def test_render_nonempty(self, name, fixture_fn):
        png_bytes = render_artifact(fixture_fn())
        assert len(png_bytes) > 100

    @pytest.mark.parametrize("name,fixture_fn", list(ALL_FIXTURES.items()))
    def test_render_png_header(self, name, fixture_fn):
        png_bytes = render_artifact(fixture_fn())
        assert png_bytes[:4] == b'\x89PNG'

    @pytest.mark.parametrize("name,fixture_fn", list(ALL_FIXTURES.items()))
    def test_parse_count(self, name, fixture_fn):
        spec = fixture_fn()
        parsed = parse_artifact(render_artifact(spec))
        assert len(parsed) == len(spec.primitives)

    @pytest.mark.parametrize("name,fixture_fn", list(ALL_FIXTURES.items()))
    def test_roundtrip_bbox_exact(self, name, fixture_fn):
        spec = fixture_fn()
        parsed = parse_artifact(render_artifact(spec))
        spec_bboxes = sorted([(p.x, p.y, p.w, p.h) for p in spec.primitives])
        parsed_bboxes = sorted([tuple(p["bbox"]) for p in parsed])
        assert spec_bboxes == parsed_bboxes

    @pytest.mark.parametrize("name,fixture_fn", list(ALL_FIXTURES.items()))
    def test_confidence_exact(self, name, fixture_fn):
        spec = fixture_fn()
        parsed = parse_artifact(render_artifact(spec))
        assert all(p["confidence"] == 1.0 for p in parsed)


# ═══════ RENDER DETERMINISM ═══════

class TestRenderDeterminism:
    def test_render_deterministic(self):
        spec = fixture_adjacent_pair()
        renders = [render_artifact(spec) for _ in range(5)]
        assert all(r == renders[0] for r in renders)


# ═══════ BRIDGE TO SUBSTRATE ═══════

class TestBridgeAdjacentPair:
    def test_verdict(self):
        br = bridge_to_substrate(fixture_adjacent_pair())
        assert br.verdict == BridgeVerdict.BRIDGED

    def test_roundtrip(self):
        br = bridge_to_substrate(fixture_adjacent_pair())
        assert br.parse_roundtrip_exact

    def test_well_typed(self):
        br = bridge_to_substrate(fixture_adjacent_pair())
        assert br.type_check_verdict == "WELL_TYPED"

    def test_pass(self):
        br = bridge_to_substrate(fixture_adjacent_pair())
        assert br.execution_verdict == "PASS"

    def test_prims(self):
        br = bridge_to_substrate(fixture_adjacent_pair())
        assert br.parsed_primitives == 2


class TestBridgeContainment:
    def test_verdict(self):
        br = bridge_to_substrate(fixture_containment())
        assert br.verdict == BridgeVerdict.BRIDGED

    def test_pass(self):
        br = bridge_to_substrate(fixture_containment())
        assert br.execution_verdict == "PASS"


class TestBridgeThreeRegions:
    def test_verdict(self):
        br = bridge_to_substrate(fixture_three_regions())
        assert br.verdict == BridgeVerdict.BRIDGED

    def test_prims(self):
        br = bridge_to_substrate(fixture_three_regions())
        assert br.parsed_primitives == 3


class TestBridgeSingleRegion:
    def test_verdict(self):
        br = bridge_to_substrate(fixture_single_region())
        assert br.verdict == BridgeVerdict.BRIDGED


class TestBridgeNonAdjacent:
    def test_roundtrip(self):
        br = bridge_to_substrate(fixture_non_adjacent())
        assert br.parse_roundtrip_exact

    def test_typed(self):
        br = bridge_to_substrate(fixture_non_adjacent())
        assert br.type_check_verdict == "WELL_TYPED"

    def test_fail(self):
        br = bridge_to_substrate(fixture_non_adjacent())
        assert br.execution_verdict == "FAIL" or br.verdict == BridgeVerdict.EXEC_FAILED


class TestBridgeInvalidSpec:
    def test_verdict(self):
        br = bridge_to_substrate(ArtifactSpec(primitives=()))
        assert br.verdict == BridgeVerdict.INVALID_SPEC


# ═══════ SERIALIZATION ═══════

class TestBridgeResultSerialization:
    def test_ser_verdict(self):
        d = bridge_to_substrate(fixture_adjacent_pair()).to_dict()
        assert d["verdict"] == "BRIDGED"

    def test_ser_roundtrip(self):
        d = bridge_to_substrate(fixture_adjacent_pair()).to_dict()
        assert d["parse_roundtrip_exact"] is True

    def test_ser_version(self):
        d = bridge_to_substrate(fixture_adjacent_pair()).to_dict()
        assert d["bridge_version"] == BRIDGE_VERSION

    def test_ser_prims(self):
        d = bridge_to_substrate(fixture_adjacent_pair()).to_dict()
        assert d["parsed_primitives"] == 2


# ═══════ FULL BRIDGE DETERMINISM ═══════

class TestFullBridgeDeterminism:
    def test_bridge_deterministic(self):
        results = [bridge_to_substrate(fixture_adjacent_pair()).to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)


# ═══════ CONTAINMENT DETAIL ═══════

class TestContainmentDetail:
    def test_inner_found(self):
        spec = fixture_containment()
        parsed = parse_artifact(render_artifact(spec))
        inner = [p for p in parsed if p["_artifact_color"] == list(PRIMITIVE_PALETTE[1])]
        assert len(inner) == 1

    def test_inner_bbox(self):
        spec = fixture_containment()
        parsed = parse_artifact(render_artifact(spec))
        inner = [p for p in parsed if p["_artifact_color"] == list(PRIMITIVE_PALETTE[1])]
        assert tuple(inner[0]["bbox"]) == (100, 100, 100, 100)
