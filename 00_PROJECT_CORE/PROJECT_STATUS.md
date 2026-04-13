# AUREXIS CORE — Master Project Status
**Owner:** Vincent Anderson
**Last Updated:** April 12, 2026 — Recovered Sequence Collection Signature Match Bridge V1 COMPLETE
**Status:** V1 Substrate Candidate accepted and baseline-locked. Seventeen bridge milestones complete: Raster Law, Capture Tolerance, Artifact Localization, Orientation Normalization, Perspective Normalization, Composed Recovery, Artifact Dispatch, Multi-Artifact Layout, Artifact Set Contract, Recovered Set Signature, Recovered Set Signature Match, Recovered Page Sequence Contract, Recovered Page Sequence Signature, Recovered Page Sequence Signature Match, Recovered Sequence Collection Contract, Recovered Sequence Collection Signature, Recovered Sequence Collection Signature Match. 2365 standalone assertions + 658 pytest functions, all passing.

---

## What Aurexis Core Is

Aurexis Core is a **programming language and new computer interface layer** with the physical world.

The core conceptual sentence: **Aurexis Core is the code that sits between a computer's optic nerve and its brain.**

- The **world** is primary reality
- The **camera** is the sensory intake surface
- The **phoxel field** is the machine's immediate observed stream
- **Core** is the law that organizes that stream into structured, bounded, machine-usable reality

This is not image processing. It is the deeper language layer for machine vision grounded in physics, light, and structured observation. The long-term vision is for Aurexis Core to become the underlying code of vision for computers.

---

## Current Gate Status

| Gate | Name | Status | Notes |
|------|------|--------|-------|
| Gate 1 | Core Law Frozen | ✅ COMPLETE | Law frozen at V20. All 7 sections implemented and tested. |
| Gate 2 | Runtime Obeys Law | ✅ COMPLETE | **Confirmed April 8, 2026.** All 11 audit checks pass. 100% compliance across 8 components. |
| Gate 3 | Earned Evidence Loop | ✅ COMPLETE | **Confirmed April 8, 2026.** 130 S23 files, 912 frames, 100% law compliance, earned promoted. All 10 audit checks pass. |
| Gate 4 | EXECUTABLE Promotion | ✅ COMPLETE | **Confirmed April 8, 2026.** 25 files, 301 EXECUTABLE nodes, 25 programs serialized. All 9 audit checks pass. First attempt. |
| Gate 5 | Expansion Without Rewrite | ✅ COMPLETE | **Confirmed April 8, 2026.** Cross-device validation added, SHA-256 proof Core Law untouched. All 8 audit checks pass. |

---

## Version History Summary

| Version | Focus | Key Change |
|---------|-------|-----------|
| V80 | Repo verification surface | 154 tests, release-candidate surfaces, repo verification infrastructure |
| V81-V82 | Cleanup + root authority | Terminology normalization, root authority surface |
| V83 | Phoxel runtime status starts | Parser/token level gains explicit phoxel runtime status |
| V84 | Execution runtime status | Execution trace + interpreter surfaces carry phoxel status |
| V85 | Core audit drop | Full aurexis_lang source included; plan/state/branch surfaces carry phoxel status rollup |
| **V86** | **Control/mutation lane** | **Control-resolution, transitions, state-machine, mutation summaries all carry phoxel status** |

---

## What the Core Law Enforces (7 Sections)

1. **Phoxel Record** — Every visual claim must have pixel coordinates, camera metadata, evidence chain, timestamp. No synthetic data.
2. **Native Relations** — Spatial relationships must be physically measurable (distance in px, angle in degrees). No abstract semantics.
3. **World/Image Authority** — World is primary authority. Image is primary access. Neither overrides the other. Model cannot suppress observed image.
4. **Executable Promotion** — Things only become "executable" after passing: evidence validated + multi-frame consistent + geometric coherent + cross-register consistent + language legal + bounded inference + confidence ≥ 0.7.
5. **Illegal Inference** — Nine named blocked claim rules. Cannot claim world truth from single observation, cannot claim permanence from one frame, cannot claim identity from resemblance alone, etc.
6. **Current Tech Floor** — Must run on current mobile hardware (≤30s processing, ≤500MB RAM, ≤5% battery/min). No exotic hardware dependencies.
7. **Future Tech Ceiling** — Better hardware must improve precision/robustness without requiring core law rewrite or ontology change.

---

## Evidence Tier System

| Tier | Meaning | Can claim... |
|------|---------|-------------|
| LAB | Simulated/synthetic data | Lab-level proof only |
| AUTHORED | Hand-crafted test assets | Authored-asset evidence |
| REAL_CAPTURE | Actual camera input | Real-world pipeline validation |
| EARNED | Multi-frame validated real camera, all gates passed | Earned physical proof |

**Current tier in active tests:** AUTHORED + REAL_CAPTURE + **EARNED** (Gate 3 confirmed April 8, 2026).

---

## What Has Been Built (Honest)

**Complete and tested:**
- Core law enforcement engine (all 7 sections, delegating to specialized modules)
- Phoxel schema validator (canonical 6-field schema with full error reporting)
- Illegal inference matrix (9 named blocked claim rules, runtime-enforced)
- Relation legality checker (primary + higher-order kinds, physical measurement required)
- Executable promotion checklist (6 mandatory checks + confidence threshold)
- Evidence tier system (4 tiers, prevents upward fake-claiming)
- AST pipeline: tokenizer → parser → interpreter → execution plan → resolution → state propagation → branch execution
- Multi-frame consistency validator
- Runtime obedience reporting surface
- 66+ pytest tests as of V86

**Scaffolded / partial:**
- Perception/learning layer (scaffold)
- Training loop (scaffold)

**Completed since Gates (M6–M11):**
- ✅ CV extraction: 100 prims/frame, 0.807 confidence (M6)
- ✅ 116 end-to-end tests, all passing (M7)
- ✅ Real-time camera: live WiFi feed, 54 frames EXECUTABLE (M8)
- ✅ Mobile APK: Kivy+Buildozer on S23 Ultra, 0.172s/frame (M9)
- ✅ Visual GUI: phoxel overlay, IR tree, evidence inspector, promotion tracker (M10)
- ✅ Debugger: step-through IR, breakpoints, law inspector, 101 nodes (M11)
- ✅ ScreenManager nav with deferred permissions (M11 bug fix)

---

## Honest Completion Estimate

| Area | Estimated Done |
|------|---------------|
| Core law enforcement engine | ~95% |
| Runtime chain (AST → execution) | ~75% |
| Gate 2 obedience surface | ~70% |
| CV extraction quality | ✅ M6 COMPLETE — April 9, 2026. Prims: 24→100, Conf: 0.618→0.807 |
| Gate 3 evidence loop | ✅ 100% — COMPLETE April 8, 2026 |
| Gate 4 EXECUTABLE promotion | ✅ 100% — COMPLETE April 8, 2026 (first attempt) |
| Camera bridge / real input | ✅ 100% — file-based + live camera fully working |
| Real-time camera integration | ✅ M8 COMPLETE — 54 frames, all EXECUTABLE, 100% law compliance |
| Gate 5 expansion without rewrite | ✅ 100% — COMPLETE April 8, 2026 |
| Mobile on-device (S23 Ultra) | ✅ M9 COMPLETE — 30 frames, 0.172s/frame, 29 EXECUTABLE |
| Visual GUI (phoxel overlay + IR tree + evidence + promos) | ✅ M10 COMPLETE — 4 tabs, 7/7 checks, all on-device |
| Debugger and Inspector Tools | ✅ M11 COMPLETE — step-through debugger, breakpoints, law inspector, 8/8 checks |
| Overall toward full vision | ~97% (foundation + M6–M11 complete) |

---

## Preferred Working Style (for AI continuations)

- Direct language. No fluff. No fake certainty.
- Every progress report must include: current state / what changed / what was verified / honest limit / tracker with % / dumbed-down summary / best next step.
- No fake completion theater. Do not claim earned proof from lab/authored evidence.
- Prefer complete package-level passes over tiny loose patches.
- Ask Vincent before anything that would change project law.
- Core-first. Aurexis E/D is deferred downstream — do not expand toward it.
- Future conceptual definitions should be concretized into actual code when feasible.

---

## V1 Substrate Ladder (LOCKED)

V1 Substrate Candidate accepted by ChatGPT audit. Baseline locked April 9, 2026.
Narrow law-bearing substrate candidate — not full Aurexis Core completion.

| Milestone | Name | Status | Tests |
|-----------|------|--------|-------|
| M1 | Visual Grammar V1 | ✅ COMPLETE | 192 assertions |
| M2 | Visual Parse Rules V1 | ✅ COMPLETE | 69 assertions |
| M3 | Visual Executor V1 | ✅ COMPLETE | 66 assertions |
| M4 | Print/Scan Stability V1 | ✅ COMPLETE | 44 assertions |
| M5 | Temporal Law V1 | ✅ COMPLETE | 33 assertions |
| M6 | Type System V1 | ✅ COMPLETE | 39 assertions |
| M7 | Composition V1 | ✅ COMPLETE | 43 assertions |
| M8 | Hardware Calibration V1 | ✅ COMPLETE | 56 assertions |
| M9 | Self-Hosting V1 (narrow) | ✅ COMPLETE | 49 assertions |
| M10 | Substrate Integration | ✅ COMPLETE | 39 assertions |
| — | **Baseline Lock** | ✅ LOCKED | SHA-256 manifest |
| — | **Raster Law Bridge V1** | ✅ COMPLETE | 58 assertions |
| — | **Capture Tolerance Bridge V1** | ✅ COMPLETE | 99 assertions |
| — | **Artifact Localization Bridge V1** | ✅ COMPLETE | 54 assertions |
| — | **Orientation Normalization Bridge V1** | ✅ COMPLETE | 70 assertions |
| — | **Perspective Normalization Bridge V1** | ✅ COMPLETE | 53 assertions |
| — | **Composed Recovery Bridge V1** | ✅ COMPLETE | 72 assertions |
| — | **Artifact Dispatch Bridge V1** | ✅ COMPLETE | 58 assertions |
| — | **Multi-Artifact Layout Bridge V1** | ✅ COMPLETE | 68 assertions |
| — | **Artifact Set Contract Bridge V1** | ✅ COMPLETE | 89 assertions |
| — | **Recovered Set Signature Bridge V1** | ✅ COMPLETE | 86 assertions |
| — | **Recovered Set Signature Match Bridge V1** | ✅ COMPLETE | 100 assertions |
| — | **Recovered Page Sequence Contract Bridge V1** | ✅ COMPLETE | 149 assertions |
| — | **Recovered Page Sequence Signature Bridge V1** | ✅ COMPLETE | 154 assertions |
| — | **Recovered Page Sequence Signature Match Bridge V1** | ✅ COMPLETE | 141 assertions |
| — | **Recovered Sequence Collection Contract Bridge V1** | ✅ COMPLETE | 163 assertions |
| — | **Recovered Sequence Collection Signature Bridge V1** | ✅ COMPLETE | 173 assertions |
| — | **Recovered Sequence Collection Signature Match Bridge V1** | ✅ COMPLETE | 148 assertions |

**Total:** 2365 standalone assertions, 658 pytest functions, 27 runners — all passing.

**Rule:** Do not skip or reorder. Each milestone gets a gate verification audit.

---

## Ownership

© 2026 Vincent Anderson — Aurexis Core. All rights reserved for the core concept and implementation.
Sole inventor and owner: Vincent Anderson.
