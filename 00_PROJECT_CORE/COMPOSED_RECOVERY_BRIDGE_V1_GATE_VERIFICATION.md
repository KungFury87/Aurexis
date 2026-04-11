# Composed Recovery Bridge V1 — Gate Verification

**Date:** April 10, 2026
**Implementer:** Claude (constrained implementer)
**Authority chain:** Vincent > Master Law > Frozen spec > Code/tests > Task instructions

---

## Gate Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frozen composed-recovery profile exists | ✅ PASS | `ComposedProfile(host_width=800, host_height=800, supported_angles=(0,90,180,270), max_corner_offset_px=30, max_brightness_shift=20, max_contrast_deviation=0.10, max_noise_amplitude=15)` — all bounds inherited from individual bridge profiles, none widened |
| 2 | Deterministic composed host-image generation exists | ✅ PASS | `generate_composed_host_image()` applies render → rotate → warp → degrade → scale → blit chain; produces identical bytes on repeated calls |
| 3 | Composed recovery works for in-bounds cases | ✅ PASS | 10 in-bounds cases × adjacent_pair fixture all RECOVERED; 4 containment cases RECOVERED; 3 three_regions cases RECOVERED. Includes 3 full-composition cases exercising rotation + distortion + degradation + scale simultaneously |
| 4 | Unsupported or out-of-bounds composed cases fail honestly | ✅ PASS | 4 OOB cases: off-canvas (NOT_FOUND), extreme non-frozen distortion (NOT_FOUND), extreme combined degradation (TRANSFORM_UNKNOWN), extreme miniaturization (NOT_FOUND) — all correctly rejected |
| 5 | New tests run successfully | ✅ PASS | Standalone runner: **72/72 passed**; Pytest shim: **35/35 passed** |
| 6 | Existing locked baseline package remains intact and runnable | ✅ PASS | All 16 standalone runners pass from clean-room extraction; 15 pre-existing + 1 new |
| 7 | Existing bridges remain intact | ✅ PASS | Raster, capture tolerance, localization, orientation normalization, perspective normalization — all tests pass unchanged |
| 8 | Framing stays narrow and honest | ✅ PASS | Module docstring: "narrow integrated recovery proof, not general invariance or camera-complete behavior"; no claims of full Aurexis Core completion |
| 9 | Returned zip ACTUALLY CONTAINS the new files | ✅ PASS | `composed_recovery_bridge_v1.py`, `test_composed_recovery_bridge_v1.py`, `run_v1_composed_recovery_tests.py` — all confirmed in 55-file zip |
| 10 | Returned zip is clean-room verified after packaging | ✅ PASS | Extracted to `/tmp/cleanroom_v2/`, imported successfully, **16/16 standalone runners pass** |

**Result: 10/10 PASS**

---

## Composed Cases Exercised

| # | Label | Rotation | Distortion | Degradation | Scale | Result |
|---|-------|----------|------------|-------------|-------|--------|
| 0 | identity_baseline | 0° | identity | none | 1.0 | RECOVERED |
| 1 | rotation_90_only | 90° | identity | none | 1.0 | RECOVERED |
| 2 | h_keystone_only | 0° | h_keystone_mild | none | 1.0 | RECOVERED |
| 3 | degradation_only | 0° | identity | bright+noise | 1.0 | RECOVERED |
| 4 | rot180_v_keystone | 180° | v_keystone_mild | none | 0.95 | RECOVERED |
| 5 | rot270_contrast | 270° | identity | contrast | 1.0 | RECOVERED |
| 6 | corner_pull_brightness | 0° | corner_pull | brightness | 1.0 | RECOVERED |
| 7 | **full_composition** | 90° | h_keystone_mild | bright+noise | 0.90 | RECOVERED |
| 8 | **full_composition** | 270° | mild_trapezoid | contrast | 0.95 | RECOVERED |
| 9 | **full_composition** | 180° | h_keystone_rev | bright+noise | 1.0 | RECOVERED |

---

## Test Counts

| Category | Count |
|----------|-------|
| Standalone assertions (composed bridge) | 72 |
| Pytest functions (composed bridge) | 35 |
| Total standalone assertions (all V1) | 1036 |
| Total pytest functions (all V1) | 467 |
| Standalone runners (all V1) | 16 |

---

## Honest Limits

- This is bounded multi-transform recovery, NOT general transform invariance or camera-complete behavior.
- The composed profile inherits all bounds from the individual bridges and does NOT widen any bound.
- The exhaustive trial is O(4 angles × 7 distortions) = 28 candidates per extraction. This is tractable for the frozen family but would not scale to unconstrained transforms.
- Mild distortions currently detect as "identity" distortion because the tolerant parser absorbs them. This is correct — the pipeline confirms recoverability regardless of which inverse produces the match.
- Evidence tier: AUTHORED. Synthetic test assets only, never real camera captures.

---

## Files Added

- `aurexis_lang/src/aurexis_lang/composed_recovery_bridge_v1.py` — Source module
- `tests/test_composed_recovery_bridge_v1.py` — Pytest test file
- `tests/standalone_runners/run_v1_composed_recovery_tests.py` — Standalone runner

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
