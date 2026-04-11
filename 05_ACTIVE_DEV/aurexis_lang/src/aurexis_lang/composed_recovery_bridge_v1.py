"""
Aurexis Core — Composed Recovery Bridge V1

Bounded multi-transform recovery for the narrow V1 raster bridge.
Proves that a canonical V1 artifact embedded in a host image through
a frozen composition of already-proven transform families — host
placement, scale, cardinal rotation, mild keystone distortion, and
mild photometric degradation — can be recovered deterministically
through the existing bridge/substrate path.

What this proves:
  The individual recovery lanes (localization, orientation normalization,
  perspective normalization, capture tolerance) compose correctly:
  a single artifact subjected to a bounded combination of ALL of them
  in one host image can still be localized, normalized, parsed, and
  bridged to the V1 substrate.

What this does NOT prove:
  - Full camera capture robustness
  - Arbitrary transform composition
  - Unconstrained scene decoding
  - General transform invariance
  - Full print/scan round-trip robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen ComposedProfile defines exactly which combinations are
    in-bounds: host placement + embed scale + cardinal rotation +
    one frozen keystone distortion + optional mild degradation
  - Host image generation: render → rotate → warp → optionally
    degrade → blit onto host
  - Recovery: localize → extract → try all (rotation × distortion)
    combinations → tolerant parse → substrate
  - All operations are deterministic
  - Reuses existing bridge modules — no new algorithms

This is a narrow integrated recovery proof, not general invariance
or camera-complete behavior.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.raster_law_bridge_v1 import (
    BRIDGE_VERSION, CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_COLOR,
    PRIMITIVE_PALETTE, ArtifactSpec, ArtifactPrimitive,
    render_artifact, _render_to_raw_rgb, _encode_png, _decode_png_to_rgb,
    _color_distance_sq,
    fixture_adjacent_pair, fixture_containment, fixture_three_regions,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    parse_artifact_tolerant, V1_TOLERANCE_PROFILE, ToleranceProfile,
    degrade_brightness, degrade_contrast, degrade_noise,
)
from aurexis_lang.artifact_localization_bridge_v1 import (
    LocalizationProfile, V1_LOCALIZATION_PROFILE,
    ALLOWED_HOST_BACKGROUNDS,
    localize_artifact, extract_and_normalize,
    _is_palette_pixel,
)
from aurexis_lang.orientation_normalization_bridge_v1 import (
    SUPPORTED_ANGLES, OrientationProfile, V1_ORIENTATION_PROFILE,
    rotate_image, rotate_png,
    _color_signature_matches,
)
from aurexis_lang.perspective_normalization_bridge_v1 import (
    FROZEN_DISTORTIONS, KeystoneDistortion,
    PerspectiveProfile, V1_PERSPECTIVE_PROFILE,
    warp_forward, warp_inverse,
)
from aurexis_lang.type_system_v1 import safe_execute_image_as_program


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

COMPOSED_VERSION = "V1.0"
COMPOSED_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN COMPOSED-RECOVERY PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ComposedProfile:
    """
    Frozen profile defining the bounded composition of transforms
    allowed for V1 composed recovery.

    Each composed case applies:
      1. Host placement (offset_x, offset_y within bounds)
      2. Embed scale (within [min_embed_scale, max_embed_scale])
      3. Cardinal rotation (0, 90, 180, 270)
      4. One frozen keystone distortion (from FROZEN_DISTORTIONS)
      5. Optional mild photometric degradation (within tolerance)

    All bounds are inherited from the individual bridge profiles.
    No bound is widened.
    """
    # Host canvas
    host_width: int = 800
    host_height: int = 800

    # Placement bounds (same as localization bridge)
    min_offset_x: int = 50
    max_offset_x: int = 350
    min_offset_y: int = 50
    max_offset_y: int = 350

    # Scale bounds (same as localization bridge)
    min_embed_scale: float = 0.80
    max_embed_scale: float = 1.20

    # Rotation: only cardinal angles
    supported_angles: Tuple[int, ...] = SUPPORTED_ANGLES

    # Perspective: only frozen distortions
    max_corner_offset_px: int = 30

    # Degradation bounds (subset of capture tolerance)
    max_brightness_shift: int = 20
    max_contrast_deviation: float = 0.10   # factor = 1.0 ± this
    max_noise_amplitude: int = 15

    # Detection thresholds
    min_artifact_pixels: int = 200
    extraction_padding: int = 5
    palette_detect_threshold_sq: int = 7500


V1_COMPOSED_PROFILE = ComposedProfile()


# ════════════════════════════════════════════════════════════
# COMPOSED HOST SPEC
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DegradationSpec:
    """Optional mild photometric degradation."""
    brightness_shift: int = 0
    contrast_factor: float = 1.0
    noise_amplitude: int = 0
    noise_seed: int = 42


NO_DEGRADATION = DegradationSpec()


@dataclass(frozen=True)
class ComposedHostSpec:
    """
    Full specification for a composed-case host image.

    Applies transforms in order:
      render → rotate → warp → degrade → blit onto host
    """
    artifact_spec: ArtifactSpec = field(default_factory=fixture_adjacent_pair)
    offset_x: int = 200
    offset_y: int = 200
    embed_scale: float = 1.0
    rotation_angle: int = 0
    distortion: KeystoneDistortion = field(default_factory=lambda: FROZEN_DISTORTIONS[0])
    degradation: DegradationSpec = field(default_factory=lambda: NO_DEGRADATION)
    host_background: Tuple[int, int, int] = (220, 220, 220)


# ════════════════════════════════════════════════════════════
# COMPOSED HOST IMAGE GENERATION
# ════════════════════════════════════════════════════════════

def generate_composed_host_image(spec: ComposedHostSpec) -> bytes:
    """
    Generate a host image with a canonical artifact subjected to a
    composed chain of bounded transforms:
      render → rotate → warp → degrade → scale → blit onto host

    All transforms are deterministic. Returns PNG bytes.
    """
    # 1. Render the canonical artifact to raw RGB
    art_png = render_artifact(spec.artifact_spec)
    art_w, art_h, art_rgb = _decode_png_to_rgb(art_png)

    # 2. Rotate by cardinal angle
    if spec.rotation_angle != 0:
        art_rgb, art_w, art_h = rotate_image(
            art_rgb, art_w, art_h, spec.rotation_angle
        )

    # 3. Apply keystone distortion (if not identity)
    if spec.distortion.name != "identity":
        art_rgb, art_w, art_h = warp_forward(
            art_rgb, art_w, art_h, spec.distortion
        )

    # 4. Apply photometric degradation
    deg = spec.degradation
    if deg.brightness_shift != 0:
        art_rgb = degrade_brightness(art_rgb, art_w, art_h, deg.brightness_shift)
    if deg.contrast_factor != 1.0:
        art_rgb = degrade_contrast(art_rgb, art_w, art_h, deg.contrast_factor)
    if deg.noise_amplitude > 0:
        art_rgb = degrade_noise(
            art_rgb, art_w, art_h, deg.noise_amplitude, deg.noise_seed
        )

    # 5. Scale if needed
    if spec.embed_scale != 1.0:
        from aurexis_lang.capture_tolerance_bridge_v1 import degrade_scale
        art_rgb, art_w, art_h = degrade_scale(
            art_rgb, art_w, art_h, spec.embed_scale
        )

    # 6. Blit onto host canvas
    host_w, host_h = V1_COMPOSED_PROFILE.host_width, V1_COMPOSED_PROFILE.host_height
    bg = spec.host_background
    host_rgb = bytearray(host_w * host_h * 3)
    for i in range(host_w * host_h):
        host_rgb[i * 3] = bg[0]
        host_rgb[i * 3 + 1] = bg[1]
        host_rgb[i * 3 + 2] = bg[2]

    for row in range(art_h):
        for col in range(art_w):
            hx = spec.offset_x + col
            hy = spec.offset_y + row
            if 0 <= hx < host_w and 0 <= hy < host_h:
                src_idx = (row * art_w + col) * 3
                dst_idx = (hy * host_w + hx) * 3
                host_rgb[dst_idx] = art_rgb[src_idx]
                host_rgb[dst_idx + 1] = art_rgb[src_idx + 1]
                host_rgb[dst_idx + 2] = art_rgb[src_idx + 2]

    return _encode_png(host_w, host_h, bytes(host_rgb))


# ════════════════════════════════════════════════════════════
# COMPOSED RECOVERY: EXHAUSTIVE TRIAL
# ════════════════════════════════════════════════════════════

def _try_recovery(
    extracted_png: bytes,
    spec: ArtifactSpec,
    angle: int,
    distortion: KeystoneDistortion,
    tolerance: ToleranceProfile,
) -> Optional[List]:
    """
    Try recovering an extracted artifact image by applying:
      1. Inverse rotation (by angle)
      2. Inverse warp (by distortion)
      3. Tolerant parse
      4. Color-spatial signature check

    Returns the parsed primitives list if successful, else None.
    """
    w, h, buf = _decode_png_to_rgb(extracted_png)

    # Step 1: Undo rotation
    if angle != 0:
        inverse_angle = (360 - angle) % 360
        buf, w, h = rotate_image(buf, w, h, inverse_angle)

    # Step 2: Undo perspective distortion
    if distortion.name != "identity":
        buf, w, h = warp_inverse(buf, w, h, distortion)

    # Step 3: Tolerant parse
    candidate_png = _encode_png(w, h, bytes(buf))
    parsed = parse_artifact_tolerant(candidate_png, tolerance)

    # Step 4: Check primitive count
    if len(parsed) != len(spec.primitives):
        return None

    # Step 5: Verify color-spatial signature
    if not _color_signature_matches(parsed, spec):
        return None

    return parsed


def detect_composed_transform(
    extracted_png: bytes,
    spec: ArtifactSpec,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    profile: ComposedProfile = V1_COMPOSED_PROFILE,
) -> Optional[Tuple[int, KeystoneDistortion]]:
    """
    Exhaustive trial over all (rotation × distortion) combinations.

    Tries each combination's inverse to find the one that recovers
    the canonical artifact. Returns (detected_angle, detected_distortion)
    or None if no combination works.

    This is O(angles × distortions) = O(4 × 7) = O(28) trials.
    Each trial: rotate + warp + parse + signature check.
    """
    for angle in profile.supported_angles:
        for distortion in FROZEN_DISTORTIONS:
            parsed = _try_recovery(
                extracted_png, spec, angle, distortion, tolerance
            )
            if parsed is not None:
                return (angle, distortion)
    return None


# ════════════════════════════════════════════════════════════
# VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class ComposedVerdict(str, Enum):
    """Outcome of composed recovery attempt."""
    RECOVERED = "RECOVERED"              # Full pipeline succeeded
    NOT_FOUND = "NOT_FOUND"              # Localization failed
    TRANSFORM_UNKNOWN = "TRANSFORM_UNKNOWN"  # No (angle, distortion) matched
    PARSE_FAILED = "PARSE_FAILED"        # Parsed wrong primitive count
    BRIDGE_FAILED = "BRIDGE_FAILED"      # Substrate bridge failed
    ERROR = "ERROR"                      # Unexpected error


@dataclass
class ComposedResult:
    """Result of a composed recovery attempt."""
    host_spec: ComposedHostSpec = field(default_factory=ComposedHostSpec)
    verdict: ComposedVerdict = ComposedVerdict.ERROR
    detected_bbox: Optional[Tuple[int, int, int, int]] = None
    detected_angle: Optional[int] = None
    detected_distortion: Optional[str] = None
    expected_primitives: int = 0
    parsed_primitives: int = 0
    type_check_verdict: Optional[str] = None
    execution_verdict: Optional[str] = None
    bridge_verdict: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "detected_angle": self.detected_angle,
            "detected_distortion": self.detected_distortion,
            "expected_primitives": self.expected_primitives,
            "parsed_primitives": self.parsed_primitives,
            "type_check_verdict": self.type_check_verdict,
            "execution_verdict": self.execution_verdict,
            "bridge_verdict": self.bridge_verdict,
            "version": COMPOSED_VERSION,
        }


# ════════════════════════════════════════════════════════════
# COMPOSED RECOVERY END-TO-END PIPELINE
# ════════════════════════════════════════════════════════════

def composed_recovery(
    host_spec: ComposedHostSpec,
    profile: ComposedProfile = V1_COMPOSED_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
) -> ComposedResult:
    """
    Full composed recovery bridge path:
      host_spec -> generate composed host image -> localize ->
      extract -> detect (rotation × distortion) -> normalize ->
      tolerant parse -> substrate bridge

    1. Generate host image with composed-transform embedded artifact
    2. Localize artifact via palette-color scanning
    3. Extract and normalize to canonical canvas size
    4. Detect composed transform by exhaustive trial over all
       (angle × distortion) combinations
    5. Apply inverse transforms to recover canonical form
    6. Parse recovered image with tolerant parser
    7. Bridge to substrate

    If any step fails, returns an honest failure verdict.
    """
    result = ComposedResult(host_spec=host_spec)
    result.expected_primitives = len(host_spec.artifact_spec.primitives)

    # Step 1: Generate composed host image
    host_png = generate_composed_host_image(host_spec)

    # Step 2: Localize
    loc_profile = LocalizationProfile(
        host_width=profile.host_width,
        host_height=profile.host_height,
        min_offset_x=profile.min_offset_x,
        max_offset_x=profile.max_offset_x,
        min_offset_y=profile.min_offset_y,
        max_offset_y=profile.max_offset_y,
        min_embed_scale=profile.min_embed_scale,
        max_embed_scale=profile.max_embed_scale,
        min_artifact_pixels=profile.min_artifact_pixels,
        extraction_padding=profile.extraction_padding,
        palette_detect_threshold_sq=profile.palette_detect_threshold_sq,
    )

    bbox = localize_artifact(host_png, loc_profile)
    if bbox is None:
        result.verdict = ComposedVerdict.NOT_FOUND
        return result
    result.detected_bbox = bbox

    # Step 3: Extract and normalize to canonical size
    try:
        extracted_png = extract_and_normalize(host_png, bbox)
    except Exception:
        result.verdict = ComposedVerdict.NOT_FOUND
        return result

    # Step 4: Detect composed transform
    detection = detect_composed_transform(
        extracted_png, host_spec.artifact_spec, tolerance, profile
    )

    if detection is None:
        result.verdict = ComposedVerdict.TRANSFORM_UNKNOWN
        return result

    detected_angle, detected_distortion = detection
    result.detected_angle = detected_angle
    result.detected_distortion = detected_distortion.name

    # Step 5: Apply inverse transforms to recover canonical form
    w, h, buf = _decode_png_to_rgb(extracted_png)
    if detected_angle != 0:
        inverse_angle = (360 - detected_angle) % 360
        buf, w, h = rotate_image(buf, w, h, inverse_angle)
    if detected_distortion.name != "identity":
        buf, w, h = warp_inverse(buf, w, h, detected_distortion)
    normalized_png = _encode_png(w, h, bytes(buf))

    # Step 6: Tolerant parse
    parsed = parse_artifact_tolerant(normalized_png, tolerance)
    result.parsed_primitives = len(parsed)

    if result.parsed_primitives != result.expected_primitives:
        result.verdict = ComposedVerdict.PARSE_FAILED
        return result

    # Step 7: Bridge to substrate
    spec = host_spec.artifact_spec
    substrate_result = safe_execute_image_as_program(
        parsed,
        bindings=spec.bindings,
        operations=list(spec.operations),
    )

    if not substrate_result["executed"]:
        result.verdict = ComposedVerdict.BRIDGE_FAILED
        result.bridge_verdict = "NOT_EXECUTED"
        return result

    result.type_check_verdict = (
        "WELL_TYPED" if substrate_result["type_check"]["is_well_typed"]
        else "ILL_TYPED"
    )
    result.execution_verdict = substrate_result["execution"]["verdict"]

    if result.execution_verdict in ("PASS", "PARTIAL", "EMPTY"):
        result.verdict = ComposedVerdict.RECOVERED
        result.bridge_verdict = "BRIDGED"
    else:
        result.verdict = ComposedVerdict.BRIDGE_FAILED
        result.bridge_verdict = result.execution_verdict

    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: composed cases within ALL frozen profile bounds.
# Each exercises a DIFFERENT combination of transforms.

IN_BOUNDS_CASES = [
    # Case 0: identity baseline — no rotation, no distortion, no degradation
    {
        "label": "identity_baseline",
        "rotation_angle": 0,
        "distortion": "identity",
        "degradation": NO_DEGRADATION,
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (220, 220, 220),
    },
    # Case 1: rotation only (90°)
    {
        "label": "rotation_90_only",
        "rotation_angle": 90,
        "distortion": "identity",
        "degradation": NO_DEGRADATION,
        "offset_x": 150, "offset_y": 150,
        "embed_scale": 1.0,
        "host_background": (255, 255, 255),
    },
    # Case 2: distortion only (horizontal keystone mild)
    {
        "label": "h_keystone_only",
        "rotation_angle": 0,
        "distortion": "h_keystone_mild",
        "degradation": NO_DEGRADATION,
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (220, 220, 220),
    },
    # Case 3: degradation only (brightness + noise)
    {
        "label": "degradation_only",
        "rotation_angle": 0,
        "distortion": "identity",
        "degradation": DegradationSpec(brightness_shift=15, noise_amplitude=10, noise_seed=99),
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (180, 180, 180),
    },
    # Case 4: rotation + distortion (180° + vertical keystone)
    {
        "label": "rot180_v_keystone",
        "rotation_angle": 180,
        "distortion": "v_keystone_mild",
        "degradation": NO_DEGRADATION,
        "offset_x": 100, "offset_y": 100,
        "embed_scale": 0.95,
        "host_background": (220, 220, 220),
    },
    # Case 5: rotation + degradation (270° + contrast shift)
    {
        "label": "rot270_contrast",
        "rotation_angle": 270,
        "distortion": "identity",
        "degradation": DegradationSpec(contrast_factor=0.92),
        "offset_x": 200, "offset_y": 100,
        "embed_scale": 1.0,
        "host_background": (240, 240, 230),
    },
    # Case 6: distortion + degradation (corner pull + brightness)
    {
        "label": "corner_pull_brightness",
        "rotation_angle": 0,
        "distortion": "corner_pull_inward",
        "degradation": DegradationSpec(brightness_shift=-10),
        "offset_x": 150, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (200, 210, 220),
    },
    # Case 7: FULL COMPOSITION — rotation + distortion + degradation + scale
    {
        "label": "full_composition_90_hkey_deg",
        "rotation_angle": 90,
        "distortion": "h_keystone_mild",
        "degradation": DegradationSpec(brightness_shift=10, noise_amplitude=8, noise_seed=77),
        "offset_x": 100, "offset_y": 150,
        "embed_scale": 0.90,
        "host_background": (220, 220, 220),
    },
    # Case 8: FULL COMPOSITION — 270° + mild trapezoid + contrast + scale
    {
        "label": "full_composition_270_trap_contrast",
        "rotation_angle": 270,
        "distortion": "mild_trapezoid",
        "degradation": DegradationSpec(contrast_factor=1.08),
        "offset_x": 200, "offset_y": 100,
        "embed_scale": 0.95,
        "host_background": (180, 180, 180),
    },
    # Case 9: FULL COMPOSITION — 180° + h_keystone_reverse + brightness + noise
    {
        "label": "full_composition_180_hrev_noise",
        "rotation_angle": 180,
        "distortion": "h_keystone_reverse",
        "degradation": DegradationSpec(brightness_shift=-15, noise_amplitude=12, noise_seed=42),
        "offset_x": 150, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (255, 255, 255),
    },
]

# Out-of-bounds: composed cases that should fail honestly.
OUT_OF_BOUNDS_CASES = [
    # OOB 0: Off-canvas placement — most of artifact clipped
    {
        "label": "off_canvas",
        "rotation_angle": 0,
        "distortion": "identity",
        "degradation": NO_DEGRADATION,
        "offset_x": 790, "offset_y": 790,
        "embed_scale": 1.0,
        "host_background": (220, 220, 220),
    },
    # OOB 1: Extreme non-frozen distortion (not in FROZEN_DISTORTIONS)
    {
        "label": "extreme_distortion",
        "rotation_angle": 0,
        "distortion_override": KeystoneDistortion(
            name="_extreme_squash",
            tl=(200, 200), tr=(-200, 200),
            bl=(200, -200), br=(-200, -200),
        ),
        "degradation": NO_DEGRADATION,
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (220, 220, 220),
    },
    # OOB 2: Extreme combined degradation beyond tolerance bounds
    # Brightness + noise + contrast all at extreme levels simultaneously
    {
        "label": "extreme_combined_degradation",
        "rotation_angle": 90,
        "distortion": "h_keystone_mild",
        "degradation": DegradationSpec(
            brightness_shift=-80, contrast_factor=0.40,
            noise_amplitude=120, noise_seed=99
        ),
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 1.0,
        "host_background": (220, 220, 220),
    },
    # OOB 3: Extreme miniaturization — artifact too small to detect
    {
        "label": "extreme_miniaturization",
        "rotation_angle": 0,
        "distortion": "identity",
        "degradation": NO_DEGRADATION,
        "offset_x": 200, "offset_y": 200,
        "embed_scale": 0.05,
        "host_background": (220, 220, 220),
    },
]


def _distortion_by_name(name: str) -> KeystoneDistortion:
    """Look up a frozen distortion by name."""
    for d in FROZEN_DISTORTIONS:
        if d.name == name:
            return d
    raise ValueError(f"Unknown frozen distortion: {name}")


def build_composed_host_spec(
    case: Dict[str, Any],
    artifact_spec: ArtifactSpec = None,
) -> ComposedHostSpec:
    """Build a ComposedHostSpec from a case dict and artifact spec."""
    if artifact_spec is None:
        artifact_spec = fixture_adjacent_pair()

    # Resolve distortion
    if "distortion_override" in case:
        distortion = case["distortion_override"]
    else:
        distortion = _distortion_by_name(case["distortion"])

    return ComposedHostSpec(
        artifact_spec=artifact_spec,
        offset_x=case["offset_x"],
        offset_y=case["offset_y"],
        embed_scale=case.get("embed_scale", 1.0),
        rotation_angle=case.get("rotation_angle", 0),
        distortion=distortion,
        degradation=case.get("degradation", NO_DEGRADATION),
        host_background=case.get("host_background", (220, 220, 220)),
    )
