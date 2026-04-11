"""Terminology normalization helpers for Aurexis cleanup work.

Canonical project term: phoxel.
Legacy compatibility alias retained for older prototype paths.
These helpers let existing prototype surfaces accept both while pushing new
code/doc surfaces toward the canonical term.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

CANONICAL_RECORD_KEY = "phoxel_record"
LEGACY_RECORD_KEY = "phixel_record"
CANONICAL_TERM = "phoxel"
LEGACY_TERM = "phixel"


def get_phoxel_record(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Return the canonical phoxel record, accepting the remaining legacy record alias input."""
    if CANONICAL_RECORD_KEY in mapping and isinstance(mapping[CANONICAL_RECORD_KEY], dict):
        return mapping[CANONICAL_RECORD_KEY]
    if LEGACY_RECORD_KEY in mapping and isinstance(mapping[LEGACY_RECORD_KEY], dict):
        return mapping[LEGACY_RECORD_KEY]
    return {}


def canonicalize_record_keys(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow-copied mapping with phoxel_record present when possible.

    Legacy record alias is preserved for backward compatibility if it already exists.
    """
    data = deepcopy(mapping)
    record = get_phoxel_record(data)
    if record and CANONICAL_RECORD_KEY not in data:
        data[CANONICAL_RECORD_KEY] = deepcopy(record)
    return data


def with_legacy_alias(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow-copied mapping that includes both canonical and legacy record keys."""
    data = canonicalize_record_keys(mapping)
    if CANONICAL_RECORD_KEY in data and LEGACY_RECORD_KEY not in data:
        data[LEGACY_RECORD_KEY] = deepcopy(data[CANONICAL_RECORD_KEY])
    return data
