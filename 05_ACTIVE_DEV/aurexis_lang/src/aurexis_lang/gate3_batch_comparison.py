
"""Gate 3 batch comparison helpers.

Bridges saved evidence batches into the authored-vs-real-capture comparison/audit path.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

from .gate3_comparison_audit import (
    build_authored_reference_surface,
    build_real_capture_reference_surface,
    compare_authored_real_capture_surfaces,
    audit_gate3_earned_evidence_scaffold,
    GATE_3_COMPARISON_RULES_VERSION,
    GATE_3_AUDIT_RULES_VERSION,
)

GATE_3_BATCH_COMPARISON_RULES_VERSION = 'AUREXIS_GATE_3_BATCH_COMPARISON_RULES_V1'

def compare_authored_summary_to_batch(*, authored_summary: Mapping[str, Any], batch_summary: Mapping[str, Any], gate3_evidence_loop: Mapping[str, Any]) -> Dict[str, Any]:
    authored_surface = build_authored_reference_surface(authored_summary)
    real_capture_surface = build_real_capture_reference_surface(batch_summary)
    comparison = compare_authored_real_capture_surfaces(
        authored_surface=authored_surface,
        real_capture_surface=real_capture_surface,
        gate3_evidence_loop=gate3_evidence_loop,
    )
    audit = audit_gate3_earned_evidence_scaffold(
        comparison_summary=comparison,
        gate3_evidence_loop=gate3_evidence_loop,
    )
    return {
        'rules_version': GATE_3_BATCH_COMPARISON_RULES_VERSION,
        'gate_clearance_authority': False,
        'authored_reference_surface': authored_surface,
        'real_capture_reference_surface': real_capture_surface,
        'comparison': comparison,
        'earned_audit': audit,
        'comparison_rules_version': GATE_3_COMPARISON_RULES_VERSION,
        'audit_rules_version': GATE_3_AUDIT_RULES_VERSION,
    }
