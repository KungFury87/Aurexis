from enum import Enum
from typing import Any, Dict, List


def _node_type_label(node_type: Any) -> str:
    if isinstance(node_type, Enum):
        return str(node_type.value)
    return str(node_type)


def ast_to_semantic_summary_expanded(ast) -> Dict[str, Any]:
    semantics: List[Dict[str, Any]] = []
    ambiguous = False

    for child in getattr(ast, "children", []):
        node_type = _node_type_label(getattr(child, "node_type", "unknown"))
        if node_type == "Assignment":
            semantics.append({"semantic": "assignment", "resolvable": True})
        elif node_type == "BinaryExpression":
            semantics.append({"semantic": "binary_expression", "resolvable": True})
        elif node_type == "Control":
            semantics.append({"semantic": "control", "resolvable": False})
            ambiguous = True
        elif node_type == "Block":
            semantics.append({"semantic": "block", "resolvable": False})
            ambiguous = True
        elif "Unknown" in node_type or "NonControl" in node_type:
            semantics.append({"semantic": "unresolved", "resolvable": False})
            ambiguous = True
        else:
            semantics.append({"semantic": "generic", "resolvable": True})

    resolvable_count = sum(1 for s in semantics if s["resolvable"])
    return {
        "semantic_items": semantics,
        "semantic_count": len(semantics),
        "resolvable_count": resolvable_count,
        "partially_resolvable": resolvable_count < len(semantics),
        "ambiguous": ambiguous,
    }
