# Aurexis Core Official Release 1 — V1 Substrate Candidate

**Release name:** Aurexis Core Official Release 1 — V1 Substrate Candidate
**Short label:** ACOR-1
**Release date:** April 14, 2026
**Release tag:** `core-v1-substrate-candidate-or1`
**Release branch:** `backup/v1-substrate-candidate-20260414-120000`
**Release commit:** `d89c13b` (plus packaging commit on the release branch)
**Owner:** Vincent Anderson

---

## Summary

This is the **first official public-facing release** of Aurexis Core, in its current honest state. It packages a finalized **V1 Substrate Candidate** — a narrow, law-bearing foundation layer with 51 bridge milestones across 9 branch families, 6,358 standalone assertions, 61 runners, and a green package-level pytest surface (327 / 327).

This release is **NOT** full Aurexis Core completion. It is a release-hardened, handoff-ready substrate candidate.

---

## What Is Included

### The 9 bounded branch families (all capstones verified)

| # | Branch | Bridges | Notes |
|---|--------|---------|-------|
| 1 | Static Artifact Substrate | 1–18 | Raster, capture tolerance, localization, orientation/perspective, composition, dispatch, multi-artifact layout, contracts and signatures, global consistency |
| 2 | Screen-to-Camera Temporal Transport | 19–28 | Rolling shutter, complementary color, dispatch, consistency, frame-accurate, RS+CC fusion, payload contracts/signatures, global consistency |
| 3 | Higher-Order Coherence / Sheaf-Style Composition | 29–32 | Overlap detection, local sections, global composition, cohomological obstructions |
| 4 | View-Dependent Markers / 3D Moment Invariants | 33–36 | 4 markers × 4 viewpoints, stable identity hashes, recovery, contract validation |
| 5 | VSA / Hyperdimensional Cleanup | 37–40 | 1024-dim bipolar hypervectors, cleanup retrieval, VSA-vs-substrate consistency |
| 6 | Integration / Release Hardening | 41–44 | Machine-readable manifest, unified entrypoint, cross-branch compatibility, release audit |
| 7 | Observed Evidence Loop / Real Capture Calibration | 45–48 | Ingest profile, session manifest, delta analysis, calibration recommendations |
| 8 | Real Capture User Handoff | 49 | 10-check structural preflight of session manifests |
| 9 | Observed-Evidence Dry-Run / Replay Readiness | 50–51 | 6 authored fixtures, 5-stage pipeline replay, outcome contract validation |

### Test surfaces

- **Standalone runners:** 61 individual `run_v1_*.py` files, all passing, 6,358 total assertions
- **Pytest surface:** 19 test modules in `tests/`, 327 passed / 0 failed (clean-room verified)
- **Lightweight pytest runner:** `run_pytest_surface.py` — works without pytest installed

### Human- and machine-readable truth surface

- `README.md` — public landing page
- `ROADMAP.md`, `PROJECT_STATUS.md` — project overview and status
- `UNIFIED_CAPABILITY_MANIFEST_V1.md` + `.json` — capability enumeration
- `V1_SUBSTRATE_RELEASE_AUDIT_CAPSTONE.md` — release audit (10/10 PASS)
- `RELEASE_HANDOFF_HARDENING_V1.md` — handoff hardening
- `FINAL_CANDIDATE_PACKAGE_MAP_V1.md` — complete package map
- `FINAL_V1_CANDIDATE_HANDOFF_CAPSTONE.md` — handoff capstone
- `FINAL_CANDIDATE_FREEZE_CAPSTONE_V1.md` — authoritative freeze statement
- Real-capture intake: `REAL_CAPTURE_INTAKE_PACK_V1.md`, `REAL_CAPTURE_SESSION_TEMPLATE_V1.md` + `.json`, `DRY_RUN_EVIDENCE_REPORT_SURFACE_V1.md`, `REAL_CAPTURE_USER_HANDOFF_CAPSTONE_V1.md`
- Backup tracking: `GITHUB_BACKUP_RECORD_V1.md`

---

## What Is Solved (by this release)

- **Deterministic bounded law enforcement** across 51 bridges.
- **Static and temporal visual substrate** proven end-to-end against synthetic/authored data.
- **Higher-order composition** (sheaf-style) and **view-dependent markers** deterministic.
- **VSA cleanup layer** proven as an auxiliary (the deterministic substrate remains the truth layer).
- **Release audit** (10/10 PASS) and **cross-branch compatibility** all COMPATIBLE.
- **Observed-evidence replay readiness** with 6 authored fixtures and full 5-stage pipeline replay.
- **Package-level pytest green pass** verified from clean-room extraction.

## What Is NOT Solved (explicit)

- Real camera photographs have not been processed through the pipeline.
- Real-world temporal noise handling is not claimed.
- Continuous (non-discrete) viewpoint recovery is not claimed (4 discrete viewpoints only).
- Large-codebook VSA is not claimed (11-entry codebook at 1024 dimensions only).
- Production deployment, security, provenance, and runtime monitoring are not claimed.
- Streaming / incremental real-capture intake is not claimed (one-shot session submission only).

## Known Limits

- Authored fixtures are always labeled `evidence_tier="authored"` and are never mixed with real captures.
- The VSA layer is explicitly **AUXILIARY** — the deterministic substrate is the truth layer.
- All hashes are SHA-256.
- The package runs on current consumer hardware (Current Tech Floor).

---

## Next Major Later Step

The single most important next step is **user-supplied real capture data**. The intake/preflight/replay/delta/recommendation pipeline is infrastructure-complete but has not been exercised against real photographs. Real-capture work comes after this release surface is properly locked.

See the README section "How Real-Capture Intake Works (Future Step)" and `REAL_CAPTURE_INTAKE_PACK_V1.md`.

---

## Permanent Exclusions

The following remain permanently excluded from V1:

- OAM (Orbital Angular Momentum)
- Optical Skyrmions
- NLOS (Non-Line-of-Sight) Imaging
- Exotic Specialized Optics (metamaterials, computational optics, holographic elements)

These violate the Current Tech Floor and require hardware that is outside the bounded V1 scope.

---

## Installation / Verification

```bash
git clone https://github.com/KungFury87/Aurexis.git
cd Aurexis
# Check out the official release tag:
git checkout core-v1-substrate-candidate-or1

# Verify:
cd 05_ACTIVE_DEV/aurexis_lang
export PYTHONPATH=src
python3 run_pytest_surface.py
# Expected: TOTAL: 327 passed, 0 failed
```

The frozen zip is also available at `00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip` (186 files, ~2.2 MB).

---

## Release Removal / Revision

This release is **removable**. To remove the release artifacts:

```bash
# Delete release tag:
git push origin --delete core-v1-substrate-candidate-or1
git tag -d core-v1-substrate-candidate-or1

# Delete release branch (optional):
git push origin --delete backup/v1-substrate-candidate-20260414-120000
git branch -D backup/v1-substrate-candidate-20260414-120000

# Delete companion backup tag:
git push origin --delete backup-v1-substrate-candidate-20260414-120000
git tag -d backup-v1-substrate-candidate-20260414-120000
```

See `GITHUB_BACKUP_RECORD_V1.md` for the full removable-backup inventory.

---

## Honest Verdict

This is the **first official release** of Aurexis Core, honestly packaged as a V1 Substrate Candidate. Deterministic bridges, verified branches, green pytest surface, and a self-describing public-facing surface. It is not full Core completion. The forward path — real-capture validation — is the next user-action-dependent step.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
