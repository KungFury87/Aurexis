"""Gate 3 batch report surface helpers."""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .gate3_evidence_loop import GATE_3_STATUS

GATE_3_BATCH_REPORT_RULES_VERSION = 'AUREXIS_GATE_3_BATCH_REPORT_SURFACE_RULES_V1'


def _unique_ordered(seq):
    out = []
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_gate3_batch_report_surface(*, batch_name: str, evaluation_summary: Mapping[str, Any], comparison_package: Mapping[str, Any], earned_candidate: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    gate3_loop = dict(comparison_package.get('gate3_evidence_loop', {}))
    comparison = dict(comparison_package.get('gate3_batch_comparison', {}).get('comparison', {}))
    audit = dict(comparison_package.get('gate3_batch_comparison', {}).get('earned_audit', {}))
    source_counts = dict(gate3_loop.get('source_counts', {}))
    earned_candidate = dict(earned_candidate or {})
    if bool(earned_candidate.get('earned_promotion_passed', False)):
        source_counts = dict(earned_candidate.get('source_counts', source_counts))
    blocking = _unique_ordered(
        list(gate3_loop.get('blocking_reasons', []))
        + list(comparison.get('blocking_reasons', []))
        + list(audit.get('blocking_reasons', []))
    )
    return {
        'batch_name': batch_name,
        'gate_3_status': GATE_3_STATUS,
        'gate_clearance_authority': False,
        'report_scope': 'gate3_batch_report',
        'report_rules_version': GATE_3_BATCH_REPORT_RULES_VERSION,
        'output_honesty_explicit': True,
        'comparison_ready': bool(comparison.get('comparison_ready', False)),
        'earned_candidate_ready': bool(gate3_loop.get('earned_candidate_ready', False)),
        'earned_audit_ready': bool(audit.get('earned_audit_ready', False)),
        'earned_promotion_ready': bool(earned_candidate.get('earned_promotion_ready', False)),
        'earned_promotion_passed': bool(earned_candidate.get('earned_promotion_passed', False)),
        'promoted_evidence_tier': earned_candidate.get('promoted_evidence_tier', 'real-capture'),
        'source_counts': source_counts,
        'blocking_reasons': blocking,
        'evaluation_summary': {
            'row_count': int(evaluation_summary.get('row_count', 0)),
            'hit_count': int(evaluation_summary.get('hit_count', 0)),
            'hit_rate': float(evaluation_summary.get('hit_rate', 0.0)),
            'average_score': float(evaluation_summary.get('average_score', 0.0)),
            'success_rate': float(evaluation_summary.get('success_rate', 0.0)),
        },
    }
