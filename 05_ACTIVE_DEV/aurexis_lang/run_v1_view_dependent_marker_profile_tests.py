#!/usr/bin/env python3
"""
Aurexis Core — View-Dependent Marker Profile Bridge V1 — Standalone Test Runner

Tests the frozen view-dependent marker profile definition:
  - ViewpointBucket enum completeness
  - MarkerFacet construction and hashing
  - ViewDependentMarker frozen construction
  - Frozen marker family correctness
  - Profile lookup and counts
  - Facet hash determinism
  - Identity hash determinism

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    MARKER_PROFILE_VERSION, MARKER_PROFILE_FROZEN,
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    MarkerFacet, ViewDependentMarker, ViewDependentMarkerProfile,
    V1_MARKER_PROFILE, FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    FROZEN_MARKER_COUNT,
    compute_identity_hash, compute_facet_hash,
    EXPECTED_MARKER_COUNT, EXPECTED_VIEWPOINT_COUNT,
    EXPECTED_FACET_COUNT_PER_MARKER, EXPECTED_TOTAL_FACETS,
)


PASS_COUNT = 0
FAIL_COUNT = 0
SECTION = ""


def section(name: str):
    global SECTION
    SECTION = name
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
check(MARKER_PROFILE_VERSION == "V1.0", "Version is V1.0")
check(MARKER_PROFILE_FROZEN is True, "Module is frozen")

# ──────────────────────────────────────────────────────────
section("2. ViewpointBucket Enum")
check(len(ALL_VIEWPOINTS) == 4, "4 viewpoint buckets")
check(VIEWPOINT_COUNT == 4, "VIEWPOINT_COUNT == 4")
check(ViewpointBucket.FRONT.value == "FRONT", "FRONT bucket")
check(ViewpointBucket.LEFT.value == "LEFT", "LEFT bucket")
check(ViewpointBucket.RIGHT.value == "RIGHT", "RIGHT bucket")
check(ViewpointBucket.TILT_PLUS.value == "TILT_PLUS", "TILT_PLUS bucket")

# ──────────────────────────────────────────────────────────
section("3. Expected Counts")
check(EXPECTED_MARKER_COUNT == 4, "Expected 4 markers")
check(EXPECTED_VIEWPOINT_COUNT == 4, "Expected 4 viewpoints")
check(EXPECTED_FACET_COUNT_PER_MARKER == 4, "Expected 4 facets per marker")
check(EXPECTED_TOTAL_FACETS == 16, "Expected 16 total facets")

# ──────────────────────────────────────────────────────────
section("4. Frozen Marker Family")
check(FROZEN_MARKER_COUNT == 4, f"FROZEN_MARKER_COUNT == 4 (got {FROZEN_MARKER_COUNT})")
check(len(FROZEN_MARKER_FAMILY) == 4, f"4 markers in family")
check(len(FROZEN_MARKER_NAMES) == 4, f"4 marker names")
expected_names = ("alpha_planar", "beta_relief", "gamma_prismatic", "delta_pyramidal")
check(FROZEN_MARKER_NAMES == expected_names, f"Names match expected order")

# ──────────────────────────────────────────────────────────
section("5. Alpha Planar Marker")
alpha = FROZEN_MARKER_FAMILY[0]
check(alpha.name == "alpha_planar", "Name correct")
check(alpha.structural_class == "planar", "Structural class correct")
check(alpha.region_count == 4, "Region count correct")
check(alpha.viewpoint_count == 4, "4 viewpoint facets")
check(alpha.identity_hash == compute_identity_hash("alpha_planar", "planar", 4), "Identity hash matches recomputed")

# ──────────────────────────────────────────────────────────
section("6. Beta Relief Marker")
beta = FROZEN_MARKER_FAMILY[1]
check(beta.name == "beta_relief", "Name correct")
check(beta.structural_class == "relief", "Structural class correct")
check(beta.region_count == 6, "Region count correct")
check(beta.viewpoint_count == 4, "4 viewpoint facets")

# ──────────────────────────────────────────────────────────
section("7. Gamma Prismatic Marker")
gamma = FROZEN_MARKER_FAMILY[2]
check(gamma.name == "gamma_prismatic", "Name correct")
check(gamma.structural_class == "prismatic", "Structural class correct")
check(gamma.region_count == 5, "Region count correct")
check(gamma.viewpoint_count == 4, "4 viewpoint facets")

# ──────────────────────────────────────────────────────────
section("8. Delta Pyramidal Marker")
delta = FROZEN_MARKER_FAMILY[3]
check(delta.name == "delta_pyramidal", "Name correct")
check(delta.structural_class == "pyramidal", "Structural class correct")
check(delta.region_count == 3, "Region count correct")
check(delta.viewpoint_count == 4, "4 viewpoint facets")

# ──────────────────────────────────────────────────────────
section("9. Facet Access and Hashing")
for m in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        f = m.get_facet(vp)
        check(f is not None, f"{m.name} has facet for {vp.value}")
        if f:
            expected_fh = compute_facet_hash(m.name, vp, f.visible_regions, f.dominant_axis, f.aspect_ratio_bucket)
            check(f.facet_hash == expected_fh, f"{m.name}/{vp.value} facet hash matches recomputed")

# ──────────────────────────────────────────────────────────
section("10. Facet Uniqueness Per Marker")
for m in FROZEN_MARKER_FAMILY:
    fh_set = set(f.facet_hash for f in m.facets)
    check(len(fh_set) == 4, f"{m.name} has 4 unique facet hashes")

# ──────────────────────────────────────────────────────────
section("11. Identity Hash Uniqueness Across Markers")
id_hashes = set(m.identity_hash for m in FROZEN_MARKER_FAMILY)
check(len(id_hashes) == 4, "4 unique identity hashes across markers")

# ──────────────────────────────────────────────────────────
section("12. Profile Object")
check(V1_MARKER_PROFILE.marker_count == 4, "Profile has 4 markers")
check(V1_MARKER_PROFILE.version == "V1.0", "Profile version V1.0")
check(V1_MARKER_PROFILE.viewpoint_buckets == ALL_VIEWPOINTS, "Profile viewpoints match ALL_VIEWPOINTS")
for name in FROZEN_MARKER_NAMES:
    found = V1_MARKER_PROFILE.get_marker(name)
    check(found is not None and found.name == name, f"Profile lookup finds {name}")
check(V1_MARKER_PROFILE.get_marker("nonexistent") is None, "Profile returns None for unknown")

# ──────────────────────────────────────────────────────────
section("13. Serialization (to_dict)")
for m in FROZEN_MARKER_FAMILY:
    d = m.to_dict()
    check(d["name"] == m.name, f"{m.name}.to_dict() has correct name")
    check(len(d["facets"]) == 4, f"{m.name}.to_dict() has 4 facets")
pd = V1_MARKER_PROFILE.to_dict()
check(pd["marker_count"] == 4, "Profile dict has marker_count 4")
check(len(pd["markers"]) == 4, "Profile dict has 4 markers")

# ──────────────────────────────────────────────────────────
section("14. Hash Determinism")
h1 = compute_identity_hash("test", "planar", 5)
h2 = compute_identity_hash("test", "planar", 5)
check(h1 == h2, "Identity hash is deterministic")
h3 = compute_identity_hash("test", "planar", 6)
check(h1 != h3, "Different inputs produce different identity hashes")
fh1 = compute_facet_hash("m", ViewpointBucket.FRONT, 3, "h", "s")
fh2 = compute_facet_hash("m", ViewpointBucket.FRONT, 3, "h", "s")
check(fh1 == fh2, "Facet hash is deterministic")
fh3 = compute_facet_hash("m", ViewpointBucket.LEFT, 3, "h", "s")
check(fh1 != fh3, "Different viewpoints produce different facet hashes")

# ──────────────────────────────────────────────────────────
section("15. Total Facet Count")
total = sum(m.viewpoint_count for m in FROZEN_MARKER_FAMILY)
check(total == EXPECTED_TOTAL_FACETS, f"Total facets == {EXPECTED_TOTAL_FACETS} (got {total})")

# ──────────────────────────────────────────────────────────
section("16. Frozen Dataclass Immutability")
try:
    alpha.name = "hacked"  # type: ignore
    check(False, "Marker should be immutable")
except (AttributeError, TypeError, FrozenInstanceError if 'FrozenInstanceError' in dir() else AttributeError):
    check(True, "Marker is immutable (frozen dataclass)")

try:
    f0 = alpha.facets[0]
    f0.visible_regions = 999  # type: ignore
    check(False, "Facet should be immutable")
except (AttributeError, TypeError, FrozenInstanceError if 'FrozenInstanceError' in dir() else AttributeError):
    check(True, "Facet is immutable (frozen dataclass)")


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
