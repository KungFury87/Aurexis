# Aurexis Core — unified tree map (`core v1 incomplete`)

This file describes the layout a reader should expect when they
land on the Aurexis repo. Everything in this map exists today in
`Aurexis_Core_WORKING_20260414-1339/` (this folder).

```
Aurexis/                                        repo root
|
|-- README.md                                   unified Core readme
|-- ROADMAP.md                                  unified roadmap
|-- PROJECT_STATUS.md                           unified status
|-- CORE_UNIFICATION_REPORT.md                  this pass's audit
|-- CORE_TREE_MAP.md                            (this file)
|-- GROK_AUDIT_LANE.md                          Grok auditor lane
|-- GITHUB_PUSH_PLAN.md                         user-run push plan
|-- LICENSE
|-- FROZEN_V1_BACKUP_NOTICE.md                  V1 frozen pointer
|-- WORKING_COPY_NOTICE.md                      working-copy note
|
|-- 00_PROJECT_CORE/                            V1 truth surface (FROZEN)
|     M0..M11 gate verifications, capstones,
|     audits, lock manifest, locked release zip,
|     master law, milestone ladder, project status
|     and roadmap for V1 substrate candidate
|
|-- 01_RELEASES/                                older release zips (FROZEN)
|     LEGACY_V81ISH/, V84/, V85/, V86/,
|     RELEASE_HISTORY.md
|
|-- 02_GATE_TRACKING/                           gate-by-gate progress
|     GATE_1/ .. GATE_5/
|
|-- 03_HANDOFFS_AND_CONTEXT/                    handoff logs + AI session exports
|
|-- 04_WORKING_SESSIONS/                        session log
|
|-- 05_ACTIVE_DEV/                              active V1/V2 dev
|     aurexis_lang/                             V1 source tree (154 modules
|       src/aurexis_lang/                       at frozen baseline; current
|         v2_decode/                            branch may have V2 changes)
|     gate3_run_*, gate4_run_*, gate5_run_1,
|     m6_run_1, m8_live_run_1,
|     mobile_app/, pytest.ini, requirements.txt
|
|-- 06_PROOF_SYSTEM/                            NEW v0.6 Engine-semantics proof system
|     aurexis_research_sim/
|       aurexis_sim/                            21 source modules
|       tests/                                  21 test files (221 passing)
|       reports/                                21 dossier bundles
|       app.py                                  Streamlit UI
|       README.md, STATUS.md, RUN_ME_FIRST.txt
|       ...
|
|-- 07_VISION_SUBSTRATE/                        NEW V2 vision language
|     aurexis_workbench/                        V2 substrate package
|       fields.py, operators.py, predicates.py, runtime.py
|       dsl.py, vocabulary.py, independence.py, intake.py
|       vision_ops.py                           32 vision operators
|       visual_intake.py                        any image/video -> FieldBundle
|       vision_bridge.py                        .aurex-session -> FieldBundle
|       cli_vision.py, cli_visual.py            two runners
|     data/vision/vocab.aurex                   33-predicate vocabulary
|     VISION_LANGUAGE_AUDIT.md                  what Workbench already provided
|     VISION_LANGUAGE_v0_1.md                   language definition + growth log
|     reports/IR_RUN_2026-04-27.md              independence-ratio analysis
|     README.md                                 entry point
|
|-- BACKUPS/                                    older backup zips (FROZEN)
|
|-- V2_BENCHMARK_SET/                           V2 benchmark artifacts
|-- V2_BENCHMARK_SET.md
|-- V2_CHARTER.md, V2_CHARTER_AMENDMENTS.md
|-- V2_CAPTURE_CHECKLIST.md, V2_CAPTURE_PROTOCOL.md
|-- V2_COMPLETION_DEFINITION.md, V2_EXCLUSIONS.md
|-- V2_M1_DRY_RUN.md, V2_MILESTONE_GATES.md
|-- V2_NAMING_HOLDOVER.md, V2_PILOT_PREFLIGHT.md
|-- V2_PILOT_RUNBOOK.md, V2_ROADMAP.md
|-- V2_SESSION_MANIFEST_TEMPLATE.json
|
|-- AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md
|-- Aurexis_Core_M11_Clean.zip
|-- _acor11_body.txt, _acor1_body.txt           release-line artifacts
|-- (helper scripts: _clone_to_working.ps1,
|     _create_github_release.bat, _deep_inspect.ps1,
|     _final_verify.ps1, _fix_default_branch.ps1, etc.)
|
|-- ChatGPT-*.json                              historical AI session exports
|
\-- .git/                                       single git repo
      remote: https://github.com/KungFury87/Aurexis.git
      branches:
        main, master                            release-aligned
        working/core-v2                         V2 active
        working/core-v1-incomplete              unified Core working tree
                                                 (created by GITHUB_PUSH_PLAN)
        backup/v1-substrate-candidate-*         26 frozen V1 backup branches
      tags:
        core-v1-substrate-candidate-or1.1       ACOR-1.1 (current official)
        core-v1-substrate-candidate-or1         ACOR-1 (superseded)
        core-v2-decode-engine-d3                V2 decode-engine marker
        backup-v1-substrate-candidate-*         26 frozen V1 backup tags
        v1-substrate-20260413-*                 4 frozen V1 substrate tags
```

## What is FROZEN vs ACTIVE vs NEW

- **FROZEN**: `00_PROJECT_CORE/`, `01_RELEASES/`, `BACKUPS/`,
  release tags `core-v1-substrate-candidate-or1*`, all 26
  `backup/v1-substrate-candidate-*` branches and matching tags,
  `v1-substrate-20260413-*` tags.
  Do not modify, retag, or delete.

- **ACTIVE V2**: `V2_*.md` top-level docs, `V2_BENCHMARK_SET/`,
  `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_decode/`,
  `working/core-v2` branch, `core-v2-decode-engine-d3` tag.
  V2 research is preserved as research; further V2 work continues
  in this lane.

- **ACTIVE current Core (NEW v0.6)**: `06_PROOF_SYSTEM/`,
  unified top-level docs (`README.md`, `ROADMAP.md`,
  `PROJECT_STATUS.md`, `CORE_UNIFICATION_REPORT.md`,
  `CORE_TREE_MAP.md`, `GROK_AUDIT_LANE.md`,
  `GITHUB_PUSH_PLAN.md`), `working/core-v1-incomplete` branch (to
  be created).

## What is NOT in this repo

- `Aurexis_ED/` — Aurexis E/D (Client / Wrapper / Runtime). Lives
  outside this Core repo by design. Out of scope for this pass.
