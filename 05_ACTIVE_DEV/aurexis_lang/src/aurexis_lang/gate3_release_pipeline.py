"""Gate 3 release/build-style pipeline and root package completion stamp helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

GATE_3_RELEASE_PIPELINE_RULES_VERSION = "AUREXIS_GATE_3_RELEASE_BUILD_PIPELINE_V1"
GATE_3_ROOT_PACKAGE_COMPLETION_STAMP_RULES_VERSION = "AUREXIS_GATE_3_ROOT_PACKAGE_COMPLETION_STAMP_V1"
GATE_3_RELEASE_PIPELINE_AUTHORITY = "gate3_release_pipeline_after_default_pipeline"


def build_gate3_root_package_completion_stamp(*, project_root: str | Path, batch_name: str, default_pipeline_output: Mapping[str, Any], final_completion_report: Mapping[str, Any]) -> Dict[str, Any]:
    project_root = Path(project_root)
    stamp = {
        'report_scope': 'gate3_root_package_completion_stamp',
        'release_pipeline_rules_version': GATE_3_RELEASE_PIPELINE_RULES_VERSION,
        'root_package_completion_stamp_rules_version': GATE_3_ROOT_PACKAGE_COMPLETION_STAMP_RULES_VERSION,
        'release_pipeline_authority': GATE_3_RELEASE_PIPELINE_AUTHORITY,
        'gate_3_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'output_honesty_explicit': True,
        'batch_name': batch_name,
        'capability_present': bool(final_completion_report.get('capability_present', False)),
        'default_saved_state_complete': bool(final_completion_report.get('default_saved_state_complete', False)),
        'gate_3_complete_after_regeneration': bool(final_completion_report.get('gate_3_complete_after_regeneration', False)),
        'package_precleared': bool(final_completion_report.get('default_saved_state_complete', False)),
        'package_completion_state': 'PRE_CLEARED' if final_completion_report.get('default_saved_state_complete', False) else 'NOT_PRE_CLEARED',
        'default_pipeline_run_file': str(default_pipeline_output.get('saved_results', {}).get('gate3_default_pipeline_run_file', '')),
        'default_pipeline_stamp_file': str(default_pipeline_output.get('saved_results', {}).get('gate3_default_pipeline_stamp_file', '')),
        'final_completion_report_scope': final_completion_report.get('report_scope', ''),
        'final_completion_summary': final_completion_report.get('summary', ''),
    }
    out = project_root / 'AUREXIS_GATE_3_PACKAGE_COMPLETION_STAMP.json'
    out.write_text(json.dumps(stamp, indent=2, default=str))
    return stamp
