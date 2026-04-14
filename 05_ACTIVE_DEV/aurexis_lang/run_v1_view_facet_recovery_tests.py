#!/usr/bin/env python3
"""
Aurexis Core — View-Facet Recovery Bridge V1 — Standalone Test Runner

Tests the view-facet recovery layer:
  - Module version and frozen state
  - Observation facet hash computation
  - Marker identity recovery
  - Viewpoint recovery
  - Full recovery (identity + viewpoint + facet)
  - Batch recovery across all markers/viewpoints
  - Facet variation verification
  - Unknown marker rejection
  - Identity-only partial recovery
  - Serialization

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    generate_observation, generate_all_observations,
)
from aurexis_lang.view_facet_recovery_bridge_v1 import (
    RECOVERY_VERSION, RECOVERY_FROZEN, RecoveryVerdict,
    RecoveryResult, FacetVariationResult,
    compute_observation_facet_hash,
    recover_marker_identity, recover_viewpoint, recover_full,
    recover_all_observations, verify_facet_variation, verify_all_facet_variations,
    make_unknown_marker_observation, make_identity_only_observation,
    TOTAL_RECOVERY_COUNT, FULL_RECOVERY_EXPECTED, FACET_VARIATION_MARKER_COUNT,
)


PASS_COUNT = 0
FAIL_COUNT = 0


def section(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def check(condition: bool, label: str):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAIL_COUNT += 1
    else:
        PASS_COUNT += 1
    print(f"  [{status}] {label}")


# ──────────────────────────────────────────────────────────
section("1. Module Version and Frozen State")
check(RECOVERY_VERSION == "V1.0", "Version is V1.0")
check(RECOVERY_FROZEN is True, "Module is frozen")
check(TOTAL_RECOVERY_COUNT == 16, "TOTAL_RECOVERY_COUNT == 16")
check(FULL_RECOVERY_EXPECTED == 16, "FULL_RECOVERY_EXPECTED == 16")
check(FACET_VARIATION_MARKER_COUNT == 4, "FACET_VARIATION_MARKER_COUNT == 4")

# ──────────────────────────────────────────────────────────
section("2. Observation Facet Hash Computation")
for marker in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        obs = generate_observation(marker, vp)
        if obs:
            fh = compute_observation_facet_hash(obs)
            expected_facet = marker.get_facet(vp)
            check(fh == expected_facet.facet_hash, f"{marker.name}/{vp.value}: facet hash matches frozen facet")

# ──────────────────────────────────────────────────────────
section("3. Marker Identity Recovery")
for marker in FROZEN_MARKER_FAMILY:
    obs = generate_observation(marker, ViewpointBucket.FRONT)
    recovered = recover_marker_identity(obs)
    check(recovered is not None, f"{marker.name}: identity recovered")
    check(recovered.name == marker.name, f"{marker.name}: correct marker recovered")

# ──────────────────────────────────────────────────────────
section("4. Viewpoint Recovery")
for marker in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        obs = generate_observation(marker, vp)
        result = recover_viewpoint(obs, marker)
        check(result is not None, f"{marker.name}/{vp.value}: viewpoint recovered")
        if result:
            recovered_vp, recovered_facet = result
            check(recovered_vp == vp, f"{marker.name}/{vp.value}: correct viewpoint")
            check(recovered_facet.facet_hash == marker.get_facet(vp).facet_hash, f"{marker.name}/{vp.value}: correct facet")

# ──────────────────────────────────────────────────────────
section("5. Full Recovery — Individual Cases")
for marker in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        obs = generate_observation(marker, vp)
        result = recover_full(obs)
        check(result.verdict == RecoveryVerdict.FULL_RECOVERY, f"{marker.name}/{vp.value}: FULL_RECOVERY")
        check(result.recovered_marker_name == marker.name, f"{marker.name}/{vp.value}: correct name")
        check(result.recovered_viewpoint == vp, f"{marker.name}/{vp.value}: correct viewpoint")
        check(result.recovered_facet is not None, f"{marker.name}/{vp.value}: facet present")

# ──────────────────────────────────────────────────────────
section("6. Full Recovery — Batch")
all_results = recover_all_observations()
check(len(all_results) == TOTAL_RECOVERY_COUNT, f"Batch returns {TOTAL_RECOVERY_COUNT} results")
full_count = sum(1 for r in all_results if r.verdict == RecoveryVerdict.FULL_RECOVERY)
check(full_count == FULL_RECOVERY_EXPECTED, f"All {FULL_RECOVERY_EXPECTED} are FULL_RECOVERY")

# ──────────────────────────────────────────────────────────
section("7. Facet Variation — Individual")
for marker in FROZEN_MARKER_FAMILY:
    v = verify_facet_variation(marker)
    check(v.identity_stable is True, f"{marker.name}: identity stable")
    check(v.facets_vary is True, f"{marker.name}: facets vary")
    check(v.unique_facet_hashes == VIEWPOINT_COUNT, f"{marker.name}: {VIEWPOINT_COUNT} unique facets")
    check(v.total_viewpoints == VIEWPOINT_COUNT, f"{marker.name}: {VIEWPOINT_COUNT} viewpoints")

# ──────────────────────────────────────────────────────────
section("8. Facet Variation — Batch")
all_var = verify_all_facet_variations()
check(len(all_var) == FACET_VARIATION_MARKER_COUNT, f"Batch returns {FACET_VARIATION_MARKER_COUNT}")
check(all(v.identity_stable for v in all_var), "All markers identity-stable")
check(all(v.facets_vary for v in all_var), "All markers have varying facets")

# ──────────────────────────────────────────────────────────
section("9. Unknown Marker — NO_IDENTITY")
unk_obs = make_unknown_marker_observation()
unk_result = recover_full(unk_obs)
check(unk_result.verdict == RecoveryVerdict.NO_IDENTITY, "Unknown marker: NO_IDENTITY")
check(unk_result.recovered_marker_name == "", "Unknown marker: no recovered name")
check(unk_result.recovered_viewpoint is None, "Unknown marker: no recovered viewpoint")
check(unk_result.recovered_facet is None, "Unknown marker: no recovered facet")

# ──────────────────────────────────────────────────────────
section("10. Identity-Only — Corrupted Facet")
ido_obs = make_identity_only_observation()
ido_result = recover_full(ido_obs)
check(ido_result.verdict == RecoveryVerdict.IDENTITY_ONLY, "Identity-only: IDENTITY_ONLY")
check(ido_result.recovered_marker_name == "alpha_planar", "Identity-only: recovered alpha_planar")
check(ido_result.recovered_viewpoint is None, "Identity-only: no viewpoint")
check(ido_result.recovered_facet is None, "Identity-only: no facet")

# ──────────────────────────────────────────────────────────
section("11. RecoveryResult Serialization")
obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
result = recover_full(obs)
d = result.to_dict()
check(d["verdict"] == "FULL_RECOVERY", "to_dict verdict")
check(d["recovered_marker_name"] == "alpha_planar", "to_dict recovered_marker_name")
check(d["recovered_viewpoint"] == "FRONT", "to_dict recovered_viewpoint")
check(d["version"] == RECOVERY_VERSION, "to_dict version")

# ──────────────────────────────────────────────────────────
section("12. FacetVariationResult Serialization")
v = verify_facet_variation(FROZEN_MARKER_FAMILY[0])
vd = v.to_dict()
check(vd["marker_name"] == "alpha_planar", "Variation to_dict marker_name")
check(vd["identity_stable"] is True, "Variation to_dict identity_stable")
check(vd["facets_vary"] is True, "Variation to_dict facets_vary")
check(vd["unique_facet_hashes"] == 4, "Variation to_dict unique_facet_hashes")

# ──────────────────────────────────────────────────────────
section("13. RecoveryResult Immutability")
try:
    result.verdict = RecoveryVerdict.ERROR  # type: ignore
    check(False, "RecoveryResult should be immutable")
except (AttributeError, TypeError):
    check(True, "RecoveryResult is immutable")


# ══════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed, {PASS_COUNT + FAIL_COUNT} total")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    print("  *** FAILURES DETECTED ***")
    sys.exit(1)
else:
    print("  ALL PASS")
    sys.exit(0)
