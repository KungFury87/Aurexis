"""
Aurexis Core — Real Capture Ingest Profile Bridge V1

Bounded executable profile defining a small frozen family of supported
real-capture ingest cases and how real captures enter the existing
evidence tier system.

What this proves:
  A small frozen set of CaptureIngestCase records exists, each defining
  an allowed file shape (extension, max size, resolution bounds),
  required metadata fields, capture assumptions, and the evidence tier
  entry point. A real capture file is validated against the profile
  before any downstream processing occurs. Only files matching a
  supported case are admitted.

What this does NOT prove:
  - Arbitrary media ingestion
  - Full camera driver support
  - Full real-world robustness
  - Full Aurexis Core completion

Design:
  - CaptureFileShape: frozen dataclass for allowed file extension, max
    file size, min/max resolution.
  - CaptureAssumption: frozen dataclass for capture-environment
    constraints (e.g. lighting, distance, orientation).
  - CaptureIngestCase: frozen record linking file shape, metadata
    requirements, assumptions, and evidence tier entry.
  - IngestProfile: frozen profile of all supported cases.
  - validate_capture_file(): checks a candidate file dict against the
    profile and returns an IngestVerdict.
  - V1_INGEST_PROFILE: the frozen singleton.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import hashlib
import json


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

INGEST_PROFILE_VERSION = "V1.0"
INGEST_PROFILE_FROZEN = True


# ════════════════════════════════════════════════════════════
# CAPTURE FILE SHAPE — allowed file properties
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CaptureFileShape:
    """
    Bounded definition of an allowed file shape for real-capture ingest.

    extension: lowercase file extension including dot (e.g. ".jpg")
    max_file_size_bytes: upper bound on file size
    min_width_px: minimum image width
    min_height_px: minimum image height
    max_width_px: maximum image width
    max_height_px: maximum image height
    """
    extension: str
    max_file_size_bytes: int
    min_width_px: int = 320
    min_height_px: int = 240
    max_width_px: int = 12000
    max_height_px: int = 12000

    def matches(self, file_ext: str, file_size: int, width: int, height: int) -> bool:
        """Check if a candidate file matches this shape."""
        if file_ext.lower() != self.extension:
            return False
        if file_size > self.max_file_size_bytes:
            return False
        if width < self.min_width_px or height < self.min_height_px:
            return False
        if width > self.max_width_px or height > self.max_height_px:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extension": self.extension,
            "max_file_size_bytes": self.max_file_size_bytes,
            "min_resolution": f"{self.min_width_px}x{self.min_height_px}",
            "max_resolution": f"{self.max_width_px}x{self.max_height_px}",
        }


# ════════════════════════════════════════════════════════════
# CAPTURE ASSUMPTION — environment constraints
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CaptureAssumption:
    """
    Bounded capture-environment assumptions for an ingest case.

    name: short identifier
    description: what the assumption constrains
    required: whether violation rejects the capture outright
    """
    name: str
    description: str
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


# ════════════════════════════════════════════════════════════
# INGEST VERDICT
# ════════════════════════════════════════════════════════════

class IngestVerdict(str, Enum):
    """Result of validating a capture file against the ingest profile."""
    ACCEPTED = "ACCEPTED"
    REJECTED_NO_MATCHING_CASE = "REJECTED_NO_MATCHING_CASE"
    REJECTED_MISSING_METADATA = "REJECTED_MISSING_METADATA"
    REJECTED_SHAPE_MISMATCH = "REJECTED_SHAPE_MISMATCH"
    REJECTED_ASSUMPTION_VIOLATED = "REJECTED_ASSUMPTION_VIOLATED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# INGEST RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class IngestResult:
    """Full result of ingest validation."""
    verdict: IngestVerdict = IngestVerdict.ERROR
    matched_case_name: str = ""
    evidence_tier_entry: str = ""
    rejection_reason: str = ""
    metadata_present: List[str] = field(default_factory=list)
    metadata_missing: List[str] = field(default_factory=list)
    assumptions_checked: int = 0
    assumptions_passed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "matched_case_name": self.matched_case_name,
            "evidence_tier_entry": self.evidence_tier_entry,
            "rejection_reason": self.rejection_reason,
            "metadata_present": self.metadata_present,
            "metadata_missing": self.metadata_missing,
            "assumptions_checked": self.assumptions_checked,
            "assumptions_passed": self.assumptions_passed,
        }


# ════════════════════════════════════════════════════════════
# CAPTURE INGEST CASE — one supported ingest path
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CaptureIngestCase:
    """
    One frozen supported real-capture ingest case.

    name: unique identifier for this case
    description: what kind of capture this case handles
    file_shape: allowed file properties
    required_metadata: metadata fields that must be present
    optional_metadata: metadata fields that are nice to have
    assumptions: capture-environment constraints
    evidence_tier_entry: the EvidenceTier value this capture enters at
    """
    name: str
    description: str
    file_shape: CaptureFileShape
    required_metadata: Tuple[str, ...] = ()
    optional_metadata: Tuple[str, ...] = ()
    assumptions: Tuple[CaptureAssumption, ...] = ()
    evidence_tier_entry: str = "real-capture"

    def validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Return (present, missing) required metadata fields."""
        present = [f for f in self.required_metadata if f in metadata]
        missing = [f for f in self.required_metadata if f not in metadata]
        return present, missing

    def check_assumptions(self, metadata: Dict[str, Any]) -> Tuple[int, int, str]:
        """
        Check assumptions against metadata.
        Returns (checked, passed, first_violation_reason).
        Assumptions are checked by looking for a metadata key matching
        the assumption name with a truthy value.
        """
        checked = 0
        passed = 0
        first_violation = ""
        for assumption in self.assumptions:
            checked += 1
            value = metadata.get(assumption.name)
            if value:
                passed += 1
            elif assumption.required and not first_violation:
                first_violation = f"Required assumption '{assumption.name}' not satisfied: {assumption.description}"
        return checked, passed, first_violation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "file_shape": self.file_shape.to_dict(),
            "required_metadata": list(self.required_metadata),
            "optional_metadata": list(self.optional_metadata),
            "assumptions": [a.to_dict() for a in self.assumptions],
            "evidence_tier_entry": self.evidence_tier_entry,
        }


# ════════════════════════════════════════════════════════════
# INGEST PROFILE — frozen family of supported cases
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IngestProfile:
    """
    Frozen profile of all supported real-capture ingest cases.

    version: profile version string
    frozen: always True for V1
    cases: tuple of CaptureIngestCase records
    """
    version: str = INGEST_PROFILE_VERSION
    frozen: bool = True
    cases: Tuple[CaptureIngestCase, ...] = ()

    def find_matching_case(
        self,
        file_ext: str,
        file_size: int,
        width: int,
        height: int,
    ) -> Optional[CaptureIngestCase]:
        """Find first case whose file shape matches the candidate."""
        for case in self.cases:
            if case.file_shape.matches(file_ext, file_size, width, height):
                return case
        return None

    def case_names(self) -> List[str]:
        return [c.name for c in self.cases]

    def profile_hash(self) -> str:
        """Deterministic hash of the profile content."""
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "frozen": self.frozen,
            "case_count": len(self.cases),
            "cases": [c.to_dict() for c in self.cases],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ════════════════════════════════════════════════════════════
# VALIDATE CAPTURE FILE
# ════════════════════════════════════════════════════════════

def validate_capture_file(
    file_ext: str,
    file_size: int,
    width: int,
    height: int,
    metadata: Dict[str, Any],
    profile: Optional[IngestProfile] = None,
) -> IngestResult:
    """
    Validate a candidate capture file against the ingest profile.

    Parameters:
        file_ext: file extension including dot (e.g. ".jpg")
        file_size: file size in bytes
        width: image width in pixels
        height: image height in pixels
        metadata: dict of metadata fields present
        profile: ingest profile to validate against (default: V1_INGEST_PROFILE)

    Returns IngestResult with verdict and details.
    """
    if profile is None:
        profile = V1_INGEST_PROFILE

    result = IngestResult()

    # Find matching case by file shape
    case = profile.find_matching_case(file_ext, file_size, width, height)
    if case is None:
        result.verdict = IngestVerdict.REJECTED_NO_MATCHING_CASE
        result.rejection_reason = (
            f"No ingest case matches file_ext={file_ext}, "
            f"size={file_size}, resolution={width}x{height}"
        )
        return result

    result.matched_case_name = case.name
    result.evidence_tier_entry = case.evidence_tier_entry

    # Check required metadata
    present, missing = case.validate_metadata(metadata)
    result.metadata_present = present
    result.metadata_missing = missing

    if missing:
        result.verdict = IngestVerdict.REJECTED_MISSING_METADATA
        result.rejection_reason = f"Missing required metadata: {', '.join(missing)}"
        return result

    # Check assumptions
    checked, passed, violation = case.check_assumptions(metadata)
    result.assumptions_checked = checked
    result.assumptions_passed = passed

    if violation:
        result.verdict = IngestVerdict.REJECTED_ASSUMPTION_VIOLATED
        result.rejection_reason = violation
        return result

    result.verdict = IngestVerdict.ACCEPTED
    return result


def make_rejected_result(reason: str) -> IngestResult:
    """Create a rejected result for testing/error paths."""
    return IngestResult(
        verdict=IngestVerdict.ERROR,
        rejection_reason=reason,
    )


# ════════════════════════════════════════════════════════════
# FROZEN V1 INGEST CASES
# ════════════════════════════════════════════════════════════

# Common assumptions for phone captures
_PHONE_CAPTURE_ASSUMPTIONS = (
    CaptureAssumption(
        name="adequate_lighting",
        description="Subject lit well enough for feature extraction (no deep shadow / extreme backlight)",
        required=True,
    ),
    CaptureAssumption(
        name="stable_orientation",
        description="Capture taken without excessive motion blur (handheld acceptable, mid-swing not)",
        required=True,
    ),
    CaptureAssumption(
        name="subject_in_frame",
        description="The target artifact/page is fully visible within the frame",
        required=True,
    ),
)

# Case 1: Phone photo (JPEG)
CASE_PHONE_JPEG = CaptureIngestCase(
    name="phone_jpeg",
    description="Standard phone photo of a printed Aurexis artifact or page, JPEG format",
    file_shape=CaptureFileShape(
        extension=".jpg",
        max_file_size_bytes=50_000_000,  # 50MB
        min_width_px=640,
        min_height_px=480,
        max_width_px=12000,
        max_height_px=12000,
    ),
    required_metadata=("capture_device", "capture_timestamp"),
    optional_metadata=("focal_length_mm", "sensor_noise_level", "lens_distortion", "capture_distance_m", "gps_lat", "gps_lon"),
    assumptions=_PHONE_CAPTURE_ASSUMPTIONS,
    evidence_tier_entry="real-capture",
)

# Case 2: Phone photo (PNG)
CASE_PHONE_PNG = CaptureIngestCase(
    name="phone_png",
    description="Phone photo of a printed Aurexis artifact or page, PNG format (lossless)",
    file_shape=CaptureFileShape(
        extension=".png",
        max_file_size_bytes=100_000_000,  # 100MB
        min_width_px=640,
        min_height_px=480,
        max_width_px=12000,
        max_height_px=12000,
    ),
    required_metadata=("capture_device", "capture_timestamp"),
    optional_metadata=("focal_length_mm", "sensor_noise_level", "lens_distortion", "capture_distance_m"),
    assumptions=_PHONE_CAPTURE_ASSUMPTIONS,
    evidence_tier_entry="real-capture",
)

# Case 3: Webcam frame (JPEG)
CASE_WEBCAM_JPEG = CaptureIngestCase(
    name="webcam_jpeg",
    description="Single frame from webcam or USB camera, JPEG format",
    file_shape=CaptureFileShape(
        extension=".jpg",
        max_file_size_bytes=20_000_000,  # 20MB
        min_width_px=320,
        min_height_px=240,
        max_width_px=4096,
        max_height_px=4096,
    ),
    required_metadata=("capture_device", "capture_timestamp"),
    optional_metadata=("resolution_megapixels", "frame_index"),
    assumptions=(
        CaptureAssumption(
            name="adequate_lighting",
            description="Subject lit well enough for feature extraction",
            required=True,
        ),
        CaptureAssumption(
            name="subject_in_frame",
            description="Target artifact visible within frame",
            required=True,
        ),
    ),
    evidence_tier_entry="real-capture",
)

# Case 4: Video frame extract (PNG)
CASE_VIDEO_FRAME_PNG = CaptureIngestCase(
    name="video_frame_png",
    description="Extracted frame from video capture of Aurexis artifact, PNG format",
    file_shape=CaptureFileShape(
        extension=".png",
        max_file_size_bytes=50_000_000,
        min_width_px=320,
        min_height_px=240,
        max_width_px=8192,
        max_height_px=8192,
    ),
    required_metadata=("capture_device", "capture_timestamp", "source_video", "frame_index"),
    optional_metadata=("video_fps", "video_codec"),
    assumptions=(
        CaptureAssumption(
            name="adequate_lighting",
            description="Subject lit well enough for feature extraction",
            required=True,
        ),
        CaptureAssumption(
            name="stable_orientation",
            description="Frame not excessively blurred from camera motion",
            required=True,
        ),
        CaptureAssumption(
            name="subject_in_frame",
            description="Target artifact visible within frame",
            required=True,
        ),
    ),
    evidence_tier_entry="real-capture",
)

# Case 5: Scanner output (TIFF)
CASE_SCANNER_TIFF = CaptureIngestCase(
    name="scanner_tiff",
    description="Flatbed scanner output of a printed Aurexis artifact, TIFF format",
    file_shape=CaptureFileShape(
        extension=".tif",
        max_file_size_bytes=200_000_000,  # 200MB
        min_width_px=600,
        min_height_px=600,
        max_width_px=12000,
        max_height_px=12000,
    ),
    required_metadata=("capture_device", "capture_timestamp", "scan_dpi"),
    optional_metadata=("color_depth",),
    assumptions=(
        CaptureAssumption(
            name="flat_placement",
            description="Artifact placed flat on scanner bed without wrinkles or folds",
            required=True,
        ),
        CaptureAssumption(
            name="adequate_lighting",
            description="Scanner provides controlled illumination",
            required=False,  # scanner has its own light
        ),
    ),
    evidence_tier_entry="real-capture",
)


# ════════════════════════════════════════════════════════════
# FROZEN V1 INGEST PROFILE SINGLETON
# ════════════════════════════════════════════════════════════

FROZEN_CASES = (
    CASE_PHONE_JPEG,
    CASE_PHONE_PNG,
    CASE_WEBCAM_JPEG,
    CASE_VIDEO_FRAME_PNG,
    CASE_SCANNER_TIFF,
)

V1_INGEST_PROFILE = IngestProfile(
    version=INGEST_PROFILE_VERSION,
    frozen=True,
    cases=FROZEN_CASES,
)


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_CASE_COUNT = 5
EXPECTED_REQUIRED_METADATA_FIELDS = ("capture_device", "capture_timestamp")
EXPECTED_EVIDENCE_TIER_ENTRY = "real-capture"
EXPECTED_ASSUMPTION_NAMES = (
    "adequate_lighting",
    "stable_orientation",
    "subject_in_frame",
    "flat_placement",
)
