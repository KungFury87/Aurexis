# Release Notes — V85
**Full title:** Aurexis Core V85 — Core Audit Drop
**Date:** April 7, 2026
**Gate:** Gate 2 obedience pass

## What changed
- First release to include the complete aurexis_lang source library (not just scaffolding)
- Execution plan, runtime resolution, deeper execution, state propagation, and branch-state surfaces all carry explicit phoxel runtime status or rollups
- Runtime-obedience reporting surface extended to expose phoxel-status rollups
- V85 specifically fixed: phoxel-law metadata was dropping when AST nodes flowed through the runtime transformation chain — V85 threads phoxel_runtime_status through every stage

## Tests: 39 test files

## Key source modules included for the first time
- core_law_enforcer.py — full implementation delegating to 5 specialized modules
- phoxel_schema.py — canonical 6-field schema with full validation
- illegal_inference_matrix.py — 9 named blocked claim rules
- relation_legality.py — primary + higher-order relation kinds, physical measurement required
- executable_promotion.py — 6-check + confidence promotion checklist
- evidence_tiers.py — 4-tier system preventing upward fake-claiming
- runtime_obedience.py — full Gate 2 reporting surface
- phoxel_runtime_status.py — explicit runtime-facing status summary

## Honest state
Gate 2 obedience pass. Not completion. Not Gate 3 earned evidence.
