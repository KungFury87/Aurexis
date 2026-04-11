"""Aurexis Core — Hardware Calibration V1 Test Suite (pytest format)
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved."""
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aurexis_lang", "src"))
from aurexis_lang.hardware_calibration_v1 import *

class TestSpec:
    def test_version(self): assert CALIBRATION_VERSION == "V1.0"
    def test_frozen(self): assert CALIBRATION_FROZEN is True

class TestCameraProfile:
    def test_defaults(self):
        p = CameraProfile()
        assert p.resolution_megapixels == 12.0
    def test_to_dict(self):
        p = CameraProfile(name="test")
        assert p.to_dict()["name"] == "test"

class TestComputeFactors:
    def test_ideal_high_ceiling(self):
        p = CameraProfile(name="ideal", resolution_megapixels=48.0, sensor_noise_level=0.02,
            lens_distortion=0.01, capture_distance_m=0.3)
        f = compute_factors(p)
        assert f.hardware_ceiling >= 0.95

    def test_bad_low_ceiling(self):
        p = CameraProfile(name="bad", resolution_megapixels=1.0, sensor_noise_level=0.5,
            lens_distortion=0.4, capture_distance_m=3.0)
        f = compute_factors(p)
        assert f.hardware_ceiling < 0.7

class TestCalibrate:
    def test_uncapped(self):
        p = CameraProfile(name="good", resolution_megapixels=48.0, sensor_noise_level=0.02,
            lens_distortion=0.01, capture_distance_m=0.3)
        cr = calibrate_confidence(0.7, p)
        assert cr.verdict == CalibrationVerdict.UNCAPPED
        assert cr.calibrated_confidence == 0.7

    def test_capped(self):
        p = CameraProfile(name="bad", resolution_megapixels=1.0, sensor_noise_level=0.5,
            lens_distortion=0.4, capture_distance_m=3.0)
        cr = calibrate_confidence(0.95, p)
        assert cr.was_capped is True
        assert cr.calibrated_confidence < 0.95

    def test_degraded(self):
        p = CameraProfile(name="terrible", resolution_megapixels=0.5,
            sensor_noise_level=0.8, lens_distortion=0.7, capture_distance_m=5.0)
        cr = calibrate_confidence(0.9, p)
        assert cr.verdict == CalibrationVerdict.DEGRADED

    def test_invalid(self):
        p = CameraProfile(name="inv", resolution_megapixels=0.0)
        cr = calibrate_confidence(0.9, p)
        assert cr.verdict == CalibrationVerdict.INVALID_PROFILE

class TestCalibrateFrame:
    def test_frame(self):
        prims = [{"type":"region","bbox":[0,0,100,100],"confidence":0.95}]
        p = CameraProfile(name="mod", resolution_megapixels=12.0)
        cf = calibrate_frame(prims, p)
        assert cf["frame_summary"]["total_primitives"] == 1

class TestRegistry:
    def test_builtins(self):
        reg = CalibrationRegistry()
        assert "ideal" in reg.list_profiles()
    def test_calibrate_by_name(self):
        reg = CalibrationRegistry()
        cr = reg.calibrate(0.9, "ideal")
        assert cr.verdict != CalibrationVerdict.INVALID_PROFILE

class TestDeterminism:
    def test_deterministic(self):
        p = CameraProfile(name="test", resolution_megapixels=12.0)
        results = [calibrate_confidence(0.85, p).to_dict() for _ in range(5)]
        assert all(r == results[0] for r in results)
