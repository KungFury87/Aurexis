"""
Aurexis Core — Real Capture Intake Preflight Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.real_capture_intake_preflight_bridge_v1 import (
    PREFLIGHT_VERSION, PREFLIGHT_FROZEN,
    PreflightVerdict, PreflightCheck, PreflightResult,
    run_preflight, make_error_preflight,
    PREFLIGHT_CHECKS, EXPECTED_CHECK_COUNT,
    EXPECTED_VERDICT_COUNT, ALLOWED_EXTENSIONS,
)


def _valid_manifest():
    return {
        "session_id": "test-001",
        "description": "Test",
        "created_at": "2026-04-13T14:30:00",
        "conditions": {
            "adequate_lighting": True,
            "stable_orientation": True,
            "subject_in_frame": True,
        },
        "files": [{
            "file_ref": "capture_001.jpg",
            "file_ext": ".jpg",
            "file_size_bytes": 5000000,
            "width_px": 4000,
            "height_px": 3000,
            "capture_device": "S23Ultra",
            "capture_timestamp": "2026-04-13T14:30:00",
        }],
    }


def test_version():
    assert PREFLIGHT_VERSION == "V1.0"

def test_frozen():
    assert PREFLIGHT_FROZEN is True

def test_check_count():
    assert len(PREFLIGHT_CHECKS) == EXPECTED_CHECK_COUNT

def test_verdict_count():
    assert len(PreflightVerdict) == EXPECTED_VERDICT_COUNT

def test_valid_manifest_cleared():
    r = run_preflight(_valid_manifest())
    assert r.verdict == PreflightVerdict.CLEARED
    assert r.passed_checks == EXPECTED_CHECK_COUNT

def test_missing_session_fields():
    r = run_preflight({"files": [_valid_manifest()["files"][0]]})
    assert r.verdict == PreflightVerdict.REJECTED

def test_empty_files():
    m = dict(_valid_manifest(), files=[])
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_missing_file_fields():
    m = dict(_valid_manifest(), files=[{"file_ref": "x.jpg"}])
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_unsupported_extension():
    m = dict(_valid_manifest())
    m["files"] = [dict(_valid_manifest()["files"][0], file_ext=".bmp", file_ref="t.bmp")]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_invalid_filename():
    m = dict(_valid_manifest())
    m["files"] = [dict(_valid_manifest()["files"][0], file_ref="my file.jpg")]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_duplicate_files():
    m = dict(_valid_manifest())
    m["files"] = [_valid_manifest()["files"][0], _valid_manifest()["files"][0]]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_zero_file_size():
    m = dict(_valid_manifest())
    m["files"] = [dict(_valid_manifest()["files"][0], file_size_bytes=0)]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_zero_resolution():
    m = dict(_valid_manifest())
    m["files"] = [dict(_valid_manifest()["files"][0], width_px=0)]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.REJECTED

def test_hash_deterministic():
    r1 = run_preflight(_valid_manifest())
    r2 = run_preflight(_valid_manifest())
    assert r1.preflight_hash == r2.preflight_hash

def test_serialization():
    r = run_preflight(_valid_manifest())
    d = r.to_dict()
    assert "verdict" in d
    assert '"CLEARED"' in r.to_json()

def test_summary_text():
    r = run_preflight(_valid_manifest())
    assert "CLEARED" in r.to_summary_text()

def test_make_error_preflight():
    e = make_error_preflight("x")
    assert e.verdict == PreflightVerdict.ERROR

def test_scanner_tiff_cleared():
    m = dict(_valid_manifest())
    m["conditions"]["flat_placement"] = True
    m["files"] = [{
        "file_ref": "scan.tif", "file_ext": ".tif", "file_size_bytes": 80000000,
        "width_px": 3600, "height_px": 5400, "capture_device": "Epson", "capture_timestamp": "t",
    }]
    r = run_preflight(m)
    assert r.verdict == PreflightVerdict.CLEARED
