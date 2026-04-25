# V2-M1 Paper Dry-Run Walkthrough

**Date:** 2026-04-14
**Purpose:** Close G1 by walking `V2_CAPTURE_PROTOCOL.md` (V2-CAP-PROTO-1.0-LOCK) and `V2_CAPTURE_CHECKLIST.md` end-to-end on paper, against the locked setup, against a hypothetical benchmark artifact, without taking any real captures.
**Operator:** Vincent (solo)
**Result:** G1 closed.

This is a **paper** dry-run. No phone was used. No captures were produced. The purpose is to prove the protocol + checklist are executable as written.

---

## Simulated session target

- Session ID (fictitious): `V2S-20260420-2030-dryrun-rigHH01-pilot`
- Benchmark artifact (hypothetical): placeholder; M2 has not produced the benchmark set yet
- Rig profile: `rigHH01` (handheld, S23 Ultra, MSI G27C4X capture target monitor)

## Walkthrough

### A. Pre-session

- Room is Vincent's home desk / home office. ✓ single fixed room — protocol §5.
- Session window chosen: `evening_indoor_blinds_closed`. Any declared window works; the constraint is identity between pilot and validation.
- Window coverings, lighting, other screens, reflective items, operator clothing — every item has a matching checklist bullet (§A of `V2_CAPTURE_CHECKLIST.md`) and a protocol clause (§5 of `V2_CAPTURE_PROTOCOL.md`). No ambiguity.
- Lens + screen cleaning: dry microfiber. Unambiguous.

### B. Screen preparation

- Two MSI G27C4X units are attached. Vincent declares Display 1 as the capture target in this walkthrough, and records `capture_target_monitor_id = "Display 1"` in the session manifest.
- Secondary monitor (Display 2) is powered off for the capture window. This is one of two explicitly allowed states (off, or rotated away).
- Warm-up: 10–15 minutes before first capture. Concrete interval, no ambiguity.
- Brightness / refresh / scaling / HDR / night light / adaptive brightness / screen saver — each has a concrete directive in §4 and a matching checklist bullet.
- Display scaling: verified at Settings → System → Display → Scale on the capture target monitor. Prior context is 125%. Verification at pilot start captures the exact value into `os_scaling_percent` in the session manifest; from that moment on, V2 is locked to that value.
- Viewer: Windows Photos full-screen OR browser F11 on `file:///`. Either is executable as written.
- Cursor parked on the secondary (tooling) monitor. Taskbar auto-hide on the capture target.

### C. Phone preparation (Galaxy S23 Ultra)

- Samsung native Camera app, Photo mode, rear main 1.0x, HDR off, flash off, night mode off, Scene Optimizer off, Motion Photo off. All of these are settings the operator can reach through the Samsung Camera app's gear icon → Camera settings.
- Do Not Disturb on the phone during the session. Stock Android / One UI feature.

No protocol clause assumes third-party apps or a non-default camera pipeline. Executable solo.

### D. Rig placement

- Handheld, declared as `rigHH01`. First-pass mode is explicitly handheld (§6).
- Phone-to-screen distance: measured once with a tape or ruler at session start, recorded in `phone_to_screen_distance`, held constant. The checklist calls this out. The expected variance introduced by handheld is already acknowledged in Appendix B of the protocol as a failure-class to observe, not a protocol failure.
- Orientation: portrait default. One directive, no ambiguity.
- Framing: 70%–90% of the shorter frame dimension. Operator judgment within a range is explicitly allowed; gross miss-framings are rejects.
- Stability procedure: braced elbows, two-handed grip, breath control, self-timer shutter. All physical, solo-achievable.

### E. Per-capture loop

Walking through one iteration:

1. Tap-to-focus on the artifact's center — standard Samsung Camera behavior.
2. Tap-to-meter / AE lock — standard Samsung Camera behavior.
3. Stabilize per §D.
4. Shutter via self-timer 2 s or 3 s. Samsung Camera → settings → Timer. Concrete, executable.
5. Wait for save. Samsung saves in ~1 s.
6. Observed issue → mark in `notes.md` as re-take candidate. No on-device deletion (§11 forbids it, §12 re-take procedure keeps originals).

The loop repeats N times (default N = 3).

### F. Session close

1. USB cable, unlock phone, File Explorer → DCIM/Camera. Copy (not "Import") session's captures to `V2_PILOT_RUN/raw/<session_id>/captures/`. EXIF preserved. Protocol §10 explicitly forbids Windows' "Import pictures and videos" path.
2. PowerShell `Get-FileHash -Algorithm SHA256` one-liner produces the SHA-256 values for each file.
3. Copy `V2_SESSION_MANIFEST_TEMPLATE.json` to `V2_PILOT_RUN/raw/<session_id>/session_manifest.json`, delete the `_template_note` key, fill in every field, paste hashes into `captures[].sha256`.
4. §12 intake check is ten concrete criteria. Each criterion is observable / verifiable per file.
5. Re-takes within the declared session window, before session close. No re-takes leak outside the window.
6. No GitHub push of raw captures. Charter rule #11 on `V2_EXCLUSIONS.md`.

### G. Session-ending conditions (hard stops)

Distance / orientation / brightness / scaling / lighting / monitor swap / phone camera setting changes / any on-device edits — each explicitly ends the current session. The checklist lists them all in §H, the protocol lists them all in §11. Consistent.

## Friction points found and fixed in this pass

1. **Capture-target-monitor declaration was vague** ("by port, position, or OSD label"). → Tightened: declare using the Windows Settings → System → Display identifier and record in `session_manifest.json.screen.capture_target_monitor_id`. (`V2_CAPTURE_PROTOCOL.md` §4; `V2_CAPTURE_CHECKLIST.md` §B.)
2. **Secondary monitor state during capture was underspecified** ("oriented or positioned so it does not bounce light" leaves room for "still on and facing the rig"). → Tightened: secondary must be **off** for the capture window, or **rotated physically** away. "Still on and facing the rig" is forbidden. (Protocol §4; checklist §B.)
3. **Windows 11 per-monitor scaling** wasn't called out. Per-monitor DPI is a Windows 11 feature; the protocol previously read as if scaling were a single OS value. → Tightened: the scaling that matters is the capture target monitor's scaling; verify via Settings with that monitor selected. (Protocol §4; checklist §B.)
4. **Viewer was not specified**, only "the designated viewer". → Named two concrete, executable viewer options: Windows Photos full-screen, or a browser in F11 fullscreen on a `file:///` URL. (Protocol §6.2; checklist §B.)
5. **Cursor "moved off-screen or hidden"** was ambiguous on a two-monitor rig. → Tightened: park the cursor on the secondary (tooling) monitor. (Protocol §6.2; checklist §B.)
6. **SHA-256 computation command was absent** — operator had no concrete recipe. → Added PowerShell `Get-FileHash` one-liner in the protocol §9 and the checklist §F.
7. **Transfer path** previously said "MTP / direct file copy" but did not forbid Windows' "Import pictures and videos" importer, which can rename / recompress / strip EXIF. → Protocol §10 and checklist §F now explicitly forbid "Import" and require plain File Explorer Copy/Paste from the phone's DCIM folder.
8. **`session_manifest.json` had no shape reference.** Operator was expected to construct it from §7 prose alone. → Added `V2_SESSION_MANIFEST_TEMPLATE.json` (documentation, not code) as a copy-and-fill shape reference.
9. **On-device deletions / Samsung Gallery "trash"** not explicitly forbidden; §11 only spoke of "no image edited, cropped, rotated, or re-saved after capture". → Added explicit forbidding of on-device deletion / edits / crops / filters / Gallery trash between shutter and intake. (Protocol §11; checklist §H.)
10. **Re-take window boundary** was not explicit. If an intake reject is found after the declared session window closed, a re-take "inside the session" would already be outside the window. → Added: re-takes must occur within the declared session window, before session close. Otherwise, start a new session. (Protocol §11; checklist §F.)

## Deferred — not blockers

- **Exact Windows 11 build** — recorded at pilot start into `session_manifest.json.screen.os_version`. Not required for coherence of the protocol.
- **Exact Android version on the S23 Ultra** — recorded at pilot start into `session_manifest.json.device.os_version`. Not required for coherence.
- **Exact `os_scaling_percent`** — verified and recorded at pilot start. Prior context says 125%. Protocol freezes whatever is observed at pilot start. Not required for coherence.

These three are pilot-start metadata fields. They do not gate G1 because the protocol explicitly designates them as "recorded at session time."

## G1 decision

Gate G1 passes under the criteria in `V2_MILESTONE_GATES.md`:

- [x] `V2_CAPTURE_PROTOCOL.md` names and fixes every controllable variable.
- [x] `V2_CAPTURE_CHECKLIST.md` is executable top-to-bottom, solo, as written.
- [x] A dry-run walkthrough (this document) completes without ambiguity.
- [x] No step relies on a second person.
- [x] No step assumes equipment Vincent does not have.
- [x] V1 / V2 backup and release isolation rule — not violated in this pass. No V1 refs touched.

**G1 closed** as of the commit bundling this document and the tightens above.
