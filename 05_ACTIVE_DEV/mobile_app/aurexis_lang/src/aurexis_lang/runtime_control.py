from enum import Enum
from typing import Any


def _edge_type_label(edge_type: Any) -> str:
    if isinstance(edge_type, Enum):
        return str(edge_type.value)
    return str(edge_type)


def evaluate_program_graph(graph):
    edge_types = sorted({_edge_type_label(getattr(edge, "edge_type", "unknown")) for edge in getattr(graph, "edges", [])})
    return {
        "status": "control_scope_stub",
        "node_count": len(getattr(graph, "nodes", [])),
        "edge_count": len(getattr(graph, "edges", [])),
        "edge_types": edge_types,
    }
