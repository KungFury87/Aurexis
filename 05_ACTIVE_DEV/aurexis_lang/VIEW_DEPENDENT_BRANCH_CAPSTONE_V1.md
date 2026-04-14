# VIEW-DEPENDENT MARKERS / 3D MOMENT INVARIANTS BRANCH — CAPSTONE VERIFICATION

**Branch:** View-Dependent Markers (Bridges 33–36)
**Date:** April 13, 2026
**Auditor:** Claude (constrained implementer)
**Owner:** Vincent Anderson

---

## Branch Summary

This branch proves that a frozen family of view-dependent markers can be:
1. **Defined** with stable identity and bounded view-dependent facets (Bridge 33)
2. **Identified** across all viewpoint buckets using moment-invariant features (Bridge 34)
3. **Fully recovered** — both identity and facet — from a single observation (Bridge 35)
4. **Validated** against a frozen contract that enforces identity, viewpoint, and facet correctness (Bridge 36)

The branch proves that viewpoint changes alter the secondary facet while preserving primary identity, and that a contract can enforce this separation.

---

## Branch Bridges

| # | Bridge | Assertions | Pytest Fns | Gate |
|---|--------|-----------|------------|------|
| 33 | View-Dependent Marker Profile V1 | 95 | 30 | 20/20 PASS |
| 34 | Moment-Invariant Identity V1 | 92 | 20 | 17/17 PASS |
| 35 | View-Facet Recovery V1 | 179 | 16 | 17/17 PASS |
| 36 | View-Dependent Contract V1 | 144 | 19 | 18/18 PASS |
| **Total** | | **510** | **85** | **72/72 PASS** |

---

## What This Branch Proves

- A frozen family of 4 markers (alpha_planar, beta_relief, gamma_prismatic, delta_pyramidal) with 4 viewpoint buckets (FRONT, LEFT, RIGHT, TILT_PLUS) = 16 total facets.
- Each marker has a unique, deterministic identity hash computed from stable fields (name, structural_class, region_count).
- Each facet has a unique, deterministic facet hash computed from view-dependent fields.
- Identity is provably invariant across all 4 viewpoints for all 4 markers.
- Facets provably vary across viewpoints while identity stays constant.
- Full recovery (identity + viewpoint + facet) succeeds for all 16 marker/viewpoint combinations.
- Contract validation passes for all 16 valid recoveries.
- All 4 rejection paths tested: unknown marker, corrupted observation, identity mismatch, facet mismatch.

## What This Branch Does NOT Prove

- Full 3D moment-invariant theory generality
- Continuous viewpoint recovery or interpolation
- Noise-robust real-camera identity/facet recovery
- Full Aurexis Core completion

---

## Honest Limits

- Viewpoint buckets are discrete (4 positions), not continuous.
- Markers are defined by hand, not discovered from real imagery.
- Facet matching uses exact hash comparison, not approximate or noise-tolerant matching.
- This is a narrow bounded proof, not a general 3D appearance model.

---

## Cumulative Totals (After Branch)

- **Bridges:** 36 (18 static substrate + 10 temporal transport + 4 higher-order coherence + 4 view-dependent markers)
- **Standalone assertions:** 5603 (5093 prior + 510 new)
- **Pytest functions:** 1185 (1100 prior + 85 new)
- **Standalone runners:** 46 (42 prior + 4 new)
- **Source modules:** 48 (44 prior + 4 new)

---

## Branch Verdict: COMPLETE-ENOUGH

All 4 bridges pass gate verification. The view-dependent markers branch is complete as a narrow bounded proof. This is not a general 3D moment-invariant system — it is a bounded identity-invariance and contract-validation proof for a frozen marker family.

---

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
