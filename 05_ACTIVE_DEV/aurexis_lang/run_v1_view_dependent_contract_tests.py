#!/usr/bin/env python3
"""
Aurexis Core — View-Dependent Contract Bridge V1 — Standalone Test Runner

Tests the view-dependent contract validation layer:
  - Module version and frozen state
  - Contract profile construction
  - Contract lookup
  - Valid recovery validation
  - Batch validation
  - Incomplete recovery rejection
  - Unknown marker rejection
  - Identity mismatch rejection
  - Facet mismatch rejection
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
    generate_observation,
)
from aurexis_lang.view_facet_recovery_bridge_v1 import (
    RecoveryVerdict, recover_full,
)
from aurexis_lang.view_dependent_contract_bridge_v1 import (
    CONTRACT_VERSION, CONTRACT_FROZEN, ContractVerdict,
    MarkerContract, ViewDependentContractProfile, ContractValidationResult,
    V1_CONTRACT_PROFILE,
    validate_recovery, validate_all_recoveries,
    make_incomplete_recovery, make_unknown_marker_recovery,
    make_identity_mismatch_recovery, make_facet_mismatch_recovery,
    EXPECTED_CONTRACT_COUNT, EXPECTED_VALID_COUNT, VIOLATION_CASE_COUNT,
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
check(CONTRACT_VERSION == "V1.0", "Version is V1.0")
check(CONTRACT_FROZEN is True, "Module is frozen")
check(EXPECTED_CONTRACT_COUNT == 4, "EXPECTED_CONTRACT_COUNT == 4")
check(EXPECTED_VALID_COUNT == 16, "EXPECTED_VALID_COUNT == 16")
check(VIOLATION_CASE_COUNT == 4, "VIOLATION_CASE_COUNT == 4")

# ──────────────────────────────────────────────────────────
section("2. Contract Profile Construction")
check(V1_CONTRACT_PROFILE.contract_count == EXPECTED_CONTRACT_COUNT, f"Profile has {EXPECTED_CONTRACT_COUNT} contracts")
check(V1_CONTRACT_PROFILE.version == CONTRACT_VERSION, "Profile version correct")

# ──────────────────────────────────────────────────────────
section("3. Contract Lookup")
for name in FROZEN_MARKER_NAMES:
    c = V1_CONTRACT_PROFILE.get_contract(name)
    check(c is not None, f"Contract found for {name}")
    if c:
        check(c.marker_name == name, f"Contract name matches {name}")
        check(len(c.allowed_viewpoints) == VIEWPOINT_COUNT, f"{name}: {VIEWPOINT_COUNT} allowed viewpoints")
        check(len(c.viewpoint_facet_hashes) == VIEWPOINT_COUNT, f"{name}: {VIEWPOINT_COUNT} facet hashes")
check(V1_CONTRACT_PROFILE.get_contract("nonexistent") is None, "Unknown marker returns None")

# ──────────────────────────────────────────────────────────
section("4. Contract Identity Hashes Match Frozen Markers")
for marker in FROZEN_MARKER_FAMILY:
    c = V1_CONTRACT_PROFILE.get_contract(marker.name)
    check(c.expected_identity_hash == marker.identity_hash, f"{marker.name}: identity hash matches")
    check(c.expected_structural_class == marker.structural_class, f"{marker.name}: structural class matches")
    check(c.expected_region_count == marker.region_count, f"{marker.name}: region count matches")

# ──────────────────────────────────────────────────────────
section("5. Contract Facet Hashes Match Frozen Facets")
for marker in FROZEN_MARKER_FAMILY:
    c = V1_CONTRACT_PROFILE.get_contract(marker.name)
    for vp in ALL_VIEWPOINTS:
        expected_fh = c.get_expected_facet_hash(vp)
        actual_facet = marker.get_facet(vp)
        check(expected_fh == actual_facet.facet_hash, f"{marker.name}/{vp.value}: contract facet hash matches")

# ──────────────────────────────────────────────────────────
section("6. Valid Recovery Validation — Individual")
for marker in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        obs = generate_observation(marker, vp)
        recovery = recover_full(obs)
        result = validate_recovery(recovery)
        check(result.verdict == ContractVerdict.VALID, f"{marker.name}/{vp.value}: VALID")
        check(result.identity_check is True, f"{marker.name}/{vp.value}: identity_check")
        check(result.viewpoint_check is True, f"{marker.name}/{vp.value}: viewpoint_check")
        check(result.facet_check is True, f"{marker.name}/{vp.value}: facet_check")

# ──────────────────────────────────────────────────────────
section("7. Valid Recovery Validation — Batch")
all_results = validate_all_recoveries()
check(len(all_results) == EXPECTED_VALID_COUNT, f"Batch returns {EXPECTED_VALID_COUNT} results")
valid_count = sum(1 for r in all_results if r.verdict == ContractVerdict.VALID)
check(valid_count == EXPECTED_VALID_COUNT, f"All {EXPECTED_VALID_COUNT} are VALID")

# ──────────────────────────────────────────────────────────
section("8. Violation: Incomplete Recovery")
inc = make_incomplete_recovery()
result = validate_recovery(inc)
check(result.verdict == ContractVerdict.RECOVERY_INCOMPLETE, "Incomplete: RECOVERY_INCOMPLETE")
check(result.identity_check is False, "Incomplete: identity_check False")
check(result.viewpoint_check is False, "Incomplete: viewpoint_check False")
check(result.facet_check is False, "Incomplete: facet_check False")

# ──────────────────────────────────────────────────────────
section("9. Violation: Unknown Marker")
unk = make_unknown_marker_recovery()
result = validate_recovery(unk)
check(result.verdict == ContractVerdict.UNKNOWN_MARKER, "Unknown: UNKNOWN_MARKER")

# ──────────────────────────────────────────────────────────
section("10. Violation: Identity Mismatch")
idm = make_identity_mismatch_recovery()
result = validate_recovery(idm)
check(result.verdict == ContractVerdict.INVALID_IDENTITY, "Identity mismatch: INVALID_IDENTITY")
check(result.identity_check is False, "Identity mismatch: identity_check False")

# ──────────────────────────────────────────────────────────
section("11. Violation: Facet Mismatch")
fm = make_facet_mismatch_recovery()
result = validate_recovery(fm)
check(result.verdict == ContractVerdict.INVALID_FACET, "Facet mismatch: INVALID_FACET")
check(result.identity_check is True, "Facet mismatch: identity_check True (identity matched)")
check(result.viewpoint_check is True, "Facet mismatch: viewpoint_check True")
check(result.facet_check is False, "Facet mismatch: facet_check False")

# ──────────────────────────────────────────────────────────
section("12. ContractValidationResult Serialization")
obs = generate_observation(FROZEN_MARKER_FAMILY[0], ViewpointBucket.FRONT)
recovery = recover_full(obs)
result = validate_recovery(recovery)
d = result.to_dict()
check(d["verdict"] == "VALID", "to_dict verdict")
check(d["marker_name"] == "alpha_planar", "to_dict marker_name")
check(d["viewpoint"] == "FRONT", "to_dict viewpoint")
check(d["identity_check"] is True, "to_dict identity_check")
check(d["viewpoint_check"] is True, "to_dict viewpoint_check")
check(d["facet_check"] is True, "to_dict facet_check")
check(d["version"] == CONTRACT_VERSION, "to_dict version")

# ──────────────────────────────────────────────────────────
section("13. Contract Profile Serialization")
pd = V1_CONTRACT_PROFILE.to_dict()
check(pd["contract_count"] == EXPECTED_CONTRACT_COUNT, "Profile to_dict contract_count")
check(len(pd["contracts"]) == EXPECTED_CONTRACT_COUNT, "Profile to_dict contracts length")
check(pd["version"] == CONTRACT_VERSION, "Profile to_dict version")

# ──────────────────────────────────────────────────────────
section("14. MarkerContract Serialization")
c = V1_CONTRACT_PROFILE.contracts[0]
cd = c.to_dict()
check(cd["marker_name"] == "alpha_planar", "Contract to_dict marker_name")
check(cd["expected_structural_class"] == "planar", "Contract to_dict structural_class")
check(cd["expected_region_count"] == 4, "Contract to_dict region_count")
check(len(cd["allowed_viewpoints"]) == VIEWPOINT_COUNT, "Contract to_dict viewpoints")

# ──────────────────────────────────────────────────────────
section("15. ContractValidationResult Immutability")
try:
    result.verdict = ContractVerdict.ERROR  # type: ignore
    check(False, "ContractValidationResult should be immutable")
except (AttributeError, TypeError):
    check(True, "ContractValidationResult is immutable")


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
