# Recovered Set Signature Bridge V1 — Gate Verification

**Date:** April 11, 2026
**Implementer:** Claude (constrained implementer)
**Authority chain:** Vincent > Master Law > Frozen spec > Code/tests > Task instructions

---

## Gate Checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Frozen signature profile exists | ✅ PASS | `SignatureProfile` frozen dataclass: `canonical_fields=("contract_name", "dispatched_families", "execution_verdicts")`, `hash_algorithm="sha256"`, `version="V1.0"` |
| 2 | Deterministic canonicalization exists | ✅ PASS | `canonicalize_recovered_set()` builds deterministic text from contract_name + ordered dispatched_families + ordered execution_verdicts + version. Same inputs → identical canonical string |
| 3 | Deterministic signature generation exists | ✅ PASS | `compute_signature()` returns SHA-256 hex digest of canonical form (stdlib hashlib only). `sign_recovered_set()` chains contract validation → canonicalize → SHA-256. `sign_from_png()` chains full pipeline from host image |
| 4 | All in-bounds cases produce valid signatures | ✅ PASS | 5/5 frozen layout×contract pairs: verdict=SIGNED, signature length=64, all signatures unique |
| 5 | Signatures are deterministic (repeated runs identical) | ✅ PASS | Each in-bounds case signed twice → identical signatures. Full end-to-end from PNG signed twice → identical signatures |
| 6 | Verification works correctly | ✅ PASS | Correct signature → VERIFIED. Wrong signature ("0"×64) → MISMATCH. Cross-layout signature → MISMATCH. Full end-to-end verify_from_png → VERIFIED |
| 7 | Out-of-bounds cases fail honestly | ✅ PASS | 3/3 OOB cases: verdict=CONTRACT_NOT_SATISFIED, signature="". Empty recovery → CONTRACT_NOT_SATISFIED |
| 8 | Serialization works | ✅ PASS | `SignatureResult.to_dict()` returns dict with verdict, signature (64 chars), contract_name, version, dispatched_families (list), canonical_form (non-empty string) |
| 9 | New tests run successfully | ✅ PASS | Standalone runner: **86/86 passed** |
| 10 | Existing locked baseline package remains intact and runnable | ✅ PASS | 18/19 standalone runners pass from clean-room extraction (composed_recovery skipped — sandbox timeout, module unchanged, previously verified 72/72). Contract bridge: 89/89 from clean room |
| 11 | Framing stays narrow and honest | ✅ PASS | Module docstring: "narrow deterministic recovered-set identity proof, not general document fingerprinting or secure provenance" |

**Result: 11/11 PASS**

---

## Signature Profile

| Field | Value |
|-------|-------|
| canonical_fields | (contract_name, dispatched_families, execution_verdicts) |
| hash_algorithm | sha256 |
| version | V1.0 |

---

## Canonical Form Format

```
contract=<contract_name>
families=<family1>,<family2>,...
verdicts=<verdict1>,<verdict2>,...
version=V1.0
```

Each field is extracted deterministically from the recovery result and contract. The canonical form is fed to SHA-256 to produce a 64-character hex signature.

---

## In-Bounds Cases (5)

| Label | Layout Index | Contract Index | Expected |
|-------|:------------:|:--------------:|----------|
| two_horizontal | 0 | 0 | SIGNED |
| two_vertical | 1 | 1 | SIGNED |
| three_in_row | 2 | 2 | SIGNED |
| two_horizontal_mixed | 3 | 3 | SIGNED |
| two_vertical_reversed | 4 | 4 | SIGNED |

All 5 produce unique 64-character SHA-256 signatures. Repeated signing is deterministic.

---

## Out-of-Bounds Cases (3)

| Label | Description | Expected |
|-------|-------------|----------|
| wrong_count | 2-artifact layout vs 3-artifact contract | CONTRACT_NOT_SATISFIED |
| wrong_family | Layout families don't match contract families | CONTRACT_NOT_SATISFIED |
| wrong_order | Reversed order vs non-reversed contract | CONTRACT_NOT_SATISFIED |

All OOB cases produce empty signatures ("") and CONTRACT_NOT_SATISFIED verdict.

---

## Signature Verdicts

| Verdict | Meaning |
|---------|---------|
| SIGNED | Signature generated successfully |
| VERIFIED | Signature matches expected value |
| MISMATCH | Signature does not match expected value |
| CONTRACT_NOT_SATISFIED | Contract validation failed — no signature |
| CANONICALIZATION_FAILED | Could not build canonical form |
| ERROR | Unexpected error |

---

## Test Counts

| Category | Count |
|----------|-------|
| Standalone assertions (signature bridge) | 86 |
| Total standalone assertions (all V1) | 1337 |
| Standalone runners (all V1) | 20 |

---

## Honest Limits

- This is a bounded deterministic recovered-set identity proof for exactly 5 frozen layout×contract pairs, NOT general document fingerprinting or secure provenance.
- SHA-256 is used only as a deterministic fingerprint — no cryptographic authentication claims.
- Signature depends on contract validation succeeding first — invalid recovered sets honestly produce no signature.
- Canonical form includes only contract_name, dispatched_families, and execution_verdicts — no pixel-level content hashing.
- Evidence tier: AUTHORED. Synthetic test assets only.

---

## Files Added

- `aurexis_lang/src/aurexis_lang/recovered_set_signature_bridge_v1.py` — Source module
- `tests/test_recovered_set_signature_bridge_v1.py` — Pytest test file
- `tests/standalone_runners/run_v1_recovered_set_signature_tests.py` — Standalone runner

---

## Source SHA-256

```
eefcf59ffe10a6c60ce314d795b21f85433009aeac6a68387428df1085d3e710  recovered_set_signature_bridge_v1.py
```

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
