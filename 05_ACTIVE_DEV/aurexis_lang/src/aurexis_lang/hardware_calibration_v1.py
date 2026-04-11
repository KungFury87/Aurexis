"""
Aurexis Core — Hardware Calibration Law V1 (FROZEN)

Formal relationship between camera hardware properties and extraction
confidence. Caps raw confidence against hardware-derived ceiling.
Raw confidence from CV extraction may still be heuristic; calibration
bounds it against what the hardware can physically support.

V1 calibration defines:
  1. CameraProfile: resolution, focal length, sensor noise level, lens distortion
  2. CalibrationLaw: frozen thresholds mapping hardware properties to confidence
  3. calibrate_confidence(): compute confidence from hardware + extraction data
  4. CalibrationResult: full calibration output with diagnostics
  5. CalibrationRegistry: manage multiple camera profiles

The key insight: a POINT detected at 0.92 confidence by a 720p camera
at 2 meters is NOT the same quality as 0.92 from a 4K camera at 0.5m.
Hardware calibration normalizes confidence to a law-bearing measurement.

Calibration factors:
  - Resolution factor: higher resolution → higher confidence ceiling
  - Distance factor: closer → higher confidence
  - Noise factor: lower noise → higher confidence
  - Distortion factor: less distortion → higher confidence

These factors multiply to produce a hardware_confidence_ceiling.
The final calibrated confidence is:
  min(raw_confidence, hardware_confidence_ceiling)

This means a bad camera CAPS your confidence — it cannot inflate it.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import math


# ════════════════════════════════════════════════════════════
# CALIBRATION VERSION
# ════════════════════════════════════════════════════════════

CALIBRATION_VERSION = "V1.0"
CALIBRATION_FROZEN = True


# ════════════════════════════════════════════════════════════
# CAMERA PROFILE — describes hardware properties
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CameraProfile:
    """
    Hardware properties of a camera used for visual program extraction.

    resolution_megapixels: sensor resolution (e.g. 12.0 for a 12MP camera)
    focal_length_mm: lens focal length in mm (e.g. 26.0 for wide-angle phone)
    sensor_noise_level: normalized noise 0.0 (perfect) to 1.0 (unusable)
    lens_distortion: normalized distortion 0.0 (none) to 1.0 (extreme)
    capture_distance_m: distance from subject in meters
    name: human-readable identifier
    """
    name: str = "unknown"
    resolution_megapixels: float = 12.0
    focal_length_mm: float = 26.0
    sensor_noise_level: float = 0.1
    lens_distortion: float = 0.05
    capture_distance_m: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "resolution_megapixels": self.resolution_megapixels,
            "focal_length_mm": self.focal_length_mm,
            "sensor_noise_level": self.sensor_noise_level,
            "lens_distortion": self.lens_distortion,
            "capture_distance_m": self.capture_distance_m,
        }


# ════════════════════════════════════════════════════════════
# CALIBRATION LAW — frozen thresholds
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CalibrationLaw:
    """
    Frozen thresholds for hardware-to-confidence mapping.

    These define how hardware properties translate to confidence ceilings.
    """
    # Resolution: baseline is 2MP. Each doubling adds 0.1 to ceiling.
    resolution_baseline_mp: float = 2.0
    resolution_factor_per_doubling: float = 0.1
    resolution_max_bonus: float = 0.3

    # Distance: baseline is 1.0m. Closer = better, farther = worse.
    distance_baseline_m: float = 1.0
    distance_decay_rate: float = 0.15  # ceiling drops per meter beyond baseline

    # Noise: direct confidence penalty
    noise_penalty_factor: float = 0.5  # noise_level * factor = penalty

    # Distortion: direct confidence penalty
    distortion_penalty_factor: float = 0.3  # distortion * factor = penalty

    # Floor: minimum confidence ceiling (even terrible hardware gets this)
    confidence_floor: float = 0.1

    # Perfect hardware ceiling
    confidence_ceiling_max: float = 1.0

    # Calibration is deterministic
    version: str = CALIBRATION_VERSION


V1_CALIBRATION_LAW = CalibrationLaw()


# ════════════════════════════════════════════════════════════
# CALIBRATION FACTORS — individual hardware contributions
# ════════════════════════════════════════════════════════════

@dataclass
class CalibrationFactors:
    """Breakdown of how each hardware property contributes."""
    resolution_bonus: float = 0.0
    distance_penalty: float = 0.0
    noise_penalty: float = 0.0
    distortion_penalty: float = 0.0
    hardware_ceiling: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolution_bonus": round(self.resolution_bonus, 6),
            "distance_penalty": round(self.distance_penalty, 6),
            "noise_penalty": round(self.noise_penalty, 6),
            "distortion_penalty": round(self.distortion_penalty, 6),
            "hardware_ceiling": round(self.hardware_ceiling, 6),
        }


# ════════════════════════════════════════════════════════════
# CALIBRATION VERDICT
# ════════════════════════════════════════════════════════════

class CalibrationVerdict(str, Enum):
    """Result of calibration."""
    CALIBRATED = "CALIBRATED"          # Confidence was adjusted by hardware
    UNCAPPED = "UNCAPPED"              # Raw confidence was below hardware ceiling (no cap applied)
    DEGRADED = "DEGRADED"              # Hardware significantly limited confidence
    INVALID_PROFILE = "INVALID_PROFILE"  # Camera profile has invalid values


# ════════════════════════════════════════════════════════════
# CALIBRATION RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CalibrationResult:
    """Complete result of hardware calibration."""
    verdict: CalibrationVerdict = CalibrationVerdict.INVALID_PROFILE
    raw_confidence: float = 0.0
    calibrated_confidence: float = 0.0
    hardware_ceiling: float = 0.0
    factors: Optional[CalibrationFactors] = None
    camera_profile: Optional[CameraProfile] = None
    was_capped: bool = False
    confidence_delta: float = 0.0  # calibrated - raw (negative if capped)
    calibration_version: str = CALIBRATION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "raw_confidence": round(self.raw_confidence, 6),
            "calibrated_confidence": round(self.calibrated_confidence, 6),
            "hardware_ceiling": round(self.hardware_ceiling, 6),
            "was_capped": self.was_capped,
            "confidence_delta": round(self.confidence_delta, 6),
            "factors": self.factors.to_dict() if self.factors else None,
            "camera_profile": self.camera_profile.to_dict() if self.camera_profile else None,
            "calibration_version": self.calibration_version,
        }


# ════════════════════════════════════════════════════════════
# COMPUTE CALIBRATION FACTORS
# ════════════════════════════════════════════════════════════

def compute_factors(
    profile: CameraProfile,
    law: CalibrationLaw = V1_CALIBRATION_LAW,
) -> CalibrationFactors:
    """
    Compute individual calibration factors from a camera profile.

    Returns a CalibrationFactors with the hardware ceiling.
    """
    factors = CalibrationFactors()

    # Resolution bonus: log2(resolution / baseline) * factor_per_doubling, capped
    if profile.resolution_megapixels > 0 and law.resolution_baseline_mp > 0:
        doublings = math.log2(
            max(profile.resolution_megapixels, 0.1) / law.resolution_baseline_mp
        )
        factors.resolution_bonus = min(
            max(doublings * law.resolution_factor_per_doubling, 0.0),
            law.resolution_max_bonus,
        )

    # Distance penalty: max(0, (distance - baseline) * decay_rate)
    if profile.capture_distance_m > law.distance_baseline_m:
        factors.distance_penalty = (
            (profile.capture_distance_m - law.distance_baseline_m)
            * law.distance_decay_rate
        )

    # Noise penalty
    factors.noise_penalty = (
        max(0.0, min(1.0, profile.sensor_noise_level))
        * law.noise_penalty_factor
    )

    # Distortion penalty
    factors.distortion_penalty = (
        max(0.0, min(1.0, profile.lens_distortion))
        * law.distortion_penalty_factor
    )

    # Compute ceiling
    ceiling = (
        law.confidence_ceiling_max
        + factors.resolution_bonus
        - factors.distance_penalty
        - factors.noise_penalty
        - factors.distortion_penalty
    )

    factors.hardware_ceiling = max(law.confidence_floor, min(1.0, ceiling))

    return factors


# ════════════════════════════════════════════════════════════
# CALIBRATE CONFIDENCE
# ════════════════════════════════════════════════════════════

def calibrate_confidence(
    raw_confidence: float,
    profile: CameraProfile,
    law: CalibrationLaw = V1_CALIBRATION_LAW,
) -> CalibrationResult:
    """
    Calibrate a raw confidence value against hardware properties.

    The hardware ceiling caps confidence — bad hardware cannot produce
    high-confidence readings. Good hardware leaves confidence unchanged.

    Parameters:
        raw_confidence: The extraction confidence (0.0 to 1.0)
        profile: Camera hardware properties
        law: Calibration law thresholds

    Returns a CalibrationResult.
    """
    result = CalibrationResult(
        raw_confidence=max(0.0, min(1.0, raw_confidence)),
        camera_profile=profile,
    )

    # Validate profile
    if profile.resolution_megapixels <= 0:
        result.verdict = CalibrationVerdict.INVALID_PROFILE
        return result
    if profile.capture_distance_m < 0:
        result.verdict = CalibrationVerdict.INVALID_PROFILE
        return result

    # Compute factors
    factors = compute_factors(profile, law)
    result.factors = factors
    result.hardware_ceiling = factors.hardware_ceiling

    # Apply ceiling
    calibrated = min(result.raw_confidence, factors.hardware_ceiling)
    result.calibrated_confidence = calibrated
    result.was_capped = result.raw_confidence > factors.hardware_ceiling
    result.confidence_delta = calibrated - result.raw_confidence

    # Determine verdict
    if result.was_capped:
        if factors.hardware_ceiling < 0.5:
            result.verdict = CalibrationVerdict.DEGRADED
        else:
            result.verdict = CalibrationVerdict.CALIBRATED
    else:
        result.verdict = CalibrationVerdict.UNCAPPED

    return result


# ════════════════════════════════════════════════════════════
# CALIBRATE FRAME — apply to all primitives in a frame
# ════════════════════════════════════════════════════════════

def calibrate_frame(
    raw_primitives: List[Dict[str, Any]],
    profile: CameraProfile,
    law: CalibrationLaw = V1_CALIBRATION_LAW,
) -> Dict[str, Any]:
    """
    Calibrate all primitives in a raw frame against hardware.

    Returns a dict with:
    - calibrated_primitives: list of primitives with adjusted confidence
    - calibration_results: per-primitive calibration details
    - frame_summary: aggregate statistics
    """
    calibrated_prims = []
    cal_results = []
    total_capped = 0

    for prim_dict in raw_primitives:
        raw_conf = prim_dict.get("confidence", 1.0)
        cr = calibrate_confidence(raw_conf, profile, law)
        cal_results.append(cr)

        # Build calibrated primitive dict
        cal_prim = dict(prim_dict)
        cal_prim["confidence"] = cr.calibrated_confidence
        cal_prim["_calibration"] = {
            "raw_confidence": cr.raw_confidence,
            "hardware_ceiling": cr.hardware_ceiling,
            "was_capped": cr.was_capped,
        }
        calibrated_prims.append(cal_prim)

        if cr.was_capped:
            total_capped += 1

    return {
        "calibrated_primitives": calibrated_prims,
        "calibration_results": [cr.to_dict() for cr in cal_results],
        "frame_summary": {
            "total_primitives": len(raw_primitives),
            "capped_count": total_capped,
            "uncapped_count": len(raw_primitives) - total_capped,
            "hardware_ceiling": compute_factors(profile, law).hardware_ceiling,
            "camera_profile": profile.to_dict(),
        },
    }


# ════════════════════════════════════════════════════════════
# CALIBRATION REGISTRY — manage camera profiles
# ════════════════════════════════════════════════════════════

class CalibrationRegistry:
    """
    Registry of known camera profiles.
    Supports lookup by name and calibration against registered profiles.
    """

    def __init__(self):
        self._profiles: Dict[str, CameraProfile] = {}
        # Register built-in profiles
        for profile in BUILTIN_PROFILES:
            self._profiles[profile.name] = profile

    def register(self, profile: CameraProfile) -> bool:
        """Register a profile. Returns False if name taken."""
        if profile.name in self._profiles:
            return False
        self._profiles[profile.name] = profile
        return True

    def get(self, name: str) -> Optional[CameraProfile]:
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        return sorted(self._profiles.keys())

    def calibrate(
        self,
        raw_confidence: float,
        profile_name: str,
        law: CalibrationLaw = V1_CALIBRATION_LAW,
    ) -> CalibrationResult:
        """Calibrate using a registered profile by name."""
        profile = self._profiles.get(profile_name)
        if profile is None:
            result = CalibrationResult(raw_confidence=raw_confidence)
            result.verdict = CalibrationVerdict.INVALID_PROFILE
            return result
        return calibrate_confidence(raw_confidence, profile, law)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_count": len(self._profiles),
            "profiles": {
                name: p.to_dict()
                for name, p in sorted(self._profiles.items())
            },
        }


# ════════════════════════════════════════════════════════════
# BUILT-IN CAMERA PROFILES
# ════════════════════════════════════════════════════════════

BUILTIN_PROFILES = [
    CameraProfile(
        name="ideal",
        resolution_megapixels=48.0,
        focal_length_mm=26.0,
        sensor_noise_level=0.02,
        lens_distortion=0.01,
        capture_distance_m=0.3,
    ),
    CameraProfile(
        name="modern_phone",
        resolution_megapixels=12.0,
        focal_length_mm=26.0,
        sensor_noise_level=0.08,
        lens_distortion=0.05,
        capture_distance_m=0.5,
    ),
    CameraProfile(
        name="old_phone",
        resolution_megapixels=2.0,
        focal_length_mm=28.0,
        sensor_noise_level=0.25,
        lens_distortion=0.15,
        capture_distance_m=0.5,
    ),
    CameraProfile(
        name="webcam",
        resolution_megapixels=1.0,
        focal_length_mm=30.0,
        sensor_noise_level=0.3,
        lens_distortion=0.2,
        capture_distance_m=1.0,
    ),
    CameraProfile(
        name="distant_dslr",
        resolution_megapixels=24.0,
        focal_length_mm=50.0,
        sensor_noise_level=0.05,
        lens_distortion=0.02,
        capture_distance_m=5.0,
    ),
]
