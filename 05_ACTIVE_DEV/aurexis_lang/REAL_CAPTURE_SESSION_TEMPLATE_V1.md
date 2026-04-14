# Real Capture Session Template V1

**Purpose:** Human-readable template for preparing a capture session manifest. Fill in the fields below and save as `session_manifest.json` in your capture folder.

**Version:** V1.0
**Date:** April 13, 2026

---

## Template Fields

### Session Header

| Field | Required | Type | Your Value | Description |
|-------|----------|------|------------|-------------|
| `session_id` | YES | string | *(e.g. "session-2026-04-13-001")* | Unique session identifier |
| `description` | YES | string | *(e.g. "Phone captures of printed Aurexis page set A")* | What this session contains |
| `created_at` | YES | string | *(e.g. "2026-04-13T14:30:00")* | When this session was prepared |

### Device Information

| Field | Required | Type | Your Value | Description |
|-------|----------|------|------------|-------------|
| `device_class` | YES | string | *(one of: "phone", "webcam", "scanner", "video")* | What kind of device |
| `device_name` | YES | string | *(e.g. "Samsung S23 Ultra")* | Specific device model |
| `transport_mode` | NO | string | *(one of: "direct_capture", "print_then_capture", "screen_then_capture")* | How the artifact reached the camera |

### Capture Conditions

| Field | Required | Type | Your Value | Description |
|-------|----------|------|------------|-------------|
| `adequate_lighting` | YES | boolean | *(true/false)* | Was the subject well-lit? |
| `stable_orientation` | YES* | boolean | *(true/false)* | Was the capture stable? (*not required for scanner) |
| `subject_in_frame` | YES | boolean | *(true/false)* | Was the full artifact visible? |
| `flat_placement` | scanner only | boolean | *(true/false)* | Was the artifact flat on the scanner bed? |
| `distance_notes` | NO | string | *(e.g. "approximately 30cm from page")* | How far was the camera? |
| `angle_notes` | NO | string | *(e.g. "perpendicular to page, slight tilt")* | Camera angle relative to artifact |
| `lighting_notes` | NO | string | *(e.g. "indirect daylight, no shadows on artifact")* | Lighting description |

### File List

For each capture file, provide:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `file_ref` | YES | string | Filename (e.g. "capture_001.jpg") |
| `file_ext` | YES | string | Extension including dot (e.g. ".jpg") |
| `file_size_bytes` | YES | int | File size in bytes |
| `width_px` | YES | int | Image width in pixels |
| `height_px` | YES | int | Image height in pixels |
| `capture_device` | YES | string | Device name (same as header or per-file) |
| `capture_timestamp` | YES | string | ISO-8601 timestamp |
| `source_video` | video frames only | string | Source video filename |
| `frame_index` | video frames only | int | Frame number in source video |
| `scan_dpi` | scanner only | int | Scan resolution in DPI |

---

## Example Session Manifest

See `REAL_CAPTURE_SESSION_TEMPLATE_V1.json` for a machine-readable template with example values filled in.

---

## How to Use This Template

1. Copy `REAL_CAPTURE_SESSION_TEMPLATE_V1.json` to your capture folder
2. Rename it to `session_manifest.json`
3. Fill in the session header fields
4. Fill in the device information
5. Fill in the capture conditions (be honest about lighting and stability)
6. Add one entry per capture file in the `files` array
7. Run the preflight validator before submitting

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
