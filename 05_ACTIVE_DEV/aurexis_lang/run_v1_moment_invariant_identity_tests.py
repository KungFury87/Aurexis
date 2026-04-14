#!/usr/bin/env python3
"""
Aurexis Core — Moment-Invariant Identity Bridge V1 — Standalone Test Runner

Tests the moment-invariant identity layer:
  - Module version and frozen state
  - MarkerObservation construction
  - InvariantFeatures extraction
  - Identity verification across viewpoints
  - Batch verification of all markers
  - Marker identification lookup
  - Unknown/corrupted observation rejection
  - Serialization

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.view_dependent_marker_profile_bridge_v1 import (
    ViewpointBucket, ALL_VIEWPOINTS, VIEWPOINT_COUNT,
    FROZEN_MARKER_FAMILY, FROZEN_MARKER_NAMES,
    compute_identity_hash,
)
from aurexis_lang.moment_invariant_identity_bridge_v1 import (
    IDENTITY_VERSION, IDENTITY_FROZEN,
    IdentityVerdict,
    MarkerObservation, InvariantFeatures, IdentityVerificationResult,
    extract_invariant_features, generate_observation, generate_all_observations,
    verify_identity_across_viewpoints, verify_all_markers,
    identify_marker,
    make_unknown_observation, make_corrupted_observation,
    STABLE_MARKER_COUNT,
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
check(IDENTITY_VERSION == "V1.0", "Version is V1.0")
check(IDENTITY_FROZEN is True, "Module is frozen")
check(STABLE_MARKER_COUNT == 4, "STABLE_MARKER_COUNT == 4")

# ──────────────────────────────────────────────────────────
section("2. MarkerObservation Construction")
obs = MarkerObservation(
    marker_name="alpha_planar",
    viewpoint=ViewpointBucket.FRONT,
    structural_class="planar",
    region_count=4,
    visible_regions=4,
    dominant_axis="horizontal",
    aspect_ratio_bucket="square",
)
check(obs.marker_name == "alpha_planar", "Observation marker_name correct")
check(obs.viewpoint == ViewpointBucket.FRONT, "Observation viewpoint correct")
check(obs.structural_class == "planar", "Observation structural_class correct")
check(obs.region_count == 4, "Observation region_count correct")
d = obs.to_dict()
check(d["marker_name"] == "alpha_planar", "to_dict marker_name")
check(d["viewpoint"] == "FRONT", "to_dict viewpoint")

# ──────────────────────────────────────────────────────────
section("3. InvariantFeatures Extraction")
features = extract_invariant_features(obs)
check(features.marker_name == "alpha_planar", "Features marker_name")
check(features.structural_class == "planar", "Features structural_class")
check(features.region_count == 4, "Features region_count")
expected_hash = compute_identity_hash("alpha_planar", "planar", 4)
check(features.identity_hash == expected_hash, "Features identity_hash matches expected")
fd = features.to_dict()
check(fd["identity_hash"] == expected_hash, "Features to_dict identity_hash")

# ──────────────────────────────────────────────────────────
section("4. Invariant Features Are Viewpoint-Independent")
for vp in ALL_VIEWPOINTS:
    marker = FROZEN_MARKER_FAMILY[0]
    o = generate_observation(marker, vp)
    check(o is not None, f"Observation generated for {vp.value}")
    if o:
        f = extract_invariant_features(o)
        check(f.identity_hash == expected_hash, f"Identity hash from {vp.value} matches FRONT")

# ──────────────────────────────────────────────────────────
section("5. Generate All Observations")
for marker in FROZEN_MARKER_FAMILY:
    all_obs = generate_all_observations(marker)
    check(len(all_obs) == VIEWPOINT_COUNT, f"{marker.name}: {VIEWPOINT_COUNT} observations generated")
    viewpoints_seen = set(o.viewpoint for o in all_obs)
    check(len(viewpoints_seen) == VIEWPOINT_COUNT, f"{marker.name}: all viewpoints covered")

# ──────────────────────────────────────────────────────────
section("6. Verify Identity Across Viewpoints — Individual")
for marker in FROZEN_MARKER_FAMILY:
    result = verify_identity_across_viewpoints(marker)
    check(result.verdict == IdentityVerdict.IDENTITY_STABLE, f"{marker.name}: IDENTITY_STABLE")
    check(result.all_identical is True, f"{marker.name}: all_identical")
    check(result.viewpoints_checked == VIEWPOINT_COUNT, f"{marker.name}: {VIEWPOINT_COUNT} checked")
    check(result.expected_hash == marker.identity_hash, f"{marker.name}: expected_hash matches")

# ──────────────────────────────────────────────────────────
section("7. Verify All Markers (Batch)")
results = verify_all_markers()
check(len(results) == STABLE_MARKER_COUNT, f"Batch returns {STABLE_MARKER_COUNT} results")
all_stable = all(r.verdict == IdentityVerdict.IDENTITY_STABLE for r in results)
check(all_stable, "All markers identity-stable")

# ──────────────────────────────────────────────────────────
section("8. Marker Identification — Positive Cases")
for marker in FROZEN_MARKER_FAMILY:
    for vp in ALL_VIEWPOINTS:
        o = generate_observation(marker, vp)
        if o:
            name = identify_marker(o)
            check(name == marker.name, f"identify_marker({marker.name}/{vp.value}) = {name}")

# ──────────────────────────────────────────────────────────
section("9. Marker Identification — Unknown Marker")
unk = make_unknown_observation()
check(unk.marker_name == "unknown_marker", "Unknown observation has correct name")
check(unk.structural_class == "exotic", "Unknown observation has exotic class")
result = identify_marker(unk)
check(result is None, "Unknown marker not identified")

# ──────────────────────────────────────────────────────────
section("10. Marker Identification — Corrupted Observation")
cor = make_corrupted_observation()
check(cor.marker_name == "alpha_planar", "Corrupted has alpha_planar name")
check(cor.structural_class == "CORRUPTED", "Corrupted has wrong class")
check(cor.region_count == 999, "Corrupted has wrong region_count")
result = identify_marker(cor)
check(result is None, "Corrupted observation not identified (hash mismatch)")

# ──────────────────────────────────────────────────────────
section("11. IdentityVerificationResult Serialization")
for marker in FROZEN_MARKER_FAMILY:
    r = verify_identity_across_viewpoints(marker)
    d = r.to_dict()
    check(d["marker_name"] == marker.name, f"{marker.name}: to_dict marker_name")
    check(d["verdict"] == "IDENTITY_STABLE", f"{marker.name}: to_dict verdict")
    check(d["all_identical"] is True, f"{marker.name}: to_dict all_identical")
    check(d["version"] == IDENTITY_VERSION, f"{marker.name}: to_dict version")

# ──────────────────────────────────────────────────────────
section("12. Identity Hash Collision Resistance")
hashes = set()
for marker in FROZEN_MARKER_FAMILY:
    hashes.add(marker.identity_hash)
check(len(hashes) == len(FROZEN_MARKER_FAMILY), "All identity hashes unique across markers")

# Also check that different structural classes produce different hashes
h1 = compute_identity_hash("test", "planar", 5)
h2 = compute_identity_hash("test", "relief", 5)
h3 = compute_identity_hash("test", "planar", 6)
check(h1 != h2, "Different structural classes → different hashes")
check(h1 != h3, "Different region counts → different hashes")

# ──────────────────────────────────────────────────────────
section("13. Observation Immutability")
try:
    obs.marker_name = "hacked"  # type: ignore
    check(False, "MarkerObservation should be immutable")
except (AttributeError, TypeError):
    check(True, "MarkerObservation is immutable")

try:
    features.identity_hash = "hacked"  # type: ignore
    check(False, "InvariantFeatures should be immutable")
except (AttributeError, TypeError):
    check(True, "InvariantFeatures is immutable")


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
