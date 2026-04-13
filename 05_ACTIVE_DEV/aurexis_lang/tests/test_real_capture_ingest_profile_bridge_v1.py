"""
Aurexis Core — Real Capture Ingest Profile Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.real_capture_ingest_profile_bridge_v1 import (
    INGEST_PROFILE_VERSION, INGEST_PROFILE_FROZEN,
    CaptureFileShape, CaptureAssumption, CaptureIngestCase,
    IngestProfile, IngestVerdict, IngestResult,
    validate_capture_file, make_rejected_result,
    V1_INGEST_PROFILE, FROZEN_CASES,
    CASE_PHONE_JPEG, CASE_PHONE_PNG, CASE_WEBCAM_JPEG,
    CASE_VIDEO_FRAME_PNG, CASE_SCANNER_TIFF,
    EXPECTED_CASE_COUNT,
)


def test_version():
    assert INGEST_PROFILE_VERSION == "V1.0"

def test_frozen():
    assert INGEST_PROFILE_FROZEN is True

def test_profile_singleton():
    assert V1_INGEST_PROFILE is not None
    assert V1_INGEST_PROFILE.frozen is True
    assert len(V1_INGEST_PROFILE.cases) == EXPECTED_CASE_COUNT

def test_frozen_case_count():
    assert len(FROZEN_CASES) == 5

@pytest.mark.parametrize("name", ["phone_jpeg", "phone_png", "webcam_jpeg", "video_frame_png", "scanner_tiff"])
def test_case_names(name):
    names = [c.name for c in FROZEN_CASES]
    assert name in names

@pytest.mark.parametrize("case", FROZEN_CASES)
def test_evidence_tier_entry(case):
    assert case.evidence_tier_entry == "real-capture"

@pytest.mark.parametrize("case", FROZEN_CASES)
def test_required_metadata_has_device(case):
    assert "capture_device" in case.required_metadata

@pytest.mark.parametrize("case", FROZEN_CASES)
def test_required_metadata_has_timestamp(case):
    assert "capture_timestamp" in case.required_metadata

def _full_metadata():
    return {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:00:00",
            "adequate_lighting": True, "stable_orientation": True, "subject_in_frame": True}

def test_phone_jpeg_accept():
    r = validate_capture_file(".jpg", 5_000_000, 4000, 3000, _full_metadata())
    assert r.verdict == IngestVerdict.ACCEPTED
    assert r.matched_case_name == "phone_jpeg"

def test_too_small_rejected():
    r = validate_capture_file(".jpg", 5_000_000, 100, 100, _full_metadata())
    assert r.verdict == IngestVerdict.REJECTED_NO_MATCHING_CASE

def test_missing_metadata_rejected():
    r = validate_capture_file(".jpg", 5_000_000, 4000, 3000, {"adequate_lighting": True})
    assert r.verdict == IngestVerdict.REJECTED_MISSING_METADATA

def test_assumption_violated():
    meta = dict(_full_metadata(), adequate_lighting=False)
    r = validate_capture_file(".jpg", 5_000_000, 4000, 3000, meta)
    assert r.verdict == IngestVerdict.REJECTED_ASSUMPTION_VIOLATED

def test_scanner_tiff_accept():
    meta = {"capture_device": "Epson", "capture_timestamp": "t", "scan_dpi": 600,
            "flat_placement": True, "adequate_lighting": True}
    r = validate_capture_file(".tif", 80_000_000, 3600, 5400, meta)
    assert r.verdict == IngestVerdict.ACCEPTED

def test_unknown_extension():
    r = validate_capture_file(".bmp", 5_000_000, 4000, 3000, _full_metadata())
    assert r.verdict == IngestVerdict.REJECTED_NO_MATCHING_CASE

def test_profile_hash_deterministic():
    assert V1_INGEST_PROFILE.profile_hash() == V1_INGEST_PROFILE.profile_hash()

def test_profile_serialization():
    d = V1_INGEST_PROFILE.to_dict()
    assert d["case_count"] == 5

def test_make_rejected_result():
    r = make_rejected_result("x")
    assert r.verdict == IngestVerdict.ERROR

def test_file_shape_matches():
    shape = CaptureFileShape(extension=".jpg", max_file_size_bytes=10_000_000)
    assert shape.matches(".jpg", 5_000_000, 1000, 1000)
    assert not shape.matches(".png", 5_000_000, 1000, 1000)
    assert not shape.matches(".jpg", 50_000_000, 1000, 1000)

def test_capture_assumption_to_dict():
    a = CaptureAssumption(name="test", description="desc", required=True)
    d = a.to_dict()
    assert d["name"] == "test"

def test_ingest_result_to_dict():
    r = IngestResult(verdict=IngestVerdict.ACCEPTED, matched_case_name="phone_jpeg")
    d = r.to_dict()
    assert d["verdict"] == "ACCEPTED"
