# Orientation Normalization Bridge V1 — Gate Verification

**Milestone:** Orientation Normalization Bridge V1
**Scope:** Bounded rotated-artifact recovery for the narrow V1 raster bridge
**Date:** 2026-04-10
**Baseline:** Aurexis Core V1 Substrate Candidate — real narrow law-bearing package, not full Core completion

---

## What This Proves

A canonical V1 raster artifact, rotated by one of the four cardinal angles
(0, 90, 180, 270 degrees) and embedded in a host image, can be localized,
orientation-normalized back to canonical form, and decoded through the
existing raster bridge into the V1 substrate deterministically.

## What This Does NOT Prove

- Arbitrary-angle rotation robustness
- Full perspective correction
- Full camera capture robustness
- General rotation invariance
- Full print/scan round-trip robustness
- Full image-as-program completion
- Full Aurexis Core completion

---

## Gate Checks

### 1. Frozen orientation profile exists
**PASS**
`OrientationProfile` frozen dataclass with:
- `supported_angles`: (0, 90, 180, 270)
- `detection_method`: "exhaustive_trial"
- Host: 800x800, offset bounds 10-380, scale 0.80-1.20
- `min_artifact_pixels`: 200, `extraction_padding`: 5
- `palette_detect_threshold_sq`: 10000

### 2. Deterministic rotated host-image generation exists
**PASS**
`generate_rotated_host_image(RotatedHostSpec)` renders canonical artifact,
rotates by specified angle, optionally scales, blits onto host canvas.
Same `RotatedHostSpec` → identical PNG bytes. Verified by standalone runner
(`host_deterministic` check).

### 3. Orientation recovery / normalization works for in-bounds cases
**PASS**
8 in-bounds cases tested with adjacent_pair fixture across all 4 angles,
varying offsets, scales, and backgrounds. All 8 produce
`OrientationVerdict.NORMALIZED` with correct `detected_angle`.
Additionally tested: containment (4 angles), three_regions (4 angles),
single_region (4 angles, symmetric). All pass.

### 4. Unsupported or out-of-bounds cases fail honestly
**PASS**
4 out-of-bounds cases tested:
- Off-canvas placement (790, 790) → NOT_FOUND
- Extreme miniaturization (0.05 scale) → NOT_FOUND
- Entirely off-canvas (-500, -500) → NOT_FOUND
- Extreme miniaturization at edge (0.08 scale) → NOT_FOUND
All produce honest failure verdicts, not false success.

### 5. New tests run successfully
**PASS**
- Standalone runner: 70/70 assertions passed, 0 failed
- Pytest format: 51 functions collected, 51 passed, 0 failed
- Verified from clean-room extraction of locked zip

### 6. Existing locked baseline package remains intact and runnable
**PASS**
Zip rebuilt with 49 files (20 source + 15 test + 14 runner).
All 14 standalone runners pass from clean-room extraction.
Existing bridge runners (raster, capture tolerance, localization) all pass.

### 7. Existing bridges remain intact
**PASS**
- Raster law bridge: runner passes from clean-room
- Capture tolerance bridge: runner passes from clean-room
- Artifact localization bridge: runner passes from clean-room
No existing source files modified (only __init__.py V1_MODULES list updated).

### 8. Framing stays narrow and honest
**PASS**
Module docstring explicitly states what this proves and what it does not.
Uses: "orientation normalization bridge", "bounded rotated-artifact recovery",
"narrow orientation recovery proof".
Does NOT claim: camera robustness, general rotation invariance, perspective
correction, full Aurexis Core completion.

---

## Orientation Detection Method

**Exhaustive trial with color-spatial signature matching:**
1. Extract artifact region from host via palette-color scanning (reuses localization bridge)
2. Normalize extracted region to 400x400
3. For each candidate angle (0, 90, 180, 270):
   a. Apply inverse rotation to normalized image
   b. Parse with tolerant color-distance parser
   c. Match parsed primitives to spec by palette color
   d. Check pairwise centroid directions match canonical arrangement
4. First angle producing correct primitive count + matching spatial signature = detected orientation
5. If no angle matches → `ORIENTATION_UNKNOWN` (honest failure)

**Why color-spatial signatures:** Absolute bbox comparison fails because
localization crops tightly to palette pixels and normalization introduces
non-proportional scaling. Pairwise centroid direction (left-of, above)
is preserved under this distortion.

**Symmetric artifacts (single region):** All rotations produce matching
signatures, so angle=0 is detected (first tried). This is correct —
orientation is genuinely ambiguous for symmetric artifacts.

---

## Summary

**Gate result: 8/8 PASS**

All gate checks pass. The orientation normalization bridge is a narrow,
honest, bounded proof that cardinal rotations of V1 artifacts can be
detected and corrected deterministically within the frozen profile.
