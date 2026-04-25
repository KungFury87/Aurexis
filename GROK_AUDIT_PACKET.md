# Grok audit packet — Aurexis Core unification pass

**Pass:** Core unification + GitHub update preparation
**Date:** 2026-04-25
**Auditor:** Grok
**Auditee:** Vincent Anderson (human-in-the-loop) + Claude
(primary builder this pass).

This packet is the entry point for Grok's audit. Grok should
process the items in this order. This file is the single source
of truth for what was done in this pass and what Grok must verify.

---

## TL;DR

**Combined into one unified `core v1 incomplete` working tree:**

- The frozen V1 release surface (ACOR-1.1) — UNCHANGED.
- The V2 research/proof-system surface — UNCHANGED.
- The current Engine-semantics proof system (was `Aurexis_Research_Sim_v0_1/`,
  v0.6 framing, 221 passing tests) — ADDED at
  `06_PROOF_SYSTEM/aurexis_research_sim/`.
- Unified top-level docs — ADDED.
- Updated `README.md` — preserves ACOR-1.1 release-surface README
  body verbatim under a new unified header.

**No tag was touched.**
**No backup branch was touched.**
**No frozen file was overwritten.**
**Nothing was force-pushed.**
**Nothing was pushed at all** — the push step is the user's, run
on Vincent's PC after Grok signs off.

---

## What Grok needs to read, in order

1. `CORE_UNIFICATION_REPORT.md` — full audit of what changed.
2. `CORE_TREE_MAP.md` — top-level tree.
3. `ROADMAP.md` — unified roadmap.
4. `PROJECT_STATUS.md` — unified status.
5. `GROK_AUDIT_LANE.md` — what Grok is asked to check.
6. `GITHUB_PUSH_PLAN.md` — the user-run push sequence.
7. The proof-system reports under
   `06_PROOF_SYSTEM/aurexis_research_sim/reports/`, especially:
   - `PROOF_INDEX.md` (master Engine-semantics index)
   - `CONFIDENCE.md` (per-family TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE)
   - `SEMANTIC_STABILITY.md` (recovered semantic value vs truth)
   - `BOUNDARY.md` / `UNLOCK.md` (per-family boundary tags)

---

## Grok's audit checklist (16 items)

Reproduced from `GROK_AUDIT_LANE.md` for completeness. For each
item Grok returns ACCEPT / HOLD / FLAG.

### Frozen-surface audit
1. All 33 git tags unchanged from pre-pass state.
2. All 26 `backup/v1-substrate-candidate-*` branches unchanged.
3. ACOR-1.1 (`core-v1-substrate-candidate-or1.1`) still points at
   the same commit.
4. `00_PROJECT_CORE/`, `01_RELEASES/`, `BACKUPS/` byte-identical
   to pre-pass.

### V2-surface audit
5. No V2 document at top level (`V2_*.md`) silently modified.
6. `V2_BENCHMARK_SET/` unchanged.
7. `05_ACTIVE_DEV/aurexis_lang/.../v2_decode/` work preserved as
   working-tree changes (not silently committed).

### Unification audit
8. `06_PROOF_SYSTEM/` is the only NEW top-level directory.
9. New top-level docs do not duplicate or contradict existing V1
   truth-surface docs in `00_PROJECT_CORE/`.
10. `README.md` was UPDATED, not REPLACED — ACOR-1.1 release info
    still present.
11. `06_PROOF_SYSTEM/aurexis_research_sim/` runs and `pytest`
    reports 221 passing.

### Engine-semantics evidence audit
12. `PROOF_INDEX.md` per-family table consistent with
    `unlock.json`, `validation.json`, `confidence.json`,
    `semantic_stability.json`.
13. `ordering` calibrates to **REJECT**.
14. `repetition` is **SEMANTIC_UNSTABLE** under naive metric;
    strip-based metric in `coverage.py` recovers it.

### Push-plan audit
15. Each command in `GITHUB_PUSH_PLAN.md`: does NOT delete or move
    any existing tag/branch; does NOT force-push to `main`;
    creates new branch `working/core-v1-incomplete`; pushes new
    branch without rewriting history.
16. Note any command that could be destructive if mis-run; suggest
    safer alternative.

---

## How Grok runs the verification commands

```bash
# After Grok extracts the checkback zip:
cd Aurexis_Research_Sim_Core_Unified/Aurexis_Core_WORKING_20260414-1339

# (1) V1 substrate candidate test surface (frozen surface check):
cd 05_ACTIVE_DEV/aurexis_lang
PYTHONPATH=src python3 run_pytest_surface.py
# Expect: TOTAL: 327 passed, 0 failed (V1 substrate test surface).

# (2) Engine-semantics proof system (current research check):
cd ../../06_PROOF_SYSTEM/aurexis_research_sim
python3 -m pytest tests -q
# Expect: 221 passed.

python3 -m aurexis_sim.proof_index | tee /tmp/proof_index.txt
# Expect: family map showing ordering=REJECT, repetition with
# SEMANTIC_UNSTABLE, 5 of 8 families at PRIMITIVE_AWARE_HELPS at
# the boundary, 3 at METRIC_GAP_ROI_INSENSITIVE.
```

If any of these expected outcomes do NOT match, Grok flags.

---

## Honest constraints Grok should know

- The Cowork sandbox that ran this pass has a **write-once mount**
  — files can be created and modified, but not deleted. As a
  result, when the v0.6 simulator was rsync'd into
  `06_PROOF_SYSTEM/aurexis_research_sim/`, it brought along ~30
  CWD-output dossier files at the simulator root that mirror the
  same content in `reports/`. They are harmless. The push plan
  documents an optional `Remove-Item` cleanup step the user runs
  on his PC where deletes work. Grok should NOT flag these as
  destructive — they're additive litter.
- The Cowork sandbox **also cannot reliably run `git commit`**
  because `.git/objects/tmp_obj_*` cleanup is blocked by mount
  permissions. So no commit was made by this pass. The user runs
  `git add` and `git commit` on his PC per `GITHUB_PUSH_PLAN.md`.
  Grok should NOT flag the missing commit — it's intentional.
- The frozen V1 backup is preserved separately at
  `C:\Users\vince\Desktop\Aurexis evolved\back again\` (sibling
  to the working folder). That folder was NOT touched.

---

## What Grok produces back

A single Markdown document, e.g. `GROK_AUDIT_RESPONSE_20260425.md`,
containing:

- One ACCEPT / HOLD / FLAG verdict per numbered checklist item.
- A brief explanation per HOLD or FLAG.
- A bottom-line recommendation: ✅ proceed with push / ❌ do not push
  yet.

Vincent reads Grok's response, decides, then runs the push plan
on his PC if approved.

---

## Out-of-scope for Grok

- Aurexis E/D (`Aurexis_ED/`) is outside this repo and outside
  Grok's audit scope for this pass.
- Refactoring or rewriting the proof-system code is out of scope.
- Designing the next milestone is out of scope. Grok audits this
  pass only.
