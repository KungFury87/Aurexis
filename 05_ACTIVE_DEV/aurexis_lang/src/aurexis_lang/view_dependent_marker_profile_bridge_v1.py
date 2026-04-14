"""
Aurexis Core — View-Dependent Marker Profile Bridge V1

Bounded view-dependent marker profile definition. Defines a small frozen
family of markers whose identity remains stable while a bounded secondary
facet changes with viewpoint bucket.

What this proves:
  A frozen family of view-dependent markers can be defined such that each
  marker has a stable primary identity (name, structural hash) and a set
  of view-dependent facets (one per allowed viewpoint bucket). The viewpoint
  buckets are explicit and bounded: FRONT, LEFT, RIGHT, TILT_PLUS.

What this does NOT prove:
  - Full 3D scene understanding
  - General multiview geometry
  - Continuous viewpoint interpolation
  - Full camera capture robustness
  - Full Aurexis Core completion

Design:
  - ViewpointBucket enum: FRONT, LEFT, RIGHT, TILT_PLUS (4 bounded buckets).
  - MarkerFacet: the appearance descriptor for one marker at one viewpoint.
    Contains a facet_hash (deterministic SHA-256 of canonical facet fields).
  - ViewDependentMarker: a marker with stable identity + a dict of
    viewpoint → facet mappings.
  - ViewDependentMarkerProfile: frozen profile defining the full marker family.
  - FROZEN_MARKER_FAMILY: 4 frozen markers, each with 4 viewpoint facets.
  - All operations are deterministic.

This is a narrow bounded view-dependent marker definition, not a general
3D appearance model or full multiview geometry system.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List, FrozenSet
from enum import Enum
import hashlib


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

MARKER_PROFILE_VERSION = "V1.0"
MARKER_PROFILE_FROZEN = True


# ════════════════════════════════════════════════════════════
# VIEWPOINT BUCKETS
# ════════════════════════════════════════════════════════════

class ViewpointBucket(str, Enum):
    """Bounded set of allowed viewpoint positions."""
    FRONT = "FRONT"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TILT_PLUS = "TILT_PLUS"


ALL_VIEWPOINTS = tuple(ViewpointBucket)
VIEWPOINT_COUNT = len(ALL_VIEWPOINTS)  # 4


# ════════════════════════════════════════════════════════════
# MARKER FACET
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MarkerFacet:
    """
    The appearance descriptor for one marker at one viewpoint.

    visible_regions: number of marker regions visible from this viewpoint.
    dominant_axis: primary structural axis observed ('horizontal', 'vertical', 'diagonal').
    aspect_ratio_bucket: quantized aspect ratio ('square', 'wide', 'tall').
    facet_hash: deterministic SHA-256 of the canonical facet fields.
    """
    viewpoint: ViewpointBucket = ViewpointBucket.FRONT
    visible_regions: int = 0
    dominant_axis: str = ""
    aspect_ratio_bucket: str = ""
    facet_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "viewpoint": self.viewpoint.value,
            "visible_regions": self.visible_regions,
            "dominant_axis": self.dominant_axis,
            "aspect_ratio_bucket": self.aspect_ratio_bucket,
            "facet_hash": self.facet_hash,
        }


def compute_facet_hash(
    marker_name: str,
    viewpoint: ViewpointBucket,
    visible_regions: int,
    dominant_axis: str,
    aspect_ratio_bucket: str,
) -> str:
    """Deterministic SHA-256 hash of canonical facet fields."""
    canonical = f"{marker_name}|{viewpoint.value}|{visible_regions}|{dominant_axis}|{aspect_ratio_bucket}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# VIEW-DEPENDENT MARKER
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ViewDependentMarker:
    """
    A marker with stable identity and view-dependent facets.

    name: unique marker identifier.
    identity_hash: deterministic SHA-256 of the stable identity fields.
    structural_class: structural classification ('planar', 'relief', 'prismatic', 'pyramidal').
    region_count: total number of structural regions in the marker.
    facets: tuple of MarkerFacet, one per viewpoint bucket.
    """
    name: str = ""
    identity_hash: str = ""
    structural_class: str = ""
    region_count: int = 0
    facets: Tuple[MarkerFacet, ...] = ()

    @property
    def viewpoint_count(self) -> int:
        return len(self.facets)

    def get_facet(self, viewpoint: ViewpointBucket) -> Optional[MarkerFacet]:
        for f in self.facets:
            if f.viewpoint == viewpoint:
                return f
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "identity_hash": self.identity_hash,
            "structural_class": self.structural_class,
            "region_count": self.region_count,
            "facets": [f.to_dict() for f in self.facets],
            "viewpoint_count": self.viewpoint_count,
        }


def compute_identity_hash(name: str, structural_class: str, region_count: int) -> str:
    """Deterministic SHA-256 hash of stable identity fields."""
    canonical = f"identity|{name}|{structural_class}|{region_count}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# MARKER PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ViewDependentMarkerProfile:
    """
    Frozen profile defining the full view-dependent marker family.
    """
    markers: Tuple[ViewDependentMarker, ...] = ()
    viewpoint_buckets: Tuple[ViewpointBucket, ...] = ALL_VIEWPOINTS
    version: str = MARKER_PROFILE_VERSION

    @property
    def marker_count(self) -> int:
        return len(self.markers)

    def get_marker(self, name: str) -> Optional[ViewDependentMarker]:
        for m in self.markers:
            if m.name == name:
                return m
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "markers": [m.to_dict() for m in self.markers],
            "viewpoint_buckets": [v.value for v in self.viewpoint_buckets],
            "marker_count": self.marker_count,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN MARKER FAMILY CONSTRUCTION
# ════════════════════════════════════════════════════════════

def _build_marker(
    name: str,
    structural_class: str,
    region_count: int,
    facet_specs: Dict[ViewpointBucket, Tuple[int, str, str]],
) -> ViewDependentMarker:
    """
    Build a frozen ViewDependentMarker from specifications.

    facet_specs maps viewpoint → (visible_regions, dominant_axis, aspect_ratio_bucket).
    """
    identity_hash = compute_identity_hash(name, structural_class, region_count)
    facets = []
    for vp in ALL_VIEWPOINTS:
        if vp in facet_specs:
            vis, axis, aspect = facet_specs[vp]
        else:
            vis, axis, aspect = region_count, "horizontal", "square"
        fh = compute_facet_hash(name, vp, vis, axis, aspect)
        facets.append(MarkerFacet(
            viewpoint=vp,
            visible_regions=vis,
            dominant_axis=axis,
            aspect_ratio_bucket=aspect,
            facet_hash=fh,
        ))
    return ViewDependentMarker(
        name=name,
        identity_hash=identity_hash,
        structural_class=structural_class,
        region_count=region_count,
        facets=tuple(facets),
    )


# ── Frozen marker definitions ──
# Each marker has 4 viewpoint facets with different appearance descriptors.

_MARKER_ALPHA = _build_marker(
    name="alpha_planar",
    structural_class="planar",
    region_count=4,
    facet_specs={
        ViewpointBucket.FRONT:     (4, "horizontal", "square"),
        ViewpointBucket.LEFT:      (3, "vertical",   "tall"),
        ViewpointBucket.RIGHT:     (3, "vertical",   "tall"),
        ViewpointBucket.TILT_PLUS: (4, "diagonal",   "wide"),
    },
)

_MARKER_BETA = _build_marker(
    name="beta_relief",
    structural_class="relief",
    region_count=6,
    facet_specs={
        ViewpointBucket.FRONT:     (6, "horizontal", "wide"),
        ViewpointBucket.LEFT:      (4, "diagonal",   "tall"),
        ViewpointBucket.RIGHT:     (4, "diagonal",   "tall"),
        ViewpointBucket.TILT_PLUS: (5, "horizontal", "wide"),
    },
)

_MARKER_GAMMA = _build_marker(
    name="gamma_prismatic",
    structural_class="prismatic",
    region_count=5,
    facet_specs={
        ViewpointBucket.FRONT:     (5, "vertical",   "square"),
        ViewpointBucket.LEFT:      (3, "horizontal", "wide"),
        ViewpointBucket.RIGHT:     (3, "horizontal", "wide"),
        ViewpointBucket.TILT_PLUS: (4, "diagonal",   "tall"),
    },
)

_MARKER_DELTA = _build_marker(
    name="delta_pyramidal",
    structural_class="pyramidal",
    region_count=3,
    facet_specs={
        ViewpointBucket.FRONT:     (3, "vertical",   "tall"),
        ViewpointBucket.LEFT:      (2, "diagonal",   "square"),
        ViewpointBucket.RIGHT:     (2, "diagonal",   "square"),
        ViewpointBucket.TILT_PLUS: (3, "horizontal", "wide"),
    },
)

FROZEN_MARKER_FAMILY = (_MARKER_ALPHA, _MARKER_BETA, _MARKER_GAMMA, _MARKER_DELTA)
FROZEN_MARKER_COUNT = len(FROZEN_MARKER_FAMILY)
FROZEN_MARKER_NAMES = tuple(m.name for m in FROZEN_MARKER_FAMILY)

V1_MARKER_PROFILE = ViewDependentMarkerProfile(
    markers=FROZEN_MARKER_FAMILY,
    viewpoint_buckets=ALL_VIEWPOINTS,
)

# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

EXPECTED_MARKER_COUNT = 4
EXPECTED_VIEWPOINT_COUNT = 4
EXPECTED_FACET_COUNT_PER_MARKER = 4
EXPECTED_TOTAL_FACETS = EXPECTED_MARKER_COUNT * EXPECTED_FACET_COUNT_PER_MARKER  # 16
