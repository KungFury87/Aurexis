"""
Aurexis Core — Visual Parser V1 (DETERMINISTIC)

Converts raw CV extraction output into typed V1 grammar primitives.
This is the bridge between heuristic CV (which produces bounding boxes
and confidence scores) and the deterministic V1 grammar (which evaluates
geometry under frozen law).

The parser itself is deterministic: given the same CV output dict,
it produces the same VisualPrimitive every time. The *heuristic* is
in the CV extractor that produced the input — the parser just maps
the structure faithfully.

Accepted input formats:
  1. CV primitive dict (from existing aurexis_lang CV extractors)
  2. Zone manifest dict (from camera_primitive_extractor.py)
  3. Raw bbox dict (minimal format for testing)

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, BoundingBox, VisualPrimitive, GrammarLaw, V1_LAW,
)


# ════════════════════════════════════════════════════════════
# KIND CLASSIFICATION — deterministic mapping rules
# ════════════════════════════════════════════════════════════

# These mappings define how CV extractor labels map to V1 primitive kinds.
# The mapping is frozen. If a CV label isn't in this table, it maps to REGION
# (the default primitive kind — safest assumption for an unknown bounded area).

_KIND_MAP: Dict[str, PrimitiveKind] = {
    # Region labels (from various CV extractors)
    "region": PrimitiveKind.REGION,
    "segment": PrimitiveKind.REGION,
    "blob": PrimitiveKind.REGION,
    "color_region": PrimitiveKind.REGION,
    "contour": PrimitiveKind.REGION,
    "connected_component": PrimitiveKind.REGION,

    # Edge labels
    "edge": PrimitiveKind.EDGE,
    "boundary": PrimitiveKind.EDGE,
    "line": PrimitiveKind.EDGE,
    "edge_segment": PrimitiveKind.EDGE,

    # Point labels
    "point": PrimitiveKind.POINT,
    "keypoint": PrimitiveKind.POINT,
    "corner": PrimitiveKind.POINT,
    "feature": PrimitiveKind.POINT,
    "orb_keypoint": PrimitiveKind.POINT,
}

_DEFAULT_KIND = PrimitiveKind.REGION


def classify_kind(label: str) -> PrimitiveKind:
    """
    Deterministic kind classification from CV label string.
    Case-insensitive. Unknown labels default to REGION.
    """
    return _KIND_MAP.get(label.lower().strip(), _DEFAULT_KIND)


# ════════════════════════════════════════════════════════════
# SINGLE PRIMITIVE PARSING
# ════════════════════════════════════════════════════════════

def parse_primitive(raw: Dict[str, Any]) -> Optional[VisualPrimitive]:
    """
    Parse a single raw CV dict into a VisualPrimitive.

    Accepted dict formats:

    Format 1 — CV extractor output:
        {
            "type": "region",          # or "edge", "keypoint", etc.
            "bbox": [x, y, w, h],      # or {"x": ..., "y": ..., "width": ..., "height": ...}
            "confidence": 0.85,        # optional, defaults to 0.0
            ...extra attributes...
        }

    Format 2 — Zone manifest:
        {
            "kind": "REGION",          # V1 kind name directly
            "x": 10, "y": 20,
            "width": 100, "height": 80,
            "confidence": 0.9,
            ...
        }

    Format 3 — Minimal bbox:
        {
            "x": 10, "y": 20, "w": 100, "h": 80,
        }

    Returns None if the dict cannot be parsed into a valid structure.
    """
    try:
        # Resolve kind
        kind = _resolve_kind(raw)

        # Resolve bbox
        bbox = _resolve_bbox(raw)
        if bbox is None:
            return None

        # Resolve confidence
        conf = float(raw.get("confidence", raw.get("source_confidence", 0.0)))
        conf = max(0.0, min(1.0, conf))  # Clamp to [0.0, 1.0]

        # Collect extra attributes (anything that's not a structural key)
        _structural_keys = {
            "type", "kind", "bbox", "confidence", "source_confidence",
            "x", "y", "w", "h", "width", "height",
        }
        attrs = {k: v for k, v in raw.items() if k not in _structural_keys}

        return VisualPrimitive(
            kind=kind,
            bbox=bbox,
            source_confidence=conf,
            attributes=attrs,
        )

    except (KeyError, TypeError, ValueError):
        return None


def _resolve_kind(raw: Dict[str, Any]) -> PrimitiveKind:
    """Resolve primitive kind from raw dict."""
    # Direct V1 kind name (e.g., from zone manifest)
    if "kind" in raw:
        kind_str = str(raw["kind"]).upper().strip()
        for pk in PrimitiveKind:
            if pk.name == kind_str:
                return pk

    # CV type label
    if "type" in raw:
        return classify_kind(str(raw["type"]))

    return _DEFAULT_KIND


def _resolve_bbox(raw: Dict[str, Any]) -> Optional[BoundingBox]:
    """Resolve bounding box from raw dict."""
    # Format 1: "bbox" key as list [x, y, w, h]
    if "bbox" in raw:
        bbox_val = raw["bbox"]
        if isinstance(bbox_val, (list, tuple)) and len(bbox_val) >= 4:
            return BoundingBox(
                x=float(bbox_val[0]),
                y=float(bbox_val[1]),
                width=float(bbox_val[2]),
                height=float(bbox_val[3]),
            )
        if isinstance(bbox_val, dict):
            return BoundingBox(
                x=float(bbox_val.get("x", 0)),
                y=float(bbox_val.get("y", 0)),
                width=float(bbox_val.get("width", bbox_val.get("w", 0))),
                height=float(bbox_val.get("height", bbox_val.get("h", 0))),
            )

    # Format 2/3: direct x, y, width/w, height/h keys
    if "x" in raw and "y" in raw:
        w = float(raw.get("width", raw.get("w", 0)))
        h = float(raw.get("height", raw.get("h", 0)))
        return BoundingBox(
            x=float(raw["x"]),
            y=float(raw["y"]),
            width=w,
            height=h,
        )

    return None


# ════════════════════════════════════════════════════════════
# BATCH PARSING — full frame from CV output
# ════════════════════════════════════════════════════════════

def parse_frame(
    raw_primitives: List[Dict[str, Any]],
    law: GrammarLaw = V1_LAW,
) -> List[VisualPrimitive]:
    """
    Parse a list of raw CV dicts into typed VisualPrimitives.

    Filters out:
    - Unparseable dicts (returns None from parse_primitive)
    - Invalid primitives (area below minimum, zero dimensions)

    Does NOT enforce max_primitives_per_frame — that's the executor's job.
    The parser's role is structural conversion, not frame-level policy.
    """
    results = []
    for raw in raw_primitives:
        prim = parse_primitive(raw)
        if prim is not None and prim.is_valid(law):
            results.append(prim)
    return results


# ════════════════════════════════════════════════════════════
# REVERSE SERIALIZATION — primitive → dict (for storage/transport)
# ════════════════════════════════════════════════════════════

def primitive_to_dict(prim: VisualPrimitive) -> Dict[str, Any]:
    """
    Serialize a VisualPrimitive back to a dict.
    Deterministic: parse_primitive(primitive_to_dict(p)) reproduces p.
    """
    d: Dict[str, Any] = {
        "kind": prim.kind.name,
        "x": prim.bbox.x,
        "y": prim.bbox.y,
        "width": prim.bbox.width,
        "height": prim.bbox.height,
        "confidence": prim.source_confidence,
    }
    if prim.attributes:
        d.update(prim.attributes)
    return d


def frame_to_dicts(primitives: List[VisualPrimitive]) -> List[Dict[str, Any]]:
    """Serialize a list of primitives to transport format."""
    return [primitive_to_dict(p) for p in primitives]
