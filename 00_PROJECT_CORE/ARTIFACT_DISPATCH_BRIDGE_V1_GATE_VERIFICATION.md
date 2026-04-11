# Artifact Dispatch Bridge V1 — Gate Verification

**Date:** April 10, 2026
**Implementer:** Claude (constrained implementer)
**Authority chain:** Vincent > Master Law > Frozen spec > Code/tests > Task instructions

---

## Gate Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frozen dispatch profile exists | ✅ PASS | `DispatchProfile` with 3 frozen `ArtifactFamily` entries: adjacent_pair, containment, three_regions. Each family has a unique `StructuralFingerprint(primitive_count, operation_kinds)` |
| 2 | Deterministic dispatch/routing exists for the supported family | ✅ PASS | `dispatch_and_bridge()` uses tolerant parse → structural fingerprint matching (count + containment detection) → candidate selection → substrate execution. Deterministic: same image always routes to same family |
| 3 | Supported artifact families route correctly | ✅ PASS | All 3 families dispatch to the correct decode path: adjacent_pair→adjacent_pair, containment→containment, three_regions→three_regions. Verified from canonical specs, host-embedded images, and recover-and-dispatch pipeline |
| 4 | Unsupported or ambiguous cases fail honestly | ✅ PASS | Blank image → NO_PRIMITIVES; single_region (1 prim) → UNKNOWN_FAMILY; 4-primitive artifact → UNKNOWN_FAMILY |
| 5 | New tests run successfully | ✅ PASS | Standalone runner: **58/58 passed**; Pytest shim: **31/31 passed** |
| 6 | Existing locked baseline package remains intact and runnable | ✅ PASS | All 17 standalone runners pass from clean-room extraction |
| 7 | Existing bridges remain intact | ✅ PASS | Raster, capture tolerance, localization, orientation normalization, perspective normalization, composed recovery — all tests pass unchanged |
| 8 | Framing stays narrow and honest | ✅ PASS | Module docstring: "narrow deterministic dispatch proof, not general artifact classification or open-ended versioning" |
| 9 | Returned zip ACTUALLY CONTAINS the new dispatch files | ✅ PASS | `artifact_dispatch_bridge_v1.py`, `test_artifact_dispatch_bridge_v1.py`, `run_v1_artifact_dispatch_tests.py` — all confirmed in 58-file zip |
| 10 | Returned zip is clean-room verified after packaging | ✅ PASS | Extracted to `/tmp/cleanroom_dispatch/`, imported successfully, **17/17 standalone runners pass** |

**Result: 10/10 PASS**

---

## Dispatch Families

| Family | Fingerprint | Disambiguator |
|--------|------------|---------------|
| adjacent_pair | 2 prims, (ADJACENT,) | 2-prim + NOT containment (bbox check) |
| containment | 2 prims, (CONTAINS,) | 2-prim + IS containment (bbox check) |
| three_regions | 3 prims, (ADJACENT, ADJACENT) | Unique prim count (3) |

---

## Test Counts

| Category | Count |
|----------|-------|
| Standalone assertions (dispatch bridge) | 58 |
| Pytest functions (dispatch bridge) | 31 |
| Total standalone assertions (all V1) | 1094 |
| Total pytest functions (all V1) | 498 |
| Standalone runners (all V1) | 17 |

---

## Honest Limits

- This is bounded artifact-family routing among exactly 3 frozen types, NOT general artifact classification.
- Disambiguation uses bounding-box containment detection with a 5px margin — robust for the frozen canonical specs but not proven for arbitrary shapes.
- The single_region and non_adjacent fixture types are NOT in the frozen dispatch family. single_region fails with UNKNOWN_FAMILY. non_adjacent dispatches as adjacent_pair (structurally identical — same primitive count, same operation type, different spatial result).
- Evidence tier: AUTHORED. Synthetic test assets only.

---

## Files Added

- `aurexis_lang/src/aurexis_lang/artifact_dispatch_bridge_v1.py` — Source module
- `tests/test_artifact_dispatch_bridge_v1.py` — Pytest test file
- `tests/standalone_runners/run_v1_artifact_dispatch_tests.py` — Standalone runner

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
