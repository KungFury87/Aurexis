# AUREXIS CORE — ACCEPTED STATUS

## Package Label

**Aurexis Core V1 Substrate Candidate**
A real, narrow, law-bearing substrate package — not full Aurexis Core completion.

---

## What This Package Is

This is a narrow V1 substrate slice of Aurexis Core containing a frozen visual grammar, a deterministic law-governed semantics layer, and a top-level integration path. It is a real, coherent, substantive Aurexis milestone package.

The package contains:

- A frozen V1 grammar with 3 primitive kinds (REGION, EDGE, POINT) and 3 operations (ADJACENT, CONTAINS, BIND) governed by immutable law thresholds.
- A deterministic parser, executor, type system, composition layer, calibration law, stability prover, temporal consistency checker, and a narrow self-hosting proof — all operating on the law-governed semantics layer after inputs enter the grammar.
- A top-level substrate integration path (`substrate_v1.py`) that wires these subsystems together.
- 630 reproducible test assertions across 10 standalone test runners, all passing and all shipped in `tests/standalone_runners/`. Additionally, 139 pytest-format test functions in 10 pytest files in `tests/`.

## What This Package Is NOT

- **Not full Aurexis Core.** The broader Aurexis Core vision encompasses capabilities beyond this narrow V1 substrate slice.
- **Not the final/full visual computing substrate** in the broad project sense. This is a candidate package for one law-bearing slice.
- **Not end-to-end non-heuristic.** Primitive extraction at the CV input layer may be heuristic. The deterministic guarantee applies to the law-governed relation evaluation and semantics after inputs enter the grammar. The grammar explicitly tracks this via `ExecutionStatus.HEURISTIC_INPUT` vs `ExecutionStatus.DETERMINISTIC`.

## What Is Truly Proven

- **Frozen grammar law:** The V1 law thresholds are immutable. Same input primitives → same relation evaluations → same verdicts.
- **Deterministic semantics layer:** Once primitives enter the grammar, all relation evaluation, type checking, program execution, composition, and self-hosting operate deterministically under frozen law.
- **Narrow self-hosting:** The grammar describes its own primitive kinds, operations, and law as 7 valid, well-typed, executable visual meta-programs. These compose with each other. This is self-hosting in the narrow sense defined by the code — the grammar has enough expressive power to describe its own structure. It is not a claim of Turing-completeness or runtime self-modification.
- **Stability and temporal checks exist and pass their own tests.** Stability is exercised via `prove_stability()` and temporal via `prove_temporal_consistency()`. The `process_image()` pipeline calibrates, parses, type-checks, and executes — it does NOT itself run stability testing. The broader `verify_substrate()` exercises subsystem proofs including stability.
- **630 test assertions pass reproducibly** from the standalone runners shipped at `tests/standalone_runners/`. Each runner uses no external dependencies (no pip install required). The command to reproduce is: `cd tests/standalone_runners && python run_v1_<name>.py` for each of the 10 runners.

## What Is Still Not Claimed

- Full Aurexis Core completion.
- That all subsystems have equally strong independent proof. `verify_substrate()` is an integration coherence check — it exercises each subsystem through a representative test path. Grammar and parse rules are counted by their successful use in downstream subsystems, not by independent formal proof.
- That the system is non-heuristic end-to-end. The input/extraction boundary is explicitly heuristic.
- That `process_image()` includes stability testing (it does not).

## Exact Reproducible Test Count

| Suite | Runner | Assertions |
|-------|--------|------------|
| M1: Visual Grammar | run_v1_tests.py | 192 |
| M2: Parse Rules | run_v1_parse_tests.py | 69 |
| M3: Program Executor | run_v1_executor_tests.py | 66 |
| M4: Print/Scan Stability | run_v1_stability_tests.py | 44 |
| M5: Temporal Law | run_v1_temporal_tests.py | 33 |
| M6: Type System | run_v1_type_tests.py | 39 |
| M7: Composition | run_v1_composition_tests.py | 43 |
| M8: Hardware Calibration | run_v1_calibration_tests.py | 56 |
| M9: Self-Hosting | run_v1_selfhost_tests.py | 49 |
| M10: Substrate | run_v1_substrate_tests.py | 39 |
| **Total** | | **630** |

All runners are shipped in the package at `05_ACTIVE_DEV/tests/standalone_runners/` and require only Python 3.x with no external dependencies.

## Milestone Framing

This package represents milestones M0 through M10 of the Aurexis Core substrate ladder — a narrow V1 substrate candidate, not the completion of Aurexis Core as a whole.

---

## Baseline Lock

This file is the accepted status for the locked baseline **aurexis-core-v1-substrate-candidate**. Future work must preserve this baseline as a historical reference point. No future pass may retroactively upgrade this package's meaning to "full Aurexis Core" or blur the narrow framing established here.

See also: `BASELINE_LOCK_V1_SUBSTRATE_CANDIDATE.md`, `LOCK_MANIFEST_V1_SUBSTRATE_CANDIDATE.json`

---

**Acceptance verdict issued by:** ChatGPT (planner/auditor)
**Date:** April 9, 2026
**Locked:** April 9, 2026
**Owner:** Vincent Anderson

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
