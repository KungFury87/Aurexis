# Aurexis Core — Official Release 1 (ACOR-1) — V1 Substrate Candidate

**Owner:** Vincent Anderson
**Release date:** April 14, 2026
**Release tag:** `core-v1-substrate-candidate-or1`
**Release name:** Aurexis Core Official Release 1 — V1 Substrate Candidate
**Status:** FINALIZED V1 Substrate Candidate — handoff-ready

---

## What Aurexis Core Is

Aurexis Core is a new kind of programming language and computer interface layer with the physical world. The central idea:

> **Aurexis Core is the code that sits between a computer's optic nerve and its brain.**

- The **world** is primary reality
- The **camera** is the sensory intake surface
- The **phoxel field** is the machine's immediate observed stream
- **Core** is the law that organizes that stream into structured, bounded, machine-usable reality

This is not image processing. It is the deeper language layer for machine vision, grounded in physics, light, and structured observation.

## What This Release Is

**Official Release 1 (ACOR-1)** is the first public-facing, release-hardened package of the Aurexis Core **V1 Substrate Candidate**. It proves bounded, deterministic, law-governed visual computing properties through **51 bridge milestones** across **9 branch families**, with a green pytest surface and a removable GitHub backup.

## What This Release Is NOT

- **Not full Aurexis Core completion.** This is a narrow, law-bearing substrate *candidate*, not the full Core system.
- **Not a production deployment.** No production API, security, or monitoring layer.
- **Not a real-camera validation.** All evidence tiers are authored/synthetic. Real-capture validation is an explicit future step that requires user-supplied photographs.
- **Not an exotic-optics system.** OAM, optical skyrmions, NLOS imaging, and other exotic optics are explicitly excluded (see manifest).

---

## Package Totals

| Metric | Value |
|--------|-------|
| Bridge milestones | **51** across 9 branches |
| Standalone assertions | **6,358** (all passing) |
| Standalone runners | **61** |
| V1 source modules | **67** |
| Pytest test modules | **19** |
| Pytest surface | **327 passed, 0 failed** (clean-room verified) |
| Packaged zip | **186 files, ~2.2 MB** |
| Branch capstones verified | **9 / 9** |

---

## Quick Start

```bash
# 1) Extract the locked zip (or clone the repo)
# 2) Enter the source tree
cd 05_ACTIVE_DEV/aurexis_lang
export PYTHONPATH=src

# 3) Run the full pytest surface (no pytest install required — lightweight runner included)
python3 run_pytest_surface.py
# Expected: TOTAL: 327 passed, 0 failed

# 4) Or, if pytest is installed on your host:
pytest tests/ -q

# 5) Any of the 61 standalone runners also work:
python3 run_v1_release_audit_tests.py              # 40/40 PASS
python3 run_v1_unified_capability_manifest_tests.py # 53/53 PASS
python3 run_v1_intake_to_delta_replay_tests.py     # 42/42 PASS
```

---

## Package Map

| Path | What it is |
|------|-----------|
| `README.md` (this file) | Public landing page |
| `00_PROJECT_CORE/ROADMAP.md` | Full project roadmap (51 bridges, 9 branches, excluded optics) |
| `00_PROJECT_CORE/PROJECT_STATUS.md` | Master status tracker |
| `00_PROJECT_CORE/UNIFIED_CAPABILITY_MANIFEST_V1.md` / `.json` | Human and machine-readable capability manifest |
| `00_PROJECT_CORE/V1_SUBSTRATE_RELEASE_AUDIT_CAPSTONE.md` | Release audit (10/10 PASS) |
| `00_PROJECT_CORE/RELEASE_HANDOFF_HARDENING_V1.md` | Handoff hardening notes |
| `00_PROJECT_CORE/RELEASE_NOTES_ACOR-1.md` | Official release notes for ACOR-1 |
| `00_PROJECT_CORE/GITHUB_BACKUP_RECORD_V1.md` | Removable backup branches/tags + deletion commands |
| `05_ACTIVE_DEV/aurexis_lang/FINAL_CANDIDATE_PACKAGE_MAP_V1.md` | Detailed package map |
| `05_ACTIVE_DEV/aurexis_lang/FINAL_V1_CANDIDATE_HANDOFF_CAPSTONE.md` | Handoff capstone |
| `05_ACTIVE_DEV/aurexis_lang/FINAL_CANDIDATE_FREEZE_CAPSTONE_V1.md` | Authoritative freeze statement |
| `05_ACTIVE_DEV/aurexis_lang/REAL_CAPTURE_INTAKE_PACK_V1.md` | What to submit for real-capture intake |
| `05_ACTIVE_DEV/aurexis_lang/REAL_CAPTURE_SESSION_TEMPLATE_V1.md` / `.json` | Session manifest template |
| `05_ACTIVE_DEV/aurexis_lang/DRY_RUN_EVIDENCE_REPORT_SURFACE_V1.md` | What a dry-run looks like |
| `05_ACTIVE_DEV/aurexis_lang/REAL_CAPTURE_USER_HANDOFF_CAPSTONE_V1.md` | User-handoff readiness capstone |
| `05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/` | 67 V1 source modules |
| `05_ACTIVE_DEV/aurexis_lang/tests/` | 19 pytest test modules |
| `05_ACTIVE_DEV/aurexis_lang/run_v1_*.py` / `run_pytest_surface.py` | 61 standalone runners + pytest surface runner |
| `00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip` | The frozen release zip |

---

## The 9 Branch Families

| # | Branch | Bridges | Status |
|---|--------|---------|--------|
| 1 | Static Artifact Substrate | 1–18 | COMPLETE-ENOUGH |
| 2 | Screen-to-Camera Temporal Transport | 19–28 | COMPLETE-ENOUGH (capstone verified) |
| 3 | Higher-Order Coherence / Sheaf-Style Composition | 29–32 | COMPLETE-ENOUGH (capstone verified) |
| 4 | View-Dependent Markers / 3D Moment Invariants | 33–36 | COMPLETE-ENOUGH (capstone verified) |
| 5 | VSA / Hyperdimensional Cleanup | 37–40 | COMPLETE-ENOUGH (capstone verified) |
| 6 | Integration / Release Hardening | 41–44 | COMPLETE-ENOUGH (capstone verified) |
| 7 | Observed Evidence Loop / Real Capture Calibration | 45–48 | COMPLETE-ENOUGH (capstone verified) |
| 8 | Real Capture User Handoff | 49 | COMPLETE-ENOUGH |
| 9 | Observed-Evidence Dry-Run / Replay Readiness | 50–51 | COMPLETE-ENOUGH (capstone verified) |

---

## How Real-Capture Intake Works (Future Step)

The real-capture pipeline is infrastructure-proven but requires user-supplied data to exercise against real-world inputs.

1. Read `REAL_CAPTURE_INTAKE_PACK_V1.md` for allowed formats and structural requirements.
2. Copy `REAL_CAPTURE_SESSION_TEMPLATE_V1.json` and fill in your session metadata.
3. Run the intake preflight bridge (`real_capture_intake_preflight_bridge_v1`) against your manifest.
4. On preflight-cleared manifests, run the full 5-stage pipeline replay (`intake_to_delta_replay_harness_v1`).
5. Compare observed substrate outputs against expected reference outputs via `evidence_delta_analysis_bridge_v1`.
6. Review advisory calibration recommendations from `calibration_recommendation_bridge_v1`.

See `DRY_RUN_EVIDENCE_REPORT_SURFACE_V1.md` for an example of what a completed dry-run looks like.

---

## Explicitly Excluded (Permanent)

The following are **permanently excluded** from V1 (they violate the Current Tech Floor and require exotic hardware):

- **OAM (Orbital Angular Momentum)**
- **Optical Skyrmions**
- **NLOS (Non-Line-of-Sight) Imaging**
- **Exotic Specialized Optics** (metamaterials, computational optics, holographic elements)

---

## GitHub Backup / Release Branches

The repo includes removable backup branches documenting the release progression. See `00_PROJECT_CORE/GITHUB_BACKUP_RECORD_V1.md` for the full list with deletion commands. The current official release is:

- Release branch: `backup/v1-substrate-candidate-20260414-120000`
- Official release tag: `core-v1-substrate-candidate-or1`
- Companion backup tag: `backup-v1-substrate-candidate-20260414-120000`

All backups are designed to be removable. Deletion commands are recorded in the backup record.

---

## License / Ownership

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
Sole inventor and owner: Vincent Anderson.

---

## Honest Framing

This is the **first official release** of Aurexis Core, in its current honest state. It is a narrow, law-bearing V1 Substrate Candidate — a foundation layer, not a finished system. The bridges are deterministic and verified; the pytest surface is green; the package is self-describing. The real-world camera validation step is the explicit next forward direction and requires user action (real capture photographs) rather than more code.
