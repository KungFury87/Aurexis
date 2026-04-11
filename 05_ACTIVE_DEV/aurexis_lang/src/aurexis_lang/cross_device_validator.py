"""
cross_device_validator.py — Cross-Device Evidence Validation

Gate 5 expansion capability: when observations from multiple different
cameras (different devices, different optics) agree, the resulting
evidence is stronger than any single-device observation alone.

This module is a Gate 5 proof-of-concept:
  - It EXTENDS the Aurexis pipeline with a genuinely new capability
  - It does NOT modify any Core Law module
  - It plugs into the existing evidence tier and phoxel schema
  - Cross-device agreement strengthens evidence without changing the rules

The key insight: if a Samsung S23 Ultra and an LG LM-V600 both observe
similar primitive distributions in similar scenes, that cross-device
agreement is a new kind of evidence that the existing law already supports
(Core Law Section 4 requires multi_frame_consistent — cross-device
consistency is a stronger form of multi-frame consistency).

Design decisions:
  1. Cross-device agreement is measured by comparing per-device
     primitive distributions (type frequency, confidence distributions).
  2. Agreement score ∈ [0, 1]. Higher = more consistent across devices.
  3. This does NOT create a new evidence tier — it enriches REAL_CAPTURE
     and EARNED evidence with a cross_device_agreement field.
  4. The phoxel record is NOT modified — the cross-device result lives
     alongside it in the pipeline result, not inside the schema.

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

import numpy as np

from .evidence_tiers import EvidenceTier


# ────────────────────────────────────────────────────────────
# Types
# ────────────────────────────────────────────────────────────

class DeviceProfile:
    """Aggregated statistics for one device across all its files."""

    def __init__(self, device_id: str, make: str, model: str):
        self.device_id = device_id
        self.make = make
        self.model = model
        self.file_count = 0
        self.total_frames = 0
        self.total_primitives = 0
        self.confidence_values: List[float] = []
        self.primitive_counts: List[int] = []
        self.lenses_seen: set = set()
        self.core_law_compliance_rates: List[float] = []

    @property
    def mean_confidence(self) -> float:
        return float(np.mean(self.confidence_values)) if self.confidence_values else 0.0

    @property
    def mean_primitives_per_frame(self) -> float:
        return self.total_primitives / self.total_frames if self.total_frames > 0 else 0.0

    @property
    def mean_law_compliance(self) -> float:
        return float(np.mean(self.core_law_compliance_rates)) if self.core_law_compliance_rates else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_id': self.device_id,
            'make': self.make,
            'model': self.model,
            'file_count': self.file_count,
            'total_frames': self.total_frames,
            'total_primitives': self.total_primitives,
            'mean_confidence': self.mean_confidence,
            'mean_primitives_per_frame': self.mean_primitives_per_frame,
            'mean_law_compliance': self.mean_law_compliance,
            'lenses_seen': sorted(self.lenses_seen),
        }


class CrossDeviceResult:
    """Result of comparing two device profiles."""

    def __init__(
        self,
        device_a: str,
        device_b: str,
        agreement_score: float,
        confidence_delta: float,
        primitive_density_delta: float,
        law_compliance_delta: float,
        details: Dict[str, Any],
    ):
        self.device_a = device_a
        self.device_b = device_b
        self.agreement_score = agreement_score
        self.confidence_delta = confidence_delta
        self.primitive_density_delta = primitive_density_delta
        self.law_compliance_delta = law_compliance_delta
        self.details = details

    @property
    def devices_agree(self) -> bool:
        """True if the agreement score is above the minimum threshold."""
        return self.agreement_score >= 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            'device_a': self.device_a,
            'device_b': self.device_b,
            'agreement_score': self.agreement_score,
            'devices_agree': self.devices_agree,
            'confidence_delta': self.confidence_delta,
            'primitive_density_delta': self.primitive_density_delta,
            'law_compliance_delta': self.law_compliance_delta,
            'details': self.details,
        }


# ────────────────────────────────────────────────────────────
# Profile builder
# ────────────────────────────────────────────────────────────

def build_device_profiles(
    file_results: List[Dict[str, Any]],
) -> Dict[str, DeviceProfile]:
    """
    Group file results by device model and build aggregated profiles.
    Only includes files with status='ok'.
    """
    profiles: Dict[str, DeviceProfile] = {}

    for result in file_results:
        if result.get('status') != 'ok':
            continue

        meta = result.get('camera_metadata') or {}
        model = meta.get('model', 'unknown')
        make = meta.get('make', 'unknown')
        device_id = f'{make}_{model}'.replace(' ', '_')

        if device_id not in profiles:
            profiles[device_id] = DeviceProfile(device_id, make, model)

        p = profiles[device_id]
        p.file_count += 1
        p.total_frames += result.get('frames_processed', 0)

        # Primitives
        prims = result.get('primitives', {})
        total_prims = prims.get('total', 0)
        p.total_primitives += total_prims
        p.primitive_counts.append(total_prims)

        # Confidence
        conf = result.get('confidence', {})
        mean_conf = conf.get('mean', 0.0)
        if mean_conf > 0:
            p.confidence_values.append(mean_conf)

        # Law compliance
        law = result.get('core_law', {})
        law_rate = law.get('compliance_rate', 0.0)
        p.core_law_compliance_rates.append(law_rate)

        # Lenses
        lens = meta.get('lens_id')
        if lens:
            p.lenses_seen.add(lens)

    return profiles


# ────────────────────────────────────────────────────────────
# Cross-device comparison
# ────────────────────────────────────────────────────────────

def compare_device_pair(
    profile_a: DeviceProfile,
    profile_b: DeviceProfile,
) -> CrossDeviceResult:
    """
    Compare two device profiles and compute an agreement score.

    The agreement score is based on:
      1. Confidence similarity (how close are mean confidences?)
      2. Primitive density similarity (similar extraction rates?)
      3. Law compliance similarity (both obey the law equally?)

    Score = 1.0 means perfect agreement. Score = 0.0 means completely
    different behavior. Threshold for "agree" is 0.5.

    This is intentionally simple for Gate 5. The important thing is
    that cross-device validation WORKS within the existing law, not
    that the comparison algorithm is optimal.
    """
    # Delta metrics
    conf_delta = abs(profile_a.mean_confidence - profile_b.mean_confidence)
    density_a = profile_a.mean_primitives_per_frame
    density_b = profile_b.mean_primitives_per_frame
    density_delta = abs(density_a - density_b)
    law_delta = abs(profile_a.mean_law_compliance - profile_b.mean_law_compliance)

    # Normalize deltas to [0, 1] scores (1 = identical, 0 = very different)
    # Confidence: delta of 0.0 → 1.0, delta of 0.5 → 0.0
    conf_score = max(0.0, 1.0 - (conf_delta / 0.5))

    # Primitive density: delta of 0 → 1.0, delta of 20 → 0.0
    density_score = max(0.0, 1.0 - (density_delta / 20.0))

    # Law compliance: delta of 0 → 1.0, delta of 0.5 → 0.0
    law_score = max(0.0, 1.0 - (law_delta / 0.5))

    # Weighted agreement (confidence is most important for evidence quality)
    agreement = (
        0.4 * conf_score +
        0.3 * density_score +
        0.3 * law_score
    )

    details = {
        'confidence_score': conf_score,
        'density_score': density_score,
        'law_score': law_score,
        'device_a_stats': {
            'mean_confidence': profile_a.mean_confidence,
            'mean_density': density_a,
            'mean_law_compliance': profile_a.mean_law_compliance,
            'file_count': profile_a.file_count,
        },
        'device_b_stats': {
            'mean_confidence': profile_b.mean_confidence,
            'mean_density': density_b,
            'mean_law_compliance': profile_b.mean_law_compliance,
            'file_count': profile_b.file_count,
        },
    }

    return CrossDeviceResult(
        device_a=profile_a.device_id,
        device_b=profile_b.device_id,
        agreement_score=agreement,
        confidence_delta=conf_delta,
        primitive_density_delta=density_delta,
        law_compliance_delta=law_delta,
        details=details,
    )


# ────────────────────────────────────────────────────────────
# Full cross-device validation
# ────────────────────────────────────────────────────────────

def validate_cross_device_evidence(
    file_results: List[Dict[str, Any]],
    min_files_per_device: int = 3,
) -> Dict[str, Any]:
    """
    Run cross-device validation across all devices in the batch results.

    Returns:
      devices: dict of device profiles
      comparisons: list of pairwise comparison results
      cross_device_consistent: bool — True if at least one device pair agrees
      best_agreement_score: float
      new_evidence_produced: bool — True if cross-device evidence was generated
    """
    profiles = build_device_profiles(file_results)

    # Filter to devices with enough data
    qualified = {
        k: v for k, v in profiles.items()
        if v.file_count >= min_files_per_device
    }

    if len(qualified) < 2:
        return {
            'devices': {k: v.to_dict() for k, v in profiles.items()},
            'qualified_devices': list(qualified.keys()),
            'comparisons': [],
            'cross_device_consistent': False,
            'best_agreement_score': 0.0,
            'new_evidence_produced': False,
            'reason': f'need >= 2 devices with >= {min_files_per_device} files each, '
                      f'found {len(qualified)} qualified device(s)',
        }

    # Pairwise comparisons
    device_ids = sorted(qualified.keys())
    comparisons: List[CrossDeviceResult] = []

    for i in range(len(device_ids)):
        for j in range(i + 1, len(device_ids)):
            result = compare_device_pair(
                qualified[device_ids[i]],
                qualified[device_ids[j]],
            )
            comparisons.append(result)

    best_score = max(c.agreement_score for c in comparisons) if comparisons else 0.0
    any_agree = any(c.devices_agree for c in comparisons)

    return {
        'devices': {k: v.to_dict() for k, v in profiles.items()},
        'qualified_devices': device_ids,
        'comparisons': [c.to_dict() for c in comparisons],
        'cross_device_consistent': any_agree,
        'best_agreement_score': best_score,
        'new_evidence_produced': True,
        'evidence_type': 'cross_device_agreement',
        'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
        'note': (
            'Cross-device validation extends the pipeline without modifying Core Law. '
            'Agreement between independent devices strengthens evidence quality.'
        ),
    }
