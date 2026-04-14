# Real Capture Intake Pack V1

**Purpose:** Defines exactly what files the user should provide, allowed formats, required metadata, and naming rules for submitting real capture evidence to the Aurexis Core V1 substrate.

**Version:** V1.0
**Date:** April 13, 2026
**Status:** FROZEN — this is the accepted intake specification

---

## What You Need to Provide

A real capture intake pack is a folder containing:

1. **One or more capture image files** in a supported format
2. **One session manifest JSON file** describing the capture session
3. **Optional: device metadata** (EXIF data in image files is acceptable)

---

## Supported Capture File Formats

| Case Name | Extension | Max File Size | Min Resolution | Max Resolution |
|-----------|-----------|---------------|----------------|----------------|
| phone_jpeg | `.jpg` | 50 MB | 640x480 | 12000x12000 |
| phone_png | `.png` | 100 MB | 640x480 | 12000x12000 |
| webcam_jpeg | `.jpg` | 20 MB | 320x240 | 4096x4096 |
| video_frame_png | `.png` | 50 MB | 320x240 | 8192x8192 |
| scanner_tiff | `.tif` | 200 MB | 600x600 | 12000x12000 |

Files outside these bounds will be rejected by the ingest profile validator.

---

## Required Metadata (Per File)

Every capture file MUST have these metadata fields in the session manifest:

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `capture_device` | string | `"Samsung S23 Ultra"` | Device that produced the capture |
| `capture_timestamp` | string | `"2026-04-13T14:30:00"` | ISO-8601 timestamp of when the capture was taken |

---

## Additional Required Metadata (By Case)

| Case | Additional Required Fields |
|------|---------------------------|
| phone_jpeg | *(none beyond base)* |
| phone_png | *(none beyond base)* |
| webcam_jpeg | *(none beyond base)* |
| video_frame_png | `source_video`, `frame_index` |
| scanner_tiff | `scan_dpi` |

---

## Optional Metadata (Improves Calibration)

| Field | Type | Example | Used By |
|-------|------|---------|---------|
| `focal_length_mm` | float | `26.0` | Hardware calibration |
| `sensor_noise_level` | float | `0.08` | Hardware calibration |
| `lens_distortion` | float | `0.05` | Hardware calibration |
| `capture_distance_m` | float | `0.5` | Hardware calibration |
| `resolution_megapixels` | float | `12.0` | Hardware calibration |
| `gps_lat` | float | `37.7749` | Location reference |
| `gps_lon` | float | `-122.4194` | Location reference |
| `video_fps` | float | `30.0` | Video frame context |
| `video_codec` | string | `"h264"` | Video frame context |
| `color_depth` | int | `24` | Scanner context |

---

## Capture Assumptions (Must Be True)

The following assumptions must hold for your captures. If any required assumption is violated, the capture will be rejected.

| Assumption | Required For | Description |
|------------|-------------|-------------|
| `adequate_lighting` | All cases | Subject must be well-lit (no deep shadows or extreme backlight) |
| `stable_orientation` | phone_jpeg, phone_png, video_frame_png | No excessive motion blur (handheld OK, mid-swing not) |
| `subject_in_frame` | All cases | The target Aurexis artifact/page must be fully visible in the frame |
| `flat_placement` | scanner_tiff | Artifact must be flat on scanner bed without wrinkles or folds |

In the session manifest, indicate each assumption with `true` if satisfied.

---

## Folder Structure

```
my_capture_session/
  session_manifest.json        ← required (see template)
  capture_001.jpg              ← capture file
  capture_002.jpg              ← capture file
  capture_003.png              ← capture file (different format OK)
```

---

## File Naming Rules

1. File names must not contain spaces (use underscores)
2. Extensions must be lowercase (`.jpg` not `.JPG`)
3. Each file must have a unique name within the session folder
4. The session manifest must be named `session_manifest.json`

---

## What Happens After Submission

Your intake pack will be processed through the following pipeline:

1. **Preflight Check** — validates folder structure, file formats, metadata presence
2. **Ingest Profile Validation** — each file checked against the 5 frozen cases
3. **Session Manifest Creation** — accepted files manifested with deterministic hash
4. **Evidence Delta Analysis** — observed outputs compared against expected substrate outputs
5. **Calibration Recommendations** — advisory suggestions generated (none auto-execute)

---

## What This Intake Pack Does NOT Cover

- Video files (only extracted frames in PNG format are supported)
- RAW camera formats (convert to JPEG or PNG first)
- Multi-page documents (submit individual page captures)
- Files larger than the case limits above
- Captures where the Aurexis artifact is not fully visible

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
