from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .mobile_demo_target import validate_narrow_mobile_demonstration_target

GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION = "AUREXIS_GATE_4_NARROW_MOBILE_DEMONSTRATION_KICKOFF_V1"
GATE_4_PACKAGE_QUICKSTART_RULES_VERSION = "AUREXIS_RELEASE_WORKFLOW_QUICKSTART_V1"
GATE_4_KICKOFF_AUTHORITY = "gate4_narrow_mobile_demo_kickoff_after_gate3_release"


def build_gate4_narrow_mobile_demo_report(*, project_root: str | Path, batch_name: str, release_pipeline_output: Mapping[str, Any], batch_summary: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    project_root = Path(project_root)
    batch_summary = dict(batch_summary or {})
    root_stamp = dict(release_pipeline_output.get('gate3_root_package_completion_stamp', {}) or {})
    package_precleared = bool(root_stamp.get('package_precleared', False))
    claim = {
        'pc_preparation_supported': True,
        'phone_capture_supported': bool(batch_summary),
        'scope_is_narrow': True,
        'output_honesty_explicit': True,
        'no_hidden_exotic_hardware': True,
        'evidence_tier': 'earned' if package_precleared else 'real-capture',
        'app_store_ready_claim': False,
        'general_vision_claim': False,
        'production_ready_claim': False,
    }
    errors = list(validate_narrow_mobile_demonstration_target(claim))
    if not package_precleared:
        errors.append('gate3_not_precleared')
    report = {
        'report_scope': 'gate4_narrow_mobile_demo_kickoff',
        'rules_version': GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION,
        'quickstart_rules_version': GATE_4_PACKAGE_QUICKSTART_RULES_VERSION,
        'kickoff_authority': GATE_4_KICKOFF_AUTHORITY,
        'gate_4_status': 'IN_PROGRESS',
        'gate_clearance_authority': False,
        'output_honesty_explicit': True,
        'batch_name': batch_name,
        'gate3_package_precleared': package_precleared,
        'gate3_package_completion_state': root_stamp.get('package_completion_state', 'NOT_PRE_CLEARED'),
        'phone_capture_supported': claim['phone_capture_supported'],
        'scope_is_narrow': True,
        'demonstration_ready': len(errors) == 0,
        'blocking_reasons': errors,
        'claim': claim,
        'batch_summary_present': bool(batch_summary),
        'batch_size': int(batch_summary.get('batch_size', 0) or 0),
        'entry_command': 'python run_gate4_narrow_mobile_demo.py [batch_name]',
    }
    out = project_root / 'AUREXIS_GATE_4_NARROW_MOBILE_DEMO_REPORT.json'
    out.write_text(json.dumps(report, indent=2, default=str))
    return report
