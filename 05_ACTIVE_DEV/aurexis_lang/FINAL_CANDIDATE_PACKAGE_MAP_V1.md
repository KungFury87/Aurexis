# Aurexis Core V1 Substrate Candidate — Final Package Map

**Owner:** Vincent Anderson
**Date:** April 13, 2026
**Status:** Release-hardened handoff-ready V1 substrate candidate

---

## Package Layout

```
aurexis_core_v1_substrate_candidate_locked.zip
├── [Human-Facing Truth Surface]
│   ├── ROADMAP.md                    — full project roadmap with all milestones
│   ├── PROJECT_STATUS.md             — master project status
│   ├── GITHUB_BACKUP_RECORD_V1.md    — removable backup record + deletion commands
│   ├── UNIFIED_CAPABILITY_MANIFEST_V1.md   — human-readable 51-bridge manifest
│   ├── UNIFIED_CAPABILITY_MANIFEST_V1.json — machine-readable manifest
│   ├── V1_SUBSTRATE_RELEASE_AUDIT_CAPSTONE.md — release audit results
│   ├── RELEASE_HANDOFF_HARDENING_V1.md     — release hardening verification
│   └── FINAL_CANDIDATE_PACKAGE_MAP_V1.md   — this file
│
├── [Real-Capture Intake Surface]
│   ├── REAL_CAPTURE_INTAKE_PACK_V1.md          — what to submit + allowed formats
│   ├── REAL_CAPTURE_SESSION_TEMPLATE_V1.md     — human-readable session template
│   ├── REAL_CAPTURE_SESSION_TEMPLATE_V1.json   — machine-readable session template
│   ├── FIXTURES_AUTHORED_CAPTURE_SESSION_PACK_V1.json — 6 authored dry-run fixtures
│   ├── DRY_RUN_EVIDENCE_REPORT_SURFACE_V1.md   — what a dry-run looks like
│   ├── DELTA_READY_HANDOFF_SURFACE_V1.md        — end-to-end pipeline documentation
│   └── REAL_CAPTURE_USER_HANDOFF_CAPSTONE_V1.md — user handoff readiness capstone
│
├── [Branch Capstones]
│   ├── OBSERVED_EVIDENCE_LOOP_CAPSTONE_V1.md   — observed evidence branch
│   ├── OBSERVED_EVIDENCE_REPLAY_CAPSTONE_V1.md — replay readiness branch
│   ├── VIEW_DEPENDENT_BRANCH_CAPSTONE_V1.md    — view-dependent markers branch
│   └── VSA_CLEANUP_BRANCH_CAPSTONE_V1.md       — VSA cleanup branch
│
├── [Gate Verifications] (19 files)
│   ├── CALIBRATION_RECOMMENDATION_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── CAPTURE_SESSION_MANIFEST_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── CLEANUP_RETRIEVAL_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── EVIDENCE_DELTA_ANALYSIS_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── HYPERVECTOR_BINDING_BUNDLING_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── INTAKE_TO_DELTA_REPLAY_HARNESS_V1_GATE_VERIFICATION.md
│   ├── MOMENT_INVARIANT_IDENTITY_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── REAL_CAPTURE_INGEST_PROFILE_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── REAL_CAPTURE_INTAKE_PREFLIGHT_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── REPLAY_OUTCOME_CONTRACT_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── VIEW_DEPENDENT_CONTRACT_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── VIEW_DEPENDENT_MARKER_PROFILE_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── VIEW_FACET_RECOVERY_BRIDGE_V1_GATE_VERIFICATION.md
│   ├── VSA_CLEANUP_PROFILE_BRIDGE_V1_GATE_VERIFICATION.md
│   └── VSA_CONSISTENCY_CONTRACT_BRIDGE_V1_GATE_VERIFICATION.md
│
├── [Standalone Test Runners] (19 files, run with: PYTHONPATH=src python3 <runner>)
│   ├── run_v1_calibration_recommendation_tests.py
│   ├── run_v1_capture_session_manifest_tests.py
│   ├── run_v1_cleanup_retrieval_tests.py
│   ├── run_v1_cross_branch_compatibility_tests.py
│   ├── run_v1_evidence_delta_analysis_tests.py
│   ├── run_v1_hypervector_binding_bundling_tests.py
│   ├── run_v1_intake_to_delta_replay_tests.py
│   ├── run_v1_moment_invariant_identity_tests.py
│   ├── run_v1_real_capture_ingest_profile_tests.py
│   ├── run_v1_real_capture_intake_preflight_tests.py
│   ├── run_v1_release_audit_tests.py
│   ├── run_v1_replay_outcome_contract_tests.py
│   ├── run_v1_unified_capability_manifest_tests.py
│   ├── run_v1_unified_substrate_entrypoint_tests.py
│   ├── run_v1_view_dependent_contract_tests.py
│   ├── run_v1_view_dependent_marker_profile_tests.py
│   ├── run_v1_view_facet_recovery_tests.py
│   ├── run_v1_vsa_cleanup_profile_tests.py
│   └── run_v1_vsa_consistency_contract_tests.py
│
├── [Pytest Test Suite] (19 files, run with: PYTHONPATH=src pytest tests/ -q)
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_calibration_recommendation_bridge_v1.py
│       ├── test_capture_session_manifest_bridge_v1.py
│       ├── test_cleanup_retrieval_bridge_v1.py
│       ├── test_cross_branch_compatibility_contract_bridge_v1.py
│       ├── test_evidence_delta_analysis_bridge_v1.py
│       ├── test_hypervector_binding_bundling_bridge_v1.py
│       ├── test_intake_to_delta_replay_harness_v1.py
│       ├── test_moment_invariant_identity_bridge_v1.py
│       ├── test_real_capture_ingest_profile_bridge_v1.py
│       ├── test_real_capture_intake_preflight_bridge_v1.py
│       ├── test_replay_outcome_contract_bridge_v1.py
│       ├── test_unified_capability_manifest_bridge_v1.py
│       ├── test_unified_substrate_entrypoint_bridge_v1.py
│       ├── test_v1_substrate_release_audit_bridge_v1.py
│       ├── test_view_dependent_contract_bridge_v1.py
│       ├── test_view_dependent_marker_profile_bridge_v1.py
│       ├── test_view_facet_recovery_bridge_v1.py
│       ├── test_vsa_cleanup_profile_bridge_v1.py
│       └── test_vsa_consistency_contract_bridge_v1.py
│
├── [Handoff Capstone]
│   └── FINAL_V1_CANDIDATE_HANDOFF_CAPSTONE.md
│
└── [Source Modules] (64 V1 modules + __init__.py)
    └── src/aurexis_lang/
        ├── __init__.py (V1_MODULES list: 64 entries)
        └── <64 .py bridge/milestone modules>
```

---

## Major Branch Families (9 branches, 51 bridges)

| Branch | Bridges | Assertions | Runners |
|--------|---------|------------|---------|
| Static Raster Substrate (M1-M10 + bridges 1-18) | 18 | 2,417 | 28 |
| Temporal Transport (bridges 19-28) | 10 | 2,284 | 10 |
| Higher-Order Coherence (bridges 29-32) | 4 | 258 | 4 |
| View-Dependent Markers (bridges 33-36) | 4 | 510 | 4 |
| VSA Cleanup (bridges 37-40) | 4 | 292 | 4 |
| Integration / Release (bridges 41-44) | 4 | 186 | 4 |
| Observed Evidence Loop (bridges 45-48) | 4 | 165 | 4 |
| User Handoff (bridge 49) | 1 | 36 | 1 |
| Replay Readiness (bridges 50-51) | 2 | 76 | 2 |
| **Total** | **51** | **6,358** (standalone) | **61** |

---

## Test Surfaces

**Standalone Runners (no pytest required):**
```bash
cd <extracted_zip>
for runner in run_v1_*.py; do
    PYTHONPATH=src python3 "$runner"
done
```
Each runner prints PASS/FAIL per section and a final assertion count.

**Pytest Suite (requires pytest installed):**
```bash
cd <extracted_zip>
PYTHONPATH=src pytest tests/ -q
```
19 pytest test modules covering bridges 33-51.

---

## Entrypoints

| Entrypoint | Purpose |
|------------|---------|
| `src/aurexis_lang/unified_substrate_entrypoint_bridge_v1.py` | Dynamic routing into all 51 bridges |
| `src/aurexis_lang/unified_capability_manifest_bridge_v1.py` | Machine-readable bridge registry |
| `src/aurexis_lang/real_capture_intake_preflight_bridge_v1.py` | Session manifest validation |
| `src/aurexis_lang/intake_to_delta_replay_harness_v1.py` | Full 5-stage pipeline replay |

---

## What This Package Is

A release-hardened, handoff-ready V1 substrate candidate. Narrow law-bearing package proving bounded deterministic properties across 9 branch families. Not full Aurexis Core completion.

## What This Package Is NOT

- Not a general-purpose vision system
- Not a production deployment
- Not a claim of full Aurexis Core completion
- Not a real-capture evidence proof (all evidence is authored/synthetic)

---

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
