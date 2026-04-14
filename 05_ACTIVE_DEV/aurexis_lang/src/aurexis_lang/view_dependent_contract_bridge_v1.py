"""
Aurexis Core — View-Dependent Contract Bridge V1

Bounded executable contract layer that validates recovered marker/view
outputs against a frozen contract: expected identity, allowed viewpoint
family, allowed facet per viewpoint bucket.

What this proves:
  Given a recovery result from the view-facet recovery bridge, the
  contract validates:
    1. The recovered marker name is in the frozen family.
    2. The recovered viewpoint is in the allowed bucket set.
    3. The recovered facet hash matches the expected facet for that
       marker + viewpoint combination.
    4. The identity hash matches the frozen marker's identity hash.
  All validation is against the frozen V1 marker profile.

What this does NOT prove:
  - Full 3D contract generality
  - Continuous viewpoint contract coverage
  - Noise-robust real-camera contract enforcement
  - Full Aurexis Core completion

Design:
  - MarkerContract: frozen contract for one marker (expected identity_hash,
    allowed viewpoint → facet_hash mapping).
  - ViewDependentContractProfile: frozen profile of all marker contracts.
  - validate_recovery(): validates a RecoveryResult against the contract.
  - validate_all_recoveries(): batch validation.
  - ContractVerdict: VALID, INVALID_IDENTITY, INVALID_VIEWPOINT,
    INVALID_FACET, UNKNOWN_MARKER, RECOVERY_INCOMPLETE, ERROR.
  - Fabricated violation cases test each rejection path.
  - All operations are deterministic.

This is a narrow bounded contract proof, not a general 3D marker
contract system or full multiview validation engine.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    MARKER_PROFILE_VERSION, MARKER_PROFILE_FROZEN,
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    ViewDependentMarker, MarkerFacet, ViewDependentMarkerProfile,
    V1_MARKER_PROFILE, FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    compute_identity_hash, compute_facet_hash,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    MarkerObservation, extract_invariant_features,
)
from aurexis_lang.view_facet_recovery_bridge_v1 import (
    RECOVERY_VERSION, RECOVERY_FROZEN, RecoveryVerdict, RecoveryResult,
    recover_full, recover_all_observations,
    compute_observation_facet_hash,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CONTRACT_VERSION = "V1.0"
CONTRACT_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONTRACT VERDICTS
# ════════════════════════════════════════════════════════════

class ContractVerdict(str, Enum):
    """Outcome of contract validation."""
    VALID = "VALID"                           # All checks pass
    INVALID_IDENTITY = "INVALID_IDENTITY"     # Identity hash mismatch
    INVALID_VIEWPOINT = "INVALID_VIEWPOINT"   # Viewpoint not in allowed set
    INVALID_FACET = "INVALID_FACET"           # Facet hash mismatch
    UNKNOWN_MARKER = "UNKNOWN_MARKER"         # Marker name not in contract
    RECOVERY_INCOMPLETE = "RECOVERY_INCOMPLETE"  # Recovery didn't achieve FULL_RECOVERY
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# MARKER CONTRACT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MarkerContract:
    """
    Frozen contract for one marker.

    marker_name: the expected marker name.
    expected_identity_hash: the expected identity hash.
    expected_structural_class: the expected structural classification.
    expected_region_count: the expected region count.
    allowed_viewpoints: the set of allowed viewpoint buckets.
    viewpoint_facet_hashes: mapping of viewpoint → expected facet_hash.
    """
    marker_name: str = ""
    expected_identity_hash: str = ""
    expected_structural_class: str = ""
    expected_region_count: int = 0
    allowed_viewpoints: Tuple[ViewpointBucket, ...] = ()
    viewpoint_facet_hashes: Tuple[Tuple[str, str], ...] = ()  # ((vp_value, facet_hash), ...)

    def get_expected_facet_hash(self, viewpoint: ViewpointBucket) -> Optional[str]:
        for vp_val, fh in self.viewpoint_facet_hashes:
            if vp_val == viewpoint.value:
                return fh
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "expected_identity_hash": self.expected_identity_hash[:16] + "...",
            "expected_structural_class": self.expected_structural_class,
            "expected_region_count": self.expected_region_count,
            "allowed_viewpoints": [v.value for v in self.allowed_viewpoints],
            "viewpoint_facet_hash_count": len(self.viewpoint_facet_hashes),
        }


# ════════════════════════════════════════════════════════════
# CONTRACT VALIDATION RESULT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ContractValidationResult:
    """Result of validating a recovery against the contract."""
    marker_name: str = ""
    viewpoint: Optional[ViewpointBucket] = None
    verdict: ContractVerdict = ContractVerdict.ERROR
    identity_check: bool = False
    viewpoint_check: bool = False
    facet_check: bool = False
    detail: str = ""
    version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "viewpoint": self.viewpoint.value if self.viewpoint else None,
            "verdict": self.verdict.value,
            "identity_check": self.identity_check,
            "viewpoint_check": self.viewpoint_check,
            "facet_check": self.facet_check,
            "detail": self.detail,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CONTRACT PROFILE CONSTRUCTION
# ════════════════════════════════════════════════════════════

def _build_marker_contract(marker: ViewDependentMarker) -> MarkerContract:
    """Build a MarkerContract from a frozen ViewDependentMarker."""
    vp_facet_hashes = tuple(
        (f.viewpoint.value, f.facet_hash) for f in marker.facets
    )
    return MarkerContract(
        marker_name=marker.name,
        expected_identity_hash=marker.identity_hash,
        expected_structural_class=marker.structural_class,
        expected_region_count=marker.region_count,
        allowed_viewpoints=tuple(f.viewpoint for f in marker.facets),
        viewpoint_facet_hashes=vp_facet_hashes,
    )


@dataclass(frozen=True)
class ViewDependentContractProfile:
    """Frozen profile of all marker contracts."""
    contracts: Tuple[MarkerContract, ...] = ()
    version: str = CONTRACT_VERSION

    @property
    def contract_count(self) -> int:
        return len(self.contracts)

    def get_contract(self, marker_name: str) -> Optional[MarkerContract]:
        for c in self.contracts:
            if c.marker_name == marker_name:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contracts": [c.to_dict() for c in self.contracts],
            "contract_count": self.contract_count,
            "version": self.version,
        }


# Build frozen contract profile from frozen marker family
V1_CONTRACT_PROFILE = ViewDependentContractProfile(
    contracts=tuple(_build_marker_contract(m) for m in FROZEN_MARKER_FAMILY),
)


# ════════════════════════════════════════════════════════════
# CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

def validate_recovery(
    recovery: RecoveryResult,
    profile: ViewDependentContractProfile = V1_CONTRACT_PROFILE,
) -> ContractValidationResult:
    """
    Validate a RecoveryResult against the frozen contract profile.

    Checks:
      1. Recovery must have achieved FULL_RECOVERY.
      2. Recovered marker name must be in the contract.
      3. Identity hash must match the contract's expected identity hash.
      4. Recovered viewpoint must be in the allowed set.
      5. Recovered facet hash must match the expected facet hash for that viewpoint.
    """
    # Check recovery completeness
    if recovery.verdict != RecoveryVerdict.FULL_RECOVERY:
        return ContractValidationResult(
            marker_name=recovery.recovered_marker_name,
            viewpoint=recovery.recovered_viewpoint,
            verdict=ContractVerdict.RECOVERY_INCOMPLETE,
            detail=f"Recovery verdict was {recovery.verdict.value}, not FULL_RECOVERY",
        )

    # Look up contract
    contract = profile.get_contract(recovery.recovered_marker_name)
    if contract is None:
        return ContractValidationResult(
            marker_name=recovery.recovered_marker_name,
            viewpoint=recovery.recovered_viewpoint,
            verdict=ContractVerdict.UNKNOWN_MARKER,
            detail=f"No contract for marker '{recovery.recovered_marker_name}'",
        )

    # Check identity hash
    identity_ok = (recovery.observation_identity_hash == contract.expected_identity_hash)
    if not identity_ok:
        return ContractValidationResult(
            marker_name=recovery.recovered_marker_name,
            viewpoint=recovery.recovered_viewpoint,
            verdict=ContractVerdict.INVALID_IDENTITY,
            identity_check=False,
            detail=f"Identity hash mismatch for {recovery.recovered_marker_name}",
        )

    # Check viewpoint
    viewpoint_ok = (recovery.recovered_viewpoint in contract.allowed_viewpoints)
    if not viewpoint_ok:
        return ContractValidationResult(
            marker_name=recovery.recovered_marker_name,
            viewpoint=recovery.recovered_viewpoint,
            verdict=ContractVerdict.INVALID_VIEWPOINT,
            identity_check=True,
            viewpoint_check=False,
            detail=f"Viewpoint {recovery.recovered_viewpoint} not allowed for {recovery.recovered_marker_name}",
        )

    # Check facet hash
    expected_fh = contract.get_expected_facet_hash(recovery.recovered_viewpoint)
    facet_ok = (
        recovery.recovered_facet is not None
        and expected_fh is not None
        and recovery.recovered_facet.facet_hash == expected_fh
    )
    if not facet_ok:
        return ContractValidationResult(
            marker_name=recovery.recovered_marker_name,
            viewpoint=recovery.recovered_viewpoint,
            verdict=ContractVerdict.INVALID_FACET,
            identity_check=True,
            viewpoint_check=True,
            facet_check=False,
            detail=f"Facet hash mismatch for {recovery.recovered_marker_name} at {recovery.recovered_viewpoint.value}",
        )

    return ContractValidationResult(
        marker_name=recovery.recovered_marker_name,
        viewpoint=recovery.recovered_viewpoint,
        verdict=ContractVerdict.VALID,
        identity_check=True,
        viewpoint_check=True,
        facet_check=True,
        detail=f"Contract valid: {recovery.recovered_marker_name} at {recovery.recovered_viewpoint.value}",
    )


def validate_all_recoveries(
    profile: ViewDependentContractProfile = V1_CONTRACT_PROFILE,
) -> Tuple[ContractValidationResult, ...]:
    """Validate all recoveries from all frozen markers against the contract."""
    recoveries = recover_all_observations()
    return tuple(validate_recovery(r, profile) for r in recoveries)


# ════════════════════════════════════════════════════════════
# FABRICATED VIOLATION CASES
# ════════════════════════════════════════════════════════════

def make_incomplete_recovery() -> RecoveryResult:
    """A recovery that didn't achieve FULL_RECOVERY."""
    return RecoveryResult(
        recovered_marker_name="alpha_planar",
        verdict=RecoveryVerdict.NO_IDENTITY,
        detail="Fabricated incomplete recovery",
    )


def make_unknown_marker_recovery() -> RecoveryResult:
    """A full recovery for a marker not in the contract."""
    fake_facet = MarkerFacet(
        viewpoint=ViewpointBucket.FRONT,
        visible_regions=99,
        dominant_axis="spiral",
        aspect_ratio_bucket="extreme",
        facet_hash="fake_hash",
    )
    return RecoveryResult(
        recovered_marker_name="phantom_marker",
        recovered_viewpoint=ViewpointBucket.FRONT,
        recovered_facet=fake_facet,
        observation_identity_hash="fake_identity",
        observation_facet_hash="fake_facet",
        verdict=RecoveryVerdict.FULL_RECOVERY,
        detail="Fabricated unknown marker recovery",
    )


def make_identity_mismatch_recovery() -> RecoveryResult:
    """A full recovery with correct name but wrong identity hash."""
    real_marker = FROZEN_MARKER_FAMILY[0]
    real_facet = real_marker.facets[0]
    return RecoveryResult(
        recovered_marker_name=real_marker.name,
        recovered_viewpoint=ViewpointBucket.FRONT,
        recovered_facet=real_facet,
        observation_identity_hash="wrong_identity_hash_000000",
        observation_facet_hash=real_facet.facet_hash,
        verdict=RecoveryVerdict.FULL_RECOVERY,
        detail="Fabricated identity mismatch",
    )


def make_facet_mismatch_recovery() -> RecoveryResult:
    """A full recovery with correct identity but wrong facet hash."""
    real_marker = FROZEN_MARKER_FAMILY[0]
    fake_facet = MarkerFacet(
        viewpoint=ViewpointBucket.FRONT,
        visible_regions=99,
        dominant_axis="spiral",
        aspect_ratio_bucket="extreme",
        facet_hash="wrong_facet_hash_000000",
    )
    return RecoveryResult(
        recovered_marker_name=real_marker.name,
        recovered_viewpoint=ViewpointBucket.FRONT,
        recovered_facet=fake_facet,
        observation_identity_hash=real_marker.identity_hash,
        observation_facet_hash="wrong_facet_hash_000000",
        verdict=RecoveryVerdict.FULL_RECOVERY,
        detail="Fabricated facet mismatch",
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

EXPECTED_CONTRACT_COUNT = len(FROZEN_MARKER_FAMILY)  # 4
EXPECTED_VALID_COUNT = len(FROZEN_MARKER_FAMILY) * VIEWPOINT_COUNT  # 16
VIOLATION_CASE_COUNT = 4  # incomplete, unknown, identity mismatch, facet mismatch
