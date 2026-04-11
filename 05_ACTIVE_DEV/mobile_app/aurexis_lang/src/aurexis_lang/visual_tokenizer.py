from dataclasses import dataclass
from typing import List, Dict

from .parser_stub import Token

@dataclass
class PrimitiveObservation:
    primitive_type: str
    attributes: Dict[str, str]
    confidence: float = 1.0

def primitives_to_tokens(observations: List[PrimitiveObservation]) -> List[Token]:
    tokens = []
    for obs in observations:
        role = obs.attributes.get("role", "identifier")
        value = obs.attributes.get("value", obs.primitive_type)
        tokens.append(Token(token_type=role, value=value, confidence=obs.confidence))
    return tokens
