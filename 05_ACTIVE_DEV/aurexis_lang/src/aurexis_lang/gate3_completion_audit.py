"""Formal Gate 3 completion-audit scaffold helpers."""
from __future__ import annotations

from typing import Any, Dict, Mapping

GATE_3_COMPLETION_AUDIT_RULES_VERSION = "AUREXIS_GATE_3_COMPLETION_AUDIT_V1"
GATE_3_COMPLETION_AUTHORITY = "earned_evidence_audit_and_real_capture_comparison"


def audit_gate3_completion(*, batch_report_surface: Mapping[str, Any]) -> Dict[str, Any]:
    surface = dict(batch_report_surface or {})
    source_counts = dict(surface.get('source_counts', {}) or {})
    blocking_reasons = list(surface.get('blocking_reasons', []) or [])

    audit_checks = {
        'report_scope_explicit': str(surface.get('report_scope', '')).startswith('gate3_') and str(surface.get('report_scope', '')).endswith('_report'),
        'non_clearing_scaffold_surface': bool(surface.get('gate_clearance_authority', True)) is False,
        'comparison_ready': bool(surface.get('comparison_ready', False)),
        'earned_candidate_ready': bool(surface.get('earned_candidate_ready', False)),
        'earned_audit_ready': bool(surface.get('earned_audit_ready', False)),
        'authored_inputs_present': int(source_counts.get('authored', 0)) > 0,
        'real_capture_inputs_present': int(source_counts.get('real-capture', 0)) > 0,
        'earned_inputs_present': int(source_counts.get('earned', 0)) > 0,
        'blocking_reasons_empty': len(blocking_reasons) == 0,
        'output_honesty_explicit': bool(surface.get('output_honesty_explicit', False)),
    }

    gate_3_complete = all(audit_checks.values())
    blocking_components = [name for name, ok in audit_checks.items() if not ok]

    return {
        'audit_rules_version': GATE_3_COMPLETION_AUDIT_RULES_VERSION,
        'completion_authority': GATE_3_COMPLETION_AUTHORITY,
        'audit_checks': audit_checks,
        'blocking_components': blocking_components,
        'all_audit_checks_pass': gate_3_complete,
        'gate_3_complete': gate_3_complete,
        'summary': 'Gate 3 completion audit passed' if gate_3_complete else 'Gate 3 completion audit still blocked',
    }
