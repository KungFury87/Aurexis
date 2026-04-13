"""
Aurexis Core — Capture Session Manifest Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.capture_session_manifest_bridge_v1 import (
    SESSION_MANIFEST_VERSION, SESSION_MANIFEST_FROZEN,
    CaptureFileRecord, SessionManifestVerdict, SessionSummary,
    CaptureSessionManifest, record_from_ingest, make_empty_summary,
    EXPECTED_RECORD_FIELDS, EXPECTED_SUMMARY_FIELDS, EXPECTED_VERDICT_COUNT,
)


def _sample_record(name="img001.jpg", device="S23Ultra"):
    return CaptureFileRecord(
        file_ref=f"captures/{name}", file_ext=".jpg", file_size_bytes=5_000_000,
        width_px=4000, height_px=3000, ingest_case_name="phone_jpeg",
        evidence_tier="real-capture", capture_device=device,
        capture_timestamp="2026-04-13T12:00:00",
    )


def test_version():
    assert SESSION_MANIFEST_VERSION == "V1.0"

def test_frozen():
    assert SESSION_MANIFEST_FROZEN is True

def test_verdict_count():
    assert len(SessionManifestVerdict) == EXPECTED_VERDICT_COUNT

def test_record_creation():
    r = _sample_record()
    assert r.file_ref == "captures/img001.jpg"
    assert r.evidence_tier == "real-capture"

def test_record_to_dict():
    d = _sample_record().to_dict()
    assert "file_ref" in d
    assert d["ingest_case_name"] == "phone_jpeg"

def test_record_from_ingest():
    meta = {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:00:00"}
    r = record_from_ingest("x.jpg", ".jpg", 4_000_000, 3840, 2160, "phone_jpeg", "real-capture", meta)
    assert r.capture_device == "S23Ultra"

def test_empty_manifest():
    m = CaptureSessionManifest(session_id="t1")
    assert m.file_count == 0
    s = m.finalize()
    assert s.verdict == SessionManifestVerdict.EMPTY

def test_manifest_with_records():
    m = CaptureSessionManifest(session_id="t2")
    m.add_record(_sample_record())
    m.add_record(_sample_record("img002.jpg"))
    s = m.finalize()
    assert s.verdict == SessionManifestVerdict.VALID
    assert s.file_count == 2
    assert s.manifest_hash != ""

def test_cannot_add_after_finalize():
    m = CaptureSessionManifest(session_id="t3")
    m.finalize()
    assert m.add_record(_sample_record()) is False

def test_manifest_hash_deterministic():
    def make():
        m = CaptureSessionManifest(session_id="det", created_at="1000")
        m.add_record(_sample_record())
        return m.finalize().manifest_hash
    assert make() == make()

def test_serialization():
    m = CaptureSessionManifest(session_id="t4")
    m.add_record(_sample_record())
    m.finalize()
    d = m.to_dict()
    assert d["file_count"] == 1
    j = m.to_json()
    assert '"session_id": "t4"' in j

def test_summary_text():
    m = CaptureSessionManifest(session_id="t5")
    m.add_record(_sample_record())
    m.finalize()
    assert "t5" in m.to_summary_text()

def test_multi_device():
    m = CaptureSessionManifest(session_id="md", created_at="1001")
    m.add_record(_sample_record("a.jpg", "DevA"))
    m.add_record(_sample_record("b.jpg", "DevB"))
    s = m.finalize()
    assert s.unique_devices == 2

def test_make_empty_summary():
    s = make_empty_summary("x")
    assert s.verdict == SessionManifestVerdict.EMPTY
