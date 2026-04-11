"""
ir.py — Core IR types for Aurexis V86+

IRNode is the fundamental IR unit. The optimizer (ir_optimizer.py)
annotates nodes via the metadata dict without mutating structure.

Backward compatible: metadata defaults to empty dict, so all existing
code that uses IRNode without metadata continues to work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IRNode:
    op: str
    args: Dict[str, Any] = field(default_factory=dict)
    children: List["IRNode"] = field(default_factory=list)
    # Optimization and provenance metadata — written by ir_optimizer.py
    # Never read directly; use ir_optimizer._get_opt(node) for typed access
    metadata: Dict[str, Any] = field(default_factory=dict)


def ast_to_ir(ast) -> IRNode:
    """
    Convert a parsed AST to an IRNode tree.

    This is the structural pass — it maps node types to ops and
    preserves confidence from the token layer. The ir_optimizer
    then runs evidence annotation and optimization passes over
    the result.
    """
    root = IRNode(op='program')

    for child in getattr(ast, 'children', []):
        node_type = str(getattr(child, 'node_type', 'unknown'))
        value     = getattr(child, 'value', {}) or {}

        if node_type in ('Assignment', 'assignment'):
            # Extract target and value from assignment children
            sub_children = getattr(child, 'children', [])
            target = None
            rhs_confidence = 0.0
            if len(sub_children) >= 2:
                left  = sub_children[0]
                right = sub_children[1]
                lv = getattr(left, 'value', {}) or {}
                rv = getattr(right, 'value', {}) or {}
                target = lv.get('name') or lv.get('identifier')
                rhs_confidence = float(rv.get('confidence', 0.0) or 0.0)
            confidence = float(value.get('confidence', rhs_confidence) or rhs_confidence)
            root.children.append(IRNode(
                op='assign',
                args={
                    'target':     target,
                    'confidence': confidence,
                    'kind':       'assignment',
                },
            ))

        elif node_type in ('BinaryExpression', 'binary_expression'):
            sub_children = getattr(child, 'children', [])
            parts = []
            confs = []
            for sc in sub_children:
                sv = getattr(sc, 'value', {}) or {}
                parts.append(sv.get('name') or sv.get('value'))
                conf = float(sv.get('confidence', 0.0) or 0.0)
                confs.append(conf)
            mean_conf = sum(confs) / len(confs) if confs else 0.0
            root.children.append(IRNode(
                op='binary_expr',
                args={
                    'parts':      parts,
                    'confidence': mean_conf,
                    'kind':       'expression',
                },
            ))

        elif node_type in ('TokenStream', 'token_stream', 'Token', 'token'):
            # TokenStream may now carry mean confidence (updated parser_expanded)
            confidence = float(value.get('confidence', 0.0) or 0.0)
            token_type = value.get('token_type', 'unknown')
            root.children.append(IRNode(
                op='token',
                args={
                    'token_type': token_type,
                    'value':      value.get('value'),
                    'confidence': confidence,
                },
            ))

        elif node_type in ('TokenExpression', 'token_expression'):
            # Individual token node (updated parser_expanded multi-token path)
            confidence = float(value.get('confidence', 0.0) or 0.0)
            root.children.append(IRNode(
                op='token_expr',
                args={
                    'token_type': value.get('token_type', 'unknown'),
                    'value':      value.get('value'),
                    'confidence': confidence,
                },
            ))

        else:
            # Unknown node type — preserve as generic node with confidence
            confidence = float(value.get('confidence', 0.0) or 0.0)
            root.children.append(IRNode(
                op='stmt',
                args={
                    'node_type':  node_type,
                    'confidence': confidence,
                },
            ))

    return root
