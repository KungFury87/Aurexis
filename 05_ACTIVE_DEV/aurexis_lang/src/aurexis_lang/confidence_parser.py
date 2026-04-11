from typing import List, Dict, Any
from .parser_stub import Token, ASTNode

def summarize_confidence(tokens: List[Token]) -> Dict[str, float]:
    if not tokens:
        return {"min": 0.0, "avg": 0.0, "max": 0.0}
    vals = [float(getattr(t, "confidence", 1.0)) for t in tokens]
    return {
        "min": min(vals),
        "avg": sum(vals) / len(vals),
        "max": max(vals),
    }

def parse_with_confidence(tokens: List[Token]) -> ASTNode:
    summary = summarize_confidence(tokens)
    node = ASTNode(node_type="ConfidenceProgram", value={"confidence": summary})
    for t in tokens:
        node.children.append(
            ASTNode(
                node_type="ConfidenceToken",
                value={
                    "token_type": t.token_type,
                    "value": t.value,
                    "confidence": float(getattr(t, "confidence", 1.0)),
                },
            )
        )
    return node
