"""
Pytest-format tests for Artifact Localization Bridge V1.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os, pytest

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "aurexis_lang", "src"
))

from aurexis_lang.artifact_localization_bridge_v1 import (
    LOCALIZATION_VERSION, LOCALIZATION_FROZEN,
    V1_LOCALIZATION_PROFILE, LocalizationProfile,
    ALLOWED_HOST_BACKGROUNDS,
    LocalizationVerdict, LocalizationResult,
    HostImageSpec, generate_host_image,
    localize_artifact, extract_and_normalize,
    localize_and_bridge,
    IN_BOUNDS_PLACEMENTS, OUT_OF_BOUNDS_PLACEMENTS,
)
from aurexis_lang.raster_law_bridge_v1 import (
    fixture_adjacent_pair, fixture_single_region,
    fixture_three_regions, CANVAS_WIDTH, CANVAS_HEIGHT,
)


# ═══════ MODULE CONSTANTS ═══════

class TestModuleConstants:
    def test_version(self):
        assert LOCALIZATION_VERSION == "V1.0"

    def test_frozen(self):
        assert LOCALIZATION_FROZEN is True

    def test_profile(self):
        assert isinstance(V1_LOCALIZATION_PROFILE, LocalizationProfile)

    def test_bg_count(self):
        assert len(ALLOWED_HOST_BACKGROUNDS) == 5


# ═══════ HOST IMAGE GENERATION ═══════

class TestHostImageGeneration:
    def test_valid_png(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        png = generate_host_image(hs)
        assert png[:4] == b'\x89PNG'

    def test_deterministic(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        assert generate_host_image(hs) == generate_host_image(hs)


# ═══════ LOCALIZATION DETECTION ═══════

class TestLocalizationDetection:
    def test_finds_artifact(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        bbox = localize_artifact(generate_host_image(hs))
        assert bbox is not None

    def test_no_artifact(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=-500, offset_y=-500, host_background=(220, 220, 220))
        assert localize_artifact(generate_host_image(hs)) is None


# ═══════ IN-BOUNDS — parametrized ═══════

class TestInBoundsAdjacentPair:
    @pytest.mark.parametrize("placement", IN_BOUNDS_PLACEMENTS)
    def test_localized(self, placement):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(), **placement)
        assert localize_and_bridge(hs).verdict == LocalizationVerdict.LOCALIZED


class TestInBoundsSingleRegion:
    @pytest.mark.parametrize("placement", IN_BOUNDS_PLACEMENTS)
    def test_localized(self, placement):
        hs = HostImageSpec(artifact_spec=fixture_single_region(), **placement)
        assert localize_and_bridge(hs).verdict == LocalizationVerdict.LOCALIZED


class TestInBoundsThreeRegions:
    def test_center(self):
        hs = HostImageSpec(artifact_spec=fixture_three_regions(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        r = localize_and_bridge(hs)
        assert r.verdict == LocalizationVerdict.LOCALIZED
        assert r.parsed_primitives == 3


# ═══════ OUT-OF-BOUNDS ═══════

class TestOutOfBounds:
    @pytest.mark.parametrize("placement", OUT_OF_BOUNDS_PLACEMENTS)
    def test_rejected(self, placement):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(), **placement)
        assert localize_and_bridge(hs).verdict != LocalizationVerdict.LOCALIZED


# ═══════ DETERMINISM ═══════

class TestDeterminism:
    def test_bridge_deterministic(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        results = [localize_and_bridge(hs).to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)


# ═══════ SERIALIZATION ═══════

class TestSerialization:
    def test_verdict(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        d = localize_and_bridge(hs).to_dict()
        assert d["verdict"] == "LOCALIZED"

    def test_version(self):
        hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                           offset_x=200, offset_y=200, host_background=(220, 220, 220))
        assert localize_and_bridge(hs).to_dict()["profile_version"] == LOCALIZATION_VERSION


# ═══════ ALL BACKGROUNDS ═══════

class TestAllBackgrounds:
    def test_all_allowed_backgrounds(self):
        for bg in ALLOWED_HOST_BACKGROUNDS:
            hs = HostImageSpec(artifact_spec=fixture_adjacent_pair(),
                               offset_x=200, offset_y=200, host_background=bg)
            assert localize_and_bridge(hs).verdict == LocalizationVerdict.LOCALIZED, \
                f"Failed for background {bg}"
