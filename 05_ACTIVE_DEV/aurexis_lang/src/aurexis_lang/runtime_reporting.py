"""Shared Gate 2 runtime reporting helpers."""

from __future__ import annotations

from typing import Any, Dict

RUNTIME_REPORTING_RULES_VERSION = "AUREXIS_RUNTIME_OBEDIENCE_REPORTING_RULES_V1"
RUNTIME_EVIDENCE_SCOPE = "authored/runtime"
RUNTIME_GATE_STATUS = "IN_PROGRESS"
RUNTIME_STAGE_METADATA_VERSION = "AUREXIS_GATE_2_RUNTIME_STAGE_METADATA_RULES_V1"
RUNTIME_ALIGNMENT_TARGET = "AUREXIS_GATE_2_REPORT_SURFACE_ALIGNMENT_RULES_V1"


def stamp_runtime_surface(payload: Dict[str, Any], scope: str) -> Dict[str, Any]:
    payload["report_scope"] = scope
    payload["gate_2_status"] = RUNTIME_GATE_STATUS
    payload["reporting_rules_version"] = RUNTIME_REPORTING_RULES_VERSION
    payload["stage_metadata_version"] = RUNTIME_STAGE_METADATA_VERSION
    payload["report_surface_alignment_target"] = RUNTIME_ALIGNMENT_TARGET
    payload["evidence_scope"] = RUNTIME_EVIDENCE_SCOPE
    payload["gate_clearance_authority"] = False
    payload["world_authority_primary"] = True
    payload["image_access_primary"] = True
    payload["partial_reporting_explicit"] = True
    payload["stage_metadata_complete"] = True
    return payload
