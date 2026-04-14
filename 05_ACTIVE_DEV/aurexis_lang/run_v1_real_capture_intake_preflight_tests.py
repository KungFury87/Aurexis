#!/usr/bin/env python3
"""
Aurexis Core — Real Capture Intake Preflight Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.real_capture_intake_preflight_bridge_v1 import (
    PREFLIGHT_VERSION, PREFLIGHT_FROZEN,
    PreflightVerdict, PreflightCheck, PreflightResult,
    run_preflight, make_error_preflight,
    PREFLIGHT_CHECKS, EXPECTED_CHECK_COUNT,
    EXPECTED_VERDICT_COUNT, EXPECTED_ALLOWED_EXTENSIONS,
    EXPECTED_REQUIRED_SESSION_FIELDS, EXPECTED_REQUIRED_FILE_FIELDS,
    ALLOWED_EXTENSIONS, ALLOWED_DEVICE_CLASSES,
    REQUIRED_SESSION_FIELDS, REQUIRED_FILE_FIELDS,
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


def _valid_manifest():
    return {
        "session_id": "test-session-001",
        "description": "Test capture session",
        "created_at": "2026-04-13T14:30:00",
        "conditions": {
            "adequate_lighting": True,
            "stable_orientation": True,
            "subject_in_frame": True,
        },
        "files": [
            {
                "file_ref": "capture_001.jpg",
                "file_ext": ".jpg",
                "file_size_bytes": 5000000,
                "width_px": 4000,
                "height_px": 3000,
                "capture_device": "Samsung S23 Ultra",
                "capture_timestamp": "2026-04-13T14:30:00",
            },
            {
                "file_ref": "capture_002.png",
                "file_ext": ".png",
                "file_size_bytes": 8000000,
                "width_px": 3840,
                "height_px": 2160,
                "capture_device": "Samsung S23 Ultra",
                "capture_timestamp": "2026-04-13T14:31:00",
            },
        ],
    }


# ── 1. Module version and frozen state ──
section("1. Module Version and Frozen State")
check(PREFLIGHT_VERSION == "V1.0", "Version V1.0")
check(PREFLIGHT_FROZEN is True, "Module frozen")

# ── 2. Check count ──
section("2. Check Count")
check(len(PREFLIGHT_CHECKS) == EXPECTED_CHECK_COUNT, f"Check count == {EXPECTED_CHECK_COUNT}")
check(EXPECTED_VERDICT_COUNT == 4, "4 verdict values")

# ── 3. Allowed values ──
section("3. Allowed Values")
check(len(ALLOWED_EXTENSIONS) == EXPECTED_ALLOWED_EXTENSIONS, f"Allowed extensions == {EXPECTED_ALLOWED_EXTENSIONS}")
check(".jpg" in ALLOWED_EXTENSIONS, ".jpg allowed")
check(".png" in ALLOWED_EXTENSIONS, ".png allowed")
check(".tif" in ALLOWED_EXTENSIONS, ".tif allowed")
check(len(REQUIRED_SESSION_FIELDS) == EXPECTED_REQUIRED_SESSION_FIELDS, f"Required session fields == {EXPECTED_REQUIRED_SESSION_FIELDS}")
check(len(REQUIRED_FILE_FIELDS) == EXPECTED_REQUIRED_FILE_FIELDS, f"Required file fields == {EXPECTED_REQUIRED_FILE_FIELDS}")

# ── 4. Valid manifest passes all checks ──
section("4. Valid Manifest → CLEARED")
result = run_preflight(_valid_manifest())
check(result.verdict == PreflightVerdict.CLEARED, "CLEARED verdict")
check(result.total_checks == EXPECTED_CHECK_COUNT, f"Total checks == {EXPECTED_CHECK_COUNT}")
check(result.passed_checks == EXPECTED_CHECK_COUNT, f"Passed checks == {EXPECTED_CHECK_COUNT}")
check(result.failed_checks == 0, "Failed checks == 0")
check(result.session_id == "test-session-001", "Session ID preserved")
check(result.file_count == 2, "File count == 2")
check(len(result.preflight_hash) == 64, "Preflight hash SHA-256")

# ── 5. Missing session fields ──
section("5. Missing Session Fields → REJECTED")
bad = {"files": [{"file_ref": "x.jpg", "file_ext": ".jpg", "file_size_bytes": 100,
       "width_px": 1000, "height_px": 1000, "capture_device": "d", "capture_timestamp": "t"}]}
r2 = run_preflight(bad)
check(r2.verdict == PreflightVerdict.REJECTED, "REJECTED — missing session fields")

# ── 6. Empty files array ──
section("6. Empty Files Array → REJECTED")
bad2 = dict(_valid_manifest(), files=[])
r3 = run_preflight(bad2)
check(r3.verdict == PreflightVerdict.REJECTED, "REJECTED — empty files")

# ── 7. Missing file fields ──
section("7. Missing File Fields → REJECTED")
bad3 = dict(_valid_manifest(), files=[{"file_ref": "x.jpg"}])
r4 = run_preflight(bad3)
check(r4.verdict == PreflightVerdict.REJECTED, "REJECTED — missing file fields")

# ── 8. Unsupported extension ──
section("8. Unsupported Extension → REJECTED")
bad4 = dict(_valid_manifest())
bad4["files"] = [dict(_valid_manifest()["files"][0], file_ext=".bmp", file_ref="test.bmp")]
r5 = run_preflight(bad4)
check(r5.verdict == PreflightVerdict.REJECTED, "REJECTED — unsupported extension")

# ── 9. Invalid filename (spaces) ──
section("9. Invalid Filename → REJECTED")
bad5 = dict(_valid_manifest())
bad5["files"] = [dict(_valid_manifest()["files"][0], file_ref="my file.jpg")]
r6 = run_preflight(bad5)
check(r6.verdict == PreflightVerdict.REJECTED, "REJECTED — filename with spaces")

# ── 10. Duplicate file refs ──
section("10. Duplicate File Refs → REJECTED")
bad6 = dict(_valid_manifest())
bad6["files"] = [_valid_manifest()["files"][0], _valid_manifest()["files"][0]]
r7 = run_preflight(bad6)
check(r7.verdict == PreflightVerdict.REJECTED, "REJECTED — duplicate file refs")

# ── 11. Zero file size ──
section("11. Zero File Size → REJECTED")
bad7 = dict(_valid_manifest())
bad7["files"] = [dict(_valid_manifest()["files"][0], file_size_bytes=0)]
r8 = run_preflight(bad7)
check(r8.verdict == PreflightVerdict.REJECTED, "REJECTED — zero file size")

# ── 12. Zero resolution ──
section("12. Zero Resolution → REJECTED")
bad8 = dict(_valid_manifest())
bad8["files"] = [dict(_valid_manifest()["files"][0], width_px=0)]
r9 = run_preflight(bad8)
check(r9.verdict == PreflightVerdict.REJECTED, "REJECTED — zero resolution")

# ── 13. Missing conditions ──
section("13. Missing Conditions → REJECTED")
bad9 = dict(_valid_manifest())
del bad9["conditions"]
r10 = run_preflight(bad9)
# Without conditions section, it should warn or reject
check(r10.verdict in (PreflightVerdict.REJECTED, PreflightVerdict.WARNING),
      "Missing conditions → REJECTED or WARNING")

# ── 14. False condition value ──
section("14. Non-Boolean Condition → REJECTED")
bad10 = dict(_valid_manifest())
bad10["conditions"] = {"adequate_lighting": "yes", "subject_in_frame": True}
r11 = run_preflight(bad10)
check(r11.verdict == PreflightVerdict.REJECTED, "REJECTED — non-boolean condition")

# ── 15. Hash determinism ──
section("15. Hash Determinism")
r_a = run_preflight(_valid_manifest())
r_b = run_preflight(_valid_manifest())
check(r_a.preflight_hash == r_b.preflight_hash, "Preflight hash deterministic")

# ── 16. Serialization ──
section("16. Serialization")
d = result.to_dict()
check("verdict" in d, "to_dict has verdict")
check("checks" in d, "to_dict has checks")
j = result.to_json()
check('"CLEARED"' in j, "to_json has CLEARED")

# ── 17. Summary text ──
section("17. Summary Text")
txt = result.to_summary_text()
check("CLEARED" in txt, "Summary contains CLEARED")
check("test-session-001" in txt, "Summary contains session ID")

# ── 18. make_error_preflight ──
section("18. make_error_preflight")
err = make_error_preflight("test error")
check(err.verdict == PreflightVerdict.ERROR, "Error verdict")
check(len(err.checks) == 1, "Error has 1 check")

# ── 19. Scanner TIFF with valid metadata ──
section("19. Scanner TIFF Valid")
scanner_manifest = dict(_valid_manifest())
scanner_manifest["conditions"]["flat_placement"] = True
scanner_manifest["files"] = [{
    "file_ref": "scan_001.tif",
    "file_ext": ".tif",
    "file_size_bytes": 80000000,
    "width_px": 3600,
    "height_px": 5400,
    "capture_device": "Epson V600",
    "capture_timestamp": "2026-04-13T15:00:00",
}]
r12 = run_preflight(scanner_manifest)
check(r12.verdict == PreflightVerdict.CLEARED, "Scanner TIFF cleared")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  REAL CAPTURE INTAKE PREFLIGHT BRIDGE V1 — STANDALONE RESULTS")
print(f"  PASSED: {PASS_COUNT}  FAILED: {FAIL_COUNT}")
print(f"  TOTAL ASSERTIONS: {PASS_COUNT + FAIL_COUNT}")
if FAIL_COUNT == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print(f"{'='*60}")
sys.exit(0 if FAIL_COUNT == 0 else 1)
