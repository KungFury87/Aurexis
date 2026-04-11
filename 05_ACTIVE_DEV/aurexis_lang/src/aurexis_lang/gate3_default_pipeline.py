"""Gate 3 default pipeline entry and package state stamp helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

GATE_3_DEFAULT_PIPELINE_RULES_VERSION = "AUREXIS_GATE_3_DEFAULT_PIPELINE_ENTRY_V1"
GATE_3_PACKAGE_STATE_STAMP_RULES_VERSION = "AUREXIS_GATE_3_PACKAGE_STATE_STAMP_V1"
GATE_3_DEFAULT_PIPELINE_AUTHORITY = "gate3_default_pipeline_after_regeneration"


def build_gate3_default_pipeline_stamp(*, project_root: str | Path, batch_name: str, regeneration_output: Mapping[str, Any], final_completion_report: Mapping[str, Any]) -> Dict[str, Any]:
    project_root = Path(project_root)
    stamp = {
        'report_scope': 'gate3_default_pipeline_stamp',
        'default_pipeline_rules_version': GATE_3_DEFAULT_PIPELINE_RULES_VERSION,
        'package_state_stamp_rules_version': GATE_3_PACKAGE_STATE_STAMP_RULES_VERSION,
        'default_pipeline_authority': GATE_3_DEFAULT_PIPELINE_AUTHORITY,
        'gate_3_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'output_honesty_explicit': True,
        'batch_name': batch_name,
        'packaged_default_state_regenerated': bool(regeneration_output.get('default_saved_state_complete', False) or final_completion_report.get('packaged_default_state_regenerated', False)),
        'default_saved_state_complete': bool(final_completion_report.get('default_saved_state_complete', False)),
        'gate_3_complete_after_regeneration': bool(final_completion_report.get('gate_3_complete_after_regeneration', False)),
        'packaged_state_ready_for_shipping': bool(final_completion_report.get('default_saved_state_complete', False)),
        'regeneration_source': final_completion_report.get('regeneration_source', batch_name),
        'final_completion_report_scope': final_completion_report.get('report_scope', ''),
    }
    out = project_root / 'processing_results' / 'gate3_default_pipeline_stamp.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(stamp, indent=2, default=str))
    return stamp
