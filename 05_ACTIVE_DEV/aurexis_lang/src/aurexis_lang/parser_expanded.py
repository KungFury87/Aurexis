"""
parser_expanded.py — Token-to-AST parser for Aurexis V86+

Fix in this version (V86 / 05_ACTIVE_DEV):
  - parse_assignment() now threads mean token confidence into the
    TokenStream fallback node, so ir_optimizer can propagate it.
  - parse_tokens_expanded() now handles multi-token streams as individual
    expression nodes rather than collapsing them all into one TokenStream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .parser_stub import Token, ASTNode


def _mean_confidence(tokens: List[Token]) -> float:
    if not tokens:
        return 0.0
    return sum(t.confidence for t in tokens) / len(tokens)


def parse_assignment(tokens: List[Token]) -> ASTNode:
    """
    Try to parse an assignment (3+ tokens where tokens[1].value == '=').
    Falls back to a TokenStream node that carries confidence information.
    """
    if len(tokens) >= 3 and tokens[1].value == '=':
        # Confidence = mean of identifier + value tokens
        conf = (tokens[0].confidence + tokens[2].confidence) / 2.0
        return ASTNode(
            node_type='Assignment',
            children=[
                ASTNode(
                    node_type='Identifier',
                    value={'name': tokens[0].value, 'confidence': tokens[0].confidence},
                ),
                ASTNode(
                    node_type='Literal',
                    value={'value': tokens[2].value, 'confidence': tokens[2].confidence},
                ),
            ],
            value={'confidence': conf},
        )

    # Fallback: preserve mean confidence so the optimizer can use it
    mean_conf = _mean_confidence(tokens)
    return ASTNode(
        node_type='TokenStream',
        value={
            'count': len(tokens),
            'confidence': mean_conf,
            'token_confidences': [t.confidence for t in tokens],
        },
    )


def parse_tokens_expanded(tokens: List[Token]) -> ASTNode:
    """
    Parse a token stream into an AST.

    Strategy:
      - Try full-stream assignment parse first (existing behavior)
      - If that produces a TokenStream (no assignment pattern found),
        and there are multiple tokens, try to parse each token as its
        own expression node — this preserves per-token confidence.
    """
    program = ASTNode(node_type='Program')

    if not tokens:
        return program

    # Try assignment parse on full token stream
    stmt = parse_assignment(tokens)

    if stmt.node_type == 'Assignment' or len(tokens) <= 1:
        program.children.append(stmt)
        return program

    # No assignment found with multiple tokens — emit one BinaryExpression
    # or individual expression nodes depending on token count.
    if len(tokens) == 2:
        # Two-token stream → binary expression
        conf = _mean_confidence(tokens)
        program.children.append(ASTNode(
            node_type='BinaryExpression',
            children=[
                ASTNode(
                    node_type='Operand',
                    value={'value': tokens[0].value, 'confidence': tokens[0].confidence},
                ),
                ASTNode(
                    node_type='Operand',
                    value={'value': tokens[1].value, 'confidence': tokens[1].confidence},
                ),
            ],
            value={'confidence': conf},
        ))
    else:
        # Three or more tokens, no assignment — emit as individual token nodes
        # so each carries its own confidence into the optimizer.
        for tok in tokens:
            program.children.append(ASTNode(
                node_type='TokenExpression',
                value={
                    'token_type': tok.token_type,
                    'value':      tok.value,
                    'confidence': tok.confidence,
                },
            ))

    return program
