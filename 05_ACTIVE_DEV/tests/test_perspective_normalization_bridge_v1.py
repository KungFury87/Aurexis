"""
Pytest-format tests for Perspective Normalization Bridge V1.

Bounded distorted-artifact recovery for the narrow V1 raster bridge.
Tests that canonical V1 artifacts subjected to bounded keystone
distortions can be localized, perspective-normalized, and bridged
to the substrate deterministically.

This is NOT general perspective invariance or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "aurexis_lang", "src"
))

from aurexis_lang.perspective_normalization_bridge_v1 import (
    PERSPECTIVE_VERSION, PERSPECTIVE_FROZEN,
    V1_PERSPECTIVE_PROFILE, PerspectiveProfile,
    FROZEN_DISTORTIONS, KeystoneDistortion,
    IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD,
    VERTICAL_KEYSTONE_MILD, CORNER_PULL_INWARD,
    HORIZONTAL_KEYSTONE_REVERSE, VERTICAL_KEYSTONE_REVERSE,
    MILD_TRAPEZOID,
    warp_forward, warp_inverse,
    PerspectiveHostSpec, generate_perspective_host_image,
    detect_and_normalize_perspective,
    PerspectiveVerdict, PerspectiveResult,
    perspective_and_bridge,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_containment, fixture_three_regions,
    CANVAS_WIDTH, CANVAS_HEIGHT,
    _render_to_raw_rgb, _decode_png_to_rgb,
)


# ═══════ MODULE CONSTANTS ═══════

class TestModuleConstants:
    def test_version(self):
        assert PERSPECTIVE_VERSION == "V1.0"

    def test_frozen(self):
        assert PERSPECTIVE_FROZEN is True

    def test_profile(self):
        assert isinstance(V1_PERSPECTIVE_PROFILE, PerspectiveProfile)

    def test_max_corner_offset(self):
        assert V1_PERSPECTIVE_PROFILE.max_corner_offset_px == 30

    def test_frozen_distortions_count(self):
        assert len(FROZEN_DISTORTIONS) == 7

    def test_in_bounds_count(self):
        assert len(IN_BOUNDS_CASES) == 8

    def test_oob_count(self):
        assert len(OUT_OF_BOUNDS_CASES) == 4


# ═══════ WARP FUNCTIONS ═══════

class TestWarpFunctions:
    def test_identity_exact(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        out, ow, oh = warp_forward(rgb, w, h, IDENTITY_DISTORTION)
        assert ow == w and oh == h
        assert out == rgb

    def test_roundtrip_close(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        fwd, fw, fh = warp_forward(rgb, w, h, HORIZONTAL_KEYSTONE_MILD)
        inv, iw, ih = warp_inverse(fwd, fw, fh, HORIZONTAL_KEYSTONE_MILD)
        avg_diff = sum(abs(a - b) for a, b in zip(rgb, inv)) / len(rgb)
        assert avg_diff < 2.0

    def test_different_distortions_differ(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        fwd1, _, _ = warp_forward(rgb, w, h, HORIZONTAL_KEYSTONE_MILD)
        fwd2, _, _ = warp_forward(rgb, w, h, VERTICAL_KEYSTONE_MILD)
        assert fwd1 != fwd2

    def test_warp_deterministic(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        a, _, _ = warp_forward(rgb, w, h, CORNER_PULL_INWARD)
        b, _, _ = warp_forward(rgb, w, h, CORNER_PULL_INWARD)
        assert a == b


# ═══════ HOST IMAGE GENERATION ═══════

class TestHostImageGeneration:
    def test_valid_png(self):
        hs = PerspectiveHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            distortion=HORIZONTAL_KEYSTONE_MILD,
            offset_x=200, offset_y=200,
        )
        png = generate_perspective_host_image(hs)
        assert png[:4] == b'\x89PNG'

    def test_deterministic(self):
        hs = PerspectiveHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            distortion=HORIZONTAL_KEYSTONE_MILD,
            offset_x=200, offset_y=200,
        )
        assert generate_perspective_host_image(hs) == generate_perspective_host_image(hs)

    def test_different_distortions_different_hosts(self):
        spec = fixture_adjacent_pair()
        h1 = generate_perspective_host_image(PerspectiveHostSpec(
            artifact_spec=spec, distortion=IDENTITY_DISTORTION, offset_x=200, offset_y=200))
        h2 = generate_perspective_host_image(PerspectiveHostSpec(
            artifact_spec=spec, distortion=HORIZONTAL_KEYSTONE_MILD, offset_x=200, offset_y=200))
        assert h1 != h2


# ═══════ IN-BOUNDS CASES ═══════

class TestInBoundsCases:
    @pytest.mark.parametrize("case_idx", range(len(IN_BOUNDS_CASES)))
    def test_inbound_adjacent_pair(self, case_idx):
        case = IN_BOUNDS_CASES[case_idx]
        spec = fixture_adjacent_pair()
        host = PerspectiveHostSpec(
            artifact_spec=spec,
            distortion=case["distortion"],
            offset_x=case["offset_x"],
            offset_y=case["offset_y"],
            host_background=case["host_background"],
        )
        result = perspective_and_bridge(host)
        assert result.verdict == PerspectiveVerdict.NORMALIZED

    @pytest.mark.parametrize("distortion", [
        IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD,
        VERTICAL_KEYSTONE_MILD, CORNER_PULL_INWARD,
    ], ids=["identity", "h_keystone", "v_keystone", "corner_pull"])
    def test_inbound_containment(self, distortion):
        spec = fixture_containment()
        host = PerspectiveHostSpec(
            artifact_spec=spec, distortion=distortion,
            offset_x=200, offset_y=200,
        )
        result = perspective_and_bridge(host)
        assert result.verdict == PerspectiveVerdict.NORMALIZED

    @pytest.mark.parametrize("distortion", [
        IDENTITY_DISTORTION, HORIZONTAL_KEYSTONE_MILD, MILD_TRAPEZOID,
    ], ids=["identity", "h_keystone", "trapezoid"])
    def test_inbound_three_regions(self, distortion):
        spec = fixture_three_regions()
        host = PerspectiveHostSpec(
            artifact_spec=spec, distortion=distortion,
            offset_x=200, offset_y=200,
        )
        result = perspective_and_bridge(host)
        assert result.verdict == PerspectiveVerdict.NORMALIZED


# ═══════ OUT-OF-BOUNDS CASES ═══════

class TestOutOfBounds:
    @pytest.mark.parametrize("case_idx", range(len(OUT_OF_BOUNDS_CASES)))
    def test_oob_rejected(self, case_idx):
        case = OUT_OF_BOUNDS_CASES[case_idx]
        spec = fixture_adjacent_pair()
        host = PerspectiveHostSpec(
            artifact_spec=spec,
            distortion=case["distortion"],
            offset_x=case["offset_x"],
            offset_y=case["offset_y"],
            host_background=case["host_background"],
        )
        result = perspective_and_bridge(host)
        assert result.verdict != PerspectiveVerdict.NORMALIZED
        assert result.verdict.value in (
            "NOT_FOUND", "PERSPECTIVE_UNKNOWN", "PARSE_FAILED", "BRIDGE_FAILED"
        )


# ═══════ DETERMINISM ═══════

class TestDeterminism:
    def test_repeated_runs_identical(self):
        host = PerspectiveHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            distortion=HORIZONTAL_KEYSTONE_MILD,
            offset_x=150, offset_y=150,
            host_background=(240, 240, 230),
        )
        r1 = perspective_and_bridge(host)
        r2 = perspective_and_bridge(host)
        assert r1.verdict == r2.verdict
        assert r1.detected_distortion == r2.detected_distortion
        assert r1.parsed_primitives == r2.parsed_primitives


# ═══════ SERIALIZATION ═══════

class TestSerialization:
    def test_result_to_dict(self):
        result = perspective_and_bridge(PerspectiveHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            distortion=CORNER_PULL_INWARD,
            offset_x=200, offset_y=200,
        ))
        d = result.to_dict()
        assert d["verdict"] == "NORMALIZED"
        assert d["detected_distortion"] is not None
        assert d["parsed_primitives"] == 2
        assert d["expected_primitives"] == 2
        assert d["profile_version"] == "V1.0"


# ═══════ PROFILE VALIDATION ═══════

class TestProfileValidation:
    def test_all_frozen_within_bounds(self):
        max_off = V1_PERSPECTIVE_PROFILE.max_corner_offset_px
        for dist in FROZEN_DISTORTIONS:
            for corner in [dist.tl, dist.tr, dist.bl, dist.br]:
                assert abs(corner[0]) <= max_off
                assert abs(corner[1]) <= max_off

    def test_unique_names(self):
        names = [d.name for d in FROZEN_DISTORTIONS]
        assert len(names) == len(set(names))
