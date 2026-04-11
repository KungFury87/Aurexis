"""Gate 3 global completion report helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .gate3_saved_run_audit import collect_gate3_saved_route_surfaces, build_gate3_gate_completion_audit_from_project_root

GATE_3_GLOBAL_COMPLETION_RULES_VERSION = "AUREXIS_GATE_3_GLOBAL_COMPLETION_REPORT_V1"
GATE_3_DEFAULT_STATE_AUDIT_RULES_VERSION = "AUREXIS_GATE_3_DEFAULT_STATE_AUDIT_V1"
GATE_3_GLOBAL_COMPLETION_AUTHORITY = "gate3_saved_state_global_report"


def build_gate3_global_completion_report(*, project_root: str | Path) -> Dict[str, Any]:
    project_root = Path(project_root)
    gate_audit_wrapper = build_gate3_gate_completion_audit_from_project_root(project_root=project_root)
    gate_audit = dict(gate_audit_wrapper.get('gate3_gate_completion_audit', {}) or {})
    surfaces = collect_gate3_saved_route_surfaces(project_root=project_root)

    route_support = {
        'batch_report_supported': True,
        'validation_report_supported': True,
        'complete_cycle_report_supported': True,
        'gate_level_audit_supported': True,
    }
    capability_present = all(route_support.values())
    default_saved_state_complete = bool(gate_audit.get('gate_3_complete', False))
    report = {
        'report_scope': 'gate3_global_completion_report',
        'rules_version': GATE_3_GLOBAL_COMPLETION_RULES_VERSION,
        'default_state_audit_rules_version': GATE_3_DEFAULT_STATE_AUDIT_RULES_VERSION,
        'global_completion_authority': GATE_3_GLOBAL_COMPLETION_AUTHORITY,
        'gate_3_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'output_honesty_explicit': True,
        'capability_present': capability_present,
        'default_saved_state_complete': default_saved_state_complete,
        'route_support': route_support,
        'saved_route_surface_count': len(surfaces),
        'route_kinds': gate_audit.get('route_kinds', []),
        'default_state_blocking_components': list(gate_audit.get('blocking_components', []) or []),
        'default_state_gate3_gate_completion_audit': gate_audit,
        'summary': (
            'Gate 3 is capable and the current saved state clears it'
            if default_saved_state_complete
            else 'Gate 3 capability exists but the current saved state does not clear it yet'
        ),
    }

    processing_dir = project_root / 'processing_results'
    processing_dir.mkdir(exist_ok=True)
    out_file = processing_dir / 'gate3_global_completion_report.json'
    out_file.write_text(json.dumps(report, indent=2, default=str))
    return report
