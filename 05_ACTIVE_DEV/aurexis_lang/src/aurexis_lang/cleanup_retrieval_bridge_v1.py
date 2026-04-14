"""
Aurexis Core — Cleanup Retrieval Bridge V1

Bounded executable cleanup layer that recovers a frozen supported symbol
from a noisy or bundled hypervector representation.

What this proves:
  Given a noisy or composed hypervector, the system can retrieve the
  nearest matching symbol from the frozen codebook using cosine
  similarity. This demonstrates bounded noise tolerance: up to ~30%
  bit-flip noise can be cleaned up for single-symbol retrieval.

What this does NOT prove:
  - Full hyperdimensional computing generality
  - Noise-robust real-camera cleanup
  - VSA as a replacement for the deterministic substrate
  - Full Aurexis Core completion

Design:
  - cleanup_single(): find the nearest codebook entry to a query vector.
  - cleanup_top_k(): find the top-k nearest entries.
  - CleanupResult: contains the matched symbol, similarity score, and
    confidence assessment.
  - CleanupVerdict: CLEAN_MATCH, WEAK_MATCH, NO_MATCH, AMBIGUOUS, ERROR.
  - Confidence thresholds: HIGH (>0.7), MEDIUM (>0.3), LOW (<=0.3).
  - Bounded noise tolerance testing: verify cleanup at 0%, 10%, 20%, 30%.

The VSA layer is AUXILIARY. It does NOT replace the deterministic substrate.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    BINDING_VERSION, BINDING_FROZEN,
    DIMENSION, HyperVector,
    cosine_similarity, generate_atomic, add_noise,
    Codebook, V1_CODEBOOK, FROZEN_SYMBOL_IDS,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

RETRIEVAL_VERSION = "V1.0"
RETRIEVAL_FROZEN = True


# ════════════════════════════════════════════════════════════
# CLEANUP VERDICTS
# ════════════════════════════════════════════════════════════

class CleanupVerdict(str, Enum):
    """Outcome of cleanup retrieval."""
    CLEAN_MATCH = "CLEAN_MATCH"       # High confidence single match
    WEAK_MATCH = "WEAK_MATCH"         # Low confidence match
    NO_MATCH = "NO_MATCH"             # Below threshold
    AMBIGUOUS = "AMBIGUOUS"           # Multiple close matches
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# CONFIDENCE THRESHOLDS
# ════════════════════════════════════════════════════════════

HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.3
AMBIGUITY_GAP_THRESHOLD = 0.1  # minimum gap between 1st and 2nd match


# ════════════════════════════════════════════════════════════
# CLEANUP RESULT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CleanupResult:
    """
    Result of cleanup retrieval from a noisy/composed hypervector.

    matched_symbol_id: the best matching symbol (or "" if no match).
    similarity: cosine similarity of the match.
    runner_up_symbol_id: second best match (or "").
    runner_up_similarity: cosine similarity of the runner-up.
    gap: similarity difference between best and runner-up.
    verdict: the cleanup outcome.
    detail: human-readable explanation.
    """
    matched_symbol_id: str = ""
    similarity: float = 0.0
    runner_up_symbol_id: str = ""
    runner_up_similarity: float = 0.0
    gap: float = 0.0
    verdict: CleanupVerdict = CleanupVerdict.ERROR
    detail: str = ""
    version: str = RETRIEVAL_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched_symbol_id": self.matched_symbol_id,
            "similarity": round(self.similarity, 4),
            "runner_up_symbol_id": self.runner_up_symbol_id,
            "runner_up_similarity": round(self.runner_up_similarity, 4),
            "gap": round(self.gap, 4),
            "verdict": self.verdict.value,
            "detail": self.detail,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CORE CLEANUP FUNCTIONS
# ════════════════════════════════════════════════════════════

def cleanup_single(
    query: HyperVector,
    codebook: Codebook = V1_CODEBOOK,
) -> CleanupResult:
    """
    Find the nearest codebook entry to a query vector.

    Returns a CleanupResult with verdict:
      - CLEAN_MATCH if similarity > HIGH_CONFIDENCE_THRESHOLD and gap > AMBIGUITY_GAP_THRESHOLD
      - AMBIGUOUS if top two matches are too close
      - WEAK_MATCH if similarity > MEDIUM_CONFIDENCE_THRESHOLD but not high
      - NO_MATCH if best similarity <= MEDIUM_CONFIDENCE_THRESHOLD
    """
    if codebook.size == 0:
        return CleanupResult(verdict=CleanupVerdict.ERROR, detail="Empty codebook")

    # Compute similarities
    similarities: List[Tuple[str, float]] = []
    for sid, vec in codebook.entries:
        sim = cosine_similarity(query, vec)
        similarities.append((sid, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: -x[1])

    best_sid, best_sim = similarities[0]

    # Get runner-up
    if len(similarities) > 1:
        runup_sid, runup_sim = similarities[1]
    else:
        runup_sid, runup_sim = "", -1.0

    gap = best_sim - runup_sim

    # Determine verdict
    if best_sim <= MEDIUM_CONFIDENCE_THRESHOLD:
        verdict = CleanupVerdict.NO_MATCH
        detail = f"Best similarity {best_sim:.4f} below threshold {MEDIUM_CONFIDENCE_THRESHOLD}"
    elif best_sim > HIGH_CONFIDENCE_THRESHOLD and gap > AMBIGUITY_GAP_THRESHOLD:
        verdict = CleanupVerdict.CLEAN_MATCH
        detail = f"Clean match: {best_sid} with similarity {best_sim:.4f} (gap {gap:.4f})"
    elif gap <= AMBIGUITY_GAP_THRESHOLD and best_sim > MEDIUM_CONFIDENCE_THRESHOLD:
        verdict = CleanupVerdict.AMBIGUOUS
        detail = f"Ambiguous: {best_sid}={best_sim:.4f} vs {runup_sid}={runup_sim:.4f} (gap {gap:.4f})"
    else:
        verdict = CleanupVerdict.WEAK_MATCH
        detail = f"Weak match: {best_sid} with similarity {best_sim:.4f}"

    return CleanupResult(
        matched_symbol_id=best_sid,
        similarity=best_sim,
        runner_up_symbol_id=runup_sid,
        runner_up_similarity=runup_sim,
        gap=gap,
        verdict=verdict,
        detail=detail,
    )


def cleanup_top_k(
    query: HyperVector,
    k: int = 3,
    codebook: Codebook = V1_CODEBOOK,
) -> Tuple[Tuple[str, float], ...]:
    """Return the top-k (symbol_id, similarity) pairs for a query."""
    similarities = []
    for sid, vec in codebook.entries:
        sim = cosine_similarity(query, vec)
        similarities.append((sid, sim))
    similarities.sort(key=lambda x: -x[1])
    return tuple(similarities[:k])


# ════════════════════════════════════════════════════════════
# NOISE TOLERANCE VERIFICATION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class NoiseToleranceResult:
    """Result of testing cleanup at a specific noise level."""
    symbol_id: str = ""
    noise_fraction: float = 0.0
    similarity_after_noise: float = 0.0
    cleanup_verdict: CleanupVerdict = CleanupVerdict.ERROR
    recovered_correctly: bool = False
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "noise_fraction": self.noise_fraction,
            "similarity_after_noise": round(self.similarity_after_noise, 4),
            "cleanup_verdict": self.cleanup_verdict.value,
            "recovered_correctly": self.recovered_correctly,
            "detail": self.detail,
        }


def verify_noise_tolerance(
    symbol_id: str,
    noise_fraction: float,
    seed: int = 42,
    codebook: Codebook = V1_CODEBOOK,
) -> NoiseToleranceResult:
    """
    Verify cleanup retrieval at a specific noise level for a symbol.

    Generates the atomic vector, adds noise, then cleans up.
    """
    vec = codebook.get_vector(symbol_id)
    if vec is None:
        return NoiseToleranceResult(
            symbol_id=symbol_id,
            noise_fraction=noise_fraction,
            detail=f"Symbol {symbol_id} not in codebook",
        )

    noisy = add_noise(vec, noise_fraction, seed=seed)
    result = cleanup_single(noisy, codebook)

    return NoiseToleranceResult(
        symbol_id=symbol_id,
        noise_fraction=noise_fraction,
        similarity_after_noise=result.similarity,
        cleanup_verdict=result.verdict,
        recovered_correctly=(result.matched_symbol_id == symbol_id),
        detail=f"Noise {noise_fraction:.0%}: recovered={result.matched_symbol_id}, sim={result.similarity:.4f}",
    )


def verify_all_noise_tolerance(
    noise_fractions: Tuple[float, ...] = (0.0, 0.1, 0.2, 0.3),
    codebook: Codebook = V1_CODEBOOK,
) -> Tuple[NoiseToleranceResult, ...]:
    """Verify noise tolerance for all symbols at all noise levels."""
    results = []
    for sid in codebook.all_symbol_ids:
        for i, nf in enumerate(noise_fractions):
            results.append(verify_noise_tolerance(sid, nf, seed=42 + i, codebook=codebook))
    return tuple(results)


# ════════════════════════════════════════════════════════════
# FABRICATED TEST CASES
# ════════════════════════════════════════════════════════════

def make_random_query(seed: int = 999) -> HyperVector:
    """Generate a random vector that shouldn't match any codebook entry well."""
    return generate_atomic(f"__RANDOM_NOISE_{seed}__")


# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

SUPPORTED_NOISE_LEVELS = (0.0, 0.1, 0.2, 0.3)
EXPECTED_CLEAN_MATCH_AT_0_NOISE = len(FROZEN_SYMBOL_IDS)  # 11
EXPECTED_CLEAN_MATCH_AT_10_NOISE = len(FROZEN_SYMBOL_IDS)  # 11 (should still recover)
EXPECTED_CLEAN_MATCH_AT_20_NOISE = len(FROZEN_SYMBOL_IDS)  # 11 (should still recover)
