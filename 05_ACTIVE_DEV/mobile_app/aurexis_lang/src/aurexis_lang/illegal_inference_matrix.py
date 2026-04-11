"""Frozen blocked-claim matrix helpers for Gate 1 illegal-inference law."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping

from .evidence_tiers import normalize_evidence_tier, EvidenceTier


@dataclass(frozen=True)
class BlockedClaimRule:
    claim_id: str
    description: str
    required_action: str
    trigger: Callable[[Mapping[str, Any]], bool]


def _flag(data: Mapping[str, Any], *names: str) -> bool:
    return any(bool(data.get(name, False)) for name in names)


def _evidence_tier(data: Mapping[str, Any]) -> str | None:
    evidence = data.get('evidence')
    if isinstance(evidence, Mapping) and 'evidence_tier' in evidence:
        try:
            return normalize_evidence_tier(evidence['evidence_tier']).value
        except Exception:
            return str(evidence['evidence_tier'])
    if 'evidence_tier' in data:
        try:
            return normalize_evidence_tier(data['evidence_tier']).value
        except Exception:
            return str(data['evidence_tier'])
    return None


BLOCKED_CLAIM_RULES: tuple[BlockedClaimRule, ...] = (
    BlockedClaimRule(
        'full_world_truth_from_single_observation',
        'Single observation presented as complete world truth',
        'Downgrade claim to estimated/unknown or add multi-frame grounded evidence',
        lambda d: _flag(d, 'single_observation_as_full_world_truth') or (bool(d.get('single_observation')) and bool(d.get('full_world_truth_claim'))),
    ),
    BlockedClaimRule(
        'exact_world_placement_from_weak_evidence',
        'Exact world placement claimed from weak evidence',
        'Remove exact placement claim or add stronger grounded evidence',
        lambda d: _flag(d, 'exact_world_placement_from_weak_evidence', 'exact_world_placement_claim_without_support'),
    ),
    BlockedClaimRule(
        'hidden_geometry_or_contents_claim',
        'Hidden geometry or contents claimed as fact without observation',
        'Mark hidden structure as hypothesis only or remove the claim',
        lambda d: _flag(d, 'hidden_geometry_claim', 'hidden_contents_claim', 'unseen_structure_claim'),
    ),
    BlockedClaimRule(
        'executability_from_pattern_alone',
        'Observed pattern promoted to executable meaning without validation',
        'Keep claim descriptive/estimated until validation gates pass',
        lambda d: _flag(d, 'executability_from_pattern_alone', 'pattern_is_automatically_code'),
    ),
    BlockedClaimRule(
        'identity_from_resemblance_alone',
        'Identity claimed from resemblance alone',
        'Downgrade to estimated similarity or add stronger identity evidence',
        lambda d: _flag(d, 'identity_from_resemblance_alone', 'resemblance_as_identity'),
    ),
    BlockedClaimRule(
        'causality_or_function_from_appearance_alone',
        'Causality, intention, or function claimed from appearance alone',
        'Remove causal/function claim or add real grounded evidence',
        lambda d: _flag(d, 'causality_from_appearance_alone', 'function_from_appearance_alone', 'intent_from_appearance_alone'),
    ),
    BlockedClaimRule(
        'permanence_from_single_frame',
        'Single-frame observation claimed as permanence or persistence',
        'Downgrade permanence claim or add repeated temporal evidence',
        lambda d: _flag(d, 'permanence_from_single_frame', 'single_frame_persistence_claim'),
    ),
    BlockedClaimRule(
        'earned_physical_proof_without_earned_tier',
        'Claimed earned physical proof without earned-tier evidence',
        'Downgrade proof claim or provide earned-tier evidence',
        lambda d: bool(d.get('claims_earned_physical_proof', False)) and _evidence_tier(d) != EvidenceTier.EARNED.value,
    ),
    BlockedClaimRule(
        'world_claim_without_image_grounding',
        'World claim asserted without image-grounded evidence',
        'Remove unsupported world claim or add image-grounded evidence',
        lambda d: _flag(d, 'world_claim_without_image_grounding', 'world_knowledge_without_evidence'),
    ),
)


def evaluate_blocked_claims(data: Mapping[str, Any]) -> List[BlockedClaimRule]:
    return [rule for rule in BLOCKED_CLAIM_RULES if rule.trigger(data)]
