# Aurexis Core unification report — `core v1 incomplete` working tree

**Pass date:** 2026-04-25
**Source frame:** v0.6 Engine-semantics proof system (research/proof tree)
            + ACOR-1.1 (frozen V1 release surface)
            + V2 research/proof-system work (active V2 tree)
**Outcome:** one unified `core v1 incomplete` working body in this folder.
**Repo:** `https://github.com/KungFury87/Aurexis.git`
**Working git folder:** `Aurexis_Core_WORKING_20260414-1339/` (this folder).

This report documents EXACTLY what was combined, what remained
frozen, and what collisions existed and how they were resolved.

---

## What was combined

The unified Core tree at this folder now contains, side by side:

1. **Frozen V1 release surface** (unchanged):
   - `00_PROJECT_CORE/` — V1 truth surface (gate verifications,
     audits, capstones, manifests, locked release zip).
   - `01_RELEASES/` — older V84/V85/V86 release zips +
     RELEASE_HISTORY.md.
   - `02_GATE_TRACKING/` — gate-by-gate progress.
   - `03_HANDOFFS_AND_CONTEXT/` — handoff logs, AI session exports.
   - `04_WORKING_SESSIONS/` — session log.
   - `BACKUPS/` — older backup zips.
   - `Aurexis_Core_M11_Clean.zip`, `_acor11_body.txt`, `_acor1_body.txt`
     — preserved release-line artifacts.
   - All git tags (33 total) including the V1 release tags
     `core-v1-substrate-candidate-or1` (ACOR-1) and
     `core-v1-substrate-candidate-or1.1` (ACOR-1.1).
   - All 26 `backup/v1-substrate-candidate-*` branches.
   - `FROZEN_V1_BACKUP_NOTICE.md`, `WORKING_COPY_NOTICE.md` — status
     notices.

2. **V2 research/proof-system surface** (preserved, integrated):
   - `V2_*.md` top-level docs (CHARTER, CHARTER_AMENDMENTS, CAPTURE_*,
     COMPLETION_DEFINITION, EXCLUSIONS, M1_DRY_RUN, MILESTONE_GATES,
     NAMING_HOLDOVER, PILOT_PREFLIGHT, PILOT_RUNBOOK, ROADMAP,
     SESSION_MANIFEST_TEMPLATE).
   - `V2_BENCHMARK_SET/` + `V2_BENCHMARK_SET.md` — frozen benchmark
     artifact set.
   - `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/` — V2
     decode-engine work (M and untracked entries from prior session,
     left as working-tree changes; see "What was NOT changed" below).
   - Tag `core-v2-decode-engine-d3` — preserved.
   - Branch `working/core-v2` — preserved (current HEAD before
     unification).

3. **Current simulator / proof-system surface (NEW v0.6)**, added at
   `06_PROOF_SYSTEM/aurexis_research_sim/`:
   - The full v0.6 Engine-semantics proof-system tree built across
     prior sessions (v0.1 substrate -> v2.0 boundary unlock -> v0.6
     proof-system reframing), 221 passing tests.
   - Modules: `relations`, `stress`, `atlas`, `validation`,
     `redesign`, `interaction`, `binding`, `soft_binding`,
     `inferred_binding`, `arbitration`, `distractor_arbitration`,
     `fusion`, `primitive_aware`, `coverage`, `boundary`, `unlock`,
     `proof_taxonomy`, `confidence`, `semantic_stability`,
     `proof_index` (4 v0.6 proof-system modules), plus support:
     `truth`, `simulate`, `metrics`, `presets`, `sensor`, `color`,
     `utils`, `smoke`, `bake_examples`, `app` (deprecated stub).
   - Reports: 21 shipped report bundles in
     `06_PROOF_SYSTEM/aurexis_research_sim/reports/`.
   - Streamlit UI: `06_PROOF_SYSTEM/aurexis_research_sim/app.py`.
   - Tests: 21 test files, 221 passing.

4. **New unified top-level docs:**
   - `README.md` (UPDATED): unified Core readme. Preserves ACOR-1.1
     release-line info; adds "Core v1 incomplete" framing + pointer
     to all surfaces.
   - `ROADMAP.md` (NEW top-level): unified roadmap. V2_ROADMAP.md is
     preserved as the V2-specific historical roadmap.
   - `PROJECT_STATUS.md` (NEW top-level): unified status. The V1
     truth-surface `00_PROJECT_CORE/PROJECT_STATUS.md` is preserved
     unchanged.
   - `CORE_UNIFICATION_REPORT.md` (this file).
   - `CORE_TREE_MAP.md` (NEW): top-level tree map.
   - `GROK_AUDIT_LANE.md` (NEW): Grok auditor lane definition.
   - `GITHUB_PUSH_PLAN.md` (NEW): exact commands the user runs to
     push the unified state to GitHub.

---

## What remained frozen (UNCHANGED in this pass)

- All git tags (33 total). NONE retagged, deleted, or moved.
- All 26 `backup/v1-substrate-candidate-*` branches. NONE deleted
  or rewritten.
- `core-v1-substrate-candidate-or1` and `core-v1-substrate-candidate-or1.1`
  release tags. UNCHANGED.
- `00_PROJECT_CORE/` contents (V1 truth surface). UNCHANGED.
- `01_RELEASES/` contents. UNCHANGED.
- `BACKUPS/` contents. UNCHANGED.
- `00_PROJECT_CORE/PROJECT_STATUS.md` and
  `00_PROJECT_CORE/ROADMAP.md` (V1 truth-surface variants).
  UNCHANGED. The new unified top-level `PROJECT_STATUS.md` and
  `ROADMAP.md` are SEPARATE FILES at the repo root.
- All V2 `V2_*.md` documents. UNCHANGED.
- `V2_BENCHMARK_SET/` and `V2_BENCHMARK_SET.md`. UNCHANGED.
- `LICENSE`. UNCHANGED.
- `FROZEN_V1_BACKUP_NOTICE.md` (untracked from prior session, still
  intact at root).
- `WORKING_COPY_NOTICE.md` (untracked from prior session, still
  intact at root).
- The frozen sibling backup at `back again/` (separate folder on
  Vincent's PC) is OUTSIDE this repo and was not touched.

---

## What was NOT changed (intentionally)

The current branch `working/core-v2` had pre-existing uncommitted
V2 decode-engine modifications + several untracked notice/log files.
This pass DID NOT commit those changes. They remain as working-tree
state. The user is free to:

  - commit them on `working/core-v2` to preserve V2 WIP, OR
  - carry them forward into `working/core-v1-incomplete` (since the
    new branch is created from the same HEAD), OR
  - decide later.

Specifically uncommitted before this pass:
  M  05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/codec.js
  M  ...finder.js / format.js / gf_rs.js / homography.js / index.js
     / renderer.js / sampler.js / test_decode_engine.js
  M  _backup_log.txt
  ?? _acor11_body.txt, FROZEN_V1_BACKUP_NOTICE.md,
     WORKING_COPY_NOTICE.md
  ?? 05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/_run_s.js,
     _run_stages.js, _stage_test.js
  ?? various PowerShell helpers (`_clone_to_working.ps1`, etc.)

These were inspected, identified as legitimate prior work, and
preserved as-is. They are NOT silently overwritten.

---

## Collision report

No path/name collision was found that required overwriting an
existing file.

| candidate path | existing? | resolution |
|---|---|---|
| `06_PROOF_SYSTEM/` | NO | NEW directory; no collision. |
| `06_PROOF_SYSTEM/aurexis_research_sim/` | NO | NEW; no collision. |
| `README.md` (top-level) | YES | UPDATED in place; ACOR-1.1 release info PRESERVED at top; "Core v1 incomplete" unified framing ADDED below. No content removed. |
| `ROADMAP.md` (top-level) | NO | NEW. The V1 `00_PROJECT_CORE/ROADMAP.md` and V2 `V2_ROADMAP.md` are PRESERVED as historical surfaces. |
| `PROJECT_STATUS.md` (top-level) | NO | NEW. The V1 `00_PROJECT_CORE/PROJECT_STATUS.md` is PRESERVED. |
| `CORE_UNIFICATION_REPORT.md` | NO | NEW. |
| `CORE_TREE_MAP.md` | NO | NEW. |
| `GROK_AUDIT_LANE.md` | NO | NEW. |
| `GITHUB_PUSH_PLAN.md` | NO | NEW. |

Note: when copying the v0.6 simulator into
`06_PROOF_SYSTEM/aurexis_research_sim/`, a small set of CWD-output
runtime artifacts (top-level dossier .md/.json copies that the
simulator's CLIs emit when run from CWD) came along. They mirror
the same content already in `reports/`. They are harmless and the
simulator passes all 221 tests with them present. The user can
remove them during the first commit on
`working/core-v1-incomplete` if desired (`git rm` the ~30 files at
`06_PROOF_SYSTEM/aurexis_research_sim/*.md` and `*.json` that
duplicate `reports/`). The sandbox doing this pass cannot delete
files due to mount permissions; the user's local FS can.

---

## Branch state expected after the next git step

| ref | state | who maintains |
|---|---|---|
| `core-v1-substrate-candidate-or1` (tag) | UNCHANGED | frozen V1 release |
| `core-v1-substrate-candidate-or1.1` (tag) | UNCHANGED | frozen V1 release |
| `core-v2-decode-engine-d3` (tag) | UNCHANGED | V2 marker |
| `backup/v1-substrate-candidate-*` (26 branches) | UNCHANGED | frozen |
| `backup-v1-substrate-candidate-*` (26 tags) | UNCHANGED | frozen |
| `v1-substrate-20260413-*` (4 tags) | UNCHANGED | frozen |
| `main` | UNCHANGED until user authorizes fast-forward | release-aligned head |
| `master` | UNCHANGED | mirror of main / legacy |
| `working/core-v2` | UNCHANGED in this pass | V2 active dev |
| `working/core-v1-incomplete` | TO BE CREATED by user | unified Core working tree |

The user runs the precise commands in `GITHUB_PUSH_PLAN.md` to
finalize the branch and push.

---

## Why this pass did not push to GitHub itself

The Cowork sandbox running this pass cannot reliably commit through
the mounted filesystem (`.git/objects/tmp_obj_*` cleanup blocked by
mount permissions) and cannot push without authenticated git
credentials. To honor the directive's non-destructive rules, this
pass:

1. PREPARED the unified working tree on disk.
2. WROTE the precise `GITHUB_PUSH_PLAN.md` for the user to run on
   their PC, where git operations work normally and credentials
   are configured.
3. PRODUCED a checkback zip of the unified working tree so the
   user can review without running the simulator.

The user is the human-in-the-loop. The push step is theirs, and
they retain the ability to back out any change before publishing.
