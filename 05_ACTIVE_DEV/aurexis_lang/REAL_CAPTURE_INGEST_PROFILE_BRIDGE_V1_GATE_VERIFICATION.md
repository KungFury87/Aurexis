# Real Capture Ingest Profile Bridge V1 — Gate Verification

**Bridge:** 45th (Observed Evidence Loop Branch — 1 of 4)
**Module:** `real_capture_ingest_profile_bridge_v1.py`
**Date:** 2026-04-13
**Scope:** Bounded ingest profile for real-capture files

## Gate Checks

| # | Check | Result |
|---|-------|--------|
| 1 | Module version V1.0 | PASS |
| 2 | Module frozen = True | PASS |
| 3 | V1_INGEST_PROFILE singleton exists | PASS |
| 4 | 5 frozen ingest cases defined | PASS |
| 5 | All cases enter at evidence tier real-capture | PASS |
| 6 | All cases require capture_device metadata | PASS |
| 7 | All cases require capture_timestamp metadata | PASS |
| 8 | Phone JPEG accepted with valid metadata | PASS |
| 9 | Too-small resolution rejected | PASS |
| 10 | Missing metadata rejected | PASS |
| 11 | Assumption violation rejected | PASS |
| 12 | Unknown extension rejected | PASS |
| 13 | Oversized file rejected | PASS |
| 14 | Profile hash deterministic | PASS |
| 15 | Serialization (to_dict/to_json) correct | PASS |
| 16 | Scanner TIFF case accepted | PASS |
| 17 | Video frame PNG case accepted | PASS |

**Result: 17/17 PASS**

## Standalone Runner
- File: `run_v1_real_capture_ingest_profile_tests.py`
- Assertions: 50
- Status: ALL PASS

## pytest Suite
- File: `tests/test_real_capture_ingest_profile_bridge_v1.py`
- Functions: 22 (5 parametrized × 5 cases = 25 sub-tests + 17 standalone)

## What This Proves
A bounded frozen family of 5 supported real-capture ingest cases exists.
Each case defines allowed file shapes, required metadata, and capture
assumptions. Files are validated deterministically before admission.

## What This Does NOT Prove
- Arbitrary media ingestion
- Full camera driver support
- Full real-world robustness
- Full Aurexis Core completion
