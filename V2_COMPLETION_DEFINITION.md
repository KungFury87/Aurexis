# Aurexis Core V2 — Completion Definition

**Locked:** 2026-04-14

V2 counts as complete only when all eight criteria below are independently satisfied and documented. Partial satisfaction does not count. Each criterion has a frozen artifact or measurement that can be pointed to.

---

## C1. Frozen official screen-based capture protocol exists

A single document defines every controllable variable of the capture loop: device, lens setting, screen, display brightness, display resolution, ambient lighting, distance, mount / stability, framing, exposure, focus, file format, naming scheme, and per-step operator actions. The protocol is version-locked and reproducible by Vincent alone on demand.

**Artifact:** `V2_CAPTURE_PROTOCOL.md` (locked version header, frozen at M1)

## C2. Frozen benchmark artifact set exists

A version-locked set of on-screen artifacts the capture protocol targets. The set covers the evidence categories V2 needs to exercise (e.g. edge, gradient, chroma, fine detail, known-geometry references). Each artifact has a deterministic generator or a checked-in asset and a specification of what it is measuring.

**Artifact:** `V2_BENCHMARK_SET/` directory with a locked manifest at M2

## C3. At least one full real screen-capture evidence loop completed end-to-end

One complete pass: benchmark displayed → captured under the frozen protocol → ingested through the Core evidence pipeline → delta analysis produced → results archived. No synthetic substitutions. No skipped stages.

**Artifact:** `V2_PILOT_RUN/` directory with raw captures, ingest manifest, delta report, and pilot summary at M3

## C4. Reusable failure taxonomy from actual observed evidence

A document that names and categorizes the failure modes actually observed in the pilot run. Each entry has: name, observed-frame reference, measured signature, hypothesized cause, and calibration target. The taxonomy is reusable — future runs classify their failures against it.

**Artifact:** `V2_FAILURE_TAXONOMY.md` at M4

## C5. At least one evidence-driven calibration pass completed

Calibration parameters derived from the taxonomy (not from assumed or inherited defaults) are applied to the Core pipeline. The calibration is recorded: what parameter was changed, from what value, to what value, and which failure-class it targets.

**Artifact:** `V2_CALIBRATION_PASS_01.md` + versioned calibration profile at M5

## C6. Before/after validation on the same setup shows measurable improvement

The exact same capture protocol and benchmark set are run again after calibration. The delta between pre- and post-calibration results is reported with numbers, not adjectives. Improvement is measurable or the pass is marked unsuccessful and documented as such.

**Artifact:** `V2_BEFORE_AFTER_REPORT.md` at M6

## C7. Remaining limitations documented honestly

A document that states what V2 does not solve, does not measure, or cannot resolve under its current constraints. No hedging, no aspirational language. If a failure class was not fixed, that is stated plainly with the observed residual.

**Artifact:** `V2_REMAINING_LIMITATIONS.md` at M7

## C8. Clean V2 candidate package produced

A locked V2 candidate zip: charter, protocol, benchmark set, pilot artifacts, taxonomy, calibration pass, before/after report, limitations doc, code modules exercised, and a provenance audit continuation for V2-new code. Matches V1's packaging discipline (LOCK_MANIFEST, CODE_PROVENANCE_AUDIT, gate verification docs).

**Artifact:** `01_RELEASES/aurexis_core_v2_calibration_candidate_locked.zip` + `V2_LOCK_MANIFEST.json` + `V2_CODE_PROVENANCE_AUDIT.md` at M8

---

## Anti-criteria

V2 completion does not require:
- multi-phone validation
- print-based calibration
- motion or video capture
- third-party human reviewers
- passing ACOR-1.1 level gate counts
- pushing to GitHub (local completion is sufficient; GitHub is Vincent's call)

## Honesty clause

If at any milestone the evidence contradicts a prior claim, the prior claim is retracted in writing and the milestone is re-opened. V2 is a calibration candidate; its value depends on honest measurement.
