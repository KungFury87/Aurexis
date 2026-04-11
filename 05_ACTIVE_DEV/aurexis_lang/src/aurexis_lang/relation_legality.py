"""Frozen relation legality / measurable-requirements helpers for Gate 1."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

PRIMARY_RELATION_KINDS = (
    "position",
    "adjacency",
    "direction",
    "distance",
    "containment",
    "boundary",
    "region_membership",
    "sequence",
)

HIGHER_ORDER_RELATION_KINDS = (
    "scale",
    "hierarchy",
    "overlap",
    "continuity",
    "transition",
)

ALLOWED_RELATION_KINDS = PRIMARY_RELATION_KINDS + HIGHER_ORDER_RELATION_KINDS


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, '__dict__'):
        return dict(vars(value))
    return {}


def _truthy_measurement(measurement: Mapping[str, Any]) -> bool:
    return any(
        measurement.get(key) is not None
        for key in (
            'observed_value',
            'value',
            'distance_px',
            'distance_world',
            'direction_vector',
            'boundary_strength',
            'overlap_ratio',
            'sequence_index',
        )
    )


def validate_relation_legality(source: Any) -> List[str]:
    relation = _mapping(source)
    errors: List[str] = []

    relation_kind = relation.get('relation_kind') or relation.get('kind') or relation.get('relation_type') or relation.get('type')
    if relation_kind not in ALLOWED_RELATION_KINDS:
        errors.append('invalid_relation_kind')

    if not relation.get('source_id'):
        errors.append('missing_source_id')
    if not relation.get('target_id'):
        errors.append('missing_target_id')

    measurement = _mapping(relation.get('physical_measurement'))
    if not measurement:
        errors.append('missing_physical_measurement')
    else:
        if not measurement.get('measurement_type'):
            errors.append('missing_physical_measurement.measurement_type')
        if not _truthy_measurement(measurement):
            errors.append('missing_physical_measurement.observed_value')

    pixel_verification = _mapping(relation.get('pixel_space_verification'))
    if not pixel_verification:
        errors.append('missing_pixel_space_verification')
    else:
        if not bool(pixel_verification.get('image_grounded', False)):
            errors.append('missing_pixel_space_verification.image_grounded_true')
        if not (
            pixel_verification.get('verification_method')
            or pixel_verification.get('pixel_path')
            or pixel_verification.get('observed_pixels')
        ):
            errors.append('missing_pixel_space_verification.support')

    if relation.get('abstract_semantic', False):
        errors.append('forbidden_abstract_semantic')

    if relation.get('world_claim', False):
        world_anchor_support = _mapping(relation.get('world_anchor_support'))
        if not world_anchor_support:
            errors.append('missing_world_anchor_support')
        elif world_anchor_support.get('status') not in {'estimated', 'resolved'}:
            errors.append('invalid_world_anchor_support.status')

    return errors
