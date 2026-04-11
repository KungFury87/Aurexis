# Release Notes — V86
**Full title:** Aurexis Core V86 — Control/Mutation Runtime Status
**Date:** April 7, 2026
**Gate:** Gate 2 obedience pass (not completion)

## What changed
- Control-resolution surfaces now preserve explicit phoxel runtime status and rollups when control payload carries that status
- Control-transition and control-state-machine surfaces preserve phoxel status instead of flattening to generic runtime metadata
- State propagation exposes explicit mutation summaries (surviving environment changes surfaced directly, not just inferrable from snapshots)
- Branch-state exposes branch transition summary for blocked branch labels
- Runtime-obedience reporting extended: control-surface phoxel status, mutation summary consistency, mismatch surfacing

## Tests added
- test_gate2_state_branch_runtime_status_v85.py (carries into V86)
- Additional control/mutation lane tests proving phoxel status stays alive

## Honest state
This is Gate 2 authored/runtime evidence.
Not a claim of whole-stack Gate 2 completion.
Not Gate 3 earned evidence.
The control/mutation lane is now materially more answerable to the phoxel law.

## Source package
`aurexis_lang/src/aurexis_lang/` — 78 modules
`tests/` — 66 test files
