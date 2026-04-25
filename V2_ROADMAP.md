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

---

# Decode Engine Track (Amendment 1 — 2026-04-18)

Parallel to the calibration track (M3–M8). Extracts the decode pipeline from the E/D client into a standalone, DOM-free Core v2 JS module, proven with synthetic tests before any camera touches it. See `V2_CHARTER_AMENDMENTS.md` §1.

---

## V2-D0 — Decode Engine Extraction

Extract decode-relevant functions from `aurexis_ed_unified.html` into `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/`. Pure JS, no DOM dependencies, importable via Node `require()`. Stages: GF/RS codec, finder detection, homography, format selection, module sampling, color classification, frame fusion, payload parsing.

**Deliverables:**
- `v2_decode/` module tree with clean stage separation
- Each stage callable independently with typed inputs/outputs
- Node-runnable (no browser APIs required for core decode path)

**Gate:** Module loads in Node without error. Each public function is callable with synthetic inputs and returns structured output.

---

## V2-D1 — Synthetic Test Harness

Build a Node test suite that proves each decode stage against synthetic data — rendered artifacts with known perspective transforms, known module values, known RS encoding. No camera, no phone, no real captures.

**Deliverables:**
- `tests/test_v2_decode.py` or `tests/test_v2_decode_node/` — test suite
- Synthetic artifact generator (renders known grids, applies known warps)
- Per-stage tests: finder detection, format selection, homography accuracy, module sampling, RS decode, end-to-end

**Gate:** All tests pass. Each stage is proven independently. End-to-end synthetic decode produces byte-exact match against known input.

---

## V2-D2 — GPT-Recommended Improvements

Apply the architecture improvements from GPT's decode analysis (see `ed/references/gpt_decode_architecture_answers.md`):

1. Candidate-scored format selection (try-all-configs with multi-feature scoring)
2. Explicit BR detection + homography refinement
3. Robust frame fusion (quality-weighted, reject weak frames)
4. Better finder filtering (2D template + quiet-zone)
5. Multi-resolution detection (low-pass detect, full-res sample)

**Deliverables:**
- Updated `v2_decode/` modules with improved stages
- Tests proving each improvement against synthetic data
- Before/after accuracy measurements on synthetic test set

**Gate:** Synthetic decode accuracy measurably improves. No regression on existing test cases.

---

## V2-D3 — E/D Client Integration

Wire the proven Core v2 decode module back into the E/D client. The client becomes a thin wrapper: camera management + UI + calls to Core v2 decode functions.

**Deliverables:**
- Updated `aurexis_ed_unified.html` importing decode module
- Same encode behavior, decode now delegated to Core v2
- APK rebuild with new client

**Gate:** E/D client decode path uses Core v2 module. Phone-camera decode works at least as well as v12 baseline.

---

## V2-D4 — Decode Engine Validation

Test the integrated decode engine against real camera captures (phone → monitor → decode). Measure decode success rate, RS correction load, and per-stage metrics.

**Deliverables:**
- `V2_DECODE_VALIDATION_REPORT.md` with real-capture test results
- Per-stage diagnostic output (finder confidence, timing scores, homography residuals, RS block stats)

**Gate:** At least one HD config (128x128-4c) achieves byte-exact decode from real camera capture. Metrics documented.

---

## Recommended first coding milestone after charter lock

**V2-M1 (Official Capture Protocol)** is documentation-first, not coding. The first coding milestone is **V2-M2 (Benchmark Artifact Set Lock)** — procedural generation of the on-screen benchmark artifacts. That is where V2 code first touches disk in this working tree.

For the decode engine track, the first coding milestone is **V2-D0 (Decode Engine Extraction)** — extracting decode logic from the E/D HTML into a standalone Core module.
