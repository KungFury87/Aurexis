from typing import Any, Dict

def evaluate_ir(ir) -> Dict[str, Any]:
    child_ops = [child.op for child in getattr(ir, "children", [])]
    return {
        "status": "stub_expanded",
        "root_op": getattr(ir, "op", "unknown"),
        "child_ops": child_ops,
        "child_count": len(child_ops),
    }
