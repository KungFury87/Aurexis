# AUREXIS CORE — M1 GATE VERIFICATION

Milestone: M1 — Deterministic Visual Semantics V1
Date: April 9, 2026
Verifier: Claude (constrained implementer)

---

## Gate Checklist

| # | Gate Item | Status | Evidence |
|---|-----------|--------|----------|
| 1 | SPEC_FROZEN | PASS | `visual_grammar_v1.py` — GRAMMAR_VERSION="V1.0", GRAMMAR_FROZEN=True, GrammarLaw is frozen dataclass |
| 2 | FIXTURES_PRESENT | PASS | `visual_grammar_v1_fixtures.py` — 26 canonical fixtures across 5 categories |
| 3 | EXPECTED_OUTPUTS_PRESENT | PASS | Every fixture has exact expected_result, expected_measured_value, expected_law_threshold |
| 4 | DETERMINISTIC_TESTS_PASS | PASS | 192/192 tests passed — includes determinism checks (10x repeat), symmetry checks, boundary cases |
| 5 | EXECUTABLE_SUBSET_PRESENT | PASS | `visual_executor_v1.py` — evaluate_adjacent, evaluate_contains, evaluate_bind, execute_frame |
| 6 | HEURISTIC_REMAINDER_DECLARED | PASS | `visual_grammar_v1_heuristic_remainder.py` — 11 deterministic items, 6 heuristic items, explicit boundary |

**Result: 6/6 PASS — M1 gate cleared.**

---

## V1 Law Summary

Three primitives: REGION, EDGE, POINT
Three operations: ADJACENT (edge distance <= 30px), CONTAINS (min margin >= 0px), BIND (name assignment)
One output type: Relation with deterministic TRUE/FALSE result

Frozen thresholds:
- adjacent_max_distance_px = 30.0
- contains_min_margin_px = 0.0
- min_primitive_area_px2 = 4.0
- max_primitives_per_frame = 200

---

## Test Evidence

- 192 tests, 0 failures
- 10 ADJACENT fixtures (touching, overlapping, near, exact threshold, beyond, far, diagonal x2, mixed types, heuristic flagging)
- 6 CONTAINS fixtures (full, exact, partial overlap, outside, point-in-region, asymmetry)
- 3 BIND fixtures (region, point, edge)
- 4 VALIDITY fixtures (minimum area, below minimum, zero width, zero height)
- 3 FRAME fixtures (3-region adjacency, nested containment, max primitive cap)
- Symmetry verified for all ADJACENT pairs
- Determinism verified (10x repeat) for all fixtures
- Parser roundtrip verified
- Full pipeline determinism verified (5x repeat)

---

## Files Delivered

| File | Purpose |
|------|---------|
| `aurexis_lang/src/aurexis_lang/visual_grammar_v1.py` | Frozen V1 spec (law, types, schemas) |
| `aurexis_lang/src/aurexis_lang/visual_grammar_v1_fixtures.py` | 26 canonical fixtures with expected outputs |
| `aurexis_lang/src/aurexis_lang/visual_executor_v1.py` | Deterministic executor (ADJACENT, CONTAINS, BIND, frame) |
| `aurexis_lang/src/aurexis_lang/visual_parser_v1.py` | Deterministic parser (CV dict → V1 primitives) |
| `aurexis_lang/src/aurexis_lang/visual_grammar_v1_heuristic_remainder.py` | Explicit heuristic/deterministic boundary |
| `tests/test_visual_grammar_v1.py` | Pytest-compatible test suite (192 tests) |

---

## Ownership

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
Sole inventor and owner: Vincent Anderson.
