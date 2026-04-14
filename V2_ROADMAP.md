# Aurexis Core V2 — Roadmap

**Locked:** 2026-04-14
**Branch:** `working/core-v2`

Linear milestone ladder. Each milestone ends at a gate (see `V2_MILESTONE_GATES.md`). No milestone is skipped. No milestone is claimed complete until its gate passes.

---

## V2-M0 — Charter Lock  *(this pass)*

Lock V2 purpose, non-goals, completion criteria, milestone ladder, and gate conditions. Produce the charter-lock package. No implementation.

**Deliverables:**
- `V2_CHARTER.md`
- `V2_COMPLETION_DEFINITION.md`
- `V2_ROADMAP.md`
- `V2_EXCLUSIONS.md`
- `V2_MILESTONE_GATES.md`
- V2 git branch `working/core-v2` created (local only, not pushed)

**Gate:** Vincent signs off on the charter package. M0 closes.

---

## V2-M1 — Official Capture Protocol

Write and freeze the screen-based capture protocol. One device, one screen, one rig. Every variable controllable by Vincent is named and fixed. The protocol must be reproducible by Vincent alone without reference to outside help.

**Deliverables:**
- `V2_CAPTURE_PROTOCOL.md` (locked version)
- `V2_CAPTURE_CHECKLIST.md` (step-by-step, operator-facing)
- Equipment inventory (phone model, screen, mount, lighting baseline)

**Gate:** Protocol locked, checklist executable end-to-end on paper (dry run walk-through).

---

## V2-M2 — Benchmark Artifact Set Lock

Define and freeze the on-screen benchmark artifact set. Each artifact: generator or asset, specification, measurement target, version.

**Deliverables:**
- `V2_BENCHMARK_SET/` with artifacts and manifest
- `V2_BENCHMARK_SET_MANIFEST.json` (locked)
- Generator code (if procedural) under `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_benchmark/`

**Gate:** Manifest locked, artifacts render deterministically, each artifact has a declared measurement target.

---

## V2-M3 — First Real Capture Pilot

Execute the capture protocol against the benchmark set. Ingest the captures through the Core evidence pipeline (using the already-on-disk modules: `camera_bridge`, `capture_session_manifest_bridge_v1`, `real_capture_ingest_profile_bridge_v1`, `evidence_delta_analysis_bridge_v1`, `evidence_tiers`, relevant CV extractors). Produce a pilot report.

**Deliverables:**
- `V2_PILOT_RUN/raw/` — original captures
- `V2_PILOT_RUN/ingest_manifest.json`
- `V2_PILOT_RUN/delta_report.md`
- `V2_PILOT_RUN/PILOT_SUMMARY.md`

**Gate:** End-to-end loop executed, all stages produce artifacts, no fabricated data.

---

## V2-M4 — Failure Taxonomy

Examine pilot results. Name, categorize, and document every failure mode actually observed. Each entry is grounded in a specific captured frame and a measured signature.

**Deliverables:**
- `V2_FAILURE_TAXONOMY.md` (versioned)

**Gate:** Every failure claim is traceable to a pilot artifact. Unobserved / speculative failures are excluded.

---

## V2-M5 — Evidence-Driven Calibration

Derive calibration adjustments from the taxonomy. Apply them. Record what changed and why. Calibration lives in a versioned profile, not ad-hoc edits to V1.

**Deliverables:**
- `V2_CALIBRATION_PASS_01.md`
- `V2_CALIBRATION_PROFILES/profile_01.json`
- Code adjustments, if any, land in new V2-scoped modules — V1 substrate is not rewritten

**Gate:** Each calibration change is justified by a taxonomy entry. No untraceable adjustments.

---

## V2-M6 — Before/After Validation

Re-run the exact protocol and benchmark set with the calibration applied. Measure the delta against the pilot run. Report numerically.

**Deliverables:**
- `V2_VALIDATION_RUN/` — post-calibration captures and artifacts
- `V2_BEFORE_AFTER_REPORT.md` with per-failure-class measurements

**Gate:** Same setup, same protocol, same benchmark. Numeric deltas reported. Non-improvements stated as non-improvements.

---

## V2-M7 — Controlled Expansion

Optional expansion *within* V2 scope only: second calibration pass, second benchmark category, lighting-variant sub-protocol, etc. No new Core branches. No E/D. No multi-phone requirement. Expansion is controlled, not exploratory.

**Deliverables:**
- `V2_EXPANSION_LOG.md` listing approved expansions
- Additional calibration / validation artifacts as earned

**Gate:** Every expansion item traces to a charter-compatible goal. Anything that would broaden V2 beyond charter is rejected in writing.

---

## V2-M8 — V2 Candidate Release

Package V2 as a locked candidate release, V1-style.

**Deliverables:**
- `V2_REMAINING_LIMITATIONS.md`
- `V2_LOCK_MANIFEST.json`
- `V2_CODE_PROVENANCE_AUDIT.md`
- `01_RELEASES/aurexis_core_v2_calibration_candidate_locked.zip`
- `V2_RELEASE_NOTES.md`

**Gate:** All eight completion criteria (C1–C8) satisfied, zip reproducible, provenance clean-room verified.

---

## Recommended first coding milestone after charter lock

**V2-M1 (Official Capture Protocol)** is documentation-first, not coding. The first coding milestone is **V2-M2 (Benchmark Artifact Set Lock)** — procedural generation of the on-screen benchmark artifacts. That is where V2 code first touches disk in this working tree.
