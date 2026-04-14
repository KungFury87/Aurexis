# Intake-to-Delta Replay Harness V1 — Gate Verification

**Date:** April 13, 2026
**Bridge:** 50 (intake_to_delta_replay_harness_v1)
**Runner:** run_v1_intake_to_delta_replay_tests.py
**Evidence Tier:** AUTHORED only

---

## Gate Results: 12/12 PASS

| # | Section | Tests | Status |
|---|---------|-------|--------|
| 1 | Module version and frozen state | 2 | PASS |
| 2 | Stage and verdict counts | 2 | PASS |
| 3 | Fixture pack availability | 4 | PASS |
| 4 | valid_phone_jpeg full pipeline | 7 | PASS |
| 5 | valid_scanner_tiff full pipeline | 4 | PASS |
| 6 | valid_two_file full pipeline | 3 | PASS |
| 7 | invalid_missing_fields expected rejection | 3 | PASS |
| 8 | invalid_bad_extension expected rejection | 2 | PASS |
| 9 | invalid_duplicate_files expected rejection | 2 | PASS |
| 10 | Run all replays full pack | 7 | PASS |
| 11 | Serialization | 5 | PASS |
| 12 | Hash determinism | 1 | PASS |

**Total assertions: 42 — ALL PASS**

---

## What This Bridge Proves

- The full 5-stage pipeline (preflight → ingest → manifest → delta → recommendation) can be exercised end-to-end using authored fixtures
- Valid authored packs reach ALL_STAGES_PASSED with expected delta verdicts
- Invalid authored packs produce EXPECTED_REJECTION at preflight
- Replay results are deterministic and hashable
- All 6 fixtures in the V1 fixture pack produce correct outcomes

## What This Bridge Does NOT Prove

- Real-world camera robustness
- Processing of actual user-supplied capture files
- Automatic self-improvement
- Full Aurexis Core completion

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
