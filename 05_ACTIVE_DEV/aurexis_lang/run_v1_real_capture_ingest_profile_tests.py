#!/usr/bin/env python3
"""
Aurexis Core — Real Capture Ingest Profile Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.real_capture_ingest_profile_bridge_v1 import (
    INGEST_PROFILE_VERSION, INGEST_PROFILE_FROZEN,
    CaptureFileShape, CaptureAssumption, CaptureIngestCase,
    IngestProfile, IngestVerdict, IngestResult,
    validate_capture_file, make_rejected_result,
    V1_INGEST_PROFILE, FROZEN_CASES,
    CASE_PHONE_JPEG, CASE_PHONE_PNG, CASE_WEBCAM_JPEG,
    CASE_VIDEO_FRAME_PNG, CASE_SCANNER_TIFF,
    EXPECTED_CASE_COUNT, EXPECTED_REQUIRED_METADATA_FIELDS,
    EXPECTED_EVIDENCE_TIER_ENTRY, EXPECTED_ASSUMPTION_NAMES,
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
check(INGEST_PROFILE_VERSION == "V1.0", "Version V1.0")
check(INGEST_PROFILE_FROZEN is True, "Module frozen")

# ── 2. Profile singleton ──
section("2. Profile Singleton")
check(V1_INGEST_PROFILE is not None, "V1_INGEST_PROFILE exists")
check(V1_INGEST_PROFILE.frozen is True, "Profile frozen")
check(len(V1_INGEST_PROFILE.cases) == EXPECTED_CASE_COUNT, f"Case count == {EXPECTED_CASE_COUNT}")
check(V1_INGEST_PROFILE.version == "V1.0", "Profile version V1.0")

# ── 3. Frozen cases ──
section("3. Frozen Cases")
check(len(FROZEN_CASES) == 5, "5 frozen cases")
names = [c.name for c in FROZEN_CASES]
check("phone_jpeg" in names, "phone_jpeg case present")
check("phone_png" in names, "phone_png case present")
check("webcam_jpeg" in names, "webcam_jpeg case present")
check("video_frame_png" in names, "video_frame_png case present")
check("scanner_tiff" in names, "scanner_tiff case present")

# ── 4. Case evidence tier entries ──
section("4. Evidence Tier Entries")
for case in FROZEN_CASES:
    check(case.evidence_tier_entry == "real-capture", f"{case.name} enters at real-capture")

# ── 5. Required metadata ──
section("5. Required Metadata")
for case in FROZEN_CASES:
    check("capture_device" in case.required_metadata, f"{case.name} requires capture_device")
    check("capture_timestamp" in case.required_metadata, f"{case.name} requires capture_timestamp")

# ── 6. File shape validation — phone JPEG accept ──
section("6. Phone JPEG Accept")
meta_ok = {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:00:00",
           "adequate_lighting": True, "stable_orientation": True, "subject_in_frame": True}
result = validate_capture_file(".jpg", 5_000_000, 4000, 3000, meta_ok)
check(result.verdict == IngestVerdict.ACCEPTED, "Phone JPEG accepted")
check(result.matched_case_name == "phone_jpeg", "Matched phone_jpeg case")
check(result.evidence_tier_entry == "real-capture", "Evidence tier real-capture")
check(len(result.metadata_missing) == 0, "No missing metadata")

# ── 7. Phone JPEG reject — too small ──
section("7. Phone JPEG Reject — Too Small")
result2 = validate_capture_file(".jpg", 5_000_000, 100, 100, meta_ok)
check(result2.verdict == IngestVerdict.REJECTED_NO_MATCHING_CASE, "Rejected — too small")

# ── 8. Phone JPEG reject — missing metadata ──
section("8. Phone JPEG Reject — Missing Metadata")
meta_bad = {"adequate_lighting": True, "stable_orientation": True, "subject_in_frame": True}
result3 = validate_capture_file(".jpg", 5_000_000, 4000, 3000, meta_bad)
check(result3.verdict == IngestVerdict.REJECTED_MISSING_METADATA, "Rejected — missing metadata")
check("capture_device" in result3.metadata_missing, "capture_device is missing")

# ── 9. Phone JPEG reject — assumption violated ──
section("9. Phone JPEG Reject — Assumption Violated")
meta_no_light = {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:00:00",
                 "adequate_lighting": False, "stable_orientation": True, "subject_in_frame": True}
result4 = validate_capture_file(".jpg", 5_000_000, 4000, 3000, meta_no_light)
check(result4.verdict == IngestVerdict.REJECTED_ASSUMPTION_VIOLATED, "Rejected — assumption violated")

# ── 10. Webcam JPEG accept (low-res, within webcam range only) ──
section("10. Webcam JPEG Accept")
meta_webcam = {"capture_device": "LogitechC920", "capture_timestamp": "2026-04-13T12:05:00",
               "adequate_lighting": True, "stable_orientation": True, "subject_in_frame": True}
# First match by file shape is phone_jpeg (also accepts .jpg at this res)
# This is correct — first-match wins. Verify acceptance regardless of case name.
result5 = validate_capture_file(".jpg", 1_000_000, 1920, 1080, meta_webcam)
check(result5.verdict == IngestVerdict.ACCEPTED, "Webcam JPEG accepted")
check(result5.matched_case_name in ("phone_jpeg", "webcam_jpeg"), "Matched a JPEG case")

# ── 11. Video frame PNG accept ──
section("11. Video Frame PNG Accept")
meta_video = {"capture_device": "S23Ultra", "capture_timestamp": "2026-04-13T12:10:00",
              "source_video": "capture_001.mp4", "frame_index": 42,
              "adequate_lighting": True, "stable_orientation": True, "subject_in_frame": True}
result6 = validate_capture_file(".png", 10_000_000, 1920, 1080, meta_video)
check(result6.verdict == IngestVerdict.ACCEPTED, "Video frame PNG accepted")
# First .png match is phone_png (also accepts this resolution)
check(result6.matched_case_name in ("phone_png", "video_frame_png"), "Matched a PNG case")

# ── 12. Scanner TIFF accept ──
section("12. Scanner TIFF Accept")
meta_scan = {"capture_device": "EpsonV600", "capture_timestamp": "2026-04-13T13:00:00",
             "scan_dpi": 600, "flat_placement": True, "adequate_lighting": True}
result7 = validate_capture_file(".tif", 80_000_000, 3600, 5400, meta_scan)
check(result7.verdict == IngestVerdict.ACCEPTED, "Scanner TIFF accepted")
check(result7.matched_case_name == "scanner_tiff", "Matched scanner_tiff case")

# ── 13. Unknown extension rejected ──
section("13. Unknown Extension Rejected")
result8 = validate_capture_file(".bmp", 5_000_000, 4000, 3000, meta_ok)
check(result8.verdict == IngestVerdict.REJECTED_NO_MATCHING_CASE, "BMP rejected — no case")

# ── 14. Profile hash determinism ──
section("14. Profile Hash Determinism")
h1 = V1_INGEST_PROFILE.profile_hash()
h2 = V1_INGEST_PROFILE.profile_hash()
check(h1 == h2, "Profile hash deterministic")
check(len(h1) == 64, "Profile hash is SHA-256 length")

# ── 15. Profile serialization ──
section("15. Profile Serialization")
d = V1_INGEST_PROFILE.to_dict()
check(d["case_count"] == 5, "to_dict case_count == 5")
check(d["frozen"] is True, "to_dict frozen == True")
j = V1_INGEST_PROFILE.to_json()
check('"case_count": 5' in j, "to_json contains case_count")

# ── 16. make_rejected_result ──
section("16. make_rejected_result")
err = make_rejected_result("test error")
check(err.verdict == IngestVerdict.ERROR, "Error verdict")
check(err.rejection_reason == "test error", "Error reason preserved")

# ── 17. Oversized file rejected ──
section("17. Oversized File Rejected")
result9 = validate_capture_file(".jpg", 500_000_000, 4000, 3000, meta_ok)
check(result9.verdict == IngestVerdict.REJECTED_NO_MATCHING_CASE, "Oversized rejected")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  REAL CAPTURE INGEST PROFILE BRIDGE V1 — STANDALONE RESULTS")
print(f"  PASSED: {PASS_COUNT}  FAILED: {FAIL_COUNT}")
print(f"  TOTAL ASSERTIONS: {PASS_COUNT + FAIL_COUNT}")
if FAIL_COUNT == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print(f"{'='*60}")
sys.exit(0 if FAIL_COUNT == 0 else 1)
