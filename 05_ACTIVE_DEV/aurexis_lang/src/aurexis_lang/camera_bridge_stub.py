from typing import Dict, Any, List

from .visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from .parser_expanded import parse_tokens_expanded
from .ir import ast_to_ir

def camera_input_to_ir(observed_primitives: List[Dict[str, Any]]):
    observations = [
        PrimitiveObservation(
            primitive_type=item.get("primitive_type", "unknown"),
            attributes=item.get("attributes", {}),
            confidence=float(item.get("confidence", 1.0)),
        )
        for item in observed_primitives
    ]
    tokens = primitives_to_tokens(observations)
    ast = parse_tokens_expanded(tokens)
    ir = ast_to_ir(ast)
    return {
        "token_count": len(tokens),
        "ast_root": ast.node_type,
        "ir_root": ir.op,
        "tokens": [{"type": t.token_type, "value": t.value, "confidence": t.confidence} for t in tokens],
    }
