import json
from pathlib import Path

from .camera_primitive_extractor import zone_json_to_parser_bundle
from .visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from .confidence_parser import parse_with_confidence
from .ir import ast_to_ir
from .program_graph import ast_to_program_graph
from .runtime_semantics_stub import ast_to_semantic_summary
from .execution_trace import ast_to_trace

def _obs_from_bundle(bundle):
    obs = []
    for item in bundle.get("primitive_observations", []):
        obs.append(
            PrimitiveObservation(
                primitive_type=item.get("primitive_type", "unknown"),
                attributes=item.get("attributes", {}),
                confidence=float(item.get("confidence", item.get("projection_confidence", 1.0))),
            )
        )
    return obs

def run_zone_demo(zone_manifest_path: str):
    bundle = zone_json_to_parser_bundle(zone_manifest_path)
    observations = _obs_from_bundle(bundle)
    tokens = primitives_to_tokens(observations)
    ast = parse_with_confidence(tokens)
    ir = ast_to_ir(ast)
    graph = ast_to_program_graph(ast)
    semantics = ast_to_semantic_summary(ast)
    trace = ast_to_trace(ast)

    return {
        "source": zone_manifest_path,
        "observation_count": len(observations),
        "token_count": len(tokens),
        "ast_root": getattr(ast, "node_type", "unknown"),
        "ir_root": getattr(ir, "op", "unknown"),
        "program_graph": {
            "node_count": len(getattr(graph, "nodes", [])),
            "edge_count": len(getattr(graph, "edges", [])),
        },
        "semantic_summary": semantics,
        "trace": trace,
        "tokens": [
            {"type": t.token_type, "value": t.value, "confidence": t.confidence}
            for t in tokens
        ],
    }

def write_demo_report(zone_manifest_path: str, out_path: str):
    result = run_zone_demo(zone_manifest_path)
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
