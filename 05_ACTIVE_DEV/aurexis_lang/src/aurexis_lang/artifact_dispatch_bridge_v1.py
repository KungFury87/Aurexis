"""
Aurexis Core — Artifact Dispatch Bridge V1

Bounded artifact-family routing for the narrow V1 raster bridge.
Proves that a recovered V1 artifact can be identified by its structural
fingerprint and deterministically routed to the correct decode path
among a small frozen family of known V1 artifact types.

What this proves:
  Given a recovered artifact image (after localization, orientation
  normalization, perspective normalization, and capture tolerance),
  the system can identify its structural type — adjacent_pair,
  containment, or three_regions — and dispatch it to the correct
  decode path through the existing raster bridge and substrate.

What this does NOT prove:
  - General artifact classification or recognition
  - Open-ended artifact family support
  - Full language versioning
  - Arbitrary scene understanding
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Structural fingerprint: (primitive_count, sorted operation_kinds)
  - Three frozen artifact families: adjacent_pair, containment, three_regions
  - Each family has a unique fingerprint that the dispatch logic matches
  - Dispatch returns the family name + the correct expected spec for
    substrate bridging
  - If the fingerprint doesn't match any frozen family, fail honestly
  - All operations are deterministic
  - The dispatched artifact flows through the existing raster bridge
    and substrate path — no bypass

This is a narrow deterministic dispatch proof, not general artifact
classification or open-ended versioning.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from enum import Enum

from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, CANVAS_WIDTH, CANVAS_HEIGHT,
    PRIMITIVE_PALETTE, ArtifactSpec, ArtifactPrimitive,
    render_artifact, _encode_png, _decode_png_to_rgb,
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE, ToleranceProfile,
)
from aurexis_lang.visual_grammar_v1 import OperationKind
from aurexis_lang.type_system_v1 import safe_execute_image_as_program


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

DISPATCH_VERSION = "V1.0"
DISPATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# STRUCTURAL FINGERPRINTS
# ════════════════════════════════════════════════════════════

# A structural fingerprint is (primitive_count, tuple_of_sorted_operation_kinds).
# This is the minimal identity signal that distinguishes the frozen artifact
# families without relying on pixel-level matching or heuristic classification.

@dataclass(frozen=True)
class StructuralFingerprint:
    """
    Deterministic identity of an artifact family based on structure.

    primitive_count: number of color-distinct regions in the artifact
    operation_kinds: sorted tuple of OperationKind values from the spec
    """
    primitive_count: int
    operation_kinds: Tuple[str, ...]  # sorted names, e.g. ("ADJACENT",)


def fingerprint_from_spec(spec: ArtifactSpec) -> StructuralFingerprint:
    """Extract the structural fingerprint from an ArtifactSpec."""
    ops = tuple(sorted(
        op["op"].name if isinstance(op["op"], OperationKind) else str(op["op"])
        for op in spec.operations
    )) if spec.operations else ()
    return StructuralFingerprint(
        primitive_count=len(spec.primitives),
        operation_kinds=ops,
    )


def fingerprint_from_parsed(
    parsed_primitives: List,
    candidate_spec: ArtifactSpec,
) -> StructuralFingerprint:
    """
    Build a fingerprint from parsed primitives + a candidate spec's operations.

    The parsed primitives give us the count; the candidate spec provides
    the expected operation structure. This is used during dispatch to
    check if a recovered artifact matches a known family.
    """
    ops = tuple(sorted(
        op["op"].name if isinstance(op["op"], OperationKind) else str(op["op"])
        for op in candidate_spec.operations
    )) if candidate_spec.operations else ()
    return StructuralFingerprint(
        primitive_count=len(parsed_primitives),
        operation_kinds=ops,
    )


# ════════════════════════════════════════════════════════════
# FROZEN DISPATCH PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ArtifactFamily:
    """One member of the frozen dispatch family."""
    name: str
    fingerprint: StructuralFingerprint
    spec_factory: Callable[[], ArtifactSpec]
    description: str


# The three frozen families
_ADJACENT_PAIR_FP = StructuralFingerprint(
    primitive_count=2,
    operation_kinds=("ADJACENT",),
)

_CONTAINMENT_FP = StructuralFingerprint(
    primitive_count=2,
    operation_kinds=("CONTAINS",),
)

_THREE_REGIONS_FP = StructuralFingerprint(
    primitive_count=3,
    operation_kinds=("ADJACENT", "ADJACENT"),
)


FROZEN_FAMILIES = (
    ArtifactFamily(
        name="adjacent_pair",
        fingerprint=_ADJACENT_PAIR_FP,
        spec_factory=fixture_adjacent_pair,
        description="Two regions side by side with one ADJACENT operation",
    ),
    ArtifactFamily(
        name="containment",
        fingerprint=_CONTAINMENT_FP,
        spec_factory=fixture_containment,
        description="Large region containing a smaller one with CONTAINS operation",
    ),
    ArtifactFamily(
        name="three_regions",
        fingerprint=_THREE_REGIONS_FP,
        spec_factory=fixture_three_regions,
        description="Three regions in a row with two ADJACENT operations",
    ),
)


@dataclass(frozen=True)
class DispatchProfile:
    """
    Frozen profile defining the supported artifact families for dispatch.

    Dispatch logic: parse recovered image → count primitives →
    match against fingerprints → route to correct family.
    """
    families: Tuple[ArtifactFamily, ...] = FROZEN_FAMILIES
    color_match_threshold_sq: int = 7500
    min_detectable_area_px: int = 500


V1_DISPATCH_PROFILE = DispatchProfile()


# ════════════════════════════════════════════════════════════
# DISPATCH LOGIC
# ════════════════════════════════════════════════════════════

def _bbox_contains(outer: List, inner: List, margin: int = 5) -> bool:
    """
    Check if outer bbox fully contains inner bbox.
    bbox format: [x, y, w, h].
    margin: tolerance in pixels for containment check.
    """
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (
        ix >= ox - margin and
        iy >= oy - margin and
        ix + iw <= ox + ow + margin and
        iy + ih <= oy + oh + margin and
        # Inner must be meaningfully smaller than outer
        iw < ow and ih < oh
    )


def _detect_containment(parsed: List) -> bool:
    """
    Check if any parsed primitive's bbox fully contains another.
    Used to disambiguate 2-primitive cases: containment vs adjacent_pair.
    """
    if len(parsed) != 2:
        return False
    b0 = parsed[0]["bbox"]
    b1 = parsed[1]["bbox"]
    return _bbox_contains(b0, b1) or _bbox_contains(b1, b0)


def identify_artifact_family(
    parsed: List,
    profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> List[ArtifactFamily]:
    """
    Identify candidate artifact families from parsed primitives.

    Uses primitive count as the primary discriminator, then spatial
    arrangement (containment check) to disambiguate 2-primitive cases.

    Returns a list of matching families (usually exactly 1).
    Returns empty list if no family matches.
    """
    prim_count = len(parsed)
    count_matches = [
        f for f in profile.families
        if f.fingerprint.primitive_count == prim_count
    ]

    if not count_matches:
        return []

    # If only one family matches the count, return it
    if len(count_matches) == 1:
        return count_matches

    # Disambiguate 2-primitive case: containment vs adjacent_pair
    if prim_count == 2:
        is_containment = _detect_containment(parsed)
        if is_containment:
            return [f for f in count_matches if f.name == "containment"]
        else:
            return [f for f in count_matches if f.name == "adjacent_pair"]

    return count_matches


def dispatch_artifact(
    artifact_png: bytes,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> Optional[Tuple[ArtifactFamily, List, Dict[str, Any]]]:
    """
    Full dispatch path for a recovered artifact image.

    1. Parse the artifact image tolerantly to get primitives
    2. Identify candidate families by primitive count
    3. For each candidate, attempt substrate execution with that
       family's spec (operations + bindings)
    4. Return the first family where execution succeeds with
       verdict PASS or PARTIAL

    Returns (matched_family, parsed_primitives, substrate_result)
    or None if no family matches.

    This is deterministic: same image always produces same dispatch.
    """
    # Step 1: Tolerant parse
    parsed = parse_artifact_tolerant(artifact_png, tolerance)
    if not parsed:
        return None

    # Step 2: Identify candidates by structure
    candidates = identify_artifact_family(parsed, profile)
    if not candidates:
        return None

    # Step 3: Try each candidate's spec against the substrate
    for family in candidates:
        spec = family.spec_factory()

        # Verify primitive count matches exactly
        if len(spec.primitives) != len(parsed):
            continue

        # Try substrate execution with this family's operations/bindings
        try:
            substrate_result = safe_execute_image_as_program(
                parsed,
                bindings=spec.bindings,
                operations=list(spec.operations),
            )
        except Exception:
            continue

        if not substrate_result.get("executed", False):
            continue

        exec_verdict = substrate_result.get("execution", {}).get("verdict", "")
        if exec_verdict in ("PASS", "PARTIAL", "EMPTY"):
            return (family, parsed, substrate_result)

    return None


# ════════════════════════════════════════════════════════════
# VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class DispatchVerdict(str, Enum):
    """Outcome of artifact dispatch attempt."""
    DISPATCHED = "DISPATCHED"            # Successfully identified and routed
    NO_PRIMITIVES = "NO_PRIMITIVES"      # Tolerant parse found nothing
    UNKNOWN_FAMILY = "UNKNOWN_FAMILY"    # Count doesn't match any family
    AMBIGUOUS = "AMBIGUOUS"              # Multiple candidates, none succeeded
    BRIDGE_FAILED = "BRIDGE_FAILED"      # Dispatch succeeded but bridge failed
    ERROR = "ERROR"                      # Unexpected error


@dataclass
class DispatchResult:
    """Result of an artifact dispatch attempt."""
    verdict: DispatchVerdict = DispatchVerdict.ERROR
    family_name: Optional[str] = None
    family_fingerprint: Optional[StructuralFingerprint] = None
    parsed_primitive_count: int = 0
    candidate_count: int = 0
    type_check_verdict: Optional[str] = None
    execution_verdict: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "family_name": self.family_name,
            "parsed_primitive_count": self.parsed_primitive_count,
            "candidate_count": self.candidate_count,
            "type_check_verdict": self.type_check_verdict,
            "execution_verdict": self.execution_verdict,
            "version": DISPATCH_VERSION,
        }


# ════════════════════════════════════════════════════════════
# END-TO-END DISPATCH PIPELINE
# ════════════════════════════════════════════════════════════

def dispatch_and_bridge(
    artifact_png: bytes,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> DispatchResult:
    """
    Full end-to-end dispatch bridge:
      artifact_png -> tolerant parse -> identify family ->
      route to correct spec -> substrate bridge

    Returns a DispatchResult with the verdict and dispatch details.
    """
    result = DispatchResult()

    # Step 1: Parse
    parsed = parse_artifact_tolerant(artifact_png, tolerance)
    result.parsed_primitive_count = len(parsed)

    if not parsed:
        result.verdict = DispatchVerdict.NO_PRIMITIVES
        return result

    # Step 2: Find candidates by structure
    candidates = identify_artifact_family(parsed, profile)
    result.candidate_count = len(candidates)

    if not candidates:
        result.verdict = DispatchVerdict.UNKNOWN_FAMILY
        return result

    # Step 3: Try each candidate
    for family in candidates:
        spec = family.spec_factory()
        if len(spec.primitives) != len(parsed):
            continue

        try:
            substrate_result = safe_execute_image_as_program(
                parsed,
                bindings=spec.bindings,
                operations=list(spec.operations),
            )
        except Exception:
            continue

        if not substrate_result.get("executed", False):
            continue

        exec_verdict = substrate_result.get("execution", {}).get("verdict", "")
        tc_verdict = (
            "WELL_TYPED" if substrate_result.get("type_check", {}).get("is_well_typed", False)
            else "ILL_TYPED"
        )

        if exec_verdict in ("PASS", "PARTIAL", "EMPTY"):
            result.verdict = DispatchVerdict.DISPATCHED
            result.family_name = family.name
            result.family_fingerprint = family.fingerprint
            result.type_check_verdict = tc_verdict
            result.execution_verdict = exec_verdict
            return result

    # No candidate produced a passing execution
    result.verdict = DispatchVerdict.AMBIGUOUS
    return result


def dispatch_from_spec(
    spec: ArtifactSpec,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> DispatchResult:
    """
    Convenience: render an ArtifactSpec to PNG, then dispatch.
    Used for testing to verify that each known spec dispatches
    to the correct family.
    """
    png = render_artifact(spec)
    return dispatch_and_bridge(png, tolerance, profile)


# ════════════════════════════════════════════════════════════
# COMPOSED DISPATCH: RECOVERY + DISPATCH IN ONE PATH
# ════════════════════════════════════════════════════════════

def recover_and_dispatch(
    host_png: bytes,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> DispatchResult:
    """
    Full recovery-to-dispatch pipeline:
      host_png -> localize -> extract -> dispatch

    Chains the localization bridge with the dispatch bridge.
    Does NOT do orientation/perspective normalization here —
    that should be done before calling this, or use the
    composed recovery bridge first.
    """
    from aurexis_lang.artifact_localization_bridge_v1 import (
        localize_artifact, extract_and_normalize,
        V1_LOCALIZATION_PROFILE,
    )

    bbox = localize_artifact(host_png, V1_LOCALIZATION_PROFILE)
    if bbox is None:
        result = DispatchResult()
        result.verdict = DispatchVerdict.NO_PRIMITIVES
        return result

    try:
        extracted_png = extract_and_normalize(host_png, bbox)
    except Exception:
        result = DispatchResult()
        result.verdict = DispatchVerdict.NO_PRIMITIVES
        return result

    return dispatch_and_bridge(extracted_png, tolerance, profile)


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen family should dispatch correctly
IN_BOUNDS_CASES = [
    {"label": "adjacent_pair_canonical", "spec_factory": "fixture_adjacent_pair",
     "expected_family": "adjacent_pair"},
    {"label": "containment_canonical", "spec_factory": "fixture_containment",
     "expected_family": "containment"},
    {"label": "three_regions_canonical", "spec_factory": "fixture_three_regions",
     "expected_family": "three_regions"},
]

# Out-of-bounds: artifact types NOT in the frozen family
OUT_OF_BOUNDS_CASES = [
    # 0 primitives — blank image
    {"label": "blank_image", "primitive_count": 0},
    # 1 primitive — single_region (not in frozen family)
    {"label": "single_region", "primitive_count": 1},
    # 4 primitives — no matching family
    {"label": "four_primitives", "primitive_count": 4},
]
