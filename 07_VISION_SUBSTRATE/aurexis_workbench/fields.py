"""Typed measurement field model.

A *measurement field* is a named, typed value produced by running a
captured signal through a primitive measurement. The substrate is
typed: every field has a known dtype, and operators check against
those dtypes at compile time.

Field dtypes (v2.0):
    image     a 2-D float array in [0, 1]
    scalar    a single float
    int       a single integer
    bool      a single boolean
    regions   a list of 2-D boolean masks (connected-component-style)
    vector    a 1-D float array
    label     a string label (e.g. "ascending", "vertical")

A FieldBundle is a named collection of FieldValue objects keyed by
field name. Scenarios produce FieldBundles; predicates consume them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VALID_DTYPES = {"image", "scalar", "int", "bool",
                  "regions", "vector", "label",
                  "image_stack"}


@dataclass
class FieldSpec:
    name: str
    dtype: str
    description: str = ""

    def __post_init__(self):
        if self.dtype not in VALID_DTYPES:
            raise ValueError("unknown dtype: " + repr(self.dtype))


@dataclass
class FieldValue:
    spec: FieldSpec
    value: Any

    @property
    def dtype(self) -> str:
        return self.spec.dtype

    @property
    def name(self) -> str:
        return self.spec.name


@dataclass
class FieldBundle:
    """Named collection of FieldValue objects."""
    name: str
    fields: Dict[str, FieldValue] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def add(self, fv: FieldValue) -> None:
        self.fields[fv.name] = fv

    def add_value(self, name: str, dtype: str, value: Any,
                   description: str = "") -> None:
        self.add(FieldValue(FieldSpec(name, dtype, description), value))

    def get(self, name: str) -> FieldValue:
        if name not in self.fields:
            raise KeyError("field not in bundle: " + name)
        return self.fields[name]

    def has(self, name: str) -> bool:
        return name in self.fields

    def names(self) -> List[str]:
        return list(self.fields.keys())

    def types(self) -> Dict[str, str]:
        return {k: v.dtype for k, v in self.fields.items()}
