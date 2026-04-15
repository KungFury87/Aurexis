# V2-M3 First Real Capture Pilot — Runbook (P1)

**Status:** LOCKED (runbook only; real captures not yet taken)
**Pilot code:** `P1`
**Locked on:** 2026-04-14
**Branch:** `working/core-v2`
**Operator:** Vincent (solo)
**Prerequisite:** `V2_PILOT_PREFLIGHT.md` — every required check ticked

The runbook is the concrete execution plan. It assumes the preflight is closed and references the locked protocol / checklist / benchmark set rather than redefining them.

---

## What the first pilot IS

- One pilot window (P1).
- **Five sessions**, one per B1 artifact, in the registry order.
- **Three captures (N = 3)** per session, as per protocol default.
- **No variants.** One rig pose. One distance. One orientation. One lighting state. One session window.
- **One target monitor** (the declared capture target from preflight §3).
- **One phone** (the locked Galaxy S23 Ultra).
- **One viewer** (Windows Photos in full-screen mode).

Total captures in the minimally acceptable first pilot: **15 usable captures** = 5 sessions × 3 per session.

## What the first pilot IS NOT

- Not multi-angle. Not multi-distance. Not multi-lighting. Not multi-phone. Not multi-monitor.
- Not a calibration pass. (That is V2-M5.)
- Not a validation pass. (That is V2-M6.)
- Not print-based. Not video. Not burst. Not HDR-stacked.
- Not a test of E/D.
- Not ingested through the Core evidence pipeline within the runbook itself — pipeline ingest is a separate step once the raw files are on disk.

Angle / distance / lighting variants are explicitly deferred to **V2-M7 Controlled Expansion** and require a charter amendment before entering V2.

## Ordering (locked)

Sessions run in this order, no reordering:

1. `b1-clean-solid`
2. `b1-edge-half`
3. `b1-grid-64`
4. `b1-gradient-h`
5. `b1-corners-fiducials`

Reason for this order: move from the most homogeneous artifact (noise floor / AWB baseline) to the most spatially structured (geometric fiducials). If anything environmental drifts mid-pilot, the high-structure artifacts captured later are the ones most likely to surface that drift as taxonomy entries.

## Session IDs (plan — `HHMM` set at session start)

```
P1-S01: V2S-<YYYYMMDD>-<HHMM1>-b1-clean-solid-rigHH01-pilot
P1-S02: V2S-<YYYYMMDD>-<HHMM2>-b1-edge-half-rigHH01-pilot
P1-S03: V2S-<YYYYMMDD>-<HHMM3>-b1-grid-64-rigHH01-pilot
P1-S04: V2S-<YYYYMMDD>-<HHMM4>-b1-gradient-h-rigHH01-pilot
P1-S05: V2S-<YYYYMMDD>-<HHMM5>-b1-corners-fiducials-rigHH01-pilot
```

Each session is independent of the others with respect to the protocol's "hard stops" in `V2_CAPTURE_CHECKLIST.md` §H. A hard stop within one session does not require re-running the earlier sessions, provided no state that would invalidate them has changed.

## Capture file naming

Per `V2_CAPTURE_PROTOCOL.md` §8:

```
<session_id>_cap_01.jpg
<session_id>_cap_02.jpg
<session_id>_cap_03.jpg
```

Re-takes: letter-suffixed (`_cap_01b.jpg`, `_cap_01c.jpg`), original kept, manifest records which supersedes which.

## Folder layout on disk

```
V2_PILOT_RUN/
└── raw/
    ├── P1-S01_<session_id>/
    │   ├── session_manifest.json
    │   ├── captures/
    │   │   ├── <session_id>_cap_01.jpg
    │   │   ├── <session_id>_cap_02.jpg
    │   │   └── <session_id>_cap_03.jpg
    │   ├── rejected/            # created only if §12 intake rejects anything
    │   └── notes.md
    ├── P1-S02_<session_id>/
    ├── P1-S03_<session_id>/
    ├── P1-S04_<session_id>/
    └── P1-S05_<session_id>/
```

The `P1-S0N_` directory prefix is **runbook-local bookkeeping** to keep the five sessions visually grouped as P1; the actual `session_id` (the full `V2S-...` string) is the authoritative identifier everywhere else.

## Execution order within one session

Follow `V2_CAPTURE_CHECKLIST.md` top to bottom, in order:

1. Section A — Pre-session (only applies at session 1 / P1-S01; sessions 2–5 can skip this if nothing changed since the last session closed and the window label is identical)
2. Section B — Screen preparation (open the next B1 artifact in Windows Photos full-screen; press **F11** if needed to reach true full-screen; verify black padding)
3. Section C — Phone preparation (verify camera state unchanged from last session)
4. Section D — Rig placement (reconfirm distance using the same measurement taken at P1 start; orientation unchanged)
5. Section E — Per-capture loop (N = 3)
6. Section F — Session close (transfer + manifest + intake)

If section A shows any change in environmental state between sessions, the window has drifted and the pilot is aborted (see "Abort conditions" below).

## Per-session capture count and intake

- Target: **3 usable captures** per session (N = 3).
- If a shutter produces an obviously unusable capture (reflection, blur, framing miss), **do not delete on device** — take a re-take labeled `_cap_NN<letter>.jpg` and continue. The intake step will move the bad one to `rejected/` on the workstation.
- If after 6 attempts in a single session the operator cannot reach 3 usable captures, abort that session, record the reason in `notes.md`, and start a new session with a new `session_id`.

## Viewer and display procedure (locked for P1)

1. On the workstation, open the benchmark PNG in **Windows Photos**:
   - File Explorer → `V2_BENCHMARK_SET\assets\b1-<artifact>.png` → double-click.
   - Windows Photos opens the image.
2. Enter **full-screen**: press **F11** (or the Photos app's full-screen toggle). The artifact is displayed centered, fit-to-native, with black padding where the aspect mismatches.
3. Do **not** use Photos' "edit," "enhance," "filter," or "slideshow" features. The only Photos action used is full-screen display of a single image.
4. Between sessions: press **Esc** to exit full-screen, navigate to the next artifact, re-enter full-screen. Photos should remember no state between artifacts (each is a fresh file open).

## Transfer procedure (locked for P1)

After all three captures of a session are taken (or at the end of the pilot — either is acceptable, but mid-session transfer is the safer path):

1. Connect the S23 Ultra via USB. Unlock the phone. Grant File Transfer permission.
2. Open File Explorer → `This PC` → the phone → `Phone` → `DCIM` → `Camera`.
3. Identify the session's captures by timestamp. Select them.
4. **Copy** (Ctrl+C). Navigate to `V2_PILOT_RUN\raw\P1-S0N_<session_id>\captures\`. **Paste** (Ctrl+V).
5. Do **not** use the "Import pictures and videos" Windows action — it can rename, recompress, or strip EXIF.
6. After paste completes, run the SHA-256 PowerShell one-liner from `V2_CAPTURE_PROTOCOL.md` §9:

```powershell
Get-ChildItem .\V2_PILOT_RUN\raw\P1-S0N_<session_id>\captures\ |
  ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash, $_.Name }
```

Paste the hashes into the session's manifest.

## Session manifest procedure

1. Copy `V2_SESSION_MANIFEST_TEMPLATE.json` to `V2_PILOT_RUN\raw\P1-S0N_<session_id>\session_manifest.json`.
2. Delete the `_template_note` key and any `_first_pilot_guidance` key.
3. Fill every field per protocol §7. For P1-S01, all pilot-start metadata (see preflight Appendix) is newly written. For P1-S02 through P1-S05, `device`, `screen`, `environment` sections are copied verbatim from P1-S01 — only `session_id`, `benchmark_artifact_id`, `benchmark_artifact_checksum`, `captured_at_session_start`, `captured_at_session_end`, `captures[]`, and `notes` change.
4. `benchmark_artifact_checksum` is copied from `V2_BENCHMARK_SET/V2_BENCHMARK_SET_MANIFEST.json` — specifically the `sha256` field of the matching `artifact_id`.
5. Save.

## Minimally acceptable first pilot set

The pilot is complete only when all of the following hold:

- [ ] 5 session directories exist under `V2_PILOT_RUN/raw/`, one per B1 artifact
- [ ] Each session's `captures/` has **at least 3 usable captures** that pass `V2_CAPTURE_PROTOCOL.md` §12 intake
- [ ] Each session has a valid, filled `session_manifest.json` matching the shape in `V2_SESSION_MANIFEST_TEMPLATE.json`
- [ ] Each session's `captures[].sha256` values match `Get-FileHash` on disk
- [ ] The benchmark asset's SHA-256 recorded in each session manifest matches the live `V2_BENCHMARK_SET/V2_BENCHMARK_SET_MANIFEST.json` value (i.e. the benchmark was not silently re-rendered between sessions)
- [ ] `notes.md` exists for each session, populated with honest observations
- [ ] All five sessions share identical `screen`, `rig`, and `environment` field values except where they must legitimately differ (only `captured_at_*` timestamps)
- [ ] No files in `V2_PILOT_RUN/raw/**/captures/` were edited, cropped, rotated, or re-saved after capture

Anything less — missing session, unusable capture count below 3 in any session, EXIF stripped, benchmark checksum drift, etc. — marks the pilot incomplete. Incomplete pilots do not feed V2-M4 taxonomy; they are either completed or re-run from scratch.

## Abort conditions (session-level and pilot-level)

**Session-level** (end this session, start a new one with a new `session_id`; earlier sessions remain valid if nothing they depend on changed):

- Any `V2_CAPTURE_CHECKLIST.md` §H hard stop triggers (distance / orientation / brightness / scaling / lighting / monitor swap / camera setting change / any on-device edit)
- 6 consecutive shutter attempts fail to produce 3 usable captures
- The phone battery runs low enough to change exposure/focus behavior
- Any unusable capture is detected mid-session that cannot be re-taken without changing declared state

**Pilot-level** (abort P1 entirely, discard what you have, restart P1 from preflight):

- Environmental state has clearly drifted since earlier sessions and cannot be restored before the next session (e.g. window covering opened, main room light changed, capture target monitor swapped)
- The declared session window has closed (e.g. sunset changed the ambient light in the middle of an evening pilot)
- The capture target monitor's resolution or scaling changes between sessions
- The benchmark set has been re-rendered or the manifest has changed since the pilot started
- A power event (blink, reboot) resets any locked state

Aborted pilots are documented: a `V2_PILOT_RUN/P1_ABORTED_<datetime>.md` lists the reason, which sessions were completed, and why P1 must restart. Do **not** mix partial-P1 sessions with a future P1 restart.

## After the pilot — out of this runbook's scope

Once P1 is complete (every item in "Minimally acceptable first pilot set" ticked), the next step is V2-M3 pipeline ingest: run the raw captures through the Core evidence delta pipeline using the V1 modules present on disk (`real_capture_ingest_profile_bridge_v1`, `evidence_delta_analysis_bridge_v1`, `evidence_tiers`, relevant CV extractors). That is a separate pass and will have its own preflight.

This runbook ends at "P1 captures on disk, session manifests filled, intake passed." Nothing further is in-scope for M3 preflight.
