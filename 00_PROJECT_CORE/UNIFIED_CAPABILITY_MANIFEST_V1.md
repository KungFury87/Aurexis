# Unified Capability Manifest — Aurexis Core V1 Substrate Candidate

**Owner:** Vincent Anderson
**Date:** April 13, 2026
**Manifest Hash:** `fbd7328f7a69aa4fab6306686be67d6f042a9017b209a956edd25e74aabaa6a7`
**Machine-Readable Version:** `UNIFIED_CAPABILITY_MANIFEST_V1.json`

---

## What This Package Is

The Aurexis Core V1 Substrate Candidate is a narrow law-bearing substrate package. It proves bounded, deterministic, law-governed visual computing properties through 44 bridge milestones across 6 branches. It is NOT full Aurexis Core completion.

---

## Package Totals

| Metric | Value |
|--------|-------|
| Bridge milestones | 44 (40 capability + 4 integration) |
| Completed branches | 6 (5 capability + 1 integration/release) |
| Standalone assertions | 6081, all passing |
| Standalone runners | 54 |
| V1 modules | 56 (12 foundation + 44 bridges) |
| Pytest files | 12 (in aurexis_lang/tests/) |
| Branch capstones verified | 6 |

---

## Branch Inventory

### Branch 1: Static Artifact Substrate (Bridges 1–18)

**Status:** COMPLETE-ENOUGH
**Assertions:** 1873
**What it proves:** Deterministic raster geometry, capture tolerance, artifact localization, orientation/perspective normalization, composed recovery, artifact dispatch, multi-artifact layout, set/sequence/collection contracts and signatures, global consistency.
**Honest limits:** Deterministic geometry only. No real-camera noise model.

### Branch 2: Screen-to-Camera Temporal Transport (Bridges 19–28)

**Status:** COMPLETE-ENOUGH — Capstone verified (2284 assertions)
**What it proves:** Rolling-shutter stripe transport, complementary-color transport, temporal dispatch, temporal consistency, frame-accurate transport, RS+CC fusion, temporal payload contracts/signatures/matching, temporal global consistency.
**Honest limits:** Synthetic captures only. Two frozen transport modes. No real-camera temporal noise.

### Branch 3: Higher-Order Coherence / Sheaf-Style Composition (Bridges 29–32)

**Status:** COMPLETE-ENOUGH — Capstone verified (258 assertions)
**What it proves:** Overlap detection, local section consistency, sheaf-style global composition, cohomological obstruction detection.
**Honest limits:** Bounded to frozen collection family. Sheaf analogy is design inspiration, not full sheaf theory.

### Branch 4: View-Dependent Markers / 3D Moment Invariants (Bridges 33–36)

**Status:** COMPLETE-ENOUGH — Capstone verified (510 assertions)
**What it proves:** 4 frozen markers with stable identity hashes across 4 viewpoint buckets. Full recovery (identity + viewpoint + facet) from single observation. Contract validation.
**Honest limits:** 4 discrete viewpoints, not continuous. Hand-defined markers. Exact hash matching.

### Branch 5: VSA / Hyperdimensional Cleanup (Bridges 37–40)

**Status:** COMPLETE-ENOUGH — Capstone verified (292 assertions)
**What it proves:** 11 cleanup targets mapped to VSA symbols. Bipolar hypervector operations (bind, bundle, permute). Cosine-similarity cleanup retrieval at up to 20% noise. VSA-vs-substrate consistency validation.
**Honest limits:** Dim=1024, 11-entry codebook, simple bit-flip noise. VSA is explicitly AUXILIARY — subordinate to deterministic substrate.

### Branch 6: Integration / Release Hardening (Bridges 41–44)

**Status:** COMPLETE-ENOUGH — Capstone verified (186 assertions)
**What it proves:** Machine-readable manifest, unified entrypoint (7 routes into 44 bridges), 12 cross-branch compatibility rules (all COMPATIBLE), 10 release audit checks (all PASS).
**Honest limits:** Structural checks (imports, namespaces, routing). Not runtime interoperation under load.

---

## Top-Level Entry Points

| Entry Point | Module | Purpose |
|-------------|--------|---------|
| Unified Entrypoint | `unified_substrate_entrypoint_bridge_v1` | Route into any of 44 bridges via 7 named routes |
| Capability Manifest | `unified_capability_manifest_bridge_v1` | Machine-readable enumeration of all capabilities |
| Compatibility Contract | `cross_branch_compatibility_contract_bridge_v1` | 12-rule cross-branch coherence validation |
| Release Audit | `v1_substrate_release_audit_bridge_v1` | 10-check release-level validation |

---

## Entrypoint Routes

| Route | Target | Bridges |
|-------|--------|---------|
| `STATIC_SUBSTRATE` | Static artifact substrate | 1–18 (18 bridges) |
| `TEMPORAL_TRANSPORT` | Temporal transport | 19–28 (10 bridges) |
| `HIGHER_ORDER_COHERENCE` | Sheaf-style coherence | 29–32 (4 bridges) |
| `VIEW_DEPENDENT` | View-dependent markers | 33–36 (4 bridges) |
| `VSA_CLEANUP` | Hyperdimensional cleanup | 37–40 (4 bridges) |
| `MANIFEST` | Capability manifest | Integration module |
| `COMPATIBILITY` | Compatibility contract | Integration module |

---

## What This Package Does NOT Support

This package does NOT claim or provide:

- Full Aurexis Core completion
- Production readiness or deployment infrastructure
- Real-camera noise robustness
- Security, provenance, or tamper-proof identity
- Runtime state management or production API
- Continuous viewpoint recovery (only 4 discrete viewpoints)
- Large-codebook VSA (only 11 entries at 1024 dimensions)
- Real-world temporal noise handling

---

## Explicitly Excluded Technologies

- **OAM (Orbital Angular Momentum)** — Exotic optical encoding not relevant to standard camera/screen pipelines.
- **Optical Skyrmions** — Topological light structures requiring specialized detection hardware.
- **NLOS (Non-Line-of-Sight) Imaging** — Imaging around corners. Irrelevant to direct camera-to-screen pipeline.
- **Exotic Specialized Optics** — Metamaterials, computational optics, holographic elements. Violates Current Tech Floor.

---

## Foundation Modules (Pre-Bridge)

The 12 foundation modules (M1–M10 + fixtures) provide the core substrate: visual grammar, parser, parse rules, executor, program executor, type system, composition, print/scan stability, temporal law, hardware calibration, self-hosting, and substrate integration.

---

## Invariants

1. All bridge outputs are deterministic — same inputs always produce same outputs.
2. The Core Law (7 sections, frozen at V20) is never violated.
3. The VSA layer is auxiliary — the deterministic substrate is always the truth layer.
4. SHA-256 hashes are used for all identity, signature, and manifest operations.
5. No external dependencies beyond Python 3.x standard library.
6. The package runs on current consumer hardware (Current Tech Floor).

---

## How to Verify

```bash
cd aurexis_lang
export PYTHONPATH=src
python3 run_v1_release_audit_tests.py    # 10 release checks, all PASS
python3 run_v1_cross_branch_compatibility_tests.py  # 12 rules, all COMPATIBLE
python3 run_v1_unified_capability_manifest_tests.py  # 53 assertions
python3 run_v1_unified_substrate_entrypoint_tests.py # 57 assertions
```

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
