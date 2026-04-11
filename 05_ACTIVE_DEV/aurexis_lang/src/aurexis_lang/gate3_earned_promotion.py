"""Gate 3 earned-tier promotion helpers."""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .evidence_tiers import EvidenceTier

GATE_3_EARNED_PROMOTION_RULES_VERSION = 'AUREXIS_GATE_3_EARNED_TIER_PROMOTION_RULES_V1'


def promote_gate3_earned_candidate(*, comparison_package: Mapping[str, Any], delta_threshold: float = 1.5) -> Dict[str, Any]:
    gate3_loop = dict(comparison_package.get('gate3_evidence_loop', {}))
    batch_comp = dict(comparison_package.get('gate3_batch_comparison', {}))
    comparison = dict(batch_comp.get('comparison', {}))
    audit = dict(batch_comp.get('earned_audit', {}))

    blocking_reasons = []
    if not bool(comparison.get('comparison_ready', False)):
        blocking_reasons.append('comparison_not_ready')
    if not bool(audit.get('earned_audit_ready', False)):
        blocking_reasons.append('earned_audit_not_ready')
    overlap_metric_count = int(comparison.get('overlap_metric_count', 0) or 0)
    if overlap_metric_count <= 0:
        blocking_reasons.append('no_overlap_metrics')

    metric_deltas = dict(comparison.get('metric_deltas', {}) or {})
    max_metric_delta = max([float(v) for v in metric_deltas.values()], default=0.0)
    if overlap_metric_count > 0 and max_metric_delta > float(delta_threshold):
        blocking_reasons.append('metric_delta_too_high')
    if not bool(gate3_loop.get('output_honesty_explicit', False)):
        blocking_reasons.append('output_honesty_not_explicit')

    for reason in list(comparison.get('blocking_reasons', [])) + list(audit.get('blocking_reasons', [])):
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)

    ready = bool(comparison.get('comparison_ready', False)) and bool(audit.get('earned_audit_ready', False))
    passed = ready and len(blocking_reasons) == 0

    source_counts = dict(gate3_loop.get('source_counts', {}) or {})
    source_counts.setdefault(EvidenceTier.AUTHORED.value, 0)
    source_counts.setdefault(EvidenceTier.REAL_CAPTURE.value, 0)
    source_counts.setdefault(EvidenceTier.EARNED.value, 0)
    if passed:
        source_counts[EvidenceTier.EARNED.value] = max(1, int(source_counts.get(EvidenceTier.EARNED.value, 0) or 0))

    return {
        'report_scope': 'gate3_earned_candidate',
        'rules_version': GATE_3_EARNED_PROMOTION_RULES_VERSION,
        'gate_clearance_authority': False,
        'output_honesty_explicit': bool(gate3_loop.get('output_honesty_explicit', False)),
        'earned_promotion_ready': bool(ready),
        'earned_promotion_passed': bool(passed),
        'promoted_evidence_tier': EvidenceTier.EARNED.value if passed else EvidenceTier.REAL_CAPTURE.value,
        'source_counts': source_counts,
        'overlap_metric_count': overlap_metric_count,
        'metric_deltas': metric_deltas,
        'max_metric_delta': float(max_metric_delta),
        'delta_threshold': float(delta_threshold),
        'blocking_reasons': blocking_reasons,
    }
