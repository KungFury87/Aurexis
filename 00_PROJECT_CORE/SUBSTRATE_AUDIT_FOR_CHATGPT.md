# AUREXIS CORE V1 SUBSTRATE CANDIDATE — AUDIT DOCUMENT

**Date:** April 9, 2026
**Owner:** Vincent Anderson
**Implementer:** Claude (constrained)
**Auditor/Planner:** ChatGPT
**Accepted Label: Aurexis Core V1 Substrate Candidate**
**Status: Narrow V1 law-bearing substrate package — not full Aurexis Core completion.**

---

## 1. MILESTONE LADDER STATUS

Milestones M0–M10 of the substrate ladder are complete. This represents a narrow V1 substrate candidate, not the completion of Aurexis Core as a whole.

| # | Milestone | Gate | Standalone Tests | Files Delivered |
|---|-----------|------|------------------|-----------------|
| M0 | Baseline Freeze | 6/6 PASS | — | M0_BASELINE_REALITY_MAP.md |
| M1 | Deterministic Visual Semantics V1 | 6/6 PASS | 192 | visual_grammar_v1.py, visual_grammar_v1_fixtures.py, visual_parser_v1.py, visual_executor_v1.py |
| M2 | Canonical Parse Rules | 6/6 PASS | 69 | visual_parse_rules_v1.py, visual_parse_rules_v1_fixtures.py |
| M3 | Image-as-Program Execution | 6/6 PASS | 66 | visual_program_executor_v1.py |
| M4 | Print/Scan Stability | 6/6 PASS | 44 | print_scan_stability_v1.py |
| M5 | Multi-Frame Temporal Law | 6/6 PASS | 33 | temporal_law_v1.py |
| M6 | Formal Type System | 6/6 PASS | 39 | type_system_v1.py |
| M7 | Composition and Modularity | 6/6 PASS | 43 | composition_v1.py |
| M8 | Hardware Calibration Law | 6/6 PASS | 56 | hardware_calibration_v1.py |
| M9 | Self-Hosting Proof | 6/6 PASS | 49 | self_hosting_v1.py |
| M10 | Substrate Integration | 6/6 PASS | 39 | substrate_v1.py |
| **TOTAL** | | **66/66 gate items** | **630 assertions** | **14 source + 10 pytest + 10 standalone runners** |

Test count note: The 630 figure comes from 10 standalone test runners shipped at `tests/standalone_runners/`. These require only Python 3.x with no external dependencies. Additionally, 139 pytest-format test functions exist in 10 pytest files at `tests/`. Both suites are included in the package.

---

## 2. SUBSYSTEM VERSION REGISTRY

All subsystems frozen at V1.0. The frozen/deterministic guarantee applies to the law-governed semantics layer — relation evaluation, type checking, execution, composition — after inputs enter the grammar. Primitive extraction at the CV input layer may be heuristic; the grammar explicitly tracks this via `ExecutionStatus.HEURISTIC_INPUT` vs `ExecutionStatus.DETERMINISTIC`.

| Subsystem | Version Constant | Frozen Constant | Value |
|-----------|-----------------|-----------------|-------|
| Grammar | GRAMMAR_VERSION | GRAMMAR_FROZEN | V1.0 / True |
| Parse Rules | PARSE_RULES_VERSION | PARSE_RULES_FROZEN | V1.0 / True |
| Executor | EXECUTOR_VERSION | (implicit) | V1.0 |
| Stability | STABILITY_VERSION | STABILITY_FROZEN | V1.0 / True |
| Temporal | TEMPORAL_VERSION | TEMPORAL_FROZEN | V1.0 / True |
| Type System | TYPE_SYSTEM_VERSION | TYPE_SYSTEM_FROZEN | V1.0 / True |
| Composition | COMPOSITION_VERSION | COMPOSITION_FROZEN | V1.0 / True |
| Calibration | CALIBRATION_VERSION | CALIBRATION_FROZEN | V1.0 / True |
| Self-Hosting | SELF_HOSTING_VERSION | SELF_HOSTING_FROZEN | V1.0 / True |
| Substrate | SUBSTRATE_VERSION | SUBSTRATE_FROZEN | V1.0 / True |

---

## 3. SUBSTRATE COHERENCE VERIFICATION OUTPUT

`verify_substrate()` is an integration coherence check — it exercises each subsystem through a representative test path to confirm the package holds together. Grammar and parse rules are counted by their successful use in downstream subsystems, not by independent formal proof. This is the actual JSON output:

```json
{
  "verdict": "COMPLETE",
  "all_frozen": true,
  "all_versions_v1": true,
  "subsystems_passed": 9,
  "subsystems_total": 9,
  "type_system_works": true,
  "execution_works": true,
  "stability_works": true,
  "temporal_works": true,
  "composition_works": true,
  "calibration_works": true,
  "self_hosting_works": true,
  "errors": [],
  "substrate_version": "V1.0"
}
```

---

## 4. SELF-HOSTING PROOF OUTPUT

The grammar describes its own primitive kinds, operations, and law as 7 valid, well-typed, executable visual meta-programs. This is self-hosting in the narrow sense: the grammar has enough expressive power to describe its own structure as valid programs. It is not a claim of Turing-completeness or runtime self-modification.

```json
{
  "verdict": "SELF_HOSTED",
  "valid_count": 7,
  "total_count": 7,
  "meta_programs": [
    {"describes": "REGION", "is_valid": true, "properties": {"kind": "REGION", "min_area_px2": 4.0}},
    {"describes": "EDGE", "is_valid": true, "properties": {"kind": "EDGE", "aspect": "wide_thin"}},
    {"describes": "POINT", "is_valid": true, "properties": {"kind": "POINT", "characteristic": "small_area"}},
    {"describes": "ADJACENT", "is_valid": true, "properties": {"operation": "ADJACENT", "operand_count": 2, "threshold_px": 30.0}},
    {"describes": "CONTAINS", "is_valid": true, "properties": {"operation": "CONTAINS", "operand_count": 2, "min_margin_px": 0.0}},
    {"describes": "BIND", "is_valid": true, "properties": {"operation": "BIND", "operand_count": 1}},
    {"describes": "V1_LAW", "is_valid": true, "properties": {"grammar_version": "V1.0", "adjacent_max_distance_px": 30.0, "contains_min_margin_px": 0.0, "min_primitive_area_px2": 4.0, "max_primitives_per_frame": 200}}
  ],
  "composition_tested": true,
  "composition_succeeded": true,
  "execution_tested": true,
  "execution_succeeded": true,
  "errors": []
}
```

---

## 5. TEST RESULTS — 630 STANDALONE ASSERTIONS PASSING

Reproduced from `tests/standalone_runners/` (no external dependencies required):

```
M1  (Visual Grammar):       192 passed, 0 failed   run_v1_tests.py
M2  (Parse Rules):            69 passed, 0 failed   run_v1_parse_tests.py
M3  (Program Executor):       66 passed, 0 failed   run_v1_executor_tests.py
M4  (Print/Scan Stability):   44 passed, 0 failed   run_v1_stability_tests.py
M5  (Temporal Law):            33 passed, 0 failed   run_v1_temporal_tests.py
M6  (Type System):             39 passed, 0 failed   run_v1_type_tests.py
M7  (Composition):             43 passed, 0 failed   run_v1_composition_tests.py
M8  (Hardware Calibration):    56 passed, 0 failed   run_v1_calibration_tests.py
M9  (Self-Hosting):            49 passed, 0 failed   run_v1_selfhost_tests.py
M10 (Substrate):               39 passed, 0 failed   run_v1_substrate_tests.py
───────────────────────────────────────────────────────────────────
TOTAL:                        630 passed, 0 failed
```

Each suite includes a determinism check (5x repeated execution, identical output confirmed).

To reproduce: `cd tests/standalone_runners && python run_v1_<name>.py`

---

## 6. FILE INVENTORY

### Source Files (5,419 lines total)
All in `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/`

| File | Lines | Milestone |
|------|-------|-----------|
| visual_grammar_v1.py | 273 | M1 |
| visual_grammar_v1_fixtures.py | 667 | M1 |
| visual_parser_v1.py | 237 | M1 |
| visual_executor_v1.py | 251 | M1 |
| visual_parse_rules_v1.py | 356 | M2 |
| visual_parse_rules_v1_fixtures.py | 347 | M2 |
| visual_program_executor_v1.py | 343 | M3 |
| print_scan_stability_v1.py | 415 | M4 |
| temporal_law_v1.py | 328 | M5 |
| type_system_v1.py | 451 | M6 |
| composition_v1.py | 357 | M7 |
| hardware_calibration_v1.py | 453 | M8 |
| self_hosting_v1.py | 462 | M9 |
| substrate_v1.py | 479 | M10 |

### Pytest Files (139 test functions)
All in `05_ACTIVE_DEV/tests/`

| File | Test Functions | Milestone |
|------|---------------|-----------|
| test_visual_grammar_v1.py | 41 | M1 |
| test_visual_parse_rules_v1.py | 13 | M2 |
| test_visual_program_executor_v1.py | 7 | M3 |
| test_print_scan_stability_v1.py | 9 | M4 |
| test_temporal_law_v1.py | 8 | M5 |
| test_type_system_v1.py | 8 | M6 |
| test_composition_v1.py | 14 | M7 |
| test_hardware_calibration_v1.py | 14 | M8 |
| test_self_hosting_v1.py | 13 | M9 |
| test_substrate_v1.py | 12 | M10 |

### Standalone Test Runners (630 assertions)
All in `05_ACTIVE_DEV/tests/standalone_runners/`

10 files, one per milestone, requiring only Python 3.x.

### Gate Verification Reports
All in `00_PROJECT_CORE/`

M1_GATE_VERIFICATION.md through M10_GATE_VERIFICATION.md (10 files, each confirming 6/6 gate items)

---

## 7. V1 GRAMMAR LAW — FROZEN THRESHOLDS

These are the immutable law values that govern all operations in the deterministic semantics layer:

| Threshold | Value | Used By |
|-----------|-------|---------|
| adjacent_max_distance_px | 30.0 | ADJACENT: edge distance must be <= 30px |
| contains_min_margin_px | 0.0 | CONTAINS: all 4 margins must be >= 0px |
| min_primitive_area_px2 | 4.0 | All: primitives smaller than 4px2 are invalid |
| max_primitives_per_frame | 200 | All: excess primitives dropped (sorted by confidence) |

---

## 8. ARCHITECTURE SUMMARY

### process_image() Pipeline
`process_image()` calibrates, parses, type-checks, and executes. It does NOT run stability testing. Stability is exercised separately via `prove_stability()` and by `verify_substrate()`.

```
Raw CV data (may include heuristic extraction confidence)
  → Hardware Calibration (camera profile caps confidence) [optional]
  → Parse Primitives (CV dicts → typed VisualPrimitive objects)
  → Build Frame (evaluate operations under frozen law)
  → Parse to Program Tree (grammar frame → program nodes)
  → Type Check (reject ill-formed compositions)
  → Execute (deterministic verdict: PASS/FAIL/PARTIAL/EMPTY)
```

### Heuristic Boundary
The grammar explicitly allows heuristic CV extraction at the input layer. Primitives may arrive with `source_confidence < 1.0`, which propagates as `ExecutionStatus.HEURISTIC_INPUT` through relation evaluation and results in `ProgramVerdict.PARTIAL` instead of `ProgramVerdict.PASS`. The deterministic guarantee is: given the same input primitives with the same confidence values, the law-governed evaluation always produces the same output.

### Subsystem Dependencies
```
M1 Grammar ← foundation (primitives, operations, law)
M2 Parse Rules ← M1 (frame → program tree)
M3 Executor ← M2 (program → verdict + trace)
M4 Stability ← M3 (proves physical round-trip survival)
M5 Temporal ← M3 (proves multi-frame consistency)
M6 Type System ← M1, M2, M3 (prevents ill-formed programs)
M7 Composition ← M6 (modules that compose under law)
M8 Calibration ← M1 (hardware → confidence ceiling)
M9 Self-Hosting ← M1-M7 (grammar describes itself, narrow sense)
M10 Substrate ← M1-M9 (integration path, coherence verification)
```

### Key Verdicts
| Verdict | Meaning |
|---------|---------|
| ProgramVerdict.PASS | All assertions TRUE, all inputs deterministic |
| ProgramVerdict.FAIL | At least one assertion FALSE |
| ProgramVerdict.PARTIAL | All TRUE but some heuristic inputs |
| ProgramVerdict.EMPTY | No assertions to evaluate |
| StabilityVerdict.STABLE | Program survives print/scan degradation |
| TemporalVerdict.CONFIRMED | Consistent across confirmation window |
| TypeCheckVerdict.WELL_TYPED | No type errors, safe to execute |
| CompositionVerdict.SUCCESS | Modules merged, result well-typed |
| CalibrationVerdict.CALIBRATED | Hardware ceiling applied |
| SelfHostingVerdict.SELF_HOSTED | Grammar describes itself (narrow sense) |
| SubstrateVerdict.COMPLETE | Integration coherence check passed |

---

## 9. WHAT THIS IS AND IS NOT

**This package IS:**
- A real, coherent, substantive Aurexis milestone package
- A narrow V1 law-bearing substrate candidate
- A frozen grammar with deterministic semantics after input entry
- Self-hosting in the narrow sense (grammar describes its own structure)

**This package IS NOT:**
- Full Aurexis Core
- The final/full visual computing substrate in the broad project sense
- Non-heuristic end-to-end (CV extraction inputs may be heuristic)
- A claim that every subsystem has equally strong independent proof

See `ACCEPTED_STATUS_V1_SUBSTRATE_CANDIDATE.md` for the full acceptance positioning.

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
