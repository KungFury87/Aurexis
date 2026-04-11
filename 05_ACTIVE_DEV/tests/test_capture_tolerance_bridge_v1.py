"""
Pytest-format tests for Capture Tolerance Bridge V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "aurexis_lang", "src"
))

from aurexis_lang.capture_tolerance_bridge_v1 import (
    CAPTURE_TOLERANCE_VERSION, CAPTURE_TOLERANCE_FROZEN,
    V1_TOLERANCE_PROFILE, ToleranceProfile,
    ToleranceVerdict, ToleranceResult,
    bridge_degraded_to_substrate, apply_degradation,
    parse_artifact_tolerant,
    degrade_scale, degrade_translate, degrade_blur,
    degrade_noise, degrade_brightness, degrade_contrast,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_containment, fixture_three_regions,
    render_artifact, CANVAS_WIDTH, CANVAS_HEIGHT,
    _render_to_raw_rgb,
)


# ═══════ MODULE CONSTANTS ═══════

class TestModuleConstants:
    def test_version(self):
        assert CAPTURE_TOLERANCE_VERSION == "V1.0"

    def test_frozen(self):
        assert CAPTURE_TOLERANCE_FROZEN is True

    def test_profile_type(self):
        assert isinstance(V1_TOLERANCE_PROFILE, ToleranceProfile)

    def test_min_area(self):
        assert V1_TOLERANCE_PROFILE.min_detectable_area_px == 500


# ═══════ DEGRADATION FUNCTIONS ═══════

class TestDegradationFunctions:
    def test_scale_shrink(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        buf, w, h = degrade_scale(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 0.95)
        assert w < CANVAS_WIDTH and h < CANVAS_HEIGHT

    def test_scale_grow(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        buf, w, h = degrade_scale(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 1.05)
        assert w > CANVAS_WIDTH and h > CANVAS_HEIGHT

    def test_blur_differs(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        blurred = degrade_blur(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 1)
        assert blurred != rgb

    def test_noise_deterministic(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        n1 = degrade_noise(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 10, seed=42)
        n2 = degrade_noise(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 10, seed=42)
        assert n1 == n2

    def test_noise_differs(self):
        rgb = _render_to_raw_rgb(fixture_adjacent_pair())
        noisy = degrade_noise(rgb, CANVAS_WIDTH, CANVAS_HEIGHT, 10, seed=42)
        assert noisy != rgb


# ═══════ APPLY DEGRADATION API ═══════

class TestApplyDegradation:
    def test_blur_png(self):
        png = apply_degradation(fixture_adjacent_pair(), "blur", radius=1)
        assert png[:4] == b'\x89PNG'

    def test_noise_png(self):
        png = apply_degradation(fixture_adjacent_pair(), "noise", amplitude=10, seed=42)
        assert png[:4] == b'\x89PNG'

    def test_deterministic(self):
        spec = fixture_adjacent_pair()
        p1 = apply_degradation(spec, "blur", radius=1)
        p2 = apply_degradation(spec, "blur", radius=1)
        assert p1 == p2


# ═══════ TOLERANT PARSER ═══════

class TestTolerantParser:
    def test_exact_parse_count(self):
        png = render_artifact(fixture_adjacent_pair())
        parsed = parse_artifact_tolerant(png)
        assert len(parsed) == 2

    def test_tolerant_confidence(self):
        png = render_artifact(fixture_adjacent_pair())
        parsed = parse_artifact_tolerant(png)
        assert all(p["confidence"] == 0.95 for p in parsed)

    def test_noisy_parse(self):
        png = apply_degradation(fixture_adjacent_pair(), "noise", amplitude=15, seed=42)
        parsed = parse_artifact_tolerant(png)
        assert len(parsed) == 2


# ═══════ IN-BOUNDS — parametrized ═══════

class TestInBoundsAdjacentPair:
    @pytest.mark.parametrize("dtype,params", IN_BOUNDS_CASES)
    def test_tolerated(self, dtype, params):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), dtype, **params)
        assert r.verdict == ToleranceVerdict.TOLERATED


class TestInBoundsSingleRegion:
    @pytest.mark.parametrize("dtype,params", IN_BOUNDS_CASES)
    def test_tolerated(self, dtype, params):
        r = bridge_degraded_to_substrate(fixture_single_region(), dtype, **params)
        assert r.verdict == ToleranceVerdict.TOLERATED


class TestInBoundsContainmentNonBlur:
    """Containment fixture: all non-blur degradations must pass."""
    @pytest.mark.parametrize("dtype,params",
        [(d, p) for d, p in IN_BOUNDS_CASES if d != "blur"])
    def test_tolerated(self, dtype, params):
        r = bridge_degraded_to_substrate(fixture_containment(), dtype, **params)
        assert r.verdict == ToleranceVerdict.TOLERATED


# ═══════ CONTAINMENT BLUR BOUNDARY ═══════

class TestContainmentBlurBoundary:
    """Documented edge case: blur on containment creates boundary artifacts."""
    @pytest.mark.parametrize("radius", [1, 2])
    def test_honest_reject(self, radius):
        r = bridge_degraded_to_substrate(fixture_containment(), "blur", radius=radius)
        assert r.verdict != ToleranceVerdict.TOLERATED


# ═══════ OUT-OF-BOUNDS ═══════

class TestOutOfBounds:
    @pytest.mark.parametrize("dtype,params", OUT_OF_BOUNDS_CASES)
    def test_rejected(self, dtype, params):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), dtype, **params)
        assert r.verdict != ToleranceVerdict.TOLERATED


# ═══════ DETERMINISM ═══════

class TestDeterminism:
    def test_bridge_deterministic(self):
        spec = fixture_adjacent_pair()
        results = [bridge_degraded_to_substrate(spec, "noise", amplitude=20, seed=99).to_dict()
                   for _ in range(5)]
        assert all(r == results[0] for r in results)

    def test_render_deterministic(self):
        spec = fixture_adjacent_pair()
        pngs = [apply_degradation(spec, "blur", radius=2) for _ in range(5)]
        assert all(p == pngs[0] for p in pngs)


# ═══════ SERIALIZATION ═══════

class TestSerialization:
    def test_verdict(self):
        d = bridge_degraded_to_substrate(fixture_adjacent_pair(), "noise", amplitude=10, seed=42).to_dict()
        assert d["verdict"] == "TOLERATED"

    def test_degradation_type(self):
        d = bridge_degraded_to_substrate(fixture_adjacent_pair(), "noise", amplitude=10, seed=42).to_dict()
        assert d["degradation_type"] == "noise"

    def test_version(self):
        d = bridge_degraded_to_substrate(fixture_adjacent_pair(), "noise", amplitude=10, seed=42).to_dict()
        assert d["profile_version"] == CAPTURE_TOLERANCE_VERSION


# ═══════ BOUNDARY CASES ═══════

class TestBoundaryCases:
    def test_noise_at_limit(self):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), "noise", amplitude=25, seed=42)
        assert r.verdict == ToleranceVerdict.TOLERATED

    def test_blur_at_limit(self):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), "blur", radius=2)
        assert r.verdict == ToleranceVerdict.TOLERATED

    def test_brightness_high_limit(self):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), "brightness", shift=30)
        assert r.verdict == ToleranceVerdict.TOLERATED

    def test_brightness_low_limit(self):
        r = bridge_degraded_to_substrate(fixture_adjacent_pair(), "brightness", shift=-30)
        assert r.verdict == ToleranceVerdict.TOLERATED
