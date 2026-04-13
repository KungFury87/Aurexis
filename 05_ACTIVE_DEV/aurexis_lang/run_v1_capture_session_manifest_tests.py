#!/usr/bin/env python3
"""
Aurexis Core — Capture Session Manifest Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.capture_session_manifest_bridge_v1 import (
    SESSION_MANIFEST_VERSION, SESSION_MANIFEST_FROZEN,
    CaptureFileRecord, SessionManifestVerdict, SessionSummary,
    CaptureSessionManifest, record_from_ingest, make_empty_summary,
    EXPECTED_RECORD_FIELDS, EXPECTED_SUMMARY_FIELDS, EXPECTED_VERDICT_COUNT,
)

PASS_COUNT = 0
FAIL_COUNT = 0

def section(name):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")

def check(cond, label):
    global PASS_COUNT, FAIL_COUNT
    s = "PASS" if cond else "FAIL"
    if cond: PASS_COUNT += 1
    else: FAIL_COUNT += 1
    print(f"  [{s}] {label}")

# ── 1. Module version and frozen state ──
section("1. Module Version and Frozen State")
check(SESSION_MANIFEST_VERSION == "V1.0", "Version V1.0")
check(SESSION_MANIFEST_FROZEN is True, "Module frozen")

# ── 2. Verdict enum ──
section("2. Verdict Enum")
check(len(SessionManifestVerdict) == EXPECTED_VERDICT_COUNT, f"Verdict count == {EXPECTED_VERDICT_COUNT}")
check(SessionManifestVerdict.VALID.value == "VALID", "VALID verdict")
check(SessionManifestVerdict.EMPTY.value == "EMPTY", "EMPTY verdict")

# ── 3. CaptureFileRecord creation ──
section("3. CaptureFileRecord Creation")
rec = CaptureFileRecord(
    file_ref="captures/img001.jpg", file_ext=".jpg", file_size_bytes=5_000_000,
    width_px=4000, height_px=3000, ingest_case_name="phone_jpeg",
    evidence_tier="real-capture", capture_device="S23Ultra",
    capture_timestamp="2026-04-13T12:00:00",
)
check(rec.file_ref == "captures/img001.jpg", "file_ref correct")
check(rec.file_size_bytes == 5_000_000, "file_size correct")
check(rec.evidence_tier == "real-capture", "evidence_tier correct")
d = rec.to_dict()
check("file_ref" in d, "to_dict has file_ref")
check(d["ingest_case_name"] == "phone_jpeg", "to_dict ingest_case_name")

# ── 4. record_from_ingest ──
section("4. record_from_ingest")
meta = {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:00:00"}
rec2 = record_from_ingest("captures/img002.jpg", ".jpg", 4_000_000, 3840, 2160,
                          "phone_jpeg", "real-capture", meta)
check(rec2.capture_device == "S23Ultra", "capture_device from metadata")
check(rec2.capture_timestamp == "2026-04-13T12:00:00", "capture_timestamp from metadata")
check(len(rec2.metadata) > 0, "metadata tuple populated")

# ── 5. Empty session manifest ──
section("5. Empty Session Manifest")
manifest = CaptureSessionManifest(session_id="test-001", description="empty test")
check(manifest.session_id == "test-001", "session_id correct")
check(manifest.file_count == 0, "file_count == 0 before adding")
check(manifest.finalized is False, "not finalized initially")
summary = manifest.finalize()
check(summary.verdict == SessionManifestVerdict.EMPTY, "Empty session → EMPTY verdict")
check(manifest.finalized is True, "finalized after finalize()")

# ── 6. Session with records ──
section("6. Session With Records")
manifest2 = CaptureSessionManifest(session_id="test-002", description="two files")
ok1 = manifest2.add_record(rec)
ok2 = manifest2.add_record(rec2)
check(ok1 is True, "add_record succeeds")
check(ok2 is True, "second add_record succeeds")
check(manifest2.file_count == 2, "file_count == 2")
summary2 = manifest2.finalize()
check(summary2.verdict == SessionManifestVerdict.VALID, "VALID verdict")
check(summary2.file_count == 2, "summary file_count == 2")
check(summary2.total_bytes == 9_000_000, "total_bytes correct")
check(summary2.unique_devices == 1, "unique_devices == 1")
check("S23Ultra" in summary2.device_list, "S23Ultra in device_list")
check(summary2.manifest_hash != "", "manifest_hash computed")

# ── 7. Cannot add after finalize ──
section("7. Cannot Add After Finalize")
ok3 = manifest2.add_record(rec)
check(ok3 is False, "add_record returns False after finalize")
check(manifest2.file_count == 2, "file_count still 2")

# ── 8. Manifest hash determinism ──
section("8. Manifest Hash Determinism")
m3 = CaptureSessionManifest(session_id="det-test", created_at="1000000")
m3.add_record(rec)
s3 = m3.finalize()
m4 = CaptureSessionManifest(session_id="det-test", created_at="1000000")
m4.add_record(rec)
s4 = m4.finalize()
check(s3.manifest_hash == s4.manifest_hash, "Deterministic manifest hash")

# ── 9. Serialization ──
section("9. Serialization")
d2 = manifest2.to_dict()
check(d2["file_count"] == 2, "to_dict file_count")
check(d2["finalized"] is True, "to_dict finalized")
j = manifest2.to_json()
check('"session_id": "test-002"' in j, "to_json has session_id")

# ── 10. Summary text ──
section("10. Summary Text")
txt = manifest2.to_summary_text()
check("test-002" in txt, "Summary contains session_id")
check("Files: 2" in txt, "Summary contains file count")

# ── 11. Case breakdown ──
section("11. Case Breakdown")
check("phone_jpeg" in summary2.ingest_case_breakdown, "phone_jpeg in breakdown")
check(summary2.ingest_case_breakdown["phone_jpeg"] == 2, "phone_jpeg count == 2")

# ── 12. make_empty_summary ──
section("12. make_empty_summary")
es = make_empty_summary("x")
check(es.verdict == SessionManifestVerdict.EMPTY, "Empty summary verdict")
check(es.session_id == "x", "Empty summary session_id")

# ── 13. Multi-device session ──
section("13. Multi-Device Session")
rec3 = CaptureFileRecord(
    file_ref="captures/webcam001.jpg", file_ext=".jpg", file_size_bytes=1_000_000,
    width_px=1920, height_px=1080, ingest_case_name="webcam_jpeg",
    evidence_tier="real-capture", capture_device="LogitechC920",
    capture_timestamp="2026-04-13T12:05:00",
)
m5 = CaptureSessionManifest(session_id="multi-dev", created_at="1000001")
m5.add_record(rec)
m5.add_record(rec3)
s5 = m5.finalize()
check(s5.unique_devices == 2, "unique_devices == 2")
check("LogitechC920" in s5.device_list, "LogitechC920 in device_list")
check("S23Ultra" in s5.device_list, "S23Ultra in device_list")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  CAPTURE SESSION MANIFEST BRIDGE V1 — STANDALONE RESULTS")
print(f"  PASSED: {PASS_COUNT}  FAILED: {FAIL_COUNT}")
print(f"  TOTAL ASSERTIONS: {PASS_COUNT + FAIL_COUNT}")
if FAIL_COUNT == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print(f"{'='*60}")
sys.exit(0 if FAIL_COUNT == 0 else 1)
