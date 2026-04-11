from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class GraphEdge:
    edge_type: str
    source: str
    target: str
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProgramGraph:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)

def ast_to_program_graph(ast) -> ProgramGraph:
    graph = ProgramGraph()
    root_type = getattr(ast, "node_type", "unknown")
    graph.nodes.append({"id": "root", "type": root_type})
    for idx, child in enumerate(getattr(ast, "children", []), start=1):
        node_id = f"n{idx}"
        graph.nodes.append({"id": node_id, "type": getattr(child, "node_type", "unknown")})
        graph.edges.append(GraphEdge(edge_type="contains", source="root", target=node_id))
    return graph
