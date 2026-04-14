# V2 Capture Checklist — Operator-Facing (one page)

**Protocol:** V2-CAP-PROTO-1.0-LOCK
**Operator:** Vincent (solo)
**Rig profile:** `rigHH01` (handheld, S23 Ultra, MSI G27C4X capture target)
**Default N:** 3 captures per artifact

Read top-to-bottom. If any step cannot be completed as written, stop the session and record the reason in `notes.md`.

---

## A. Pre-session (once per session)

- [ ] Room: home desk / home office only
- [ ] Session window matches the declared window (same as pilot if this is validation)
- [ ] Window coverings: same state as pilot (blinds / curtains)
- [ ] Lighting fixtures: same set, same settings as pilot
- [ ] No other screens visible to the capture path; other screens off or turned away
- [ ] Notifications: Windows Focus Assist / Do Not Disturb ON
- [ ] Reflective items (mirrors, glossy posters, shiny objects) behind / beside the phone — moved or covered
- [ ] Wear dark / non-reflective clothing if operator reflection has been an issue
- [ ] Clean S23 Ultra rear main lens with dry microfiber
- [ ] Clean MSI G27C4X capture-target screen with dry microfiber

## B. Screen preparation

- [ ] Confirm capture target monitor (one of the two MSI G27C4X units) — declared by port, position, or OSD label
- [ ] Wake capture target monitor; **warm up 10–15 minutes** before any capture
- [ ] Confirm monitor brightness is the V2-locked default (unchanged)
- [ ] Confirm Windows 11 display scaling matches the frozen V2 value (prior context 125% — verify at Settings → System → Display → Scale)
- [ ] Confirm native resolution at 1:1 pixel mapping; browser / viewer zoom = 100%
- [ ] HDR output OFF on the capture target monitor
- [ ] Night light / blue-light filter / color profile tweaks: OFF
- [ ] Screen saver / auto-dim / auto-sleep: disabled for the session
- [ ] Adaptive brightness: OFF
- [ ] Secondary monitor oriented / positioned so it is not in the capture frame and does not bounce light at the phone
- [ ] Open benchmark artifact full-screen, 100% zoom, black padding if aspect mismatches
- [ ] Cursor moved off-screen or hidden; taskbar auto-hidden or covered

## C. Phone preparation (Galaxy S23 Ultra)

- [ ] Samsung native Camera app, Photo mode
- [ ] Lens: rear main, **1.0x exactly** (no ultrawide, no telephoto)
- [ ] HDR: **OFF**
- [ ] Flash: **OFF**
- [ ] Night mode: **OFF**
- [ ] Scene Optimizer / AI enhancements: **OFF**
- [ ] Motion Photo / Single Take / burst / panorama / HDR-stacked: **OFF / not used**
- [ ] Grid / level overlay: optional (framing only)
- [ ] Do Not Disturb on the phone during the session

## D. Rig placement (handheld)

- [ ] Declared phone-to-screen distance measured / recorded at session start (tape or ruler once; hold constant)
- [ ] Orientation: portrait (landscape only if the artifact requires it)
- [ ] Optical axis as close to perpendicular to screen center as possible
- [ ] Framing: artifact fills 70%–90% of the shorter frame dimension, no crop
- [ ] Two-handed grip, both elbows braced on desk or body
- [ ] Shutter via **self-timer 2 s or 3 s** (preferred); tap shutter is fallback only

## E. Per-capture loop (repeat N times; default N = 3)

For each capture:

- [ ] Tap-to-focus at artifact center, wait for focus indicator stable
- [ ] Tap-to-meter / confirm AE lock at artifact center
- [ ] Stabilize: breath out, hold, braced elbows
- [ ] Release shutter via self-timer (2 s or 3 s)
- [ ] Wait for save to complete before next iteration
- [ ] Note any observed issue (reflection, blur, framing drift) in `notes.md`; mark as re-take candidate, **do not delete on device**

## F. Session close

- [ ] Write `session_manifest.json` with every field from protocol §7 populated
- [ ] Transfer captures via USB (preferred) or EXIF-preserving direct path to:
      `V2_PILOT_RUN/raw/<session_id>/captures/`
- [ ] Compute SHA-256 per file; record in `session_manifest.json`
- [ ] Verify `captures/` matches manifest filenames and checksums
- [ ] Run §12 intake check on each file; move rejects to
      `V2_PILOT_RUN/raw/<session_id>/rejected/` with `rejection_reason.txt`
- [ ] If fewer than N usable captures, re-run the loop or mark session failed in `notes.md`
- [ ] Confirm no GitHub push attempted; `V2_PILOT_RUN` stays local

## G. Session ID (fill in at session start)

```
V2S-<YYYYMMDD>-<HHMM>-<benchmark_artifact_id>-rigHH01-<pass_label>
```

- `pass_label`: `pilot` for V2-M3, `validation` for V2-M6, `expansion-<n>` for V2-M7 earned expansions

## H. Hard stops (end the session and start a new one)

Any of the following ends the current session — do not mix conditions within one `session_id`:

- Distance changes mid-session
- Orientation changes mid-session
- Monitor brightness changes mid-session
- OS display scaling changes mid-session
- Lighting changes mid-session (fixture on/off, bulb change, window state change)
- Capture target monitor swapped for the secondary monitor
- Phone camera settings changed (HDR, Scene Optimizer, lens, zoom)

## I. Forbidden (protocol §11 exclusions)

- Print-based captures, physical calibration boards, paper targets
- Video, Motion Photo, Single Take, burst, HDR-stacked, panorama, night mode
- Front camera, ultrawide, telephoto, zoom ≠ 1.0x
- Flash, torch, supplemental lighting beyond the declared set
- Notifications, cursors, taskbars, any non-artifact pixels visible
- Captures outside the declared session window
- Multi-device captures
- Third-party camera apps or Pro mode with unrecorded settings
- Any image edited, cropped, rotated, or re-saved after capture
- Any E/D-track activity
- Cloud-sync paths that strip EXIF or recompress
- GitHub push of raw captures without Vincent's explicit instruction
