"""Formal evidence-tier helpers for Aurexis cleanup enforcement."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterable, Mapping


class EvidenceTier(str, Enum):
    LAB = "lab"
    AUTHORED = "authored"
    REAL_CAPTURE = "real-capture"
    EARNED = "earned"


_ORDER = {
    EvidenceTier.LAB: 0,
    EvidenceTier.AUTHORED: 1,
    EvidenceTier.REAL_CAPTURE: 2,
    EvidenceTier.EARNED: 3,
}


def normalize_evidence_tier(value: Any) -> EvidenceTier:
    if isinstance(value, EvidenceTier):
        return value
    text = str(value).strip().lower().replace('_', '-').replace(' ', '-')
    aliases = {
        'tier-a': EvidenceTier.LAB,
        'tier-b': EvidenceTier.AUTHORED,
        'tier-c': EvidenceTier.REAL_CAPTURE,
        'tier-d': EvidenceTier.EARNED,
        'realcapture': EvidenceTier.REAL_CAPTURE,
    }
    if text in aliases:
        return aliases[text]
    return EvidenceTier(text)


def is_earned_tier(value: Any) -> bool:
    return normalize_evidence_tier(value) == EvidenceTier.EARNED


def build_evidence_stamp(
    default_tier: Any,
    *,
    source_tiers: Iterable[Any] | None = None,
    earned_proof: bool = False,
    note: str = '',
    requires_real_capture: bool = False,
) -> Dict[str, Any]:
    tier = normalize_evidence_tier(default_tier)
    sources = [normalize_evidence_tier(v).value for v in (source_tiers or [tier])]
    if earned_proof and tier != EvidenceTier.EARNED:
        raise ValueError('Only earned-tier results may claim earned proof')
    return {
        'evidence_tier': tier.value,
        'source_tiers': sources,
        'earned_proof': earned_proof,
        'requires_real_capture': requires_real_capture,
        'note': note,
    }


def stamp_result(
    result: Mapping[str, Any],
    default_tier: Any,
    *,
    source_tiers: Iterable[Any] | None = None,
    earned_proof: bool = False,
    note: str = '',
    requires_real_capture: bool = False,
) -> Dict[str, Any]:
    stamped = dict(result)
    stamped['evidence'] = build_evidence_stamp(
        default_tier,
        source_tiers=source_tiers,
        earned_proof=earned_proof,
        note=note,
        requires_real_capture=requires_real_capture,
    )
    return stamped
