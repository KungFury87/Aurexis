"""
Aurexis Core — Visual Parse Rules V1 (FROZEN)

Deterministic rules that convert a V1 GrammarFrame into program structures
compatible with the existing AST/IR pipeline.

A parse rule maps a pattern (primitives + relations) to a program fragment.
Rules are evaluated in priority order. The first matching rule wins.
If no rule matches, the frame produces a DESCRIPTIVE-only stub (no error).

Parse rules do NOT create new node types. They produce standard AST nodes
(Assignment, BinaryExpression, TokenExpression) and IR nodes (assign,
binary_expr, token_expr) that the existing optimizer can process.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, RelationResult, ExecutionStatus,
    GrammarLaw, V1_LAW, BoundingBox, VisualPrimitive, Binding,
    Relation, GrammarFrame, GRAMMAR_VERSION,
)


# ════════════════════════════════════════════════════════════
# PARSE RULE VERSION — frozen
# ════════════════════════════════════════════════════════════

PARSE_RULES_VERSION = "V1.0"
PARSE_RULES_FROZEN = True


# ════════════════════════════════════════════════════════════
# PROGRAM NODE — the output of parsing
# ════════════════════════════════════════════════════════════

class ProgramNodeKind(str, Enum):
    """Kinds of program nodes produced by parse rules.
    These map 1:1 to existing AST/IR node types."""
    PROGRAM = "Program"           # Root node
    BINDING_STMT = "Assignment"   # BIND → Assignment (name = primitive)
    RELATION_EXPR = "BinaryExpression"  # ADJACENT/CONTAINS → BinaryExpression
    PRIMITIVE_REF = "TokenExpression"   # Reference to a primitive


@dataclass
class ProgramNode:
    """
    Output of the parse rules. Compatible with existing AST/IR pipeline.

    Each ProgramNode carries:
    - kind: maps to an AST node_type
    - value: dict of attributes (mirrors ASTNode.value)
    - children: ordered child nodes
    - confidence: computed from source primitives
    - execution_status: from V1 grammar evaluation
    """
    kind: ProgramNodeKind
    value: Dict[str, Any] = field(default_factory=dict)
    children: List["ProgramNode"] = field(default_factory=list)
    confidence: float = 0.0
    execution_status: ExecutionStatus = ExecutionStatus.DETERMINISTIC
    grammar_version: str = GRAMMAR_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for inspection and testing."""
        return {
            "kind": self.kind.value,
            "value": self.value,
            "confidence": self.confidence,
            "execution_status": self.execution_status.name,
            "grammar_version": self.grammar_version,
            "children": [c.to_dict() for c in self.children],
        }


# ════════════════════════════════════════════════════════════
# PARSE RULE — individual rule definition
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ParseRule:
    """
    A frozen parse rule. Matches a pattern in a GrammarFrame
    and produces ProgramNodes.
    """
    name: str
    priority: int  # Lower = higher priority
    description: str

    def matches(self, frame: GrammarFrame) -> bool:
        """Does this rule apply to the given frame?"""
        raise NotImplementedError

    def apply(self, frame: GrammarFrame) -> List[ProgramNode]:
        """Apply this rule, producing program nodes."""
        raise NotImplementedError


# ════════════════════════════════════════════════════════════
# RULE 1: BIND → Assignment
# ════════════════════════════════════════════════════════════

class BindToAssignment(ParseRule):
    """
    For each binding in the frame, produce an Assignment node.
    BIND(name, primitive) → Assignment(target=name, value=primitive_ref)

    This is the simplest parse rule: naming a visual primitive is
    equivalent to variable assignment in a program.
    """

    def __init__(self):
        object.__setattr__(self, 'name', 'bind_to_assignment')
        object.__setattr__(self, 'priority', 10)
        object.__setattr__(self, 'description',
            'Each BIND produces an Assignment node (name = primitive reference)')

    def matches(self, frame: GrammarFrame) -> bool:
        return len(frame.bindings) > 0

    def apply(self, frame: GrammarFrame) -> List[ProgramNode]:
        nodes = []
        for name, binding in sorted(frame.bindings.items()):
            prim = binding.primitive
            # Primitive reference node
            prim_ref = ProgramNode(
                kind=ProgramNodeKind.PRIMITIVE_REF,
                value={
                    "token_type": prim.kind.name,
                    "value": f"{prim.kind.name}@({prim.bbox.x},{prim.bbox.y},{prim.bbox.width},{prim.bbox.height})",
                    "primitive_kind": prim.kind.name,
                    "bbox": {"x": prim.bbox.x, "y": prim.bbox.y,
                             "width": prim.bbox.width, "height": prim.bbox.height},
                },
                confidence=prim.source_confidence,
                execution_status=(
                    ExecutionStatus.DETERMINISTIC if prim.source_confidence >= 1.0
                    else ExecutionStatus.HEURISTIC_INPUT
                ),
            )
            # Assignment node
            assign = ProgramNode(
                kind=ProgramNodeKind.BINDING_STMT,
                value={
                    "target": name,
                    "confidence": prim.source_confidence,
                    "kind": "bind",
                },
                children=[prim_ref],
                confidence=prim.source_confidence,
                execution_status=prim_ref.execution_status,
            )
            nodes.append(assign)
        return nodes


# ════════════════════════════════════════════════════════════
# RULE 2: ADJACENT/CONTAINS → BinaryExpression
# ════════════════════════════════════════════════════════════

class RelationToExpression(ParseRule):
    """
    For each evaluated relation in the frame, produce a BinaryExpression.
    ADJACENT(a, b) → BinaryExpression(op="ADJACENT", lhs=a_ref, rhs=b_ref)
    CONTAINS(a, b) → BinaryExpression(op="CONTAINS", lhs=a_ref, rhs=b_ref)

    The result (TRUE/FALSE) becomes an attribute of the expression,
    not a control flow decision. V1 has no conditional execution —
    relations are pure assertions about spatial reality.
    """

    def __init__(self):
        object.__setattr__(self, 'name', 'relation_to_expression')
        object.__setattr__(self, 'priority', 20)
        object.__setattr__(self, 'description',
            'Each ADJACENT/CONTAINS relation produces a BinaryExpression node')

    def matches(self, frame: GrammarFrame) -> bool:
        return len(frame.relations) > 0

    def apply(self, frame: GrammarFrame) -> List[ProgramNode]:
        nodes = []
        for rel in frame.relations:
            # Left operand reference
            lhs = _primitive_ref_node(rel.operand_a)
            # Right operand reference
            rhs = _primitive_ref_node(rel.operand_b)
            # Combined confidence (mean of both operands)
            combined_conf = (rel.operand_a.source_confidence
                             + rel.operand_b.source_confidence) / 2.0

            expr = ProgramNode(
                kind=ProgramNodeKind.RELATION_EXPR,
                value={
                    "operation": rel.operation.name,
                    "result": rel.result.name,
                    "measured_value": rel.measured_value,
                    "law_threshold": rel.law_threshold,
                    "confidence": combined_conf,
                    "kind": "relation",
                },
                children=[lhs, rhs],
                confidence=combined_conf,
                execution_status=rel.execution_status,
            )
            nodes.append(expr)
        return nodes


# ════════════════════════════════════════════════════════════
# HELPER — build a primitive reference node
# ════════════════════════════════════════════════════════════

def _primitive_ref_node(prim: VisualPrimitive) -> ProgramNode:
    """Create a ProgramNode referencing a primitive."""
    return ProgramNode(
        kind=ProgramNodeKind.PRIMITIVE_REF,
        value={
            "token_type": prim.kind.name,
            "value": f"{prim.kind.name}@({prim.bbox.x},{prim.bbox.y},{prim.bbox.width},{prim.bbox.height})",
            "primitive_kind": prim.kind.name,
            "bbox": {"x": prim.bbox.x, "y": prim.bbox.y,
                     "width": prim.bbox.width, "height": prim.bbox.height},
        },
        confidence=prim.source_confidence,
        execution_status=(
            ExecutionStatus.DETERMINISTIC if prim.source_confidence >= 1.0
            else ExecutionStatus.HEURISTIC_INPUT
        ),
    )


# ════════════════════════════════════════════════════════════
# RULE SET — frozen ordered collection
# ════════════════════════════════════════════════════════════

V1_PARSE_RULES: List[ParseRule] = sorted([
    BindToAssignment(),
    RelationToExpression(),
], key=lambda r: r.priority)


# ════════════════════════════════════════════════════════════
# FRAME PARSER — applies rules to produce a program
# ════════════════════════════════════════════════════════════

def parse_frame_to_program(
    frame: GrammarFrame,
    rules: Optional[List[ParseRule]] = None,
) -> ProgramNode:
    """
    Parse a GrammarFrame into a Program tree.

    Applies all matching rules in priority order.
    Each rule produces zero or more child nodes of the root Program.

    The root Program node's confidence is the mean of all children.
    Its execution_status is HEURISTIC_INPUT if any child is HEURISTIC_INPUT.

    Returns a ProgramNode of kind PROGRAM containing all produced nodes.
    """
    if rules is None:
        rules = V1_PARSE_RULES

    all_children: List[ProgramNode] = []

    for rule in rules:
        if rule.matches(frame):
            children = rule.apply(frame)
            all_children.extend(children)

    # Compute root-level confidence and status
    if all_children:
        root_confidence = sum(c.confidence for c in all_children) / len(all_children)
        has_heuristic = any(
            c.execution_status == ExecutionStatus.HEURISTIC_INPUT
            for c in all_children
        )
        root_status = (
            ExecutionStatus.HEURISTIC_INPUT if has_heuristic
            else ExecutionStatus.DETERMINISTIC
        )
    else:
        root_confidence = 0.0
        root_status = ExecutionStatus.DETERMINISTIC

    return ProgramNode(
        kind=ProgramNodeKind.PROGRAM,
        value={
            "frame_index": frame.frame_index,
            "grammar_version": GRAMMAR_VERSION,
            "parse_rules_version": PARSE_RULES_VERSION,
            "total_statements": len(all_children),
        },
        children=all_children,
        confidence=root_confidence,
        execution_status=root_status,
    )


# ════════════════════════════════════════════════════════════
# AST/IR BRIDGE — convert ProgramNode → existing pipeline types
# ════════════════════════════════════════════════════════════

def program_node_to_ast_dict(node: ProgramNode) -> Dict[str, Any]:
    """
    Convert a ProgramNode to an AST-compatible dict structure
    that mirrors the existing ASTNode format.

    This allows V1 parse output to flow into the existing
    ir_builder (ast_to_ir) and optimizer pipeline.
    """
    return {
        "node_type": node.kind.value,
        "value": {**node.value, "confidence": node.confidence},
        "children": [program_node_to_ast_dict(c) for c in node.children],
    }


def program_node_to_ir_dict(node: ProgramNode) -> Dict[str, Any]:
    """
    Convert a ProgramNode directly to an IR-compatible dict structure
    that mirrors the existing IRNode format.

    IR op mapping:
    - PROGRAM → "program"
    - BINDING_STMT → "assign"
    - RELATION_EXPR → "binary_expr"
    - PRIMITIVE_REF → "token_expr"
    """
    op_map = {
        ProgramNodeKind.PROGRAM: "program",
        ProgramNodeKind.BINDING_STMT: "assign",
        ProgramNodeKind.RELATION_EXPR: "binary_expr",
        ProgramNodeKind.PRIMITIVE_REF: "token_expr",
    }

    return {
        "op": op_map[node.kind],
        "args": {
            **node.value,
            "confidence": node.confidence,
            "execution_status": node.execution_status.name,
        },
        "children": [program_node_to_ir_dict(c) for c in node.children],
        "metadata": {
            "grammar_version": node.grammar_version,
            "parse_rules_version": PARSE_RULES_VERSION,
        },
    }
