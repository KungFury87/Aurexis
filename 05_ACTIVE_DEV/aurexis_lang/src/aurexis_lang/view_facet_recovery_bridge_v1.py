"""
Aurexis Core — View-Facet Recovery Bridge V1

Bounded executable recovery layer that recovers both the stable marker
identity AND the bounded view-dependent facet/state from a single
observation. Proves that viewpoint changes alter the secondary facet
while preserving primary identity.

What this proves:
  Given a single MarkerObservation (simulated capture), the system can:
    1. Recover the stable marker identity (which frozen marker produced it).
    2. Recover which viewpoint bucket the observation came from.
    3. Recover the full MarkerFacet for that viewpoint.
  The primary identity is invariant across viewpoints; only the secondary
  facet changes.

What this does NOT prove:
  - Full 3D moment-invariant theory generality
  - Continuous viewpoint recovery
  - Noise-robust real-camera facet recovery
  - Full Aurexis Core completion

Design:
  - recover_marker_identity(): recovers which frozen marker produced an
    observation by matching the identity hash.
  - recover_viewpoint(): recovers which viewpoint bucket an observation
    came from by matching the facet hash against known facets.
  - recover_full_facet(): full recovery — identity + viewpoint + facet.
  - RecoveryResult: contains identity, viewpoint, facet, and verdict.
  - verify_facet_variation(): proves that a marker's facets actually
    change across viewpoints while identity stays constant.
  - Fabricated cases test unknown marker and ambiguous facet paths.
  - All operations are deterministic.

This is a narrow bounded recovery proof, not a general 3D appearance
recovery system or full multiview reconstruction.

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
    IDENTITY_VERSION, IDENTITY_FROZEN,
    MarkerObservation, InvariantFeatures,
    extract_invariant_features, identify_marker,
    generate_observation, generate_all_observations,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

RECOVERY_VERSION = "V1.0"
RECOVERY_FROZEN = True


# ════════════════════════════════════════════════════════════
# RECOVERY VERDICTS
# ════════════════════════════════════════════════════════════

class RecoveryVerdict(str, Enum):
    """Outcome of view-facet recovery."""
    FULL_RECOVERY = "FULL_RECOVERY"           # Identity + viewpoint + facet all recovered
    IDENTITY_ONLY = "IDENTITY_ONLY"           # Identity recovered but viewpoint/facet not matched
    NO_IDENTITY = "NO_IDENTITY"               # Marker not found in frozen family
    AMBIGUOUS_FACET = "AMBIGUOUS_FACET"        # Multiple facets match (should not happen with frozen family)
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# RECOVERY RESULT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RecoveryResult:
    """
    Result of recovering identity and facet from an observation.

    recovered_marker_name: the identified frozen marker (or "" if unknown).
    recovered_viewpoint: the recovered viewpoint bucket (or None).
    recovered_facet: the matched MarkerFacet (or None).
    observation_identity_hash: the identity hash from the observation.
    observation_facet_hash: the facet hash computed from observation fields.
    verdict: the recovery outcome.
    detail: human-readable explanation.
    """
    recovered_marker_name: str = ""
    recovered_viewpoint: Optional[ViewpointBucket] = None
    recovered_facet: Optional[MarkerFacet] = None
    observation_identity_hash: str = ""
    observation_facet_hash: str = ""
    verdict: RecoveryVerdict = RecoveryVerdict.ERROR
    detail: str = ""
    version: str = RECOVERY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovered_marker_name": self.recovered_marker_name,
            "recovered_viewpoint": self.recovered_viewpoint.value if self.recovered_viewpoint else None,
            "recovered_facet_hash": self.recovered_facet.facet_hash[:16] + "..." if self.recovered_facet else None,
            "observation_identity_hash": self.observation_identity_hash[:16] + "..." if self.observation_identity_hash else "",
            "observation_facet_hash": self.observation_facet_hash[:16] + "..." if self.observation_facet_hash else "",
            "verdict": self.verdict.value,
            "detail": self.detail,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FACET HASH FROM OBSERVATION
# ════════════════════════════════════════════════════════════

def compute_observation_facet_hash(obs: MarkerObservation) -> str:
    """Compute the facet hash from an observation's view-dependent fields."""
    return compute_facet_hash(
        obs.marker_name, obs.viewpoint,
        obs.visible_regions, obs.dominant_axis, obs.aspect_ratio_bucket,
    )


# ════════════════════════════════════════════════════════════
# CORE RECOVERY FUNCTIONS
# ════════════════════════════════════════════════════════════

def recover_marker_identity(obs: MarkerObservation) -> Optional[ViewDependentMarker]:
    """
    Recover which frozen marker produced an observation.

    Returns the ViewDependentMarker or None if not found.
    """
    features = extract_invariant_features(obs)
    for marker in FROZEN_MARKER_FAMILY:
        if marker.identity_hash == features.identity_hash:
            return marker
    return None


def recover_viewpoint(
    obs: MarkerObservation,
    marker: ViewDependentMarker,
) -> Optional[Tuple[ViewpointBucket, MarkerFacet]]:
    """
    Recover which viewpoint bucket an observation came from.

    Matches the observation's facet hash against the marker's known facets.
    Returns (viewpoint, facet) or None if no match.
    """
    obs_facet_hash = compute_observation_facet_hash(obs)
    for facet in marker.facets:
        if facet.facet_hash == obs_facet_hash:
            return (facet.viewpoint, facet)
    return None


def recover_full(obs: MarkerObservation) -> RecoveryResult:
    """
    Full recovery: identity + viewpoint + facet from a single observation.

    Steps:
      1. Recover marker identity via invariant features.
      2. If found, recover viewpoint/facet via facet hash matching.
      3. Return RecoveryResult with full information.
    """
    features = extract_invariant_features(obs)
    obs_facet_hash = compute_observation_facet_hash(obs)

    # Step 1: Recover identity
    marker = recover_marker_identity(obs)
    if marker is None:
        return RecoveryResult(
            observation_identity_hash=features.identity_hash,
            observation_facet_hash=obs_facet_hash,
            verdict=RecoveryVerdict.NO_IDENTITY,
            detail=f"No frozen marker matches identity hash {features.identity_hash[:16]}...",
        )

    # Step 2: Recover viewpoint/facet
    vp_result = recover_viewpoint(obs, marker)
    if vp_result is None:
        return RecoveryResult(
            recovered_marker_name=marker.name,
            observation_identity_hash=features.identity_hash,
            observation_facet_hash=obs_facet_hash,
            verdict=RecoveryVerdict.IDENTITY_ONLY,
            detail=f"Marker {marker.name} identified but facet hash {obs_facet_hash[:16]}... not matched",
        )

    viewpoint, facet = vp_result
    return RecoveryResult(
        recovered_marker_name=marker.name,
        recovered_viewpoint=viewpoint,
        recovered_facet=facet,
        observation_identity_hash=features.identity_hash,
        observation_facet_hash=obs_facet_hash,
        verdict=RecoveryVerdict.FULL_RECOVERY,
        detail=f"Full recovery: {marker.name} from {viewpoint.value}",
    )


# ════════════════════════════════════════════════════════════
# FACET VARIATION VERIFICATION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FacetVariationResult:
    """Result of verifying that facets vary across viewpoints."""
    marker_name: str = ""
    identity_stable: bool = False
    facets_vary: bool = False
    unique_facet_hashes: int = 0
    total_viewpoints: int = 0
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "identity_stable": self.identity_stable,
            "facets_vary": self.facets_vary,
            "unique_facet_hashes": self.unique_facet_hashes,
            "total_viewpoints": self.total_viewpoints,
            "detail": self.detail,
        }


def verify_facet_variation(marker: ViewDependentMarker) -> FacetVariationResult:
    """
    Verify that a marker's facets actually change across viewpoints
    while identity remains constant.

    A marker with view-dependent facets should have:
      - Identical identity hash from all viewpoints (identity_stable=True)
      - Different facet hashes from at least some viewpoints (facets_vary=True)
    """
    observations = generate_all_observations(marker)
    if not observations:
        return FacetVariationResult(
            marker_name=marker.name,
            detail="No observations generated",
        )

    # Check identity stability
    identity_hashes = set()
    facet_hashes = set()
    for obs in observations:
        features = extract_invariant_features(obs)
        identity_hashes.add(features.identity_hash)
        facet_hashes.add(compute_observation_facet_hash(obs))

    identity_stable = len(identity_hashes) == 1
    facets_vary = len(facet_hashes) > 1

    return FacetVariationResult(
        marker_name=marker.name,
        identity_stable=identity_stable,
        facets_vary=facets_vary,
        unique_facet_hashes=len(facet_hashes),
        total_viewpoints=len(observations),
        detail=f"Identity {'stable' if identity_stable else 'UNSTABLE'}, "
               f"{len(facet_hashes)} unique facets across {len(observations)} viewpoints",
    )


def verify_all_facet_variations() -> Tuple[FacetVariationResult, ...]:
    """Verify facet variation for all frozen markers."""
    return tuple(verify_facet_variation(m) for m in FROZEN_MARKER_FAMILY)


# ════════════════════════════════════════════════════════════
# BATCH RECOVERY
# ════════════════════════════════════════════════════════════

def recover_all_observations() -> Tuple[RecoveryResult, ...]:
    """
    Recover identity + facet for every observation of every frozen marker
    from every viewpoint.
    """
    results = []
    for marker in FROZEN_MARKER_FAMILY:
        for obs in generate_all_observations(marker):
            results.append(recover_full(obs))
    return tuple(results)


# ════════════════════════════════════════════════════════════
# FABRICATED TEST CASES
# ════════════════════════════════════════════════════════════

def make_unknown_marker_observation() -> MarkerObservation:
    """Create an observation from an unknown marker (no identity match)."""
    return MarkerObservation(
        marker_name="phantom_marker",
        viewpoint=ViewpointBucket.FRONT,
        structural_class="exotic",
        region_count=42,
        visible_regions=42,
        dominant_axis="spiral",
        aspect_ratio_bucket="extreme",
    )


def make_identity_only_observation() -> MarkerObservation:
    """
    Create an observation with valid identity but corrupted facet data.
    Identity will match alpha_planar, but facet hash won't match any viewpoint.
    """
    return MarkerObservation(
        marker_name="alpha_planar",
        viewpoint=ViewpointBucket.FRONT,
        structural_class="planar",
        region_count=4,
        # These facet fields don't match any frozen facet for alpha_planar
        visible_regions=99,
        dominant_axis="spiral",
        aspect_ratio_bucket="extreme",
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

TOTAL_RECOVERY_COUNT = len(FROZEN_MARKER_FAMILY) * VIEWPOINT_COUNT  # 16
FULL_RECOVERY_EXPECTED = TOTAL_RECOVERY_COUNT  # all 16 should fully recover
FACET_VARIATION_MARKER_COUNT = len(FROZEN_MARKER_FAMILY)  # 4
