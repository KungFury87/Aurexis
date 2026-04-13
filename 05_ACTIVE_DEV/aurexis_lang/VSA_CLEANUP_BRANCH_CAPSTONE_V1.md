# VSA / HYPERDIMENSIONAL CLEANUP BRANCH — CAPSTONE VERIFICATION

**Branch:** VSA Cleanup (Bridges 37-40)
**Date:** April 13, 2026
**Auditor:** Claude (constrained implementer)
**Owner:** Vincent Anderson

---

## Branch Summary

This branch proves that a bounded hyperdimensional (VSA) cleanup layer can be built as an AUXILIARY helper to the deterministic substrate:
1. **Defined** a frozen cleanup profile mapping 11 substrate outputs to VSA symbol IDs (Bridge 37)
2. **Implemented** MAP-style hypervector operations: atomic generation, binding, bundling, permutation (Bridge 38)
3. **Demonstrated** bounded noise-tolerant cleanup retrieval from noisy/composed vectors (Bridge 39)
4. **Validated** VSA recovery against deterministic substrate truth, keeping VSA subordinate (Bridge 40)

---

## Branch Bridges

| # | Bridge | Assertions | Pytest Fns | Gate |
|---|--------|-----------|------------|------|
| 37 | VSA Cleanup Profile V1 | 64 | 15 | 15/15 PASS |
| 38 | Hypervector Binding / Bundling V1 | 55 | 23 | 17/17 PASS |
| 39 | Cleanup Retrieval V1 | 100 | 11 | 15/15 PASS |
| 40 | VSA Consistency / Contract V1 | 73 | 10 | 15/15 PASS |
| **Total** | | **292** | **59** | **62/62 PASS** |

---

## What This Branch Proves

- 11 frozen cleanup targets (5 set contracts + 3 sequence contracts + 3 collection contracts) mapped to VSA symbols.
- 1024-dimensional bipolar hypervectors with deterministic generation.
- Binding is self-inverse. Bundling preserves component similarity. Permutation encodes order.
- Cleanup retrieval recovers correct symbol at up to 20%+ bit-flip noise.
- VSA recovery is cross-checked against substrate truth: 11/11 CONSISTENT at 0% and 10% noise.
- All 3 rejection paths tested: mismatch, VSA failure, unknown target.

## What This Branch Does NOT Prove

- Full hyperdimensional computing generality
- VSA as a replacement for the deterministic substrate
- Noise-robust real-camera cleanup
- Full Aurexis Core completion

---

## Honest Limits

- Dimension (1024) is small — sufficient for bounded demo but not production scale.
- Noise model is simple bit-flip — real-world noise is more complex.
- Codebook has only 11 entries — VSA advantages scale with larger vocabularies.
- VSA is explicitly AUXILIARY — it compresses/cleans substrate outputs but the deterministic substrate remains the truth layer.

---

## Cumulative Totals (After Branch)

- **Bridges:** 40 (18 static + 10 temporal + 4 higher-order + 4 view-dependent + 4 VSA cleanup)
- **Standalone assertions:** 5895 (5603 prior + 292 new)
- **Pytest functions:** 1244 (1185 prior + 59 new)
- **Standalone runners:** 50 (46 prior + 4 new)
- **Source modules:** 52 (48 prior + 4 new)

---

## Branch Verdict: COMPLETE-ENOUGH

All 4 bridges pass gate verification. The VSA cleanup branch is complete as a bounded auxiliary helper layer proof. This is NOT a general hyperdimensional computing engine or a replacement for the deterministic substrate — it is a bounded noise-tolerant cleanup and consistency-check layer.

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
