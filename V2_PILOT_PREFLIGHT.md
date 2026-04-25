# V2-M3 First Real Capture Pilot — Preflight

**Status:** LOCKED (preflight only; real captures not yet taken)
**Pilot code:** `P1` (Pilot-1)
**Locked on:** 2026-04-14
**Branch:** `working/core-v2`
**Operator:** Vincent (solo)

This is the preflight a single operator runs **before** executing the first real pilot. It verifies everything that must be true for the pilot to be valid, pins the pilot-start metadata that only exists at runtime, and gates entry to the runbook (`V2_PILOT_RUNBOOK.md`).

Do not skip steps. Do not start the runbook until every check here is satisfied or consciously deferred per the explicit deferral rules.

---

## 1. Pre-existing locks that must be present

Before preflight begins, confirm the tree already has:

- [ ] `V2_CAPTURE_PROTOCOL.md` at `V2-CAP-PROTO-1.0-LOCK`
- [ ] `V2_CAPTURE_CHECKLIST.md` present
- [ ] `V2_BENCHMARK_SET/V2_BENCHMARK_SET_MANIFEST.json` — `set_id = V2-BENCH-B1`, `set_version = 1.0.0`, resolution `[1920, 1080]`
- [ ] `V2_BENCHMARK_SET/assets/` contains all five PNGs: `b1-clean-solid`, `b1-edge-half`, `b1-grid-64`, `b1-gradient-h`, `b1-corners-fiducials`
- [ ] `V2_SESSION_MANIFEST_TEMPLATE.json` present
- [ ] Working branch is `working/core-v2`

If any is missing, **stop** — preflight fails, fix missing pieces before continuing.

## 2. Benchmark set verification

From the V2 working folder root:

```powershell
python 05_ACTIVE_DEV\aurexis_lang\run_v2_benchmark_verify.py
```

Expected output:

```
rendered 5 B1 artifacts under <...>\V2_BENCHMARK_SET\
OK: V2 benchmark set verified (manifest, checksums, bytes)
```

If any `FAIL:` line prints, **stop** — the set is not coherent and must be re-locked before any pilot captures.

## 3. Capture target monitor declaration

The workstation has two MSI G27C4X units attached. Pick one for the pilot.

- [ ] Open Windows **Settings → System → Display**. Both monitors are listed as "Display 1" and "Display 2."
- [ ] Decide which is the **capture target** for P1 (and for every subsequent V2 session until an expansion amendment changes it). Record:
  - `capture_target_monitor_id` (e.g. `"Display 1"`)
  - port if known (e.g. `"DP-1"`, `"HDMI-1"`)
- [ ] Put the **secondary monitor** into its capture-window state. One of:
  - **powered off** (recommended for first pilot — simplest), OR
  - **physically rotated** so it is not visible from the phone's optical axis and cannot bounce light at the capture target screen or the phone.
- [ ] Record `secondary_monitor_state` = `"off"` or `"rotated_away"`.

## 4. Native resolution pre-flight (critical branch)

The benchmark set is locked at **1920 × 1080**. Before the pilot runs, confirm the capture target monitor's native resolution.

- [ ] Settings → System → Display → (capture target selected) → **Display resolution**. Note the value Windows reports as "Recommended."
- [ ] In the MSI OSD on the capture target monitor, note the resolution displayed in the OSD banner when the monitor wakes.

**Branch:**

- If native is **1920 × 1080**: good — proceed.
- If native is **any other resolution** (e.g. 2560 × 1440, 2560 × 1080, 1920 × 1200, etc.): **stop the pilot.** The B1 manifest must be re-rendered at the actual native resolution and `set_version` bumped to `1.1.0` before captures begin. Procedure:
  1. Edit `DEFAULT_WIDTH` / `DEFAULT_HEIGHT` in `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_benchmark/__init__.py`, or pass `--width` / `--height` to the CLI.
  2. Bump `SET_VERSION` in the same file to `"1.1.0"`.
  3. Re-run `run_v2_benchmark_verify.py`.
  4. Commit.
  5. Resume preflight from step 1.

Record the verified native resolution in the preflight log regardless.

## 5. Display scaling verification

Windows 11 supports per-monitor DPI scaling. The scaling value for the **capture target monitor** is the one that matters.

- [ ] Settings → System → Display → (capture target selected) → **Scale** → note the percentage.
- [ ] Prior context value is **125%**. If the value is 125%, confirm and proceed.
- [ ] If the value is different, record it; it becomes the V2-frozen scaling for the remainder of V2. Do not change it between pilot and validation.
- [ ] Record `os_scaling_percent` as an integer (e.g. `125`).

## 6. Host OS / device metadata capture

These four values only exist at runtime and are pinned into the first session manifest.

- [ ] **Windows 11 build**: Start → type `winver` → Enter. Record the full line, e.g. `"Windows 11 Version 24H2 (OS Build 26100.2894)"`.
- [ ] **Samsung Android OS version**: on the S23 Ultra: Settings → About phone → Software information → Android version + One UI version. Record both, e.g. `{"android": "14", "one_ui": "6.1"}`.
- [ ] **MSI G27C4X refresh rate on the capture target monitor**: Settings → System → Display → Advanced display → (capture target) → **Choose a refresh rate**. Record the value (e.g. `180 Hz`).
- [ ] **MSI G27C4X panel class / native**: confirmed via §4.

## 7. Rig state verification

- [ ] Rig profile: `rigHH01` (handheld, S23 Ultra).
- [ ] Phone-to-screen distance: pick one baseline and measure with a tape or ruler **once**. Record it (e.g. `"400 mm"` or `"16 in"`). This distance is held constant across all five P1 sessions and across V2-M6 validation.
- [ ] Phone orientation: **portrait** unless you've already decided an artifact needs landscape. For B1, portrait works for all five.
- [ ] Framing target: artifact fills 70 %–90 % of the shorter frame dimension, full artifact visible, no crop.

## 8. Environmental state verification

- [ ] Room: Vincent's home desk / home office (confirmed)
- [ ] Session window label: declared and recorded (e.g. `"evening_indoor_blinds_closed"` or `"afternoon_indoor_curtains_drawn"`). This **exact label** will be reused for the V2-M6 validation run; if you cannot commit to reproducing this window later, pick a more reproducible one now.
- [ ] Window coverings in their declared state
- [ ] Lighting fixtures in their declared set and settings; no extras, no absences
- [ ] Other screens in the room off or turned away from the capture rig
- [ ] Reflective items behind / beside the phone moved or covered
- [ ] Dark / non-reflective clothing if operator reflection has been observed

## 9. Phone / camera app verification

- [ ] Samsung native **Camera** app in **Photo mode**
- [ ] Rear main lens, **1.0x exactly**
- [ ] **HDR off**, **flash off**, **night mode off**, **Scene Optimizer off**, **Motion Photo off**, **Single Take off**, burst/panorama/HDR-stacked off
- [ ] Grid / level overlay optional (framing only)
- [ ] Phone **Do Not Disturb ON** for the session window
- [ ] Phone charged enough for the whole pilot window
- [ ] Phone lens cleaned with dry microfiber

## 10. Host-side preparation

- [ ] Windows **Focus Assist / Do Not Disturb ON** on the capture target monitor
- [ ] Cursor parked on the secondary (tooling) monitor
- [ ] Taskbar auto-hidden or covered on the capture target
- [ ] Capture target monitor: night light off, adaptive brightness off, HDR output off, color profile tweaks off, screen saver / auto-dim / auto-sleep disabled for the session window
- [ ] Capture target monitor brightness at V2-locked default (unchanged from normal state)
- [ ] Capture target monitor has been **awake for 10–15 minutes** before the first shutter release
- [ ] **Viewer for P1: Windows Photos, full-screen view.** (Browser F11 remains legal per protocol but P1 standardizes on Photos to reduce variables.)

## 11. Disk layout preparation

- [ ] `V2_PILOT_RUN/` does not yet exist, OR is empty of P1 content.
- [ ] Plan the five session IDs (actual `HHMM` set at session start; placeholders here):

```
V2S-<YYYYMMDD>-<HHMM1>-b1-clean-solid-rigHH01-pilot
V2S-<YYYYMMDD>-<HHMM2>-b1-edge-half-rigHH01-pilot
V2S-<YYYYMMDD>-<HHMM3>-b1-grid-64-rigHH01-pilot
V2S-<YYYYMMDD>-<HHMM4>-b1-gradient-h-rigHH01-pilot
V2S-<YYYYMMDD>-<HHMM5>-b1-corners-fiducials-rigHH01-pilot
```

- [ ] USB cable available; plan to transfer via File Explorer Copy/Paste from the phone's `DCIM\Camera` (no Windows Import).

## 12. Preflight-close check

If every box above is either ticked or consciously deferred to pilot-start per the protocol (Windows build, Android version, refresh rate, scaling %, native resolution), preflight is **passed**. Proceed to `V2_PILOT_RUNBOOK.md`.

If any required check is unmet, preflight fails — fix the condition before running the pilot.

---

## Appendix — Pilot-start metadata, the definitive list

These are the fields that only exist at pilot start and must be written into the **first** session manifest (P1-S01, `b1-clean-solid`). Subsequent P1 sessions copy the same device/screen/environment fields verbatim.

| Field (JSON path) | Source |
|---|---|
| `device.os_version` | S23 Ultra Settings → About phone → Android version |
| `screen.model` | MSI OSD confirms `G27C4X` |
| `screen.native_resolution` | Windows Display → Recommended / MSI OSD |
| `screen.refresh_rate_hz` | Windows Display → Advanced display → Refresh rate |
| `screen.os_scaling_percent` | Windows Display → Scale (capture target selected) |
| `screen.os_version` | `winver` output |
| `screen.brightness_osd_value` | MSI OSD brightness, if visible |
| `screen.capture_target_monitor_id` | "Display 1" or "Display 2" |
| `rig.phone_to_screen_distance` | Tape / ruler measurement at session start |
| `environment.session_window` | Declared label reused for validation |
| `environment.lighting_profile` | Prose describing fixtures + states |
