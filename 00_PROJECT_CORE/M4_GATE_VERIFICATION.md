# AUREXIS CORE — M4 GATE VERIFICATION

Milestone: M4 — Print/Scan Stability
Date: April 9, 2026
Verifier: Claude (constrained implementer)

---

## Gate Checklist

| # | Gate Item | Status | Evidence |
|---|-----------|--------|----------|
| 1 | STABILITY_CONTRACT_FROZEN | PASS | `print_scan_stability_v1.py` — STABILITY_VERSION="V1.0", STABILITY_FROZEN=True, frozen dataclass |
| 2 | DEGRADATION_DETERMINISTIC | PASS | Same seed → same degradation output (tested with jitter, scale, confidence) |
| 3 | MARGIN_ANALYSIS_PRESENT | PASS | analyze_margins() computes headroom and max safe jitter for each assertion |
| 4 | STABILITY_VERDICTS_DEFINED | PASS | STABLE, UNSTABLE, MARGINAL — each with clear criteria |
| 5 | MULTI_LEVEL_TESTING | PASS | 5 degradation levels tested per proof, covering jitter (0-10px), scale (0.85-1.15), confidence drop (0-0.3) |
| 6 | DETERMINISTIC_TESTS_PASS | PASS | 44/44 tests passed, 5x determinism verified |

**Result: 6/6 PASS — M4 gate cleared.**

---

## What M4 Proves

V1 visual programs survive physical-world degradation within frozen stability bounds:

- **Touching regions** (30px headroom): STABLE — survives full degradation range
- **Well-contained regions** (50px headroom): STABLE — large margin of safety
- **Near-threshold regions** (5px headroom): MARGINAL — correct detection of thin margins
- **Failed assertions** (70px beyond threshold): STABLE — FALSE stays FALSE under degradation
- **Multi-assertion programs**: STABLE — all assertions preserve their verdicts

The stability contract defines:
- Max jitter: 10px per axis
- Max scale: 0.85x to 1.15x
- Max confidence drop: 0.3
- Stability margin: 10px (below this → MARGINAL warning)

---

## Files Delivered

| File | Purpose |
|------|---------|
| `aurexis_lang/src/aurexis_lang/print_scan_stability_v1.py` | Stability contract, degradation, margin analysis, proof |
| `tests/test_print_scan_stability_v1.py` | Pytest-compatible test suite |

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
