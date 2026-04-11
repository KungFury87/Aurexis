# Aurexis Core — Release History

## Active Development Line

### V86 — Control/Mutation Runtime Status
**File:** `V86/Aurexis_Core_V86_Control_Mutation_Runtime_Status.zip`
**Date:** April 7, 2026
**Gate focus:** Gate 2 obedience pass

What changed:
- Control-resolution surfaces now preserve explicit phoxel runtime status and rollups
- Control-transition and control-state-machine surfaces preserve phoxel status instead of flattening
- State propagation exposes explicit mutation summaries
- Branch-state exposes branch transition summary for blocked branch labels
- Runtime-obedience reporting exposes control-surface phoxel status, mutation summaries, and mismatch surfacing
- Tests proving control/mutation lane keeps phoxel-law status alive

Honest limit: Gate 2 authored/runtime evidence. Not whole-stack Gate 2 completion. Not Gate 3 earned evidence.

---

### V85 — Core Audit Drop
**File:** `V85/Aurexis_Core_V85_Core_Audit_Drop.zip`
**Date:** April 7, 2026
**Gate focus:** Gate 2 — phoxel status into plan/state/branch surfaces

What changed:
- First zip to include the full aurexis_lang source package (not just scaffolding)
- Execution plan, runtime resolution, deeper execution, state propagation, branch-state all carry explicit phoxel runtime status or rollups
- Runtime-obedience reporting surface extended to expose phoxel-status rollups
- 39 tests (up from prior)

---

### V84 — Execution Runtime Status
**File:** `V84/Aurexis_Core_V84_Execution_Runtime_Status.zip`
**Date:** April 7, 2026
**Gate focus:** Gate 2 — phoxel status into execution trace + interpreter

What changed:
- Execution trace surface carries phoxel_runtime_status_explicit
- Interpreter execution traces keep phoxel status alive
- Runtime obedience report exposes phoxel status summary

---

## Legacy Development Line (V81ish cleanup track)

### V81ish Cleanup V31 — Gate 3 Comparison Audit
**File:** `LEGACY_V81ISH/aurexis_vision_track_v81ish_cleanup_v31_gate3_comparison_audit.zip`
**Date:** April 7, 2026

### V81ish Cleanup V19 — Gate 1 Mobile Future
**File:** `LEGACY_V81ISH/aurexis_vision_track_v81ish_cleanup_v19_gate1_mobile_future.zip`
**Date:** April 7, 2026

### V81ish Cleanup V2 — Initial cleanup pass
**File:** `LEGACY_V81ISH/aurexis_vision_track_v81ish_cleanup_v2.zip`
**Date:** April 6, 2026

### V80 (referenced in handoff) — Repo Verification Surface
Not in this folder as a zip but fully documented in the V80 handoff file.
154 tests. Release-candidate surfaces. Repo verification infrastructure.

---

## Demo / Prototype Archive

### Newest Continuation Demo
**File:** `LEGACY_V81ISH/aurexis_newest_continuation_demo.zip`
Contains: Visual programming GUI prototype (Tkinter), demo CV scripts, phase 1-4 scaffolding.
Note: This is the earlier prototype without the full aurexis_lang library. Useful for understanding the UI vision and demo layer, not for production development.
