"""Gate 3 secondary route report surface helpers."""
from __future__ import annotations

from typing import Any, Dict, Mapping

GATE_3_ROUTE_REPORT_RULES_VERSION = "AUREXIS_GATE_3_SECOND_ROUTE_RULES_V1"


def _unique(seq):
    out=[]
    seen=set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_gate3_route_report_surface(*, route_kind: str, summary: Mapping[str, Any], comparison_package: Mapping[str, Any], earned_candidate: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    gate3_loop = dict(comparison_package.get("gate3_evidence_loop", {}) or {})
    batch_comp = dict(comparison_package.get("gate3_batch_comparison", {}) or {})
    comparison = dict(batch_comp.get("comparison", {}) or {})
    audit = dict(batch_comp.get("earned_audit", {}) or {})
    earned_candidate = dict(earned_candidate or {})
    source_counts = dict(gate3_loop.get("source_counts", {}) or {})
    if bool(earned_candidate.get("earned_promotion_passed", False)):
        source_counts = dict(earned_candidate.get("source_counts", source_counts) or source_counts)
    blocking = _unique(list(gate3_loop.get("blocking_reasons", [])) + list(comparison.get("blocking_reasons", [])) + list(audit.get("blocking_reasons", [])) + list(earned_candidate.get("blocking_reasons", [])))
    return {
        "route_kind": route_kind,
        "report_scope": f"gate3_{route_kind}_report",
        "report_rules_version": GATE_3_ROUTE_REPORT_RULES_VERSION,
        "gate_clearance_authority": False,
        "output_honesty_explicit": True,
        "comparison_ready": bool(comparison.get("comparison_ready", False)),
        "earned_candidate_ready": bool(gate3_loop.get("earned_candidate_ready", False)),
        "earned_audit_ready": bool(audit.get("earned_audit_ready", False)),
        "earned_promotion_ready": bool(earned_candidate.get("earned_promotion_ready", False)),
        "earned_promotion_passed": bool(earned_candidate.get("earned_promotion_passed", False)),
        "promoted_evidence_tier": earned_candidate.get("promoted_evidence_tier", "real-capture"),
        "source_counts": source_counts,
        "blocking_reasons": blocking,
        "summary": dict(summary or {}),
    }
