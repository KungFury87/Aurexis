# AUREXIS CORE — NEW MILESTONE LADDER (ChatGPT-Defined)

Source: ChatGPT planner/auditor, April 9, 2026
Status: Active — governs implementation order for Core substrate work

This ladder runs PARALLEL to the product roadmap (M6-M11, which are complete).
These milestones address the substrate — turning Aurexis from a working prototype
into a deterministic visual computing system.

---

## M0: Baseline Freeze — ✅ COMPLETE
**Deliverable:** M0_BASELINE_REALITY_MAP.md
Honest reality map of entire codebase. Classification of all 88 modules as
LIVE/PARTIAL/SCAFFOLD/DEAD, deterministic vs heuristic inventory, test inventory,
gap analysis.

## M1: Deterministic Visual Semantics V1 — ✅ COMPLETE
**Deliverables:** visual_grammar_v1.py, visual_grammar_v1_fixtures.py,
visual_executor_v1.py, visual_parser_v1.py, visual_grammar_v1_heuristic_remainder.py,
test_visual_grammar_v1.py, M1_GATE_VERIFICATION.md

First law-bearing slice of Core. Three primitives (REGION, EDGE, POINT), three
operations (ADJACENT, CONTAINS, BIND), frozen law thresholds, deterministic
executor, 192 tests, 26 canonical fixtures, explicit heuristic boundary.

## M2: Canonical Parse Rules
**Goal:** Formal rules that convert a GrammarFrame (set of visual primitives with
evaluated relations) into a structured program representation. This is the bridge
from "what do I see?" (M1) to "what does it mean as a program?"

Required outputs:
- Frozen parse rule set (input pattern → output structure)
- Canonical fixtures with expected parse outputs
- Deterministic tests proving same frame → same parse tree
- Integration with V1 grammar types

## M3: Image-as-Program Execution
**Goal:** Given a parsed program from M2, execute it deterministically.
Proves that a photograph can be treated as source code.

## M4: Print/Scan Stability
**Goal:** Prove that the same program survives print → photograph → re-parse
with deterministic output. The physical-world round-trip.

## M5: Multi-Frame Temporal Law
**Goal:** Formal rules for consistency across frames over time.
Currently heuristic (multi_frame_consistency.py uses magic thresholds).

## M6: Formal Type System
**Goal:** Type-check visual programs. Prevent ill-formed compositions.

## M7: Composition and Modularity
**Goal:** Visual programs that reference other visual programs.
Composability rules under law.

## M8: Hardware Calibration Law
**Goal:** Formal relationship between camera hardware properties
and extraction confidence. Hardware-derived ceiling caps raw
confidence (which may still be heuristic from CV extraction).

## M9: Self-Hosting Proof
**Goal:** The V1 grammar can describe its own primitive kinds, operations,
and law as valid visual programs within itself (narrow self-hosting).

## M10: Substrate Integration
**Goal:** Narrow V1 substrate candidate with a unified integration path.
Integration coherence verification confirms the package holds together.
This completes the V1 substrate ladder — not full Aurexis Core.

---

## Rules
- Do not skip milestones
- Each milestone gets a gate verification
- Heuristics must be temporary, explicit, and replaceable
- Vincent's word overrides everything

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
