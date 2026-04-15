# Aurexis Core V2 — Milestone Gates

**Locked:** 2026-04-14

## Gate status (live)

| Gate | Milestone | Status | Commit |
|---|---|---|---|
| G0 | V2-M0 Charter Lock | **CLOSED** (2026-04-14) | `39d1c38` |
| G1 | V2-M1 Capture Protocol | **CLOSED** (2026-04-14) | `19f2fa1` (bundled with paper dry-run + template + tightens) |
| G2 | V2-M2 Benchmark Artifact Set | **CLOSED** (2026-04-14) | `75f0fec` (B1 set locked, 5 mandatory artifacts, 21/21 V2 tests green, 636 total suite green) |
| G3 | V2-M3 First Capture Pilot | open | — |
| G4 | V2-M4 Failure Taxonomy | open | — |
| G5 | V2-M5 Evidence-Driven Calibration | open | — |
| G6 | V2-M6 Before/After Validation | open | — |
| G7 | V2-M7 Controlled Expansion | open | — |
| G8 | V2-M8 V2 Candidate Release | open | — |


Each milestone has an explicit gate. A milestone is not "complete" until its gate passes. Gate failure re-opens the milestone; it does not downgrade the definition.

---

## G0 — Charter Lock Gate  *(V2-M0)*

**Passes when:**
- `V2_CHARTER.md`, `V2_COMPLETION_DEFINITION.md`, `V2_ROADMAP.md`, `V2_EXCLUSIONS.md`, `V2_MILESTONE_GATES.md` all exist in the working tree
- `working/core-v2` git branch exists locally
- The V1/V2 backup and release isolation rule (below) is documented in `V2_CHARTER.md` and `V2_EXCLUSIONS.md`
- Vincent explicitly signs off on the charter package

**Fails if:** any of the five docs is missing, contradicts another, or contradicts the frozen V1 posture.

### V1 / V2 backup and release isolation (hard gate rule, applies to every gate)

No gate on any milestone passes if the V2 tree has:
- reused or mutated any `backup/v1-...` branch
- reused or mutated any `backup-v1-...` tag
- altered `core-v1-substrate-candidate-or1` or `core-v1-substrate-candidate-or1.1`
- pushed V2 state onto any V1 release surface
- force-pushed, deleted, renamed, or retagged any V1 ref

Allowed V2 namespaces: `working/core-v2`, `backup/v2-...`, `backup-v2-...`, future `core-v2-...` release tags only.

Any gate-level check must verify this rule has not been violated before passing.

---

## G1 — Capture Protocol Gate  *(V2-M1)*

**Passes when:**
- `V2_CAPTURE_PROTOCOL.md` names and fixes every controllable variable (device, lens, screen, display brightness, display resolution, ambient lighting, distance, mount, framing, exposure, focus, file format, naming, operator actions)
- `V2_CAPTURE_CHECKLIST.md` is executable as written, top to bottom, solo
- A dry-run walkthrough (no captures yet) completes without ambiguity

**Fails if:** any variable is undefined, any step relies on a second person, or any step assumes equipment Vincent does not have.

---

## G2 — Benchmark Artifact Set Gate  *(V2-M2)*

**Passes when:**
- `V2_BENCHMARK_SET_MANIFEST.json` is locked (version, checksums, per-artifact spec)
- Each artifact renders deterministically from its generator or is a checked-in asset with a checksum
- Each artifact declares a measurement target (what failure class it is designed to reveal)

**Fails if:** any artifact lacks a spec, any generator is non-deterministic, or any artifact has no declared measurement target.

---

## G3 — First Capture Pilot Gate  *(V2-M3)*

**Passes when:**
- `V2_PILOT_RUN/raw/` contains captures produced under G1's protocol against G2's benchmark set, with timestamps and device metadata preserved
- `V2_PILOT_RUN/ingest_manifest.json` lists every ingested capture with its pipeline status
- `V2_PILOT_RUN/delta_report.md` is produced by the Core evidence delta pipeline
- `V2_PILOT_RUN/PILOT_SUMMARY.md` documents what happened, in prose, with honest language

**Fails if:** any stage fabricates or skips evidence, if the pipeline was bypassed, or if the summary overstates what was observed.

---

## G4 — Failure Taxonomy Gate  *(V2-M4)*

**Passes when:**
- Every taxonomy entry has: name, observed-frame reference (file + region), measured signature, hypothesized cause, calibration target
- No entry is speculative — each is grounded in an actual pilot artifact
- The taxonomy covers every failure class observed; no observed failure is silently dropped

**Fails if:** any entry lacks a frame reference, any observed failure is missing from the taxonomy, or entries describe failures that were not observed.

---

## G5 — Evidence-Driven Calibration Gate  *(V2-M5)*

**Passes when:**
- Every calibration change in `V2_CALIBRATION_PROFILES/profile_01.json` traces to a specific taxonomy entry
- `V2_CALIBRATION_PASS_01.md` records: prior value, new value, target failure class, justification, expected effect
- V1 substrate modules remain unmodified; calibration lives in new V2 modules or versioned profile data

**Fails if:** any change is untraceable, if V1 substrate was edited, or if calibration values appear arbitrary.

---

## G6 — Before/After Validation Gate  *(V2-M6)*

**Passes when:**
- The validation run uses the exact same protocol (G1) and benchmark set (G2) as the pilot
- `V2_BEFORE_AFTER_REPORT.md` reports numeric deltas per failure class
- Non-improvements are reported as non-improvements with honest language
- No protocol drift between pilot and validation (same device, same settings, same rig)

**Fails if:** the protocol drifted, deltas are qualitative instead of numeric, or non-improvements are dressed up as improvements.

---

## G7 — Controlled Expansion Gate  *(V2-M7)*

**Passes when:**
- Every expansion item in `V2_EXPANSION_LOG.md` traces to a charter-compatible goal
- No expansion introduces excluded items (see `V2_EXCLUSIONS.md`) without a formal amendment
- Each expansion has its own mini-gate that matches the relevant milestone pattern (e.g. an additional benchmark category runs its own G2-style gate)

**Fails if:** an expansion silently broadens V2 scope, or introduces excluded items without amendment.

---

## G8 — V2 Candidate Release Gate  *(V2-M8)*

**Passes when:**
- All eight completion criteria (C1–C8 in `V2_COMPLETION_DEFINITION.md`) are independently satisfied
- `V2_LOCK_MANIFEST.json` matches the zip contents exactly
- `V2_CODE_PROVENANCE_AUDIT.md` certifies V2-new code is clean-room (V1 code inherits V1's audit)
- `V2_REMAINING_LIMITATIONS.md` is written honestly
- The release zip is reproducible from the working tree

**Fails if:** any completion criterion is unsatisfied, the manifest diverges from the zip, or the limitations doc hedges.

---

## Recommended first coding milestone after charter lock

**V2-M2 — Benchmark Artifact Set Lock.** M1 is documentation (capture protocol). M2 is where V2 code first lands on disk: deterministic generators for the on-screen benchmark artifacts under `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_benchmark/`. M2 is the first gate that exercises V2 code and is the natural transition from planning into implementation.
