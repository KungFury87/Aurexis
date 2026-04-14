# Aurexis Core V1 Substrate Candidate — Final Freeze Capstone

**Owner:** Vincent Anderson
**Date:** April 14, 2026
**Freeze State:** FINALIZED V1 Substrate Candidate (handoff-ready)

---

## Purpose of This Capstone

This document is the single authoritative statement that the package is at a stable freeze point as a V1 Substrate Candidate. It is NOT a claim of full Aurexis Core completion.

---

## What Is Frozen

| Item | State |
|------|-------|
| Architecture | Frozen — no new bridges or branches in this pass |
| Bridge count | 51, across 9 branch families |
| Source modules | 67 (64 V1 modules + 2 fixture support + `__init__.py`) |
| Standalone runners | 61, all passing |
| Standalone assertions | 6,358, all passing |
| Pytest test modules | 19 |
| Pytest surface | 327 passed, 0 failed (clean-room verified) |
| Package zip file count | 185 |
| Truth surface files | Consistent across ROADMAP, PROJECT_STATUS, UNIFIED_CAPABILITY_MANIFEST, RELEASE_AUDIT_CAPSTONE, RELEASE_HANDOFF_HARDENING, PACKAGE_MAP, HANDOFF_CAPSTONE, this freeze capstone |
| Evidence tier separation | Authored fixtures always labeled `evidence_tier="authored"` — never mixed with REAL_CAPTURE |
| GitHub backup | Removable branch/tag, deletion commands recorded |

---

## Package-Level Tests Are Green

```
$ PYTHONPATH=src python3 run_pytest_surface.py
TOTAL: 327 passed, 0 failed
ALL PYTEST SURFACE TESTS PASSED
```

Equivalent command when pytest is installed: `PYTHONPATH=src pytest tests/ -q`.

Clean-room verified by extracting the locked zip to an empty directory and running both the standalone runners and `run_pytest_surface.py`.

---

## Major Bounded Branches Are Complete-Enough

| # | Branch | Bridges | Capstone Verified |
|---|--------|---------|-------------------|
| 1 | Static Artifact Substrate | 1–18 | yes |
| 2 | Screen-to-Camera Temporal Transport | 19–28 | yes |
| 3 | Higher-Order Coherence / Sheaf-Style Composition | 29–32 | yes |
| 4 | View-Dependent Markers / 3D Moment Invariants | 33–36 | yes |
| 5 | VSA / Hyperdimensional Cleanup | 37–40 | yes |
| 6 | Integration / Release Hardening | 41–44 | yes |
| 7 | Observed Evidence Loop / Real Capture Calibration | 45–48 | yes |
| 8 | Real Capture User Handoff | 49 | yes |
| 9 | Observed-Evidence Dry-Run / Replay Readiness | 50–51 | yes |

---

## What Still Requires Future User-Supplied Real Captures

The following are infrastructure-proven and deterministic against authored fixtures, but have NOT been exercised against real photographs:

- Real capture ingest (pipeline is proven; real file submission is the gap)
- Evidence delta analysis against real substrate outputs
- Calibration recommendations triggered by real deltas
- Dry-run replay replaced by real capture replay

This gap is not a code bug. It is a user-action dependency. Resolving it requires user-supplied `.jpg` / `.png` / `.tif` capture files processed through the intake preflight and replay harness using real substrate reference outputs.

---

## Later Work Remains Later

The following explicitly remains outside the V1 Substrate Candidate and would require new branches / new user decisions / new research:

- Continuous (non-discrete) viewpoint recovery
- Large-codebook VSA (beyond 11 entries at 1024 dimensions)
- Advanced temporal transport modes beyond RS / CC / fusion
- Production deployment, security, tamper-proof identity
- Real-world camera noise robustness at full physical fidelity
- Streaming / incremental real-capture intake
- Automated file discovery / OS integration
- OAM, optical skyrmions, NLOS imaging, other exotic optics (permanently excluded by Current Tech Floor)

---

## Freeze Verdict

The Aurexis Core V1 Substrate Candidate is **finalized** as a handoff-ready package. The package is self-describing, self-verifying, and internally consistent across all top-level truth surface files.

**"Finalized" here means:** this is the stable freeze point of the V1 Substrate Candidate bundle.

**"Finalized" here does NOT mean:** full Aurexis Core completion, production readiness, or real-capture validation.

The remaining forward step — exercising the pipeline on user-supplied real captures — is a real stop for this package phase.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
