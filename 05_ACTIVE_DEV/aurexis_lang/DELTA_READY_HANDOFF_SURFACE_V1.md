# Delta-Ready Handoff Surface V1

**Purpose:** Shows exactly how a valid user capture pack maps into the observed-evidence pipeline. This is the "what happens after upload" truth surface.

**Version:** V1.0
**Date:** April 13, 2026

---

## End-to-End Pipeline

When you submit a valid capture session pack, the system processes it through these stages:

### Stage 1: Preflight Validation (Bridge 49)

**Input:** Your `session_manifest.json` file
**Module:** `real_capture_intake_preflight_bridge_v1.py`
**What happens:** 10 structural checks validate your manifest:

1. Required session fields present (session_id, description, created_at, files)
2. Session ID is non-empty
3. Files array exists and is non-empty
4. Each file entry has all 7 required fields
5. All file extensions are supported (.jpg, .png, .tif)
6. Filenames follow naming rules (no spaces)
7. No duplicate file references
8. All file sizes are positive
9. All resolutions are positive
10. Required capture conditions are declared

**Output:** `PreflightResult` with verdict CLEARED, REJECTED, WARNING, or ERROR
**If rejected:** You get explicit reasons for each failed check

---

### Stage 2: Ingest Profile Validation (Bridge 45)

**Input:** Each capture file's metadata from your manifest
**Module:** `real_capture_ingest_profile_bridge_v1.py`
**What happens:** Each file is matched against 5 frozen ingest cases:

| Case | Extension | Size Limit | Resolution Range |
|------|-----------|-----------|-----------------|
| phone_jpeg | .jpg | 50 MB | 640x480 to 12000x12000 |
| phone_png | .png | 100 MB | 640x480 to 12000x12000 |
| webcam_jpeg | .jpg | 20 MB | 320x240 to 4096x4096 |
| video_frame_png | .png | 50 MB | 320x240 to 8192x8192 |
| scanner_tiff | .tif | 200 MB | 600x600 to 12000x12000 |

Then required metadata and capture assumptions are checked.

**Output:** `IngestResult` with verdict ACCEPTED or REJECTED_*
**If rejected:** You get the specific rejection reason (no matching case, missing metadata, or assumption violated)

---

### Stage 3: Session Manifest Creation (Bridge 46)

**Input:** All accepted file records
**Module:** `capture_session_manifest_bridge_v1.py`
**What happens:**
- Accepted files are collected into a `CaptureSessionManifest`
- Device tracking, case breakdown, total size computed
- Manifest is finalized with a deterministic SHA-256 hash

**Output:** `SessionSummary` with:
- File count and total bytes
- Unique device list
- Ingest case breakdown
- Deterministic manifest hash

---

### Stage 4: Evidence Delta Analysis (Bridge 47)

**Input:** Observed outputs (from your captures) + Expected outputs (from substrate)
**Module:** `evidence_delta_analysis_bridge_v1.py`
**What happens:**
- Primitive-level comparison: missing, extra, changed (confidence + position)
- Contract-level comparison: pass/fail changes
- Signature-level comparison: match/mismatch changes
- Bounded tolerance checking (default: 0.05 confidence, 5.0px position)

**Output:** `DeltaSurface` with:
- Missing/extra/matched primitive counts
- Max confidence delta and max position delta
- Contract and signature change counts
- Overall verdict: IDENTICAL, WITHIN_TOLERANCE, DEGRADED, MISSING_PRIMITIVES, EXTRA_PRIMITIVES, MIXED, or ERROR

---

### Stage 5: Calibration Recommendations (Bridge 48)

**Input:** DeltaSurface from Stage 4
**Module:** `calibration_recommendation_bridge_v1.py`
**What happens:** 7 recommendation rules fire based on delta patterns:

| Rule | Trigger | Recommendation Kind |
|------|---------|-------------------|
| 1 | Missing primitives | CAPTURE_GUIDANCE |
| 2 | Extra primitives | EXTRACTOR_PROFILE |
| 3 | Large confidence delta | THRESHOLD_ADJUSTMENT |
| 4 | Large position delta | CAPTURE_GUIDANCE |
| 5 | Contract failures | CONTRACT_REVIEW |
| 6 | Signature mismatches | SIGNATURE_REVIEW |
| 7 | Multiple degraded primitives | THRESHOLD_ADJUSTMENT |

**Output:** `RecommendationSurface` with:
- List of advisory recommendations (kind, priority, rationale, suggested action)
- Overall verdict: NO_ACTION_NEEDED, ADVISORY_ISSUED, or CRITICAL_ADVISORY

**Critical:** ALL recommendations are ADVISORY. None auto-execute. None mutate frozen law.

---

## What You Will Receive Back

After processing, you will receive:

1. **Preflight report** — did your pack pass structural validation?
2. **Ingest results** — which files were accepted, which were rejected and why?
3. **Session summary** — manifest hash, device list, case breakdown
4. **Delta analysis** — what changed between expected and observed?
5. **Recommendations** — what could improve your next capture session?

---

## What This Handoff Surface Does NOT Cover

- Automatic correction of capture issues
- Automatic re-extraction or re-processing
- Root-cause analysis of why deltas occurred
- Continuous monitoring or live feedback
- Full real-world robustness claims

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
