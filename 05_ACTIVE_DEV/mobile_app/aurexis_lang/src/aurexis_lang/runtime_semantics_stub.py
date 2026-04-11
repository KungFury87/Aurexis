from enum import Enum
from typing import Any, Dict, List


def _node_type_label(node_type: Any) -> str:
    if isinstance(node_type, Enum):
        return str(node_type.value)
    return str(node_type)


def ast_to_semantic_summary(ast) -> Dict[str, Any]:
    sem_classes: List[str] = []
    ambiguous = False
    for child in getattr(ast, "children", []):
        node_type = _node_type_label(getattr(child, "node_type", "unknown"))
        if node_type in {"Assignment", "Identifier", "Value"}:
            sem_classes.append("assignment_semantic")
        elif node_type in {"BinaryExpression", "Operator"}:
            sem_classes.append("binary_expression_semantic")
        elif node_type in {"Control", "Block"}:
            sem_classes.append("control_or_block_semantic")
        elif "Unknown" in node_type or "NonControl" in node_type:
            sem_classes.append("unresolved_semantic")
            ambiguous = True
        else:
            sem_classes.append("generic_semantic")
    return {
        "semantic_classes": sem_classes,
        "unique_semantics": sorted(set(sem_classes)),
        "ambiguous": ambiguous,
        "resolvable": not ambiguous,
    }
