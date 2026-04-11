# Recovered Set Signature Match Bridge V1 — Gate Verification

**Date:** April 11, 2026
**Implementer:** Claude (constrained implementer)
**Authority chain:** Vincent > Master Law > Frozen spec > Code/tests > Task instructions

---

## Gate Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frozen expected-signature profile exists | ✅ PASS | `ExpectedSignatureBaseline` frozen dataclass: 5 supported contracts, lazy-computed SHA-256 expected signatures, `version="V1.0"` |
| 2 | Deterministic signature match/mismatch logic exists | ✅ PASS | `match_signature()` signs → looks up expected → compares. `match_from_png()` chains full end-to-end pipeline. Both deterministic |
| 3 | Supported recovered sets match correctly against expected signatures | ✅ PASS | All 5 frozen layout×contract pairs: verdict=MATCH, computed_signature==expected_signature, all 64-char SHA-256 |
| 4 | Changed order / changed family / changed validated content produce honest mismatch or failure | ✅ PASS | 3 OOB cases: wrong_count → SIGN_FAILED, wrong_family → SIGN_FAILED, wrong_order → SIGN_FAILED. Empty recovery → SIGN_FAILED |
| 5 | Unsupported cases fail honestly | ✅ PASS | Unknown contract name → UNSUPPORTED, empty computed/expected signatures |
| 6 | New tests run successfully | ✅ PASS | Standalone runner: **100/100 passed** |
| 7 | Existing locked baseline package remains intact and runnable | ✅ PASS | Signature bridge from clean room: 86/86 PASS. 23 V1 modules imported successfully |
| 8 | Existing bridges remain intact | ✅ PASS | All prior bridge modules unchanged — no modifications to any existing source file except `__init__.py` (added 1 module name) |
| 9 | Framing stays narrow and honest | ✅ PASS | Module docstring: "narrow deterministic recovered-set match proof, not general document fingerprinting or secure provenance" |
| 10 | Returned zip ACTUALLY CONTAINS new match files | ✅ PASS | `recovered_set_signature_match_bridge_v1.py`, `test_recovered_set_signature_match_bridge_v1.py`, `run_v1_recovered_set_signature_match_tests.py` — all confirmed in 70-file zip |
| 11 | Returned zip is clean-room verified | ✅ PASS | Extracted to `/tmp/clean_room_match/`, 23 modules imported, 100/100 standalone runner PASS |
| 12 | Removable GitHub backup pushed | ✅ PASS | Pushed to `https://github.com/KungFury87/Aurexis` via Git Credential Manager (browser OAuth). Commit `457cb8cc` |
| 13 | Remote backup branch exists | ✅ PASS | `backup/v1-substrate-candidate-20260411` verified via `git ls-remote` |
| 14 | Remote backup tag exists | ✅ PASS | `backup-v1-substrate-candidate-20260411` verified via `git ls-remote` |
| 15 | Backup deletion commands written | ✅ PASS | Full deletion commands in `GITHUB_BACKUP_RECORD_V1.md` |

**Result: 15/15 PASS**

---

## Expected-Signature Baseline

| Contract | Supported |
|----------|:---------:|
| two_horizontal_adj_cont | ✅ |
| two_vertical_adj_three | ✅ |
| three_row_all | ✅ |
| two_horizontal_cont_three | ✅ |
| two_vertical_three_adj | ✅ |

5 frozen expected signatures, computed deterministically from the frozen pipeline. Each signature is a unique 64-character SHA-256 hex digest.

---

## Match Policy

1. **Baseline check**: Is the contract_name in the frozen baseline? If not → UNSUPPORTED
2. **Sign**: Generate SHA-256 signature from recovery + contract via existing signature bridge
3. **Sign check**: Did signing succeed? If not → SIGN_FAILED
4. **Lookup**: Get expected signature from frozen baseline
5. **Compare**: computed == expected → MATCH, else → MISMATCH

---

## Match Verdicts

| Verdict | Meaning |
|---------|---------|
| MATCH | Computed signature matches frozen expected value |
| MISMATCH | Computed signature differs from expected value |
| UNSUPPORTED | Contract not in frozen expected-signature baseline |
| SIGN_FAILED | Signature generation failed (contract not satisfied, etc.) |
| ERROR | Unexpected error |

---

## Test Counts

| Category | Count |
|----------|-------|
| Standalone assertions (signature match bridge) | 100 |
| Total standalone assertions (all V1) | 1437 |
| Standalone runners (all V1) | 21 |

---

## Honest Limits

- This is bounded expected-signature verification for exactly 5 frozen layout×contract pairs, NOT general document fingerprinting or secure provenance.
- Expected signatures are computed deterministically from the same frozen pipeline — no external signature authority or pre-shared secrets.
- SHA-256 is used only as a deterministic fingerprint — no cryptographic authentication claims.
- The match layer sits on top of the existing recovery + dispatch + contract + signature path. It adds only a frozen comparison baseline.
- Evidence tier: AUTHORED. Synthetic test assets only.

---

## Files Added

- `aurexis_lang/src/aurexis_lang/recovered_set_signature_match_bridge_v1.py` — Source module
- `tests/test_recovered_set_signature_match_bridge_v1.py` — Pytest test file
- `tests/standalone_runners/run_v1_recovered_set_signature_match_tests.py` — Standalone runner

---

## Source SHA-256

```
660db97d4cc0cdfb780ee624aa55da30ac90652a3def42066fc3b8b7fe530e07  recovered_set_signature_match_bridge_v1.py
```

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
