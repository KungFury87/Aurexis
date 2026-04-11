"""Gate 3 saved-run aggregation and gate-level audit helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .gate3_gate_completion_audit import audit_gate3_gate_completion

GATE_3_SAVED_RUN_RULES_VERSION = "AUREXIS_GATE_3_SAVED_RUN_RULES_V1"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def collect_gate3_saved_route_surfaces(*, project_root: Path | str) -> List[Dict[str, Any]]:
    project_root = Path(project_root)
    surfaces: List[Dict[str, Any]] = []

    processing_dir = project_root / 'processing_results'
    if processing_dir.exists():
        for report_file in sorted(processing_dir.glob('gate3_report_*.json')):
            data = _load_json(report_file)
            surface = dict(data.get('gate3_batch_report', {}) or {})
            if not surface:
                continue
            surface['completion_audit_passed'] = bool(data.get('gate3_completion_audit', {}).get('gate_3_complete', False))
            surface['saved_run_origin'] = report_file.name
            surfaces.append(surface)

    for route_dir_name in ('evidence_validation', 'complete_evidence_loop'):
        route_dir = project_root / route_dir_name
        if not route_dir.exists():
            continue
        for report_file in sorted(route_dir.glob('*.json')):
            data = _load_json(report_file)
            surface = dict(data.get('gate_3_route_report', {}) or {})
            if not surface:
                continue
            surface['completion_audit_passed'] = bool(data.get('gate_3_completion_audit', {}).get('gate_3_complete', False))
            surface['saved_run_origin'] = report_file.name
            surfaces.append(surface)

    return surfaces


def build_gate3_gate_completion_audit_from_project_root(*, project_root: Path | str) -> Dict[str, Any]:
    project_root = Path(project_root)
    surfaces = collect_gate3_saved_route_surfaces(project_root=project_root)
    audit = audit_gate3_gate_completion(report_surfaces=surfaces)
    out = {
        'gate_3_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'report_scope': 'gate3_gate_completion_audit',
        'saved_run_rules_version': GATE_3_SAVED_RUN_RULES_VERSION,
        'route_surface_count': len(surfaces),
        'gate3_gate_completion_audit': audit,
    }
    processing_dir = project_root / 'processing_results'
    processing_dir.mkdir(exist_ok=True)
    out_file = processing_dir / 'gate3_gate_completion_audit.json'
    out_file.write_text(json.dumps(out, indent=2, default=str))
    return out
