"""Frozen executable-promotion checklist helpers for Gate 1."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .evidence_tiers import normalize_evidence_tier, EvidenceTier


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, '__dict__'):
        return dict(vars(value))
    return {}


def _evidence_tier(executable: Mapping[str, Any]) -> str | None:
    evidence = executable.get('evidence')
    if isinstance(evidence, Mapping) and 'evidence_tier' in evidence:
        try:
            return normalize_evidence_tier(evidence['evidence_tier']).value
        except Exception:
            return str(evidence['evidence_tier'])
    if 'evidence_tier' in executable:
        try:
            return normalize_evidence_tier(executable['evidence_tier']).value
        except Exception:
            return str(executable['evidence_tier'])
    return None


def validate_executable_promotion_checklist(source: Any) -> List[str]:
    executable = _mapping(source)
    errors: List[str] = []

    if not executable.get('evidence_validated', False):
        errors.append('missing_evidence_validated')
    if not executable.get('multi_frame_consistent', False):
        errors.append('missing_multi_frame_consistency')
    if not executable.get('geometric_coherence', False):
        errors.append('missing_geometric_coherence')
    if not executable.get('cross_register_consistency', False):
        errors.append('missing_cross_register_consistency')
    if not executable.get('language_legal', False):
        errors.append('missing_language_legality')
    if not executable.get('bounded_inference', False):
        errors.append('missing_bounded_inference')

    confidence = float(executable.get('confidence', 0.0) or 0.0)
    if confidence < 0.7:
        errors.append('confidence_below_threshold')

    unresolved = executable.get('unresolved_reasons') or executable.get('blocked_reasons') or []
    if unresolved:
        errors.append('has_unresolved_reasons')

    if executable.get('promotion_by_assumption', False):
        errors.append('promotion_by_assumption')

    tier = _evidence_tier(executable)
    if executable.get('claims_earned_physical_proof', False) and tier != EvidenceTier.EARNED.value:
        errors.append('earned_proof_without_earned_tier')

    return errors
