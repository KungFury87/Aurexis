"""Formal Gate 3 gate-level completion audit helpers."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, List

GATE_3_GATE_COMPLETION_AUDIT_RULES_VERSION = "AUREXIS_GATE_3_GATE_COMPLETION_AUDIT_V1"
GATE_3_GATE_COMPLETION_AUTHORITY = "earned_evidence_audit_plus_multi_route_coverage"


def _classify_route(scope: str) -> str:
    scope = str(scope or "")
    if scope.startswith("gate3_batch_report"):
        return "batch_report"
    if scope.startswith("gate3_") and scope.endswith("_report"):
        return scope[len("gate3_"):]
    return "unknown"


def audit_gate3_gate_completion(*, report_surfaces: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    surfaces: List[Dict[str, Any]] = [dict(s or {}) for s in report_surfaces or []]
    route_kinds = sorted({_classify_route(s.get('report_scope', '')) for s in surfaces if s})

    authored_total = 0
    real_capture_total = 0
    earned_total = 0
    any_earned_promotion = False
    any_completion_pass = False
    any_blocking_reasons = False
    all_honest = True
    all_non_clearing = True

    for surface in surfaces:
        counts = dict(surface.get('source_counts', {}) or {})
        authored_total += int(counts.get('authored', 0) or 0)
        real_capture_total += int(counts.get('real-capture', 0) or 0)
        earned_total += int(counts.get('earned', 0) or 0)
        any_earned_promotion = any_earned_promotion or bool(surface.get('earned_promotion_passed', False))
        any_completion_pass = any_completion_pass or bool(surface.get('gate3_completion_audit', {}).get('gate_3_complete', False)) or bool(surface.get('completion_audit_passed', False))
        any_blocking_reasons = any_blocking_reasons or bool(surface.get('blocking_reasons', []))
        all_honest = all_honest and bool(surface.get('output_honesty_explicit', False))
        all_non_clearing = all_non_clearing and (bool(surface.get('gate_clearance_authority', True)) is False)

    audit_checks = {
        'report_surfaces_present': len(surfaces) > 0,
        'multiple_evidence_routes_present': len([r for r in route_kinds if r != 'unknown']) >= 2,
        'authored_inputs_present': authored_total > 0,
        'real_capture_inputs_present': real_capture_total > 0,
        'earned_inputs_present': earned_total > 0,
        'earned_promotion_present': any_earned_promotion,
        'at_least_one_completion_ready_surface': any_completion_pass,
        'all_surfaces_output_honest': all_honest,
        'all_surfaces_non_clearing': all_non_clearing,
        'no_surface_blocking_reasons': not any_blocking_reasons,
    }

    gate_3_complete = all(audit_checks.values())
    blocking_components = [name for name, ok in audit_checks.items() if not ok]

    return {
        'audit_rules_version': GATE_3_GATE_COMPLETION_AUDIT_RULES_VERSION,
        'completion_authority': GATE_3_GATE_COMPLETION_AUTHORITY,
        'route_kinds': route_kinds,
        'report_surface_count': len(surfaces),
        'aggregate_source_counts': {
            'authored': authored_total,
            'real-capture': real_capture_total,
            'earned': earned_total,
        },
        'audit_checks': audit_checks,
        'blocking_components': blocking_components,
        'all_audit_checks_pass': gate_3_complete,
        'gate_3_complete': gate_3_complete,
        'summary': 'Gate 3 gate-level audit passed' if gate_3_complete else 'Gate 3 gate-level audit still blocked',
    }
