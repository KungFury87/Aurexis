# VIEW-DEPENDENT CONTRACT BRIDGE V1 — GATE VERIFICATION

**Bridge:** 36th (View-Dependent Contract)
**Date:** April 13, 2026
**Auditor:** Claude (constrained implementer)
**Owner:** Vincent Anderson

---

## What This Bridge Proves

Given a recovery result from the view-facet recovery bridge, the contract validates: (1) the recovered marker name is in the frozen family, (2) the recovered viewpoint is in the allowed bucket set, (3) the recovered facet hash matches the expected facet for that marker+viewpoint, (4) the identity hash matches the frozen marker's identity hash. All validation is against the frozen V1 marker profile.

## What This Bridge Does NOT Prove

- Full 3D contract generality
- Continuous viewpoint contract coverage
- Noise-robust real-camera contract enforcement
- Full Aurexis Core completion

---

## Gate Checks

| # | Check | Result |
|---|-------|--------|
| 1 | Module version is V1.0 | ✅ PASS |
| 2 | Module frozen flag is True | ✅ PASS |
| 3 | EXPECTED_CONTRACT_COUNT == 4, EXPECTED_VALID_COUNT == 16 | ✅ PASS |
| 4 | V1_CONTRACT_PROFILE has 4 contracts | ✅ PASS |
| 5 | Contract lookup finds all 4 marker names | ✅ PASS |
| 6 | Contract identity hashes match frozen marker identity hashes | ✅ PASS |
| 7 | Contract facet hashes match frozen facet hashes for all 16 combinations | ✅ PASS |
| 8 | All 16 valid recoveries produce VALID verdict | ✅ PASS |
| 9 | Batch validate_all_recoveries returns 16 VALID results | ✅ PASS |
| 10 | Incomplete recovery produces RECOVERY_INCOMPLETE | ✅ PASS |
| 11 | Unknown marker recovery produces UNKNOWN_MARKER | ✅ PASS |
| 12 | Identity mismatch recovery produces INVALID_IDENTITY | ✅ PASS |
| 13 | Facet mismatch recovery produces INVALID_FACET | ✅ PASS |
| 14 | ContractValidationResult serialization correct | ✅ PASS |
| 15 | Profile and contract serialization correct | ✅ PASS |
| 16 | ContractValidationResult is immutable | ✅ PASS |
| 17 | Standalone runner: 144 assertions, ALL PASS | ✅ PASS |
| 18 | Pytest file: 19 test functions | ✅ PASS |

**Result: 18/18 PASS**

---

## Source Module

- **File:** `view_dependent_contract_bridge_v1.py`
- **SHA-256:** `2220eb3cf4ca5e5e8dc764be43e3f7827084087bfa6719ea9386a1717e622c7c`
- **Standalone assertions:** 144
- **Pytest functions:** 19

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
