"""Typed field model for the Workbench.

A FieldBundle is a dict of named, typed fields. The whole substrate is
typed: every field has a known dtype, and operators check against
those dtypes at compile time.

Field dtypes (v2.0):
  image         -- 2D float array in [0,1] (luma).
  scalar        -- single float.
  int           -- single int.
  bool          -- single bool.
  regions       -- list of (y, x, h, w) tuples.
  vector        -- 1D float array.
  label         -- string token (e.g. axis="x").
  image_stack   -- 3D float array (T, H, W) - bursts, exposure stacks, etc.
  color_image   -- 3D float array (H, W, 3) in [0,1] - RGB image.
  depth         -- 2D float array in [0,1] - depth map (R107).
  hyperspectral -- 3D float array (H, W, N_BANDS) in [0,1] - spectral cube (R107).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VALID_DTYPES = {"image", "scalar", "int", "bool",
                  "regions", "vector", "label",
                  "image_stack",
                  "color_image",
                  "depth",          # added R107 (R103 first light)
                  "hyperspectral"}  # added R107 (R104 first light)


@dataclass
class FieldSpec:
    name: str
    dtype: str
    description: Optional[str] = None

    def __post_init__(self):
        if self.dtype not in VALID_DTYPES:
            raise ValueError("unknown dtype: " + repr(self.dtype))


@dataclass
class FieldValue:
    spec: FieldSpec
    value: Any

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def dtype(self) -> str:
        return self.spec.dtype


@dataclass
class FieldBundle:
    name: str
    fields: Dict[str, FieldValue] = field(default_factory=dict)

    def add(self, fv: FieldValue) -> None:
        self.fields[fv.spec.name] = fv

    def add_value(self, name: str, dtype: str, value: Any,
                    description: Optional[str] = None) -> None:
        self.add(FieldValue(FieldSpec(name, dtype, description), value))

    def get(self, name: str) -> FieldValue:
        if name not in self.fields:
            raise KeyError("field not in bundle: " + name)
        return self.fields[name]

    def has(self, name: str) -> bool:
        return name in self.fields

    def names(self) -> List[str]:
        return sorted(self.fields.keys())

    def types(self) -> Dict[str, str]:
        return {k: v.dtype for k, v in self.fields.items()}
