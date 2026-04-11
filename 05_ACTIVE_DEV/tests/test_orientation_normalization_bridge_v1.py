"""
Pytest-format tests for Orientation Normalization Bridge V1.

Bounded rotated-artifact recovery for the narrow V1 raster bridge.
Tests that canonical V1 artifacts, rotated by cardinal angles and
embedded in host images, can be localized, orientation-normalized,
and bridged to the substrate deterministically.

This is NOT general rotation invariance or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "aurexis_lang", "src"
))

from aurexis_lang.orientation_normalization_bridge_v1 import (
    ORIENTATION_VERSION, ORIENTATION_FROZEN, SUPPORTED_ANGLES,
    V1_ORIENTATION_PROFILE, OrientationProfile,
    rotate_image, rotate_90_cw, rotate_180, rotate_270_cw, rotate_png,
    RotatedHostSpec, generate_rotated_host_image,
    detect_orientation, normalize_orientation,
    OrientationVerdict, OrientationResult,
    orient_and_bridge,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_containment, fixture_three_regions,
    CANVAS_WIDTH, CANVAS_HEIGHT,
    _render_to_raw_rgb, _decode_png_to_rgb, render_artifact,
)


# ═══════ MODULE CONSTANTS ═══════

class TestModuleConstants:
    def test_version(self):
        assert ORIENTATION_VERSION == "V1.0"

    def test_frozen(self):
        assert ORIENTATION_FROZEN is True

    def test_profile(self):
        assert isinstance(V1_ORIENTATION_PROFILE, OrientationProfile)

    def test_supported_angles(self):
        assert SUPPORTED_ANGLES == (0, 90, 180, 270)

    def test_detection_method(self):
        assert V1_ORIENTATION_PROFILE.detection_method == "exhaustive_trial"

    def test_in_bounds_count(self):
        assert len(IN_BOUNDS_CASES) == 8

    def test_oob_count(self):
        assert len(OUT_OF_BOUNDS_CASES) == 4


# ═══════ ROTATION FUNCTIONS ═══════

class TestRotationFunctions:
    def test_4x90_identity(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        buf, ww, hh = rotate_image(rgb, w, h, 90)
        buf, ww, hh = rotate_image(buf, ww, hh, 90)
        buf, ww, hh = rotate_image(buf, ww, hh, 90)
        buf, ww, hh = rotate_image(buf, ww, hh, 90)
        assert ww == w and hh == h
        assert buf == rgb

    def test_90_270_identity(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        r90, w90, h90 = rotate_image(rgb, w, h, 90)
        back, wb, hb = rotate_image(r90, w90, h90, 270)
        assert wb == w and hb == h
        assert back == rgb

    def test_180_180_identity(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        r180, w1, h1 = rotate_image(rgb, w, h, 180)
        back, wb, hb = rotate_image(r180, w1, h1, 180)
        assert back == rgb

    def test_0_deg_copy(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        r0, w0, h0 = rotate_image(rgb, w, h, 0)
        assert r0 == rgb

    def test_90_differs_from_0(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        w, h = CANVAS_WIDTH, CANVAS_HEIGHT
        r90, _, _ = rotate_image(rgb, w, h, 90)
        assert r90 != rgb

    def test_unsupported_angle_raises(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        with pytest.raises(ValueError):
            rotate_image(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 45)

    def test_rotate_png_roundtrip(self):
        png = render_artifact(fixture_adjacent_pair())
        rotated = rotate_png(png, 90)
        back = rotate_png(rotated, 270)
        _, _, orig_buf = _decode_png_to_rgb(png)
        _, _, back_buf = _decode_png_to_rgb(back)
        assert orig_buf == back_buf


# ═══════ HOST IMAGE GENERATION ═══════

class TestHostImageGeneration:
    def test_valid_png(self):
        hs = RotatedHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            rotation_angle=90, offset_x=200, offset_y=200,
        )
        png = generate_rotated_host_image(hs)
        assert png[:4] == b'\x89PNG'

    def test_deterministic(self):
        hs = RotatedHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            rotation_angle=90, offset_x=200, offset_y=200,
        )
        assert generate_rotated_host_image(hs) == generate_rotated_host_image(hs)

    def test_different_rotations_different_images(self):
        spec = fixture_adjacent_pair()
        h0 = generate_rotated_host_image(RotatedHostSpec(
            artifact_spec=spec, rotation_angle=0, offset_x=200, offset_y=200))
        h90 = generate_rotated_host_image(RotatedHostSpec(
            artifact_spec=spec, rotation_angle=90, offset_x=200, offset_y=200))
        assert h0 != h90


# ═══════ ORIENTATION DETECTION ═══════

class TestOrientationDetection:
    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_detect_angle_adjacent_pair(self, angle):
        from aurexis_lang.artifact_localization_bridge_v1 import (
            localize_artifact, extract_and_normalize,
        )
        spec = fixture_adjacent_pair()
        host = RotatedHostSpec(
            artifact_spec=spec, rotation_angle=angle,
            offset_x=200, offset_y=200,
        )
        hpng = generate_rotated_host_image(host)
        bbox = localize_artifact(hpng)
        assert bbox is not None
        extracted = extract_and_normalize(hpng, bbox)
        detected = detect_orientation(extracted, spec)
        assert detected == angle

    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_detect_angle_containment(self, angle):
        from aurexis_lang.artifact_localization_bridge_v1 import (
            localize_artifact, extract_and_normalize,
        )
        spec = fixture_containment()
        host = RotatedHostSpec(
            artifact_spec=spec, rotation_angle=angle,
            offset_x=200, offset_y=200,
        )
        hpng = generate_rotated_host_image(host)
        bbox = localize_artifact(hpng)
        assert bbox is not None
        extracted = extract_and_normalize(hpng, bbox)
        detected = detect_orientation(extracted, spec)
        assert detected == angle


# ═══════ IN-BOUNDS CASES ═══════

class TestInBoundsCases:
    @pytest.mark.parametrize("case_idx", range(len(IN_BOUNDS_CASES)))
    def test_inbound_adjacent_pair(self, case_idx):
        case = IN_BOUNDS_CASES[case_idx]
        spec = fixture_adjacent_pair()
        host = RotatedHostSpec(
            artifact_spec=spec,
            rotation_angle=case["angle"],
            offset_x=case["offset_x"],
            offset_y=case["offset_y"],
            embed_scale=case["embed_scale"],
            host_background=case["host_background"],
        )
        result = orient_and_bridge(host)
        assert result.verdict == OrientationVerdict.NORMALIZED
        assert result.detected_angle == case["angle"]

    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_inbound_containment(self, angle):
        spec = fixture_containment()
        host = RotatedHostSpec(
            artifact_spec=spec, rotation_angle=angle,
            offset_x=200, offset_y=200,
        )
        result = orient_and_bridge(host)
        assert result.verdict == OrientationVerdict.NORMALIZED

    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_inbound_three_regions(self, angle):
        spec = fixture_three_regions()
        host = RotatedHostSpec(
            artifact_spec=spec, rotation_angle=angle,
            offset_x=200, offset_y=200,
        )
        result = orient_and_bridge(host)
        assert result.verdict == OrientationVerdict.NORMALIZED

    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_inbound_single_region_symmetric(self, angle):
        spec = fixture_single_region()
        host = RotatedHostSpec(
            artifact_spec=spec, rotation_angle=angle,
            offset_x=200, offset_y=200,
        )
        result = orient_and_bridge(host)
        assert result.verdict == OrientationVerdict.NORMALIZED


# ═══════ OUT-OF-BOUNDS CASES ═══════

class TestOutOfBounds:
    @pytest.mark.parametrize("case_idx", range(len(OUT_OF_BOUNDS_CASES)))
    def test_oob_rejected(self, case_idx):
        case = OUT_OF_BOUNDS_CASES[case_idx]
        spec = fixture_adjacent_pair()
        host = RotatedHostSpec(
            artifact_spec=spec,
            rotation_angle=case["angle"],
            offset_x=case["offset_x"],
            offset_y=case["offset_y"],
            embed_scale=case["embed_scale"],
            host_background=case["host_background"],
        )
        result = orient_and_bridge(host)
        assert result.verdict != OrientationVerdict.NORMALIZED
        assert result.verdict.value in (
            "NOT_FOUND", "ORIENTATION_UNKNOWN", "PARSE_FAILED", "BRIDGE_FAILED"
        )


# ═══════ DETERMINISM ═══════

class TestDeterminism:
    def test_repeated_runs_identical(self):
        host = RotatedHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            rotation_angle=90, offset_x=150, offset_y=150,
            host_background=(240, 240, 230),
        )
        r1 = orient_and_bridge(host)
        r2 = orient_and_bridge(host)
        assert r1.verdict == r2.verdict
        assert r1.detected_angle == r2.detected_angle
        assert r1.parsed_primitives == r2.parsed_primitives


# ═══════ SERIALIZATION ═══════

class TestSerialization:
    def test_result_to_dict(self):
        result = orient_and_bridge(RotatedHostSpec(
            artifact_spec=fixture_adjacent_pair(),
            rotation_angle=180, offset_x=200, offset_y=200,
        ))
        d = result.to_dict()
        assert d["verdict"] == "NORMALIZED"
        assert d["detected_angle"] == 180
        assert d["parsed_primitives"] == 2
        assert d["expected_primitives"] == 2
        assert d["profile_version"] == "V1.0"
