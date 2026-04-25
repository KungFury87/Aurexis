# Grok audit lane — Aurexis Core

Grok is part of the Aurexis workflow as an **auditor**, not the
primary builder. This document describes how Grok fits into the
unified Core tree, what audit Grok should perform next, and how
Grok's findings flow back into the working tree.

## Lane definition

- **Grok role:** independent third-party auditor.
- **Grok scope:**
  - Inspects the unified Core tree.
  - Sanity-checks frozen V1 surfaces (no retag, no rewrite, no
    silent overwrite of release artifacts).
  - Cross-checks V2 surfaces are preserved, not commingled
    destructively with V1.
  - Reads `06_PROOF_SYSTEM/aurexis_research_sim/reports/PROOF_INDEX.md`
    and validates that confidence states are consistent with the
    underlying boundary + validation evidence.
  - Confirms that no historical git ref (tag or backup branch) was
    mutated in this pass.
- **Grok is NOT the primary builder.** Grok does not author code or
  reframe the project; it audits the work other contributors did.
- **Grok findings flow back via** the audit packet returned to the
  user, who reconciles them and decides whether to apply.

## What Grok should audit next

After this `core v1 incomplete` unification pass, Grok should
produce a written audit answering each of the following:

### Frozen-surface audit

1. Confirm that all 33 git tags are unchanged from the pre-pass
   state.
2. Confirm that all 26 `backup/v1-substrate-candidate-*` branches
   are unchanged.
3. Confirm that ACOR-1.1 (`core-v1-substrate-candidate-or1.1`)
   still points at the same commit as before this pass.
4. Confirm that `00_PROJECT_CORE/` and `01_RELEASES/` and `BACKUPS/`
   contents are byte-identical to the frozen baseline.

### V2-surface audit

5. Confirm that no V2 document at top level (`V2_*.md`) was
   silently modified.
6. Confirm `V2_BENCHMARK_SET/` is unchanged.
7. Confirm `05_ACTIVE_DEV/aurexis_lang/.../v2_decode/` work is
   preserved (the prior-session WIP modifications are still
   present as working-tree changes, not silently committed).

### Unification audit

8. Confirm `06_PROOF_SYSTEM/` is the only NEW top-level directory
   added.
9. Confirm new top-level docs (`ROADMAP.md`, `PROJECT_STATUS.md`,
   `CORE_UNIFICATION_REPORT.md`, `CORE_TREE_MAP.md`,
   `GROK_AUDIT_LANE.md`, `GITHUB_PUSH_PLAN.md`) do not duplicate
   or contradict existing V1 truth-surface docs in
   `00_PROJECT_CORE/`.
10. Confirm `README.md` was UPDATED, not REPLACED — the ACOR-1.1
    release info is still present near the top.
11. Confirm the simulator at
    `06_PROOF_SYSTEM/aurexis_research_sim/` runs and `pytest`
    reports 221 passing.

### Engine-semantics evidence audit

12. Open
    `06_PROOF_SYSTEM/aurexis_research_sim/reports/PROOF_INDEX.md`
    and verify the per-family table is consistent with
    `unlock.json` (boundary tags) +
    `validation.json` (validation verdicts) +
    `confidence.json` (confidence states) +
    `semantic_stability.json` (semantic verdicts).
13. Specifically validate that `ordering` calibrates to **REJECT**
    (PRIMITIVE_AWARE_HELPS at boundary + SUSPECT at validation
    -> REJECT under the v0.6 confidence combinator). This is the
    single most important calibrated finding from v0.6.
14. Specifically validate that `repetition` is
    **SEMANTIC_UNSTABLE** under the naive full-row autocorrelation
    metric tested in `semantic_stability.py`, even though the v1.8
    strip-based metric in `coverage.py` recovers it. The
    Engine-semantics conclusion is that the repetition law
    requires ROI/strip-aware evaluation.

### Push-plan audit

15. Read `GITHUB_PUSH_PLAN.md`. Verify each command:
    - Does NOT delete or move any existing tag or branch.
    - Does NOT force-push to `main`.
    - Creates a new branch `working/core-v1-incomplete`.
    - Pushes the new branch to origin without rewriting history.
16. Note any command that could be destructive if run incorrectly,
    and recommend a safer alternative.

### Flag / hold / accept

For each section above, Grok returns one of:
  - **ACCEPT** — pass this audit point.
  - **HOLD** — needs the human builder to clarify.
  - **FLAG** — Grok believes there's a problem; explain.

## What Grok should NOT do

- Grok must NOT push to GitHub. Pushing is the user's step, run
  on Vincent's PC after Grok's audit completes.
- Grok must NOT rewrite or delete any code or doc in this pass.
  Grok's output is purely a written audit (Markdown).
- Grok must NOT generate new evidence. Grok validates the
  evidence already produced.

## How Grok consumes this packet

The unified working tree is delivered as a checkback zip. Grok
extracts it into a clean folder, runs the verification commands in
`PROJECT_STATUS.md` ("How to verify locally"), reads
`CORE_UNIFICATION_REPORT.md` first, then `CORE_TREE_MAP.md`, then
the proof-system reports under
`06_PROOF_SYSTEM/aurexis_research_sim/reports/`, and produces a
single Markdown audit answering each numbered item above.
