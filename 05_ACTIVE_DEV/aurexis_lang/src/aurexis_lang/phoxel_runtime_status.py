"""Helpers for surfacing explicit phoxel-law status in active Gate 2 runtime paths."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .phoxel_schema import coerce_phoxel_schema, validate_phoxel_schema


def _normalize_execution_status(execution_status: Any) -> Optional[str]:
    if execution_status is None:
        return None
    value = getattr(execution_status, 'value', execution_status)
    text = str(value).strip().lower()
    return text or None


def summarize_phoxel_runtime_status(
    record: Any,
    *,
    evidence_validated: bool = False,
    execution_status: Any = None,
    relation_count: int = 0,
) -> Dict[str, Any]:
    """Return an explicit runtime-facing summary of the canonical phoxel-law fields."""
    schema = coerce_phoxel_schema(record)
    schema_errors = validate_phoxel_schema(schema)
    normalized_status = _normalize_execution_status(execution_status)

    if normalized_status == 'executable':
        observation_status = 'executable'
    elif normalized_status == 'validated' or evidence_validated:
        observation_status = 'validated'
    elif schema.get('world_anchor_state', {}).get('status') == 'estimated':
        observation_status = 'estimated'
    else:
        observation_status = 'observed'

    image_anchor = schema.get('image_anchor', {})
    world_anchor_state = schema.get('world_anchor_state', {})
    photonic_signature = schema.get('photonic_signature', {})
    time_slice = schema.get('time_slice', {})
    relation_set = schema.get('relation_set', [])
    integrity_state = schema.get('integrity_state', {})
    evidence_chain = integrity_state.get('evidence_chain', []) or []

    return {
        'observation_status': observation_status,
        'image_anchor': {
            'present': bool(image_anchor.get('pixel_coordinates')),
            'pixel_coordinates': image_anchor.get('pixel_coordinates'),
        },
        'world_anchor_state': {
            'status': world_anchor_state.get('status', 'unknown'),
            'evidence_status': world_anchor_state.get('evidence_status', 'image-grounded-only'),
            'world_coordinates_present': world_anchor_state.get('world_coordinates') is not None,
        },
        'photonic_signature': {
            'pixel_data_available': bool(photonic_signature.get('pixel_data_available')),
            'measurement_origin': photonic_signature.get('measurement_origin', 'camera-observation'),
        },
        'time_slice': {
            'present': bool(time_slice.get('image_timestamp')),
            'image_timestamp': time_slice.get('image_timestamp'),
        },
        'relation_links': {
            'count': max(int(relation_count), len(relation_set)),
        },
        'integrity': {
            'traceable': bool(integrity_state.get('traceable', evidence_chain)),
            'synthetic': bool(integrity_state.get('synthetic', False)),
            'evidence_chain_length': len(evidence_chain),
            'schema_errors': schema_errors,
        },
    }



def extract_phoxel_runtime_status(subject: Any) -> Dict[str, Any]:
    """Return explicit runtime status from AST/runtime objects or step dictionaries when present."""
    if isinstance(subject, dict):
        direct = subject.get("phoxel_runtime_status")
        if isinstance(direct, dict):
            return direct
        if "observation_status" in subject and "image_anchor" in subject and "integrity" in subject:
            return subject
        return {}
    direct = getattr(subject, "phoxel_runtime_status", None)
    if isinstance(direct, dict):
        return direct
    attributes = getattr(subject, "attributes", None)
    if isinstance(attributes, dict) and isinstance(attributes.get("phoxel_runtime_status"), dict):
        return attributes["phoxel_runtime_status"]
    record = getattr(subject, "phoxel_record", None)
    if record is None:
        return {}
    node_type = str(getattr(subject, "node_type", "")).lower()
    relation_count = 1 if node_type.endswith("relation_declaration") else 0
    return summarize_phoxel_runtime_status(
        record,
        evidence_validated=bool(getattr(subject, "evidence_validated", False)),
        execution_status=getattr(subject, "execution_status", None),
        relation_count=relation_count,
    )


def rollup_phoxel_runtime_statuses(statuses: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    explicit = 0
    traceable = 0
    image_anchor_present = 0
    world_anchor_present = 0
    relation_link_count = 0
    for status in statuses:
        if not isinstance(status, dict) or not status:
            continue
        explicit += 1
        obs = str(status.get("observation_status", "unknown"))
        counts[obs] = counts.get(obs, 0) + 1
        if bool(status.get("integrity", {}).get("traceable", False)):
            traceable += 1
        if bool(status.get("image_anchor", {}).get("present", False)):
            image_anchor_present += 1
        if bool(status.get("world_anchor_state", {}).get("world_coordinates_present", False)):
            world_anchor_present += 1
        relation_link_count += int(status.get("relation_links", {}).get("count", 0) or 0)
    return {
        "explicit_count": explicit,
        "observation_status_counts": counts,
        "traceable_count": traceable,
        "image_anchor_present_count": image_anchor_present,
        "world_anchor_present_count": world_anchor_present,
        "relation_link_count": relation_link_count,
    }


def collect_step_phoxel_runtime_statuses(steps: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for step in steps or []:
        status = extract_phoxel_runtime_status(step)
        if status:
            collected.append(status)
        nested = step.get("nested_output_steps") if isinstance(step, dict) else None
        if nested:
            collected.extend(collect_step_phoxel_runtime_statuses(nested))
    return collected
