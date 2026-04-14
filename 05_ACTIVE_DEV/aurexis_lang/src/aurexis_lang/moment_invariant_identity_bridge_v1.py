"""
Aurexis Core — Moment-Invariant Identity Bridge V1

Bounded executable identity layer using simple invariant-style features
for the frozen marker family. Proves that marker identity survives across
the allowed viewpoint buckets.

What this proves:
  Given a view-dependent marker observed from any allowed viewpoint bucket,
  the system can recover the marker's stable identity using structural
  features that do not change with viewpoint (name, structural_class,
  region_count). The identity hash is viewpoint-invariant by construction.

What this does NOT prove:
  - Full 3D moment-invariant theory generality
  - Continuous viewpoint invariance
  - Noise-robust real-camera identity recovery
  - Full Aurexis Core completion

Design:
  - extract_invariant_features(): extracts the stable structural features
    from a marker observation (simulated capture at a viewpoint).
  - compute_observation_identity(): computes the identity hash from
    invariant features only (excludes view-dependent facet data).
  - verify_identity_across_viewpoints(): proves that a marker's identity
    hash is identical across all viewpoint buckets.
  - Fabricated misidentification cases test the rejection path.
  - All operations are deterministic.

This is a narrow bounded identity-invariance proof, not a general
3D moment-invariant computation or multiview feature matcher.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import hashlib

from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    MARKER_PROFILE_VERSION, MARKER_PROFILE_FROZEN,
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    ViewDependentMarker, MarkerFacet, ViewDependentMarkerProfile,
    V1_MARKER_PROFILE, FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    compute_identity_hash, compute_facet_hash,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

IDENTITY_VERSION = "V1.0"
IDENTITY_FROZEN = True


# ════════════════════════════════════════════════════════════
# IDENTITY VERDICTS
# ════════════════════════════════════════════════════════════

class IdentityVerdict(str, Enum):
    """Outcome of identity verification."""
    IDENTITY_STABLE = "IDENTITY_STABLE"
    IDENTITY_UNSTABLE = "IDENTITY_UNSTABLE"
    UNKNOWN_MARKER = "UNKNOWN_MARKER"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# MARKER OBSERVATION (SIMULATED CAPTURE)
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MarkerObservation:
    """
    A simulated observation of a marker from a specific viewpoint.

    Contains both stable identity fields and view-dependent facet data.
    """
    marker_name: str = ""
    viewpoint: ViewpointBucket = ViewpointBucket.FRONT
    # Stable identity fields (invariant across viewpoints)
    structural_class: str = ""
    region_count: int = 0
    # View-dependent facet fields
    visible_regions: int = 0
    dominant_axis: str = ""
    aspect_ratio_bucket: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "viewpoint": self.viewpoint.value,
            "structural_class": self.structural_class,
            "region_count": self.region_count,
            "visible_regions": self.visible_regions,
            "dominant_axis": self.dominant_axis,
            "aspect_ratio_bucket": self.aspect_ratio_bucket,
        }


# ════════════════════════════════════════════════════════════
# INVARIANT FEATURE EXTRACTION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InvariantFeatures:
    """
    The viewpoint-invariant structural features of a marker observation.
    These do NOT change with viewpoint.
    """
    marker_name: str = ""
    structural_class: str = ""
    region_count: int = 0
    identity_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "structural_class": self.structural_class,
            "region_count": self.region_count,
            "identity_hash": self.identity_hash,
        }


def extract_invariant_features(obs: MarkerObservation) -> InvariantFeatures:
    """Extract viewpoint-invariant features from a marker observation."""
    identity_hash = compute_identity_hash(
        obs.marker_name, obs.structural_class, obs.region_count,
    )
    return InvariantFeatures(
        marker_name=obs.marker_name,
        structural_class=obs.structural_class,
        region_count=obs.region_count,
        identity_hash=identity_hash,
    )


# ════════════════════════════════════════════════════════════
# IDENTITY VERIFICATION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class IdentityVerificationResult:
    """Result of verifying identity stability across viewpoints."""
    marker_name: str = ""
    verdict: IdentityVerdict = IdentityVerdict.ERROR
    viewpoints_checked: int = 0
    identity_hashes: Tuple[str, ...] = ()
    all_identical: bool = False
    expected_hash: str = ""
    detail: str = ""
    version: str = IDENTITY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marker_name": self.marker_name,
            "verdict": self.verdict.value,
            "viewpoints_checked": self.viewpoints_checked,
            "all_identical": self.all_identical,
            "expected_hash": self.expected_hash[:16] + "..." if self.expected_hash else "",
            "detail": self.detail,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# OBSERVATION GENERATION (SIMULATED)
# ════════════════════════════════════════════════════════════

def generate_observation(
    marker: ViewDependentMarker,
    viewpoint: ViewpointBucket,
) -> Optional[MarkerObservation]:
    """Generate a simulated observation of a marker from a viewpoint."""
    facet = marker.get_facet(viewpoint)
    if facet is None:
        return None
    return MarkerObservation(
        marker_name=marker.name,
        viewpoint=viewpoint,
        structural_class=marker.structural_class,
        region_count=marker.region_count,
        visible_regions=facet.visible_regions,
        dominant_axis=facet.dominant_axis,
        aspect_ratio_bucket=facet.aspect_ratio_bucket,
    )


def generate_all_observations(
    marker: ViewDependentMarker,
) -> Tuple[MarkerObservation, ...]:
    """Generate observations of a marker from all viewpoints."""
    obs = []
    for vp in ALL_VIEWPOINTS:
        o = generate_observation(marker, vp)
        if o is not None:
            obs.append(o)
    return tuple(obs)


# ════════════════════════════════════════════════════════════
# IDENTITY VERIFICATION
# ════════════════════════════════════════════════════════════

def verify_identity_across_viewpoints(
    marker: ViewDependentMarker,
) -> IdentityVerificationResult:
    """
    Verify that a marker's identity hash is identical across all viewpoints.

    Generates observations from each viewpoint, extracts invariant features,
    and checks that all identity hashes match.
    """
    observations = generate_all_observations(marker)
    if not observations:
        return IdentityVerificationResult(
            marker_name=marker.name,
            verdict=IdentityVerdict.ERROR,
            detail="No observations generated",
        )

    hashes = []
    for obs in observations:
        features = extract_invariant_features(obs)
        hashes.append(features.identity_hash)

    all_identical = len(set(hashes)) == 1
    verdict = IdentityVerdict.IDENTITY_STABLE if all_identical else IdentityVerdict.IDENTITY_UNSTABLE

    return IdentityVerificationResult(
        marker_name=marker.name,
        verdict=verdict,
        viewpoints_checked=len(observations),
        identity_hashes=tuple(hashes),
        all_identical=all_identical,
        expected_hash=marker.identity_hash,
        detail=f"{'All' if all_identical else 'Not all'} {len(hashes)} hashes identical",
    )


def verify_all_markers() -> Tuple[IdentityVerificationResult, ...]:
    """Verify identity stability for all markers in the frozen family."""
    return tuple(verify_identity_across_viewpoints(m) for m in FROZEN_MARKER_FAMILY)


# ════════════════════════════════════════════════════════════
# IDENTITY LOOKUP
# ════════════════════════════════════════════════════════════

def identify_marker(obs: MarkerObservation) -> Optional[str]:
    """
    Identify which frozen marker produced an observation.
    Returns the marker name or None if not found.
    """
    features = extract_invariant_features(obs)
    for marker in FROZEN_MARKER_FAMILY:
        if marker.identity_hash == features.identity_hash:
            return marker.name
    return None


# ════════════════════════════════════════════════════════════
# FABRICATED MISIDENTIFICATION CASES
# ════════════════════════════════════════════════════════════

def make_unknown_observation() -> MarkerObservation:
    """Create an observation that doesn't match any frozen marker."""
    return MarkerObservation(
        marker_name="unknown_marker",
        viewpoint=ViewpointBucket.FRONT,
        structural_class="exotic",
        region_count=99,
        visible_regions=99,
        dominant_axis="spiral",
        aspect_ratio_bucket="extreme",
    )


def make_corrupted_observation() -> MarkerObservation:
    """Create an observation with a valid name but wrong structural data."""
    return MarkerObservation(
        marker_name="alpha_planar",
        viewpoint=ViewpointBucket.FRONT,
        structural_class="CORRUPTED",
        region_count=999,
        visible_regions=4,
        dominant_axis="horizontal",
        aspect_ratio_bucket="square",
    )


# Predefined counts
STABLE_MARKER_COUNT = 4  # all 4 markers should be identity-stable
