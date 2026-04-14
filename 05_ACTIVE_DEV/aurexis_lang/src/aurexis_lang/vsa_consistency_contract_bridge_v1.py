"""
Aurexis Core — VSA Consistency / Contract Bridge V1

Bounded executable consistency layer that validates whether a cleaned-up
hyperdimensional representation is consistent with the corresponding
deterministic substrate output.

What this proves:
  Given a substrate output (e.g., an artifact set contract name) and a
  VSA-cleaned-up symbol ID, the consistency check verifies that the
  VSA recovery matches the substrate truth. This keeps VSA subordinate
  to the deterministic substrate.

What this does NOT prove:
  - Full hyperdimensional computing generality
  - VSA as a replacement for the deterministic substrate
  - Noise-robust real-camera cleanup
  - Full Aurexis Core completion

Design:
  - ConsistencyVerdict: CONSISTENT, MISMATCH, VSA_FAILED, UNKNOWN_TARGET, ERROR.
  - ConsistencyResult: contains substrate truth, VSA recovery, and verdict.
  - check_consistency(): cross-checks a CleanupResult against a known
    substrate output.
  - check_all_consistency(): batch validation across all frozen targets.
  - Fabricated mismatch cases test each rejection path.
  - All operations are deterministic.

The VSA layer is AUXILIARY. It does NOT replace the deterministic substrate.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    CLEANUP_PROFILE_VERSION, CLEANUP_PROFILE_FROZEN,
    V1_CLEANUP_PROFILE, FROZEN_SYMBOL_IDS,
    CleanupTarget, CleanupTargetKind, CleanupProfile,
)
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    BINDING_VERSION, BINDING_FROZEN,
    HyperVector, V1_CODEBOOK, Codebook,
    generate_atomic, add_noise,
)
from aurexis_lang.cleanup_retrieval_bridge_v1 import (
    RETRIEVAL_VERSION, RETRIEVAL_FROZEN,
    CleanupVerdict, CleanupResult,
    cleanup_single,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CONSISTENCY_VERSION = "V1.0"
CONSISTENCY_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONSISTENCY VERDICTS
# ════════════════════════════════════════════════════════════

class ConsistencyVerdict(str, Enum):
    """Outcome of VSA-vs-substrate consistency check."""
    CONSISTENT = "CONSISTENT"         # VSA recovery matches substrate truth
    MISMATCH = "MISMATCH"             # VSA recovered a different symbol
    VSA_FAILED = "VSA_FAILED"         # VSA cleanup returned no match or error
    UNKNOWN_TARGET = "UNKNOWN_TARGET" # Substrate name not in cleanup profile
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# CONSISTENCY RESULT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConsistencyResult:
    """
    Result of checking VSA recovery against substrate truth.

    substrate_name: the deterministic substrate output name.
    expected_symbol_id: the symbol ID that the substrate maps to.
    vsa_recovered_symbol_id: what VSA cleanup actually returned.
    vsa_similarity: the similarity score from cleanup.
    vsa_verdict: the CleanupVerdict from retrieval.
    consistency_verdict: CONSISTENT, MISMATCH, etc.
    detail: human-readable explanation.
    """
    substrate_name: str = ""
    expected_symbol_id: str = ""
    vsa_recovered_symbol_id: str = ""
    vsa_similarity: float = 0.0
    vsa_verdict: CleanupVerdict = CleanupVerdict.ERROR
    consistency_verdict: ConsistencyVerdict = ConsistencyVerdict.ERROR
    detail: str = ""
    version: str = CONSISTENCY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "substrate_name": self.substrate_name,
            "expected_symbol_id": self.expected_symbol_id,
            "vsa_recovered_symbol_id": self.vsa_recovered_symbol_id,
            "vsa_similarity": round(self.vsa_similarity, 4),
            "vsa_verdict": self.vsa_verdict.value,
            "consistency_verdict": self.consistency_verdict.value,
            "detail": self.detail,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CONSISTENCY CHECK
# ════════════════════════════════════════════════════════════

def check_consistency(
    substrate_name: str,
    query_vector: HyperVector,
    profile: CleanupProfile = V1_CLEANUP_PROFILE,
    codebook: Codebook = V1_CODEBOOK,
) -> ConsistencyResult:
    """
    Check if VSA cleanup of query_vector is consistent with the
    substrate output identified by substrate_name.

    Steps:
      1. Look up the cleanup target for this substrate name.
      2. Run VSA cleanup on the query vector.
      3. Compare the recovered symbol ID with the expected symbol ID.
    """
    # Step 1: Find target
    target = profile.get_target_by_substrate_name(substrate_name)
    if target is None:
        return ConsistencyResult(
            substrate_name=substrate_name,
            consistency_verdict=ConsistencyVerdict.UNKNOWN_TARGET,
            detail=f"No cleanup target for substrate name '{substrate_name}'",
        )

    expected_sid = target.symbol_id

    # Step 2: VSA cleanup
    cleanup = cleanup_single(query_vector, codebook)

    # Step 3: Compare
    if cleanup.verdict in (CleanupVerdict.NO_MATCH, CleanupVerdict.ERROR):
        return ConsistencyResult(
            substrate_name=substrate_name,
            expected_symbol_id=expected_sid,
            vsa_recovered_symbol_id=cleanup.matched_symbol_id,
            vsa_similarity=cleanup.similarity,
            vsa_verdict=cleanup.verdict,
            consistency_verdict=ConsistencyVerdict.VSA_FAILED,
            detail=f"VSA cleanup failed: {cleanup.detail}",
        )

    if cleanup.matched_symbol_id == expected_sid:
        return ConsistencyResult(
            substrate_name=substrate_name,
            expected_symbol_id=expected_sid,
            vsa_recovered_symbol_id=cleanup.matched_symbol_id,
            vsa_similarity=cleanup.similarity,
            vsa_verdict=cleanup.verdict,
            consistency_verdict=ConsistencyVerdict.CONSISTENT,
            detail=f"Consistent: VSA recovered {expected_sid} (sim={cleanup.similarity:.4f})",
        )
    else:
        return ConsistencyResult(
            substrate_name=substrate_name,
            expected_symbol_id=expected_sid,
            vsa_recovered_symbol_id=cleanup.matched_symbol_id,
            vsa_similarity=cleanup.similarity,
            vsa_verdict=cleanup.verdict,
            consistency_verdict=ConsistencyVerdict.MISMATCH,
            detail=f"Mismatch: expected {expected_sid}, got {cleanup.matched_symbol_id}",
        )


def check_all_consistency(
    noise_fraction: float = 0.0,
    seed: int = 42,
    profile: CleanupProfile = V1_CLEANUP_PROFILE,
    codebook: Codebook = V1_CODEBOOK,
) -> Tuple[ConsistencyResult, ...]:
    """
    Check consistency for all frozen targets.
    Generates the atomic vector for each target's symbol, optionally adds noise,
    then runs consistency check.
    """
    results = []
    for target in profile.targets:
        vec = codebook.get_vector(target.symbol_id)
        if vec is None:
            results.append(ConsistencyResult(
                substrate_name=target.substrate_name,
                expected_symbol_id=target.symbol_id,
                consistency_verdict=ConsistencyVerdict.ERROR,
                detail=f"Symbol {target.symbol_id} not in codebook",
            ))
            continue

        if noise_fraction > 0:
            vec = add_noise(vec, noise_fraction, seed=seed)

        results.append(check_consistency(target.substrate_name, vec, profile, codebook))
    return tuple(results)


# ════════════════════════════════════════════════════════════
# FABRICATED VIOLATION CASES
# ════════════════════════════════════════════════════════════

def make_mismatch_query(target_symbol_id: str, wrong_symbol_id: str, codebook: Codebook = V1_CODEBOOK) -> HyperVector:
    """
    Return the atomic vector of wrong_symbol_id to simulate a mismatch
    when checking against target_symbol_id's substrate name.
    """
    vec = codebook.get_vector(wrong_symbol_id)
    if vec is None:
        raise ValueError(f"Symbol {wrong_symbol_id} not in codebook")
    return vec


def make_random_noise_query(seed: int = 999) -> HyperVector:
    """Generate a random vector that shouldn't match anything well."""
    return generate_atomic(f"__RANDOM_CONSISTENCY_{seed}__")


# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

EXPECTED_CONSISTENT_COUNT = len(V1_CLEANUP_PROFILE.targets)  # 11
VIOLATION_CASE_COUNT = 3  # mismatch, vsa_failed (random noise), unknown_target
