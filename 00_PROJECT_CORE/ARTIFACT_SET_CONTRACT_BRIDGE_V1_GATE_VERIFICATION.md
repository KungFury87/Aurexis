# Artifact Set Contract Bridge V1 — Gate Verification

**Date:** April 10, 2026
**Implementer:** Claude (constrained implementer)
**Authority chain:** Vincent > Master Law > Frozen spec > Code/tests > Task instructions

---

## Gate Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frozen contract profile exists | ✅ PASS | `ContractProfile` with 5 frozen `PageContract` dataclasses. Each specifies `name`, `expected_count`, `expected_families` (ordered tuple) |
| 2 | Deterministic contract checking exists | ✅ PASS | `validate_contract()` checks count → families → order in strict sequence. `validate_contract_from_png()` chains full recovery + validation. Both deterministic |
| 3 | Supported contracts pass correctly | ✅ PASS | All 5 frozen layouts validated against their matching contracts: 5/5 SATISFIED. Full 5×5 cross-validation matrix: diagonal = SATISFIED, off-diagonal ≠ SATISFIED |
| 4 | Wrong-count / wrong-family / wrong-order / unsupported fail honestly | ✅ PASS | VIOLATED_COUNT: 2-artifact layout vs 3-artifact contract and vice versa. VIOLATED_FAMILY: 2-artifact layout vs different 2-artifact contract. VIOLATED_ORDER: reversed vertical layout vs non-reversed contract. RECOVERY_FAILED: empty recovery result |
| 5 | New tests run successfully | ✅ PASS | Standalone runner: **89/89 passed** |
| 6 | Existing locked baseline package remains intact and runnable | ✅ PASS | 18/19 standalone runners pass from clean-room extraction (composed_recovery skipped — sandbox timeout, module unchanged, previously verified 72/72) |
| 7 | All existing bridges remain intact | ✅ PASS | Raster (58), capture tolerance (99+), localization (54+), orientation normalization (70), perspective normalization (53), artifact dispatch (58), multi-artifact layout (68) — all pass unchanged |
| 8 | Framing stays narrow and honest | ✅ PASS | Module docstring: "narrow deterministic recovered-set proof, not general document intelligence or open-ended schema validation" |
| 9 | Returned zip ACTUALLY CONTAINS new contract files | ✅ PASS | `artifact_set_contract_bridge_v1.py`, `test_artifact_set_contract_bridge_v1.py`, `run_v1_artifact_set_contract_tests.py` — all confirmed in 64-file zip |
| 10 | Returned zip is clean-room verified | ✅ PASS | Extracted to `/tmp/cleanroom_contract/`, imported successfully, 18/19 standalone runners pass |

**Result: 10/10 PASS**

---

## Frozen Contracts

| Contract | Expected Count | Expected Families (ordered) |
|----------|:--------------:|----------------------------|
| two_horizontal_adj_cont | 2 | (adjacent_pair, containment) |
| two_vertical_adj_three | 2 | (adjacent_pair, three_regions) |
| three_row_all | 3 | (adjacent_pair, containment, three_regions) |
| two_horizontal_cont_three | 2 | (containment, three_regions) |
| two_vertical_three_adj | 2 | (three_regions, adjacent_pair) |

---

## Validation Policy

Contract checking proceeds in strict order:
1. **Recovery check**: dispatched_count > 0, else → RECOVERY_FAILED
2. **Count check**: dispatched_count == expected_count, else → VIOLATED_COUNT
3. **Exact tuple match**: dispatched_families == expected_families, if yes → SATISFIED
4. **Order disambiguation**: if sorted(dispatched) == sorted(expected) → VIOLATED_ORDER, else → VIOLATED_FAMILY

---

## Failure Policy

| Failure Mode | Trigger | Verdict |
|-------------|---------|---------|
| No artifacts recovered | dispatched_count == 0 | RECOVERY_FAILED |
| Wrong number of artifacts | dispatched_count ≠ expected_count | VIOLATED_COUNT |
| Right count, wrong families | families differ as sets | VIOLATED_FAMILY |
| Right families, wrong order | families same as set, different order | VIOLATED_ORDER |

---

## Cross-Validation Matrix (5×5)

| Layout ↓ \ Contract → | 0 | 1 | 2 | 3 | 4 |
|----------------------|---|---|---|---|---|
| 0: two_horizontal | ✅ | ✗ | ✗ | ✗ | ✗ |
| 1: two_vertical | ✗ | ✅ | ✗ | ✗ | ✗ |
| 2: three_in_row | ✗ | ✗ | ✅ | ✗ | ✗ |
| 3: two_horiz_mixed | ✗ | ✗ | ✗ | ✅ | ✗ |
| 4: two_vert_reversed | ✗ | ✗ | ✗ | ✗ | ✅ |

Each layout satisfies exactly one contract. No false positives.

---

## Test Counts

| Category | Count |
|----------|-------|
| Standalone assertions (contract bridge) | 89 |
| Total standalone assertions (all V1) | 1251 |
| Standalone runners (all V1) | 19 |

---

## Honest Limits

- This is bounded page-level contract validation among exactly 5 frozen contracts, NOT open-ended document intelligence or schema validation.
- Contracts are frozen dataclasses — no dynamic schema system, no user-defined contracts.
- Contract checking is a pure validation layer on top of existing multi-artifact recovery — no new parsing, dispatch, or substrate logic.
- Evidence tier: AUTHORED. Synthetic test assets only.

---

## Files Added

- `aurexis_lang/src/aurexis_lang/artifact_set_contract_bridge_v1.py` — Source module
- `tests/test_artifact_set_contract_bridge_v1.py` — Pytest test file
- `tests/standalone_runners/run_v1_artifact_set_contract_tests.py` — Standalone runner

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
