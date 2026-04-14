# Aurexis Core V2 — Official Screen-Based Capture Protocol

**Status:** LOCKED
**Protocol version:** V2-CAP-PROTO-1.0-LOCK
**Locked on:** 2026-04-14
**Branch:** `working/core-v2`
**Operator:** Vincent (solo)
**Supersedes:** V2-CAP-PROTO-0.1-DRAFT (M1 draft)

This document defines the one and only authorized capture procedure for V2. Any deviation invalidates the capture. The protocol is screen-based, one-phone-first, static-first, solo-feasible, and requires no printing, no multi-device setup, and no third-party involvement.

---

## 1. Exact capture purpose

Produce a reproducible set of real-world camera captures of a fixed on-screen benchmark artifact, taken under a fixed rig and fixed conditions, suitable for ingestion through the Aurexis Core evidence pipeline. The captures support: evidence delta analysis, failure taxonomy construction, evidence-driven calibration, and before/after validation on the identical rig.

The protocol is **not** a data-collection campaign. Each invocation produces exactly one *capture session* bound to one *benchmark artifact* under one *rig configuration*.

## 2. Exact target artifact class for the first real pass

**First-pass target class:** single-image static benchmark artifact displayed full-screen on the capture monitor.

For V2-M3 (the first real capture pilot), the target artifact class is restricted to:
- **Static 2D raster artifact** (no animation, no interactive content, no scrolling)
- Rendered at native display resolution, 1:1 pixel mapping (no browser zoom, no OS scaling change from the declared system default)
- Full-screen, black background padding if the artifact aspect does not match the screen
- One artifact per capture session

Specific artifact *identities* (edge chart, gradient ramp, chroma wedge, fine-detail grid, geometry reference, etc.) are defined in V2-M2 (`V2_BENCHMARK_SET_MANIFEST.json`) and are not in scope for this protocol. The protocol is artifact-agnostic within this class.

## 3. Exact phone role

The phone is the **sole capture device**. Its role is:
- Take still-photo captures of the benchmark artifact on the screen
- Preserve original file format, resolution, and embedded EXIF metadata
- Never transform, compress, crop, filter, or edit the capture in-device beyond the default camera pipeline

**Phone — locked:**
- **Device:** Samsung Galaxy S23 Ultra (one unit, exclusive use for V2)
- **OS:** Android, device-current installed version (the installed version at the session's date is the declared version; record it in the session manifest)
- **Camera app:** Samsung native camera app, Photo mode
- **Lens:** rear main, 1.0x exactly (no ultrawide, no telephoto, no front camera)
- **Zoom:** 1.0x; digital zoom not permitted
- **Photo format:** device-default highest-quality still (Samsung native JPEG); no "RAW + JPEG", no Pro mode overrides
- **HDR:** OFF
- **Flash:** OFF
- **Night mode / low-light mode:** OFF
- **Scene Optimizer / AI enhancements:** OFF where togglable
- **Motion Photo / Single Take / burst / panorama / HDR-stacked:** OFF / not used
- **Video:** not used in V2 first pass
- **Grid / level overlay:** may be enabled for framing only
- **Focus:** tap-to-focus on the artifact's center region, confirm focus lock before shutter
- **Exposure:** tap-to-meter on the artifact's center region, confirm AE lock before shutter

## 4. Exact screen role

The screen is the **sole artifact presenter**. Its role is:
- Display one benchmark artifact at a time at its native resolution
- Hold display parameters constant across the session and across pilot/validation runs

**Screen — locked:**
- **Monitor:** MSI curved monitor, ~23" class (exact model recorded in `session_manifest.json` at session time; treat the unit as fixed for the duration of V2)
- **Panel output:** SDR only (HDR output OFF)
- **OS:** Windows on the capture machine (prior context = Windows 11; verify and record the exact version in the session manifest)
- **OS display scaling:** the system default on the capture machine at V2-M1 lock time (prior context = 125%). Whatever value is set at first pilot session is the locked V2 scaling; do not change it between pilot and validation.
- **Browser / viewer zoom:** 100% / fit-to-native; artifact displayed full-screen with black padding
- **Brightness:** monitor's current default setting, unchanged throughout V2. If the OSD shows a numeric value, record it in the session manifest. Do not auto-adjust between pilot and validation.
- **Night light / blue-light filter / color profile tweaks:** OFF
- **Adaptive brightness:** OFF
- **Screen saver / auto-dim / auto-sleep:** disabled for the session
- **Refresh rate:** monitor's current default, recorded per session
- **Cursor:** moved off-screen or hidden during capture
- **Notifications / overlays:** Focus Assist / Do Not Disturb on; no other windows, toasts, or overlays visible

## 5. Exact room and lighting assumptions

- **Location:** Vincent's primary home desk / home office capture area (one fixed room for all V2 captures).
- **Session window:** a **declared consistent indoor session window** — the same time-of-day bucket and the same lighting state for the pilot (V2-M3) and the validation (V2-M6). Record the window in the session manifest (e.g. `evening-indoor-blinds-closed`, `afternoon-indoor-curtains-drawn`).
- **Window coverings:** the same state across pilot and validation. If blinds are closed for pilot, they are closed for validation. If they are not, they are not.
- **Artificial lighting:** normal home-desk / home-office room lighting as it exists at V2-M1 lock — whatever fixtures Vincent already uses at his desk. Keep the fixture set and settings identical between pilot and validation. Record the fixture configuration in words in the session manifest.
- **Reflective surfaces:** check the area behind and beside the phone for reflective items that would bounce screen light into the capture path. Move or cover them before the session.
- **Other screens:** off or turned away from the capture rig.
- **Operator reflection:** Vincent is not framed in the screen reflection. Prefer dark / non-reflective clothing when reflectivity is visible.
- **Ambient vibration / sound:** not directly capture-relevant for static stills, but avoid bumping the desk during shutter.

## 6. Exact capture sequence (per session)

A capture session targets **one artifact** under **one rig configuration** and produces N captures (default N = 3 per artifact for intra-session repeatability; N is fixed in the session manifest).

Step order:

1. **Pre-session hygiene**
   - Confirm room and lighting per §5
   - Clean the Galaxy S23 Ultra rear main lens with a dry microfiber cloth
   - Clean the MSI screen surface with a dry microfiber cloth (no liquid cleaners)

2. **Screen preparation**
   - Wake the MSI monitor and allow **10–15 minutes** warm-up before any capture is taken
   - Confirm brightness, refresh rate, scaling, and color settings per §4
   - Open the benchmark artifact in the designated viewer, full-screen, 100% zoom, with black padding if needed
   - Move / hide the cursor; enable Do Not Disturb on Windows

3. **Rig placement (handheld baseline for first pass)**
   - **Mount:** handheld is the locked first-pass mode. A fixed stand may be adopted later; until then, handheld is the declared rig.
   - **Handheld stability procedure:**
     - Brace both elbows on the desk or body
     - Two-handed grip on the phone
     - Breathe out, hold breath at shutter release
     - Use the self-timer (see shutter release) so no tap-vibration occurs at the exposure moment
   - **Phone-to-screen distance:** a single baseline distance chosen at the start of the pilot session and **held constant** across every capture in the session and across pilot and validation. The chosen distance is recorded (estimate in inches or centimeters is acceptable for handheld; a tape / ruler pass at the start of the session is strongly preferred).
   - **Orientation:** portrait, unless the artifact's aspect clearly requires landscape; the choice per artifact is recorded and does not change between pilot and validation.
   - **Alignment:** phone's optical axis as close to perpendicular to the screen center as the operator can maintain. Tilt / yaw / pitch deviations are taxonomy items, not rejects.
   - **Framing:** artifact dominates the frame without cropping — roughly 70%–90% of the shorter frame dimension. Do not crop the artifact.

4. **Per-capture loop (N times)**
   - Tap-to-focus at the artifact's center; wait for the focus indicator to stabilize
   - Tap-to-meter / confirm AE lock on the artifact's center
   - Stabilize per the handheld stability procedure above
   - Release shutter via **self-timer with short delay** (2 s or 3 s) as the preferred path; fallback is a careful single tap on the shutter if the self-timer is unavailable for a given shot (record which path was used per capture)
   - Wait for the capture to save before the next iteration
   - If an obvious reflection, motion blur, or framing miss occurred, mark the shot as a re-take candidate and continue; do not delete on-device

5. **Session close**
   - Record session metadata per §7
   - Transfer captures to the working tree per §10
   - Verify file integrity (filesize > 0, opens in viewer, EXIF present) per §12 intake

## 7. Exact metadata required

Each capture session has a `session_manifest.json` with the following fields, populated at session time:

- `session_id` — string, see §8
- `protocol_version` — `V2-CAP-PROTO-1.0-LOCK`
- `benchmark_artifact_id` — references `V2_BENCHMARK_SET_MANIFEST.json`
- `benchmark_artifact_checksum` — SHA-256 of the artifact file
- `capture_count` — integer N
- `device`
  - `make` = `"Samsung"`, `model` = `"Galaxy S23 Ultra"`, `os_name` = `"Android"`, `os_version` (recorded from device at session time), `camera_app` = `"Samsung Camera"`, `lens` = `"rear_main_1x"`, `zoom` = `1.0`, `hdr` = `"off"`, `flash` = `"off"`, `night_mode` = `"off"`, `ai_enhance` = `"off"`, `format` (as written by device, typically `"jpeg"`)
- `screen`
  - `make` = `"MSI"`, `model` (recorded at session time), `panel_class` = `"curved_~23in"`, `native_resolution` (recorded), `refresh_rate_hz` (recorded), `brightness_setting` = `"default_unchanged"` (plus OSD value if visible), `os` = `"Windows"`, `os_version` (recorded), `os_scaling_percent` (recorded; prior context 125), `hdr_output` = `"off"`
- `rig`
  - `mount_type` = `"handheld"` (first pass), `phone_to_screen_distance` (recorded with units), `orientation` (`"portrait"` or `"landscape"`), `framing_fill_range` = `"70-90_percent"`
- `environment`
  - `room_id` = `"home_desk"`, `session_window` (recorded label, e.g. `"evening_indoor_blinds_closed"`), `lighting_profile` (short prose description of fixtures and state), `blackout` (`"yes"` / `"no"`)
- `operator` = `"Vincent"`
- `captured_at` — ISO-8601 local timestamp per capture
- `captures` — list of `{filename, sha256, exif_summary: {shutter, iso, aperture, focal_length, focus_distance, white_balance}, shutter_release: "self_timer_2s" | "self_timer_3s" | "tap"}`
- `notes` — free text, honest observations (reflections caught, re-takes, anomalies)

Metadata is written at session close and not edited after.

## 8. Exact folder and session naming structure

All V2 captures live under:

```
V2_PILOT_RUN/
  raw/
    <session_id>/
      session_manifest.json
      captures/
        <session_id>_cap_<NN>.<ext>
      rejected/                # only if §12 intake rejects any captures
      notes.md
```

Session ID pattern (fixed):

```
V2S-<YYYYMMDD>-<HHMM>-<benchmark_artifact_id>-<rig_profile_id>-<pass_label>
```

Where:
- `YYYYMMDD`, `HHMM` — local clock at session start
- `benchmark_artifact_id` — from the M2 manifest
- `rig_profile_id` — short identifier for the exact rig configuration. First pass locked to `rigHH01` = handheld rig #1 (S23 Ultra, portrait default, chosen baseline distance). A future fixed stand would be `rigST01`, etc.
- `pass_label` — `pilot` for V2-M3, `validation` for V2-M6, `expansion-<n>` for V2-M7 earned expansions

Example:

```
V2S-20260420-2030-edge-chart-rigHH01-pilot
```

Capture file naming (fixed):

```
<session_id>_cap_<NN>.<ext>
```

NN is zero-padded two digits starting at 01. Re-takes append a letter (`01b`, `01c`) and are kept alongside the originals; the manifest records which capture supersedes which.

## 9. Exact file format expectations

- Format: device-native highest-quality still as written by the S23 Ultra's native camera (JPEG unless Samsung's default changes on this device; record whatever is written). No transcoding. No re-encoding. No "save as".
- EXIF: preserved in full. Any transfer path that strips or rewrites EXIF is forbidden.
- Resolution: native sensor output at 1.0x zoom. No downscaling.
- Color space: as written by the device. Recorded in manifest.
- Checksums: SHA-256 computed on arrival in `V2_PILOT_RUN/raw/<session_id>/captures/` and recorded in `session_manifest.json`.
- Filesize: > 0; corrupt files fail §12 intake.

## 10. Exact upload expectations for later review

- **Preferred transfer:** USB cable from the S23 Ultra to the Windows workstation, MTP / direct file copy, preserving original files and EXIF.
- **Acceptable alternatives:** any direct transfer path that preserves originals and EXIF (e.g. Samsung's direct Windows link, a local-network SMB / SFTP transfer, or similar). The path used is recorded in `notes.md`.
- **Forbidden transfer paths:** messaging apps, cloud photo sync paths with "optimize storage" or "compress uploads" enabled, or any path that re-encodes / strips EXIF.
- **Upload destination:** `V2_PILOT_RUN/raw/<session_id>/captures/` exactly. No staging under `Downloads` / `Desktop` / temp folders that are later moved (moves alter timestamps).
- **Post-transfer verification:** run the §12 intake check before closing the session.
- **No GitHub push of raw captures** without Vincent's explicit instruction. `V2_PILOT_RUN` contents stay local unless he authorizes.

## 11. Exact first-pass exclusions

For the V2-M3 pilot run under this protocol, the following are explicitly excluded and must not appear:

- Print-based captures, physical calibration boards, paper targets
- Video, Motion Photo, Single Take, burst, HDR-stacked, panorama, night-mode captures
- Captures from front camera, ultrawide, or telephoto lenses
- Captures at zoom ≠ 1.0x
- Captures with flash or torch
- Supplemental artificial lighting beyond §5's declared home-desk / home-office setup
- Captures with notifications, cursors, taskbars, or any non-artifact pixels visible on screen
- Captures taken outside the declared session window
- Multi-device captures (second phone, DSLR, webcam, etc.)
- Third-party camera apps or Pro mode overrides whose settings are not recorded
- Any image that has been edited, cropped, rotated, or re-saved after capture
- Any E/D-track activity
- Any cloud-sync path that strips EXIF or recompresses
- Mid-session changes to distance, orientation, brightness, scaling, or lighting (any such change ends the session and starts a new one with a new session_id)

## 12. Exact intake criteria — usable vs. unusable

A capture is **usable** if and only if all of the following hold:

1. File exists in `V2_PILOT_RUN/raw/<session_id>/captures/` with correct name
2. Filesize > 0 and opens in a standard viewer
3. EXIF present and includes shutter, ISO, aperture (if supported), focal length, white balance
4. `session_manifest.json` references it and its SHA-256 matches the recorded checksum
5. Artifact fills roughly 70%–90% of the shorter frame dimension (operator judgment; gross miss-framings are rejects)
6. Artifact is in focus globally (no whole-image blur; localized sharpness variations are taxonomy items, not intake rejects)
7. No operator / room / reflection artifacts obscuring the benchmark region
8. No notification, cursor, or non-artifact overlay pixels visible
9. Exposure lock and focus lock were confirmed pre-shutter (noted in `notes.md`)
10. Protocol version on the manifest matches the currently locked protocol (`V2-CAP-PROTO-1.0-LOCK`)

A capture is **unusable** if any of the above fails. Unusable captures are **not deleted**; they are moved to `V2_PILOT_RUN/raw/<session_id>/rejected/` with a `rejection_reason.txt` per file. The session continues with re-takes until N usable captures are recorded.

A **session passes** intake if it produced ≥ N usable captures for its artifact. A session **fails** intake otherwise and is either re-run (same session_id with `-retry<k>` suffix) or abandoned with a written rationale in `notes.md`.

---

## Appendix A — Locked parameter summary (fast reference)

| Parameter | Value |
|---|---|
| Phone | Samsung Galaxy S23 Ultra, rear main 1.0x, Samsung native camera app, Photo mode |
| Phone format | Device-default high-quality still (JPEG unless device writes otherwise) |
| HDR | OFF |
| Flash / Night / Scene Optimizer | OFF |
| Monitor | MSI curved ~23" class (exact model recorded per session) |
| Monitor brightness | Current default, unchanged for all V2 |
| Monitor HDR | OFF |
| OS | Windows on capture workstation (version recorded per session; prior context = Win 11) |
| OS display scaling | System default at lock time (prior context = 125%); unchanged for all V2 |
| Room | Vincent's home desk / home office |
| Session window | Declared consistent indoor window, identical between pilot and validation |
| Lighting | Normal home-desk / home-office fixtures, identical between pilot and validation |
| Mount | Handheld (first pass); `rigHH01` |
| Phone-to-screen distance | Chosen baseline at pilot start, held constant (recorded) |
| Orientation | Portrait default (landscape only when artifact requires it) |
| Framing fill | 70%–90% of shorter frame dimension |
| Monitor warm-up | 10–15 minutes before first capture |
| Shutter release | Self-timer 2 s or 3 s (preferred); tap shutter as fallback, recorded per capture |
| Transfer path | USB (preferred) or any EXIF-preserving direct path; recorded per session |
| Captures per session (N) | Default 3, fixed in the session manifest |

## Appendix B — Known first-pass risks to watch in V2-M4 taxonomy

These are not protocol failures; they are expected observations the failure taxonomy will classify:

- Handheld micro-motion blur (distinct from focus miss)
- Handheld framing drift between captures within a session
- Handheld distance drift between pilot and validation
- Non-perpendicular optical axis (keystone / perspective distortion)
- Screen reflections of operator, desk objects, or room lights
- Curved-monitor geometry: the MSI panel is curved, so off-axis pixels are physically closer/further than on-axis pixels relative to the phone; this is a known capture geometry factor
- Native camera post-processing (Samsung pipeline sharpening / denoise)
- OS scaling interaction with native-resolution artifact rendering
- Moire / aliasing between panel pixel grid and phone sensor grid
- Auto white balance drift across captures
- Auto ISO / shutter selection variance under identical lighting
