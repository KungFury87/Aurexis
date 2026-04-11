from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Token:
    token_type: str
    value: str
    confidence: float = 1.0

@dataclass
class ASTNode:
    node_type: str
    children: List["ASTNode"] = field(default_factory=list)
    value: Dict[str, Any] = field(default_factory=dict)

def parse_tokens(tokens: List[Token]) -> ASTNode:
    """Very early parser stub: wrap token stream in a Program AST."""
    program = ASTNode(node_type="Program")
    for token in tokens:
        program.children.append(
            ASTNode(node_type="Token", value={
                "token_type": token.token_type,
                "value": token.value,
                "confidence": token.confidence,
            })
        )
    return program
