"""Canonical minimum legal phoxel record schema helpers for Gate 1."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

TOP_LEVEL_FIELDS = (
    "image_anchor",
    "world_anchor_state",
    "photonic_signature",
    "time_slice",
    "relation_set",
    "integrity_state",
)

ALLOWED_WORLD_ANCHOR_STATUS = {"unknown", "estimated", "resolved"}


def _mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, '__dict__'):
        return dict(vars(value))
    return {}


def coerce_phoxel_schema(source: Any) -> Dict[str, Any]:
    """Return the canonical minimum legal phoxel schema.

    Accepts the existing flat record/object shape used by the active phase-1 code
    and projects it into the Gate 1 canonical law structure.
    """
    data = _mapping(source)

    # Nested canonical input wins when already present.
    if all(key in data for key in TOP_LEVEL_FIELDS):
        schema = {key: _mapping(data.get(key)) if key != 'relation_set' else list(data.get(key) or []) for key in TOP_LEVEL_FIELDS}
        if not isinstance(schema['relation_set'], list):
            schema['relation_set'] = list(schema['relation_set'])
        return schema

    image_anchor = _mapping(data.get('image_anchor'))
    if not image_anchor:
        image_anchor = {
            'pixel_coordinates': data.get('pixel_coordinates'),
        }

    world_anchor_state = _mapping(data.get('world_anchor_state'))
    if not world_anchor_state:
        world_anchor_state = {
            'status': 'unknown',
            'world_coordinates': None,
            'evidence_status': 'image-grounded-only',
        }

    photonic_signature = _mapping(data.get('photonic_signature'))
    if not photonic_signature:
        photonic_signature = {
            'pixel_data_available': data.get('pixel_data_available'),
            'camera_metadata': data.get('camera_metadata', {}),
            'measurement_origin': 'camera-observation',
        }

    time_slice = _mapping(data.get('time_slice'))
    if not time_slice:
        time_slice = {
            'image_timestamp': data.get('image_timestamp'),
        }

    relation_set = data.get('relation_set')
    if relation_set is None:
        relation_set = []
    if not isinstance(relation_set, list):
        relation_set = list(relation_set)

    integrity_state = _mapping(data.get('integrity_state'))
    if not integrity_state:
        integrity_state = {
            'evidence_chain': list(data.get('evidence_chain', [])),
            'synthetic': bool(data.get('synthetic', False)),
            'traceable': bool(data.get('evidence_chain')),
        }

    return {
        'image_anchor': image_anchor,
        'world_anchor_state': world_anchor_state,
        'photonic_signature': photonic_signature,
        'time_slice': time_slice,
        'relation_set': relation_set,
        'integrity_state': integrity_state,
    }


def validate_phoxel_schema(source: Any) -> List[str]:
    schema = coerce_phoxel_schema(source)
    errors: List[str] = []

    for key in TOP_LEVEL_FIELDS:
        if key not in schema:
            errors.append(f'missing_top_level:{key}')

    pixel_coordinates = schema.get('image_anchor', {}).get('pixel_coordinates')
    if not pixel_coordinates:
        errors.append('missing_image_anchor.pixel_coordinates')

    status = schema.get('world_anchor_state', {}).get('status')
    if status not in ALLOWED_WORLD_ANCHOR_STATUS:
        errors.append('invalid_world_anchor_state.status')

    if 'pixel_data_available' not in schema.get('photonic_signature', {}):
        errors.append('missing_photonic_signature.pixel_data_available')

    if 'camera_metadata' not in schema.get('photonic_signature', {}):
        errors.append('missing_photonic_signature.camera_metadata')

    if 'image_timestamp' not in schema.get('time_slice', {}):
        errors.append('missing_time_slice.image_timestamp')
    else:
        timestamp = schema['time_slice'].get('image_timestamp')
        if timestamp is None:
            errors.append('missing_time_slice.image_timestamp')
        elif not isinstance(timestamp, (datetime, str)):
            errors.append('invalid_time_slice.image_timestamp')

    if not isinstance(schema.get('relation_set'), list):
        errors.append('invalid_relation_set')

    integrity_state = schema.get('integrity_state', {})
    if 'evidence_chain' not in integrity_state:
        errors.append('missing_integrity_state.evidence_chain')
    elif not isinstance(integrity_state.get('evidence_chain'), list):
        errors.append('invalid_integrity_state.evidence_chain')

    if 'synthetic' not in integrity_state:
        errors.append('missing_integrity_state.synthetic')
    elif integrity_state.get('synthetic'):
        errors.append('forbidden_integrity_state.synthetic_true')

    return errors
