# Dry-Run Evidence Report Surface V1

**Date:** April 13, 2026
**Owner:** Vincent Anderson
**Evidence Tier:** AUTHORED — NOT real-capture

---

## What This Report Shows

This document describes what a completed dry-run looks like when authored fixture packs are replayed through the full observed-evidence pipeline. It shows exactly what the user should expect once real captures are later supplied.

---

## Pipeline Stages

The dry-run replay exercises 5 stages in order:

| Stage | Module | What It Does |
|-------|--------|-------------|
| 1. PREFLIGHT | real_capture_intake_preflight_bridge_v1 | Validates session manifest structure (10 frozen checks) |
| 2. INGEST | real_capture_ingest_profile_bridge_v1 | Validates each file against 5 frozen ingest cases |
| 3. MANIFEST | capture_session_manifest_bridge_v1 | Builds deterministic session manifest with SHA-256 hash |
| 4. DELTA | evidence_delta_analysis_bridge_v1 | Compares observed vs expected substrate outputs |
| 5. RECOMMENDATION | calibration_recommendation_bridge_v1 | Generates advisory calibration recommendations |

---

## Authored Fixture Pack V1

The V1 fixture pack contains 6 authored fixtures:

### Valid Fixtures (3) — Exercise Full Pipeline

| Fixture | File Type | Expected Delta | Purpose |
|---------|-----------|---------------|---------|
| valid_phone_jpeg | .jpg (phone) | IDENTICAL | Proves clean phone JPEG passes all 5 stages |
| valid_scanner_tiff | .tif (scanner) | IDENTICAL | Proves clean scanner TIFF passes all 5 stages |
| valid_two_file | .jpg + .png | WITHIN_TOLERANCE | Proves multi-file session with small perturbation |

### Invalid Fixtures (3) — Exercise Rejection Paths

| Fixture | Rejection Point | Reason |
|---------|----------------|--------|
| invalid_missing_fields | PREFLIGHT | Missing session_id and created_at |
| invalid_bad_extension | PREFLIGHT | Unsupported .bmp extension |
| invalid_duplicate_files | PREFLIGHT | Duplicate file_ref values |

---

## What a Successful Dry-Run Looks Like

When all 6 fixtures are replayed:

- **3 valid fixtures** reach ALL_STAGES_PASSED verdict
  - Each completes all 5 stages
  - Preflight: CLEARED
  - Ingest: ALL_ACCEPTED
  - Manifest: VALID with deterministic SHA-256 hash
  - Delta: IDENTICAL or WITHIN_TOLERANCE (as expected)
  - Recommendation: NO_ACTION_NEEDED or ADVISORY_ISSUED

- **3 invalid fixtures** reach EXPECTED_REJECTION verdict
  - Each stops at PREFLIGHT with REJECTED verdict
  - No downstream stages are attempted
  - Rejection reasons are explicit and deterministic

- **Overall summary:**
  - Total: 6 fixtures
  - Passed: 6 (3 full pipeline + 3 expected rejections)
  - Failed: 0
  - Evidence tier: authored
  - Summary hash: deterministic SHA-256

---

## Replay Outcome Contract

The replay outcome contract validates that:

1. Every fixture produces the expected preflight verdict
2. Every valid fixture produces the expected ingest verdict(s)
3. Every valid fixture produces the expected delta verdict
4. Every valid fixture completes all 5 stages
5. Every invalid fixture produces EXPECTED_REJECTION
6. Every replay has a deterministic SHA-256 hash
7. The evidence tier is always "authored"
8. The summary hash is deterministic

Contract verdict: **SATISFIED** when all checks pass.

---

## What Changes When Real Captures Are Supplied

When the user provides actual capture files:

1. **Evidence tier changes:** "authored" → "real-capture"
2. **Delta verdicts may change:** Real captures may produce DEGRADED, MISSING_PRIMITIVES, EXTRA_PRIMITIVES, or MIXED deltas instead of IDENTICAL
3. **Recommendations will differ:** Real-world deltas will trigger specific advisory recommendations (threshold adjustment, capture guidance, extractor profile review)
4. **Manifest hashes will differ:** Real session data produces different deterministic hashes
5. **Pipeline structure stays the same:** The 5-stage pipeline and contract validation remain identical

---

## Critical Distinction

| Property | Authored Dry-Run | Future Real Capture |
|----------|-----------------|---------------------|
| Evidence tier | authored | real-capture |
| File source | Fixture definitions (no actual files) | User-supplied camera photos |
| Substrate outputs | Reference values (hand-defined) | Extracted from actual images |
| Delta meaning | Proves pipeline correctness | Proves real-world accuracy |
| Recommendations | Validate recommendation logic | Actionable calibration advice |

**This dry-run proves the pipeline works. It does NOT prove real-world camera robustness.**

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
