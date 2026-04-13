# Observed Evidence Loop — Branch Capstone V1

**Branch:** Observed Evidence Loop / Real Capture Calibration
**Bridges:** 45–48 (4 milestones)
**Date:** 2026-04-13
**Status:** COMPLETE-ENOUGH as a bounded real-capture calibration loop

## Branch Overview

This branch adds the structured observed-evidence loop to the V1 substrate
candidate. It defines how real captures enter the system, how they are
manifested as sessions, how their outputs are compared against expected
substrate outputs, and how bounded advisory recommendations are generated.

## Milestones

| Bridge | Name | Module | Assertions | Gate |
|--------|------|--------|------------|------|
| 45 | Real Capture Ingest Profile | `real_capture_ingest_profile_bridge_v1.py` | 50 | 17/17 PASS |
| 46 | Capture Session Manifest | `capture_session_manifest_bridge_v1.py` | 42 | 15/15 PASS |
| 47 | Evidence Delta Analysis | `evidence_delta_analysis_bridge_v1.py` | 40 | 16/16 PASS |
| 48 | Calibration Recommendation | `calibration_recommendation_bridge_v1.py` | 33 | 17/17 PASS |

**Total: 4 bridges, 165 standalone assertions, 4 runners, ALL PASS**

## Data Flow

```
Real Capture File
    │
    ▼
[Ingest Profile Bridge 45]
    │ validate file shape, metadata, assumptions
    │ → IngestVerdict: ACCEPTED or REJECTED_*
    ▼
[Session Manifest Bridge 46]
    │ collect accepted files into session
    │ → deterministic manifest with hash
    ▼
[Delta Analysis Bridge 47]
    │ compare observed vs expected outputs
    │ → DeltaSurface with missing/extra/changed
    ▼
[Calibration Recommendation Bridge 48]
    │ convert deltas to advisory recommendations
    │ → threshold adjustment, capture guidance, etc.
    │ ALL ADVISORY — none auto-execute
```

## Solved Surfaces

1. **Ingest admission:** 5 frozen cases (phone JPEG, phone PNG, webcam JPEG,
   video frame PNG, scanner TIFF) with explicit file shape, metadata, and
   assumption constraints.

2. **Session manifesting:** Deterministic session manifests with SHA-256 hash,
   file records, device tracking, case breakdown.

3. **Delta analysis:** Structured comparison producing missing/extra/changed
   primitive deltas, contract deltas, signature deltas, with bounded
   tolerances.

4. **Advisory recommendations:** 7 recommendation rules producing 5 kinds
   of advisory outputs (threshold adjustment, extractor profile, capture
   guidance, contract review, signature review) at 4 priority levels.

## Unsolved Surfaces — Honest Gaps

1. **No real capture files processed yet.** The loop infrastructure exists
   but no actual user-supplied captures have been run through it. This
   requires real capture datasets from the user.

2. **No automatic execution of recommendations.** All recommendations are
   advisory. The user or a future session must decide whether to act on them.

3. **No root-cause analysis.** Delta analysis shows what changed, not why.

4. **No continuous monitoring.** This is a one-shot analysis loop, not a
   persistent monitoring system.

5. **First-match case selection.** The ingest profile returns the first
   matching case by file shape. Overlapping cases (e.g. phone JPEG and
   webcam JPEG both accept .jpg) resolve to the first match.

## Real Stop Condition

This branch is COMPLETE-ENOUGH as a bounded real-capture calibration loop.
The next step that would advance this branch is:

**User-supplied real capture datasets.**

Until the user provides actual capture files, the loop infrastructure is
proven but not exercised against real data. That is an honest boundary,
not a missing feature.

## What This Branch Proves

The V1 substrate candidate now has a structured path from real capture
file → validated ingest → session manifest → delta analysis → advisory
calibration recommendation. Every step is deterministic, bounded, and
tested.

## What This Branch Does NOT Prove

- Full real-world robustness
- Automatic self-improvement
- Automatic law mutation
- Full image-as-program completion
- Full Aurexis Core completion

## Branch Integrity

- All 4 bridges frozen (V1.0)
- All 4 standalone runners pass (165 assertions)
- All 4 gate verifications pass (65/65 checks)
- All modules importable
- All existing branches remain intact
- No existing tests broken
