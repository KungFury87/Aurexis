"""Gate 3 packaged default-state regeneration and final completion helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .gate3_global_completion import build_gate3_global_completion_report

GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION = "AUREXIS_GATE_3_PACKAGED_DEFAULT_STATE_REGENERATION_V1"
GATE_3_FINAL_COMPLETION_REPORT_RULES_VERSION = "AUREXIS_GATE_3_FINAL_COMPLETION_REPORT_V1"
GATE_3_FINAL_COMPLETION_AUTHORITY = "gate3_packaged_default_state_after_regeneration"


def clear_gate3_saved_outputs(*, project_root: str | Path) -> Dict[str, Any]:
    project_root = Path(project_root)
    targets = {
        'processing_results': [
            'gate3_report_*.json',
            'gate3_gate_completion_audit.json',
            'gate3_global_completion_report.json',
            'gate3_multi_route_completion_*.json',
            'gate3_canonical_seed_*.json',
            'gate3_packaged_default_state_regeneration_*.json',
            'gate3_final_completion_report.json',
        ],
        'evidence_validation': [
            'gate3_validation_report_*.json',
        ],
        'complete_evidence_loop': [
            'gate3_complete_cycle_report_*.json',
        ],
    }
    removed: List[str] = []
    for rel, patterns in targets.items():
        base = project_root / rel
        if not base.exists():
            continue
        for pattern in patterns:
            for path in base.glob(pattern):
                if path.is_file():
                    path.unlink()
                    removed.append(str(path))
    return {
        'rules_version': GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION,
        'removed_files': removed,
        'removed_count': len(removed),
    }


def build_gate3_final_completion_report(*, project_root: str | Path, regenerated: bool, regeneration_source: str | None = None) -> Dict[str, Any]:
    project_root = Path(project_root)
    global_report = build_gate3_global_completion_report(project_root=project_root)
    final_report = {
        'report_scope': 'gate3_final_completion_report',
        'packaged_default_state_rules_version': GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION,
        'final_completion_rules_version': GATE_3_FINAL_COMPLETION_REPORT_RULES_VERSION,
        'final_completion_authority': GATE_3_FINAL_COMPLETION_AUTHORITY,
        'gate_3_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'output_honesty_explicit': True,
        'packaged_default_state_regenerated': bool(regenerated),
        'regeneration_source': regeneration_source or '',
        'capability_present': bool(global_report.get('capability_present', False)),
        'default_saved_state_complete': bool(global_report.get('default_saved_state_complete', False)),
        'gate_3_complete_after_regeneration': bool(regenerated and global_report.get('default_saved_state_complete', False)),
        'default_state_blocking_components': list(global_report.get('default_state_blocking_components', []) or []),
        'default_state_gate3_gate_completion_audit': dict(global_report.get('default_state_gate3_gate_completion_audit', {}) or {}),
        'route_support': dict(global_report.get('route_support', {}) or {}),
        'saved_route_surface_count': int(global_report.get('saved_route_surface_count', 0) or 0),
        'summary': (
            'Gate 3 packaged default state has been regenerated and clears now'
            if regenerated and global_report.get('default_saved_state_complete', False)
            else 'Gate 3 packaged default state regeneration did not produce a clearing saved state yet'
        ),
    }
    out = project_root / 'processing_results' / 'gate3_final_completion_report.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(final_report, indent=2, default=str))
    return final_report
