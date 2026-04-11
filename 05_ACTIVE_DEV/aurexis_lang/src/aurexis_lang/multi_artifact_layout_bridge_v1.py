"""
Aurexis Core — Multi-Artifact Layout Bridge V1

Bounded multi-artifact recovery and dispatch proof for the narrow V1
raster bridge.  Proves that two or three canonical V1 artifacts embedded
in one larger host image can be independently localized, recovered,
dispatched, and decoded in one deterministic pass.

What this proves:
  Given a host image containing 2–3 spatially separated canonical V1
  artifacts (from the frozen dispatch family), each artifact can be
  independently localized via palette-pixel clustering, extracted,
  normalized back to canonical size, and dispatched to its correct
  family through the existing bridge pipeline.

What this does NOT prove:
  - Overlapping or touching artifacts
  - Arbitrary number of artifacts (only 2–3 frozen layouts)
  - General scene understanding or object detection
  - Full camera capture robustness
  - Print/scan round-trip with multiple artifacts
  - Arbitrary spatial arrangements
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Multi-artifact host: 800×800 canvas with 2–3 artifacts at bounded
    offsets and bounded scales (0.30–0.60)
  - Candidate extraction: palette-pixel scan → spatial clustering with
    gap threshold → separate bounding boxes for each artifact
  - Independent recovery: each candidate bbox → extract → normalize →
    dispatch (reuses existing single-artifact pipeline entirely)
  - Deterministic ordering: candidates sorted top-to-bottom then
    left-to-right by centroid position
  - Five frozen layout profiles: two_horizontal, two_vertical,
    three_in_row, two_horizontal_mixed, two_vertical_reversed
  - All operations are deterministic

This is a narrow deterministic multi-artifact layout proof, not general
multi-object detection or scene understanding.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.raster_law_bridge_v1 import (
    CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_COLOR,
    PRIMITIVE_PALETTE, ArtifactSpec,
    _render_to_raw_rgb, _encode_png, _decode_png_to_rgb,
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE, ToleranceProfile,
    degrade_scale,
)
from aurexis_lang.artifact_localization_bridge_v1 import (
    _is_palette_pixel, extract_and_normalize,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import (
    dispatch_and_bridge, DispatchVerdict, DispatchResult,
    FROZEN_FAMILIES, V1_DISPATCH_PROFILE, DispatchProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

LAYOUT_VERSION = "V1.0"
LAYOUT_FROZEN = True


# ════════════════════════════════════════════════════════════
# FAMILY FACTORY MAP
# ════════════════════════════════════════════════════════════

_FAMILY_FACTORIES = {
    "adjacent_pair": fixture_adjacent_pair,
    "containment": fixture_containment,
    "three_regions": fixture_three_regions,
}


# ════════════════════════════════════════════════════════════
# FROZEN MULTI-LAYOUT PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MultiLayoutProfile:
    """
    Frozen envelope of allowed multi-artifact layout configurations.
    Layouts beyond these bounds are expected to fail.
    """
    host_width: int = 800
    host_height: int = 800
    min_embed_scale: float = 0.30
    max_embed_scale: float = 0.60
    max_artifacts: int = 3
    min_gap_px: int = 30
    cluster_gap_px: int = 40
    min_artifact_pixels: int = 200
    extraction_padding: int = 5
    palette_detect_threshold_sq: int = 10000


V1_MULTI_LAYOUT_PROFILE = MultiLayoutProfile()


# ════════════════════════════════════════════════════════════
# MULTI-ARTIFACT HOST SPECIFICATION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ArtifactEntry:
    """One artifact placement within a multi-artifact host."""
    artifact_spec: ArtifactSpec
    offset_x: int
    offset_y: int
    embed_scale: float = 0.50


@dataclass(frozen=True)
class MultiLayoutSpec:
    """Defines multiple artifacts embedded in one host image."""
    entries: Tuple[ArtifactEntry, ...]
    host_width: int = 800
    host_height: int = 800
    host_background: Tuple[int, int, int] = (220, 220, 220)


# ════════════════════════════════════════════════════════════
# MULTI-ARTIFACT HOST IMAGE GENERATOR
# ════════════════════════════════════════════════════════════

def generate_multi_artifact_host(spec: MultiLayoutSpec) -> bytes:
    """
    Generate a host image with multiple canonical artifacts embedded
    at specified offsets and scales.  Returns PNG bytes.

    Steps:
    1. Create host canvas with uniform background
    2. For each artifact entry:
       a. Render canonical artifact to raw RGB
       b. Scale if embed_scale != 1.0
       c. Blit non-white pixels onto host at (offset_x, offset_y)
    3. Encode as PNG

    Deterministic: same MultiLayoutSpec → identical PNG bytes.
    Blitting order follows entry order — later entries overwrite earlier
    ones where they overlap (which is an out-of-bounds condition).
    """
    hw, hh = spec.host_width, spec.host_height
    bg = spec.host_background
    host_buf = bytearray(bg * hw * hh)

    for entry in spec.entries:
        # Render canonical artifact to raw RGB
        art_rgb = _render_to_raw_rgb(entry.artifact_spec)
        art_w, art_h = CANVAS_WIDTH, CANVAS_HEIGHT

        # Scale if needed
        if entry.embed_scale != 1.0:
            art_rgb, art_w, art_h = degrade_scale(
                art_rgb, art_w, art_h, entry.embed_scale
            )

        # Blit non-white pixels onto host
        ox, oy = entry.offset_x, entry.offset_y
        for y in range(art_h):
            dst_y = oy + y
            if dst_y < 0 or dst_y >= hh:
                continue
            for x in range(art_w):
                dst_x = ox + x
                if dst_x < 0 or dst_x >= hw:
                    continue
                src_off = (y * art_w + x) * 3
                px = (art_rgb[src_off], art_rgb[src_off + 1],
                      art_rgb[src_off + 2])
                if px != BACKGROUND_COLOR:
                    dst_off = (dst_y * hw + dst_x) * 3
                    host_buf[dst_off] = px[0]
                    host_buf[dst_off + 1] = px[1]
                    host_buf[dst_off + 2] = px[2]

    return _encode_png(hw, hh, host_buf)


# ════════════════════════════════════════════════════════════
# MULTI-CANDIDATE LOCALIZATION
# ════════════════════════════════════════════════════════════

def localize_multiple_artifacts(
    host_png: bytes,
    profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
) -> List[Tuple[int, int, int, int]]:
    """
    Find bounding boxes of multiple V1 artifacts within a host image.

    Uses palette-pixel scanning followed by spatial clustering to
    separate distinct artifact regions.  Two palette pixels belong
    to the same cluster if either is within cluster_gap_px of the
    other cluster's current bounding box.

    After clustering, a merge pass collapses any overlapping clusters.
    Clusters below min_artifact_pixels are discarded.

    Returns a list of (x, y, w, h) bounding boxes, sorted
    top-to-bottom then left-to-right by centroid position.

    This is palette-color clustering, not general object detection.
    """
    width, height, buf = _decode_png_to_rgb(host_png)

    threshold_sq = profile.palette_detect_threshold_sq
    gap = profile.cluster_gap_px

    # Phase 1: Assign each palette pixel to the nearest cluster
    # (by expanded bounding box), or start a new cluster.
    clusters = []  # each: [min_x, min_y, max_x, max_y, pixel_count]

    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            px = (buf[offset], buf[offset + 1], buf[offset + 2])
            if not _is_palette_pixel(px, threshold_sq):
                continue

            # Try to assign to an existing cluster
            assigned = False
            for cl in clusters:
                if (cl[0] - gap <= x <= cl[2] + gap and
                        cl[1] - gap <= y <= cl[3] + gap):
                    if x < cl[0]:
                        cl[0] = x
                    if y < cl[1]:
                        cl[1] = y
                    if x > cl[2]:
                        cl[2] = x
                    if y > cl[3]:
                        cl[3] = y
                    cl[4] += 1
                    assigned = True
                    break
            if not assigned:
                clusters.append([x, y, x, y, 1])

    # Phase 2: Merge any clusters whose expanded bboxes overlap.
    # Repeat until no merges occur.
    merged = True
    while merged:
        merged = False
        new_clusters = []
        used = set()
        for i in range(len(clusters)):
            if i in used:
                continue
            ci = list(clusters[i])
            for j in range(i + 1, len(clusters)):
                if j in used:
                    continue
                cj = clusters[j]
                if (ci[0] - gap <= cj[2] and cj[0] - gap <= ci[2] and
                        ci[1] - gap <= cj[3] and cj[1] - gap <= ci[3]):
                    # Merge cj into ci
                    if cj[0] < ci[0]:
                        ci[0] = cj[0]
                    if cj[1] < ci[1]:
                        ci[1] = cj[1]
                    if cj[2] > ci[2]:
                        ci[2] = cj[2]
                    if cj[3] > ci[3]:
                        ci[3] = cj[3]
                    ci[4] += cj[4]
                    used.add(j)
                    merged = True
            new_clusters.append(ci)
        clusters = new_clusters

    # Phase 3: Filter by minimum pixel count and build result bboxes.
    min_px = profile.min_artifact_pixels
    pad = profile.extraction_padding
    results = []
    for cl in clusters:
        if cl[4] >= min_px:
            x0 = max(0, cl[0] - pad)
            y0 = max(0, cl[1] - pad)
            x1 = min(width, cl[2] + 1 + pad)
            y1 = min(height, cl[3] + 1 + pad)
            results.append((x0, y0, x1 - x0, y1 - y0))

    # Phase 4: Sort top-to-bottom then left-to-right by centroid.
    # Use row-band quantization: artifacts whose y-centroids fall within
    # the same band (ROW_BAND_PX) are treated as the same row and sorted
    # left-to-right.  This handles different artifact types having
    # different palette-pixel extents at the same offset_y.
    ROW_BAND_PX = 80
    results.sort(key=lambda b: (
        int((b[1] + b[3] / 2.0) / ROW_BAND_PX),
        b[0] + b[2] / 2.0,
    ))

    return results


# ════════════════════════════════════════════════════════════
# VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class MultiLayoutVerdict(str, Enum):
    """Outcome of multi-artifact layout recovery."""
    RECOVERED = "RECOVERED"                # All expected artifacts found and dispatched
    NO_CANDIDATES = "NO_CANDIDATES"        # No palette-pixel clusters found
    COUNT_MISMATCH = "COUNT_MISMATCH"      # Found different number than expected
    PARTIAL_RECOVERY = "PARTIAL_RECOVERY"  # Some but not all dispatched correctly
    ERROR = "ERROR"                        # Unexpected error


@dataclass
class CandidateResult:
    """Result for one candidate region within a multi-artifact host."""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    dispatch_result: Optional[DispatchResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": list(self.bbox),
            "dispatch": (self.dispatch_result.to_dict()
                         if self.dispatch_result else None),
        }


@dataclass
class MultiLayoutResult:
    """Complete result of multi-artifact layout recovery."""
    verdict: MultiLayoutVerdict = MultiLayoutVerdict.ERROR
    expected_count: int = 0
    found_count: int = 0
    dispatched_count: int = 0
    candidates: List[CandidateResult] = field(default_factory=list)
    dispatched_families: Tuple[str, ...] = ()
    ordering_correct: bool = False
    version: str = LAYOUT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "expected_count": self.expected_count,
            "found_count": self.found_count,
            "dispatched_count": self.dispatched_count,
            "dispatched_families": list(self.dispatched_families),
            "ordering_correct": self.ordering_correct,
            "candidates": [c.to_dict() for c in self.candidates],
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FULL MULTI-ARTIFACT PIPELINE
# ════════════════════════════════════════════════════════════

def multi_artifact_recover_and_dispatch(
    host_png: bytes,
    expected_families: Tuple[str, ...] = (),
    profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
) -> MultiLayoutResult:
    """
    Full multi-artifact recovery-and-dispatch pipeline.

      host_png → localize_multiple → for each candidate:
        extract → normalize → dispatch_and_bridge

    Steps:
    1. Localize multiple candidate regions via palette-pixel clustering
    2. For each candidate bbox: extract, normalize to 400×400, dispatch
    3. Collect dispatched family names in candidate order
    4. Compare against expected_families for ordering verification

    Returns MultiLayoutResult with verdict, counts, and per-candidate
    dispatch details.

    Deterministic: same host_png + same expected_families → identical result.
    """
    result = MultiLayoutResult()
    result.expected_count = len(expected_families)

    # Step 1: Localize multiple candidates
    bboxes = localize_multiple_artifacts(host_png, profile)
    result.found_count = len(bboxes)

    if not bboxes:
        result.verdict = MultiLayoutVerdict.NO_CANDIDATES
        return result

    # Step 2: Per-candidate extract → normalize → dispatch
    for bbox in bboxes:
        candidate = CandidateResult(bbox=bbox)
        try:
            extracted_png = extract_and_normalize(host_png, bbox)
            dr = dispatch_and_bridge(extracted_png, tolerance, dispatch_profile)
            candidate.dispatch_result = dr
        except Exception:
            candidate.dispatch_result = DispatchResult(
                verdict=DispatchVerdict.ERROR
            )
        result.candidates.append(candidate)

    # Step 3: Collect dispatched families
    dispatched = []
    for c in result.candidates:
        if (c.dispatch_result and
                c.dispatch_result.verdict == DispatchVerdict.DISPATCHED):
            dispatched.append(c.dispatch_result.family_name)
    result.dispatched_count = len(dispatched)
    result.dispatched_families = tuple(dispatched)

    # Step 4: Check ordering against expected
    if (expected_families and
            result.dispatched_families == expected_families):
        result.ordering_correct = True

    # Step 5: Determine verdict
    if (result.dispatched_count == result.expected_count > 0 and
            result.ordering_correct):
        result.verdict = MultiLayoutVerdict.RECOVERED
    elif result.dispatched_count == result.expected_count > 0:
        # Right count but wrong order — still recovered but flag ordering
        result.verdict = MultiLayoutVerdict.RECOVERED
    elif result.dispatched_count > 0 and result.dispatched_count < result.expected_count:
        result.verdict = MultiLayoutVerdict.PARTIAL_RECOVERY
    elif result.found_count != result.expected_count:
        result.verdict = MultiLayoutVerdict.COUNT_MISMATCH
    else:
        result.verdict = MultiLayoutVerdict.PARTIAL_RECOVERY

    return result


# ════════════════════════════════════════════════════════════
# CONVENIENCE: BUILD SPEC FROM LAYOUT DEFINITION
# ════════════════════════════════════════════════════════════

def build_layout_spec(layout_def: Dict[str, Any]) -> MultiLayoutSpec:
    """
    Build a MultiLayoutSpec from a frozen layout definition dict.

    layout_def must have:
      "entries": list of {"family": str, "offset_x": int,
                          "offset_y": int, "scale": float}
      "host_background": optional (r, g, b) tuple
    """
    entries = []
    for e in layout_def["entries"]:
        factory = _FAMILY_FACTORIES[e["family"]]
        entries.append(ArtifactEntry(
            artifact_spec=factory(),
            offset_x=e["offset_x"],
            offset_y=e["offset_y"],
            embed_scale=e["scale"],
        ))
    bg = layout_def.get("host_background", (220, 220, 220))
    return MultiLayoutSpec(
        entries=tuple(entries),
        host_background=bg,
    )


# ════════════════════════════════════════════════════════════
# FROZEN LAYOUT DEFINITIONS
# ════════════════════════════════════════════════════════════

FROZEN_LAYOUTS = (
    {
        "name": "two_horizontal",
        "entries": [
            {"family": "adjacent_pair", "offset_x": 50,  "offset_y": 200, "scale": 0.50},
            {"family": "containment",   "offset_x": 450, "offset_y": 200, "scale": 0.50},
        ],
        "expected_families": ("adjacent_pair", "containment"),
        "host_background": (220, 220, 220),
    },
    {
        "name": "two_vertical",
        "entries": [
            {"family": "adjacent_pair", "offset_x": 200, "offset_y": 50,  "scale": 0.50},
            {"family": "three_regions", "offset_x": 200, "offset_y": 450, "scale": 0.50},
        ],
        "expected_families": ("adjacent_pair", "three_regions"),
        "host_background": (220, 220, 220),
    },
    {
        "name": "three_in_row",
        "entries": [
            {"family": "adjacent_pair", "offset_x": 20,  "offset_y": 250, "scale": 0.30},
            {"family": "containment",   "offset_x": 290, "offset_y": 250, "scale": 0.30},
            {"family": "three_regions", "offset_x": 560, "offset_y": 250, "scale": 0.30},
        ],
        "expected_families": ("adjacent_pair", "containment", "three_regions"),
        "host_background": (220, 220, 220),
    },
    {
        "name": "two_horizontal_mixed",
        "entries": [
            {"family": "containment",   "offset_x": 50,  "offset_y": 200, "scale": 0.45},
            {"family": "three_regions", "offset_x": 450, "offset_y": 200, "scale": 0.45},
        ],
        "expected_families": ("containment", "three_regions"),
        "host_background": (180, 180, 180),
    },
    {
        "name": "two_vertical_reversed",
        "entries": [
            {"family": "three_regions", "offset_x": 200, "offset_y": 50,  "scale": 0.50},
            {"family": "adjacent_pair", "offset_x": 200, "offset_y": 450, "scale": 0.50},
        ],
        "expected_families": ("three_regions", "adjacent_pair"),
        "host_background": (240, 240, 230),
    },
)


OUT_OF_BOUNDS_LAYOUTS = (
    {
        "name": "overlapping_artifacts",
        "description": "Two artifacts at same position — clusters merge into one",
        "entries": [
            {"family": "adjacent_pair", "offset_x": 200, "offset_y": 200, "scale": 0.50},
            {"family": "containment",   "offset_x": 200, "offset_y": 200, "scale": 0.50},
        ],
        "expected_count": 2,
        "host_background": (220, 220, 220),
    },
    {
        "name": "one_too_small",
        "description": "Second artifact scaled below detection threshold",
        "entries": [
            {"family": "adjacent_pair", "offset_x": 50,  "offset_y": 200, "scale": 0.50},
            {"family": "containment",   "offset_x": 600, "offset_y": 200, "scale": 0.03},
        ],
        "expected_count": 2,
        "host_background": (220, 220, 220),
    },
    {
        "name": "empty_host",
        "description": "No artifacts placed — no candidates expected",
        "entries": [],
        "expected_count": 0,
        "host_background": (220, 220, 220),
    },
)
