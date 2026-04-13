# Release Handoff Hardening — V1 Substrate Candidate

**Date:** April 13, 2026
**Owner:** Vincent Anderson
**Status:** Release-hardened V1 substrate candidate

---

## What This Package Is

The Aurexis Core V1 Substrate Candidate is a narrow law-bearing substrate package. It contains 44 bridge milestones across 6 branches (5 capability + 1 integration), with 6081 standalone assertions verified across 54 runners.

This is NOT full Aurexis Core completion. It is a bounded, tested, documented substrate candidate.

---

## How to Use This Package in a New Session

### Quick Start

1. Extract the locked zip to a working directory.
2. Set `PYTHONPATH` to include the `src/` directory:
   ```
   cd aurexis_lang
   export PYTHONPATH=src
   ```
3. Run any standalone runner to verify the package:
   ```
   python3 run_v1_release_audit_tests.py
   ```
4. Import the unified entrypoint:
   ```python
   from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import V1_ENTRYPOINT
   results = V1_ENTRYPOINT.route_all()
   ```

### Key Entry Points

| Entry Point | Module | Purpose |
|-------------|--------|---------|
| Manifest | `unified_capability_manifest_bridge_v1` | What the package contains |
| Entrypoint | `unified_substrate_entrypoint_bridge_v1` | Route into any bridge |
| Compatibility | `cross_branch_compatibility_contract_bridge_v1` | Verify branch coherence |
| Release Audit | `v1_substrate_release_audit_bridge_v1` | Full release validation |

### Loading in a Claude or ChatGPT Session

Provide the locked zip and these instructions:

1. This is the Aurexis Core V1 Substrate Candidate.
2. It contains 56 V1 modules (12 foundation + 44 bridges).
3. The manifest is in `UNIFIED_CAPABILITY_MANIFEST_V1.json`.
4. The release audit is `run_v1_release_audit_tests.py`.
5. Authority: Vincent Anderson > Master Law > Frozen spec > Code/tests.
6. This is NOT full Aurexis Core completion.

---

## Package Layout

```
aurexis_lang/
├── src/aurexis_lang/
│   ├── __init__.py                         (package init, 56 V1_MODULES)
│   ├── visual_grammar_v1.py                (foundation M1)
│   ├── ... (10 more foundation modules)
│   ├── substrate_v1.py                     (foundation M10)
│   ├── raster_law_bridge_v1.py             (bridge 1)
│   ├── ... (38 more bridge modules)
│   ├── vsa_consistency_contract_bridge_v1.py (bridge 40)
│   ├── unified_capability_manifest_bridge_v1.py (bridge 41)
│   ├── unified_substrate_entrypoint_bridge_v1.py (bridge 42)
│   ├── cross_branch_compatibility_contract_bridge_v1.py (bridge 43)
│   └── v1_substrate_release_audit_bridge_v1.py (bridge 44)
├── tests/
│   ├── test_*_bridge_v1.py                 (12 pytest files)
│   └── ...
├── run_v1_*_tests.py                       (12 standalone runners)
└── ...
```

---

## Branch Summary

| Branch | Bridges | Assertions | Status |
|--------|---------|------------|--------|
| Static Artifact Substrate | 1–18 | 1873 | COMPLETE-ENOUGH |
| Temporal Transport | 19–28 | 2284 | COMPLETE-ENOUGH |
| Higher-Order Coherence | 29–32 | 258 | COMPLETE-ENOUGH |
| View-Dependent Markers | 33–36 | 510 | COMPLETE-ENOUGH |
| VSA Cleanup | 37–40 | 292 | COMPLETE-ENOUGH |
| Integration / Release | 41–44 | 186 | COMPLETE-ENOUGH |

---

## What Remains After V1

- Real-camera noise robustness (requires new branch)
- Production API design (requires architecture decision)
- Advanced temporal modes (requires new branch)
- Full Aurexis Core completion (long-term vision)
- All items in the Explicitly Excluded list remain excluded

---

## Honest Framing

This is a release-hardened V1 substrate candidate. It proves narrow law-bearing properties through deterministic tests. It does not prove full Aurexis Core completion, production readiness, or real-world camera robustness. All assertions are deterministic and reproducible.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
