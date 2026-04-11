"""
Aurexis Core — Visual Grammar V1 (FROZEN SPEC)

This is the first law-bearing slice of Aurexis Core.
It defines deterministic visual semantics for a narrow subset:

  Three primitives:  REGION, EDGE, POINT
  Three operations:  ADJACENT, CONTAINS, BIND
  One output:        RELATION nodes that are deterministically EXECUTABLE

All thresholds in this file are LAW, not heuristic magic numbers.
They are frozen and must not be changed without Vincent's authorization.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple, Any
import math


# ════════════════════════════════════════════════════════════
# GRAMMAR VERSION — frozen identifier
# ════════════════════════════════════════════════════════════

GRAMMAR_VERSION = "V1.0"
GRAMMAR_FROZEN = True


# ════════════════════════════════════════════════════════════
# PRIMITIVE TYPES — the three canonical visual primitives
# ════════════════════════════════════════════════════════════

class PrimitiveKind(Enum):
    """The three law-bearing visual primitive types in V1."""
    REGION = auto()   # Bounded color area
    EDGE = auto()     # Boundary between regions
    POINT = auto()    # Keypoint / corner


# ════════════════════════════════════════════════════════════
# OPERATION TYPES — the three canonical operations
# ════════════════════════════════════════════════════════════

class OperationKind(Enum):
    """The three law-bearing operations in V1."""
    ADJACENT = auto()   # Spatial proximity check
    CONTAINS = auto()   # Bounding box containment check
    BIND = auto()       # Name assignment to a primitive


# ════════════════════════════════════════════════════════════
# RESULT TYPES
# ════════════════════════════════════════════════════════════

class RelationResult(Enum):
    """Deterministic result of an operation evaluation."""
    TRUE = auto()
    FALSE = auto()
    ERROR = auto()


class ExecutionStatus(Enum):
    """V1 execution status. Simplified from the broader promotion ladder."""
    DETERMINISTIC = auto()   # Result is law-governed, no heuristic input
    HEURISTIC_INPUT = auto() # One or more inputs came from heuristic CV
    ERROR = auto()           # Operation could not be evaluated


# ════════════════════════════════════════════════════════════
# LAW-SET THRESHOLDS — these are law, not magic numbers
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GrammarLaw:
    """
    Frozen thresholds that govern V1 visual semantics.
    These are deterministic law. Changing them changes the language.
    """

    # ADJACENT: two primitives are adjacent if their nearest points
    # are within this pixel distance. Measured as Euclidean distance
    # between bounding box edges (not centers).
    adjacent_max_distance_px: float = 30.0

    # CONTAINS: primitive A contains primitive B if B's bounding box
    # is fully within A's bounding box with this minimum margin on
    # all sides. Margin = 0 means exact containment counts.
    contains_min_margin_px: float = 0.0

    # Minimum bounding box area for a primitive to be considered
    # valid in the grammar. Below this, it's noise.
    min_primitive_area_px2: float = 4.0

    # Maximum primitives per frame that the grammar will process.
    # Beyond this, excess primitives are dropped (lowest area first).
    max_primitives_per_frame: int = 200


# Singleton law instance
V1_LAW = GrammarLaw()


# ════════════════════════════════════════════════════════════
# PRIMITIVE SCHEMA — canonical representation
# ════════════════════════════════════════════════════════════

@dataclass
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""
    x: float       # Left edge
    y: float       # Top edge
    width: float   # Width in pixels
    height: float  # Height in pixels

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    @property
    def cx(self) -> float:
        return self.x + self.width / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.height / 2.0

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains(self, other: 'BoundingBox', margin: float = 0.0) -> bool:
        """True if other is fully within self, with optional margin."""
        return (
            other.x >= self.x + margin
            and other.y >= self.y + margin
            and other.x2 <= self.x2 - margin
            and other.y2 <= self.y2 - margin
        )

    def edge_distance(self, other: 'BoundingBox') -> float:
        """
        Minimum Euclidean distance between the edges of two bounding boxes.
        Returns 0.0 if they overlap.
        """
        dx = max(0.0, max(self.x - other.x2, other.x - self.x2))
        dy = max(0.0, max(self.y - other.y2, other.y - self.y2))
        return math.sqrt(dx * dx + dy * dy)


@dataclass
class VisualPrimitive:
    """
    A single visual primitive extracted from a camera frame.

    The primitive itself may come from heuristic CV extraction,
    but once it enters the grammar, its *relationships* are
    evaluated deterministically under V1 law.
    """
    kind: PrimitiveKind
    bbox: BoundingBox
    source_confidence: float     # From CV extractor (heuristic, 0.0-1.0)
    attributes: Dict[str, Any] = field(default_factory=dict)
    # attributes examples:
    #   REGION: {"dominant_color": "green", "area_px2": 1500}
    #   EDGE:   {"orientation_deg": 45.0, "length_px": 120}
    #   POINT:  {"descriptor_size": 31}

    def is_valid(self, law: GrammarLaw = V1_LAW) -> bool:
        """Check if this primitive meets minimum V1 law requirements."""
        return (
            self.bbox.area >= law.min_primitive_area_px2
            and self.bbox.width > 0
            and self.bbox.height > 0
        )


# ════════════════════════════════════════════════════════════
# BINDING — name assignment
# ════════════════════════════════════════════════════════════

@dataclass
class Binding:
    """A named reference to a visual primitive. Created by BIND operation."""
    name: str
    primitive: VisualPrimitive
    frame_index: int = 0


# ════════════════════════════════════════════════════════════
# RELATION — the output of ADJACENT / CONTAINS
# ════════════════════════════════════════════════════════════

@dataclass
class Relation:
    """
    The result of evaluating an operation between two primitives.
    This is the first DETERMINISTIC output in Aurexis Core V1.

    The relation result (TRUE/FALSE) is pure geometry — no confidence,
    no heuristic, no threshold tuning. It either passes the law or it doesn't.
    """
    operation: OperationKind
    operand_a: VisualPrimitive
    operand_b: VisualPrimitive
    result: RelationResult
    execution_status: ExecutionStatus
    measured_value: float           # The actual measurement (distance or margin)
    law_threshold: float            # The law threshold it was compared against
    grammar_version: str = GRAMMAR_VERSION

    @property
    def is_deterministic(self) -> bool:
        return self.execution_status == ExecutionStatus.DETERMINISTIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation.name,
            "result": self.result.name,
            "execution_status": self.execution_status.name,
            "measured_value": self.measured_value,
            "law_threshold": self.law_threshold,
            "grammar_version": self.grammar_version,
            "operand_a_kind": self.operand_a.kind.name,
            "operand_b_kind": self.operand_b.kind.name,
        }


# ════════════════════════════════════════════════════════════
# GRAMMAR FRAME — one frame's worth of parsed visual input
# ════════════════════════════════════════════════════════════

@dataclass
class GrammarFrame:
    """
    A single camera frame processed through V1 grammar.
    Contains the primitives, bindings, and evaluated relations.
    """
    frame_index: int
    primitives: List[VisualPrimitive] = field(default_factory=list)
    bindings: Dict[str, Binding] = field(default_factory=dict)
    relations: List[Relation] = field(default_factory=list)
    grammar_version: str = GRAMMAR_VERSION

    @property
    def valid_primitives(self) -> List[VisualPrimitive]:
        return [p for p in self.primitives if p.is_valid()]

    @property
    def deterministic_relations(self) -> List[Relation]:
        return [r for r in self.relations if r.is_deterministic]

    @property
    def true_relations(self) -> List[Relation]:
        return [r for r in self.relations if r.result == RelationResult.TRUE]

    def summary(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "grammar_version": self.grammar_version,
            "total_primitives": len(self.primitives),
            "valid_primitives": len(self.valid_primitives),
            "bindings": len(self.bindings),
            "total_relations": len(self.relations),
            "deterministic_relations": len(self.deterministic_relations),
            "true_relations": len(self.true_relations),
        }
