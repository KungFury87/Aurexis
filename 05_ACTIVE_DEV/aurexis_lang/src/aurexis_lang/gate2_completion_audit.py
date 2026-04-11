"""Formal Gate 2 completion audit helpers."""
from __future__ import annotations
from typing import Any, Dict

AUDIT_RULES_VERSION = "AUREXIS_GATE_2_COMPLETION_AUDIT_V1"
COMPLETION_AUTHORITY = "active_surface_audit_and_full_gate_suite"


def audit_gate2_completion(scaffold_summary: Dict[str, Any]) -> Dict[str, Any]:
    component_results = dict(scaffold_summary.get('component_results', {}) or {})
    runtime_consistency = dict(component_results.get('runtime_consistency', {}) or {})
    obedience_report = dict(runtime_consistency.get('obedience_report', {}) or {})
    checks = dict(obedience_report.get('checks', {}) or {})
    report_surface_consistency = bool(scaffold_summary.get('report_surface_alignment', False))
    runtime_stage_metadata_complete = bool(scaffold_summary.get('runtime_stage_metadata_complete', False))
    no_component_violations = all(not result.get('violations') for result in component_results.values() if isinstance(result, dict))
    all_components_high = all(float(result.get('compliance_rate', 0.0)) >= 0.95 for result in component_results.values() if isinstance(result, dict))
    blocking_components = [name for name, result in component_results.items() if isinstance(result, dict) and float(result.get('compliance_rate', 0.0)) < 0.95]
    audit_checks = {
        'overall_compliance_full': float(scaffold_summary.get('overall_compliance_rate', 0.0)) >= 1.0,
        'no_total_violations': int(scaffold_summary.get('total_violations', 0)) == 0,
        'runtime_obedience_checks_pass': bool(obedience_report.get('all_checks_pass', False)),
        'runtime_surface_alignment': report_surface_consistency,
        'runtime_stage_metadata_complete': runtime_stage_metadata_complete,
        'no_component_violations': no_component_violations,
        'components_high_compliance': all_components_high,
        'world_image_law_preserved': bool(scaffold_summary.get('world_authority_primary', False)) and bool(scaffold_summary.get('image_access_primary', False)),
        'evidence_scope_non_clearing': bool(scaffold_summary.get('gate_clearance_authority', True)) is False,
        'scaffold_scope_explicit': str(scaffold_summary.get('report_scope', '')) == 'gate_2_runtime_obedience_scaffold',
        'reporting_rules_explicit': str(scaffold_summary.get('reporting_rules_version', '')) == 'AUREXIS_RUNTIME_OBEDIENCE_REPORTING_RULES_V1',
    }
    complete = all(audit_checks.values())
    return {
        'audit_rules_version': AUDIT_RULES_VERSION,
        'completion_authority': COMPLETION_AUTHORITY,
        'audit_checks': audit_checks,
        'blocking_components': blocking_components,
        'all_audit_checks_pass': complete,
        'gate_2_complete': complete,
        'summary': 'Gate 2 completion audit passed' if complete else 'Gate 2 completion audit still blocked',
    }
