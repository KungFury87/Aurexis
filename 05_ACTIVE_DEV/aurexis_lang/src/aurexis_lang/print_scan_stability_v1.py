"""
Aurexis Core — Print/Scan Stability V1 (FROZEN)

Proves that a V1 visual program survives physical-world degradation
(print → photograph → re-extract) and produces the same verdict.

The physical world introduces:
  - Spatial jitter: bounding boxes shift by a few pixels
  - Scale change: the entire image is slightly larger/smaller
  - Rotation: slight angle tilt
  - Noise: confidence values change as extraction quality varies
  - Resolution change: pixel dimensions differ

V1 stability means: the VERDICT (PASS/FAIL) is unchanged despite
degradation, because the law thresholds have enough margin.

This module defines:
  1. StabilityContract — frozen bounds for tolerable degradation
  2. Degradation functions — deterministic transformations of primitives
  3. StabilityProof — the result of testing a program against degradation
  4. prove_stability() — run a program through multiple degradation levels

CRITICAL: The degradation functions are DETERMINISTIC given a seed.
Same seed → same degradation → same result. This is testable, not random.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, BoundingBox, VisualPrimitive,
    GrammarLaw, V1_LAW, ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import (
    execute_image_as_program, ProgramVerdict, ExecutionResult,
)
from aurexis_lang.visual_parser_v1 import primitive_to_dict


# ════════════════════════════════════════════════════════════
# STABILITY CONTRACT — frozen bounds
# ════════════════════════════════════════════════════════════

STABILITY_VERSION = "V1.0"
STABILITY_FROZEN = True


@dataclass(frozen=True)
class StabilityContract:
    """
    Frozen bounds for tolerable print/scan degradation.

    These values define the maximum degradation a V1 program
    can survive while preserving its verdict. Derived from
    the V1 law thresholds:

    - ADJACENT threshold = 30px → programs with measured_value
      well below 30 survive jitter up to (30 - measured_value)
    - CONTAINS threshold = 0px → programs with positive margin
      survive jitter up to the minimum margin
    """
    # Maximum spatial jitter per axis (pixels)
    max_jitter_px: float = 10.0

    # Maximum uniform scale change (as fraction: 1.0 = no change)
    max_scale_low: float = 0.85     # 15% shrink
    max_scale_high: float = 1.15    # 15% grow

    # Maximum confidence degradation (absolute drop)
    max_confidence_drop: float = 0.3

    # Number of degradation levels to test
    degradation_levels: int = 5

    # Stability margin: a program is "stable" if its measured values
    # have at least this much headroom relative to the law threshold
    stability_margin_px: float = 10.0


V1_STABILITY = StabilityContract()


# ════════════════════════════════════════════════════════════
# DEGRADATION FUNCTIONS — deterministic given seed
# ════════════════════════════════════════════════════════════

def _deterministic_jitter(value: float, seed: int, magnitude: float) -> float:
    """
    Deterministic pseudo-jitter. Same seed → same output.
    Uses a simple hash-based approach (no randomness).

    Returns value shifted by [-magnitude, +magnitude] based on seed.
    """
    # Simple deterministic hash
    h = ((seed * 2654435761) & 0xFFFFFFFF) / 0xFFFFFFFF  # 0.0 to 1.0
    shift = (h * 2.0 - 1.0) * magnitude  # -magnitude to +magnitude
    return value + shift


def degrade_primitive(
    prim_dict: Dict[str, Any],
    jitter_px: float = 0.0,
    scale: float = 1.0,
    confidence_drop: float = 0.0,
    seed: int = 0,
) -> Dict[str, Any]:
    """
    Apply deterministic degradation to a primitive dict.

    Parameters:
        prim_dict: CV-format dict with bbox, confidence, etc.
        jitter_px: Maximum pixel jitter per coordinate.
        scale: Uniform scale factor (1.0 = no change).
        confidence_drop: Absolute drop in confidence.
        seed: Deterministic seed for jitter direction.

    Returns a new dict with degraded values.
    """
    d = dict(prim_dict)  # shallow copy

    # Resolve bbox
    if "bbox" in d and isinstance(d["bbox"], (list, tuple)):
        x, y, w, h = d["bbox"]
    elif "x" in d:
        x, y = d.get("x", 0), d.get("y", 0)
        w, h = d.get("width", d.get("w", 0)), d.get("height", d.get("h", 0))
    else:
        return d

    # Apply scale
    x *= scale
    y *= scale
    w *= scale
    h *= scale

    # Apply jitter (deterministic per coordinate)
    x = _deterministic_jitter(x, seed * 4 + 0, jitter_px)
    y = _deterministic_jitter(y, seed * 4 + 1, jitter_px)
    w = max(2.0, _deterministic_jitter(w, seed * 4 + 2, jitter_px * 0.5))
    h = max(2.0, _deterministic_jitter(h, seed * 4 + 3, jitter_px * 0.5))

    # Apply confidence degradation
    conf = d.get("confidence", d.get("source_confidence", 1.0))
    conf = max(0.0, conf - confidence_drop)

    # Rebuild dict
    if "bbox" in prim_dict and isinstance(prim_dict["bbox"], (list, tuple)):
        d["bbox"] = [x, y, w, h]
    else:
        d["x"] = x
        d["y"] = y
        if "width" in d:
            d["width"] = w
        elif "w" in d:
            d["w"] = w
        if "height" in d:
            d["height"] = h
        elif "h" in d:
            d["h"] = h

    if "confidence" in d:
        d["confidence"] = conf
    elif "source_confidence" in d:
        d["source_confidence"] = conf

    return d


def degrade_frame(
    primitives: List[Dict[str, Any]],
    jitter_px: float = 0.0,
    scale: float = 1.0,
    confidence_drop: float = 0.0,
    base_seed: int = 0,
) -> List[Dict[str, Any]]:
    """
    Apply deterministic degradation to all primitives in a frame.
    Each primitive gets a unique seed derived from base_seed + index.
    """
    return [
        degrade_primitive(p, jitter_px, scale, confidence_drop, seed=base_seed + i)
        for i, p in enumerate(primitives)
    ]


# ════════════════════════════════════════════════════════════
# STABILITY ANALYSIS — check headroom against law thresholds
# ════════════════════════════════════════════════════════════

@dataclass
class StabilityMargin:
    """Headroom analysis for one assertion."""
    operation: str
    result: str
    measured_value: float
    law_threshold: float
    headroom_px: float  # How far from the threshold boundary
    stable_under_jitter: float  # Max jitter that preserves this result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "result": self.result,
            "measured_value": self.measured_value,
            "law_threshold": self.law_threshold,
            "headroom_px": round(self.headroom_px, 3),
            "stable_under_jitter": round(self.stable_under_jitter, 3),
        }


def analyze_margins(result: ExecutionResult) -> List[StabilityMargin]:
    """
    Analyze the stability margins of each assertion.
    How much jitter can each assertion tolerate before flipping?
    """
    margins = []
    for assertion in result.assertions:
        op = assertion["operation"]
        res = assertion["result"]
        measured = assertion["measured_value"]
        threshold = assertion["law_threshold"]

        if op == "ADJACENT":
            if res == "TRUE":
                # TRUE when measured <= threshold. Headroom = threshold - measured.
                headroom = threshold - measured
            else:
                # FALSE when measured > threshold. Headroom = measured - threshold.
                headroom = measured - threshold
        elif op == "CONTAINS":
            if res == "TRUE":
                # TRUE when measured >= threshold. Headroom = measured - threshold.
                headroom = measured - threshold
            else:
                # FALSE when measured < threshold. Headroom = threshold - measured.
                headroom = threshold - measured
        else:
            headroom = 0.0

        # Jitter tolerance: each bbox corner can shift, so the measured value
        # can change by up to 2x jitter (both primitives shift opposite directions).
        # Stable if headroom > 2 * jitter.
        stable_under = headroom / 2.0 if headroom > 0 else 0.0

        margins.append(StabilityMargin(
            operation=op,
            result=res,
            measured_value=measured,
            law_threshold=threshold,
            headroom_px=headroom,
            stable_under_jitter=stable_under,
        ))

    return margins


# ════════════════════════════════════════════════════════════
# STABILITY PROOF — the full test result
# ════════════════════════════════════════════════════════════

class StabilityVerdict(str, Enum):
    """Overall stability verdict."""
    STABLE = "STABLE"           # Verdict preserved under all degradation levels
    UNSTABLE = "UNSTABLE"       # Verdict flipped under at least one level
    MARGINAL = "MARGINAL"       # Verdict preserved but margins are thin


@dataclass
class StabilityProof:
    """Complete result of stability testing."""
    verdict: StabilityVerdict
    original_verdict: ProgramVerdict
    degradation_results: List[Dict[str, Any]] = field(default_factory=list)
    margin_analysis: List[Dict[str, Any]] = field(default_factory=list)
    min_headroom_px: float = 0.0
    max_safe_jitter_px: float = 0.0
    stability_version: str = STABILITY_VERSION
    grammar_version: str = GRAMMAR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "original_verdict": self.original_verdict.value,
            "min_headroom_px": round(self.min_headroom_px, 3),
            "max_safe_jitter_px": round(self.max_safe_jitter_px, 3),
            "degradation_levels_tested": len(self.degradation_results),
            "all_preserved": all(
                d["verdict_preserved"] for d in self.degradation_results
            ),
            "margin_analysis": self.margin_analysis,
            "degradation_results": self.degradation_results,
            "stability_version": self.stability_version,
            "grammar_version": self.grammar_version,
        }


# ════════════════════════════════════════════════════════════
# STABILITY PROVER — the main entry point
# ════════════════════════════════════════════════════════════

def prove_stability(
    raw_primitives: List[Dict[str, Any]],
    bindings: Optional[Dict[str, int]] = None,
    operations: Optional[List[Dict]] = None,
    contract: StabilityContract = V1_STABILITY,
) -> StabilityProof:
    """
    Prove (or disprove) that a V1 visual program is stable under
    print/scan degradation.

    Runs the program at multiple degradation levels and checks
    whether the verdict is preserved.

    Parameters:
        raw_primitives: Original CV extraction dicts.
        bindings: Name → primitive index mappings.
        operations: Operations to evaluate.
        contract: Stability bounds to test against.

    Returns a StabilityProof with complete analysis.
    """
    # Step 1: Execute the original (undegraded) program
    original = execute_image_as_program(
        raw_primitives, bindings, operations,
    )

    # Step 2: Analyze margins
    margins = analyze_margins(original)
    margin_dicts = [m.to_dict() for m in margins]

    if margins:
        min_headroom = min(m.headroom_px for m in margins)
        max_safe_jitter = min(m.stable_under_jitter for m in margins)
    else:
        min_headroom = 0.0
        max_safe_jitter = 0.0

    # Step 3: Run degradation levels
    degradation_results = []
    all_preserved = True

    for level in range(contract.degradation_levels):
        # Linear interpolation from 0 to max degradation
        t = (level + 1) / contract.degradation_levels

        jitter = contract.max_jitter_px * t
        # Scale oscillates: levels alternate between shrink and grow
        if level % 2 == 0:
            scale = 1.0 + (contract.max_scale_high - 1.0) * t
        else:
            scale = 1.0 - (1.0 - contract.max_scale_low) * t
        conf_drop = contract.max_confidence_drop * t

        # Degrade the primitives
        degraded = degrade_frame(
            raw_primitives,
            jitter_px=jitter,
            scale=scale,
            confidence_drop=conf_drop,
            base_seed=level * 1000,
        )

        # Execute the degraded program
        degraded_result = execute_image_as_program(
            degraded, bindings, operations,
        )

        # Check if verdict is preserved
        # For stability: PASS→PASS, FAIL→FAIL (the program's truth doesn't change)
        # We only compare the boolean outcome, not PARTIAL vs PASS
        original_bool = original.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL)
        degraded_bool = degraded_result.verdict in (ProgramVerdict.PASS, ProgramVerdict.PARTIAL)
        preserved = (original_bool == degraded_bool) or (
            original.verdict == ProgramVerdict.EMPTY and
            degraded_result.verdict == ProgramVerdict.EMPTY
        )

        if not preserved:
            all_preserved = False

        degradation_results.append({
            "level": level + 1,
            "jitter_px": round(jitter, 2),
            "scale": round(scale, 4),
            "confidence_drop": round(conf_drop, 3),
            "original_verdict": original.verdict.value,
            "degraded_verdict": degraded_result.verdict.value,
            "verdict_preserved": preserved,
            "degraded_true_assertions": degraded_result.true_assertions,
            "degraded_false_assertions": degraded_result.false_assertions,
        })

    # Step 4: Compute stability verdict
    if not margins:
        verdict = StabilityVerdict.STABLE  # Empty programs are trivially stable
    elif not all_preserved:
        verdict = StabilityVerdict.UNSTABLE
    elif min_headroom < contract.stability_margin_px:
        verdict = StabilityVerdict.MARGINAL
    else:
        verdict = StabilityVerdict.STABLE

    return StabilityProof(
        verdict=verdict,
        original_verdict=original.verdict,
        degradation_results=degradation_results,
        margin_analysis=margin_dicts,
        min_headroom_px=min_headroom,
        max_safe_jitter_px=max_safe_jitter,
    )
