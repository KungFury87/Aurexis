from __future__ import annotations

from typing import Dict, Any, List

from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses
from .runtime_reporting import stamp_runtime_surface


def _node_phoxel_runtime_status(node: Any) -> Dict[str, Any]:
    return extract_phoxel_runtime_status(node)


def _status_rollup(statuses: List[Dict[str, Any]]) -> Dict[str, Any]:
    return rollup_phoxel_runtime_statuses(statuses)


def ast_to_trace(ast) -> Dict[str, Any]:
    children = getattr(ast, "children", [])
    conf = getattr(ast, "value", {}).get("confidence", {})
    root_status = _node_phoxel_runtime_status(ast)
    step_statuses = []
    steps = []
    for idx, child in enumerate(children, start=1):
        child_status = _node_phoxel_runtime_status(child)
        step_statuses.append(child_status)
        steps.append({
            "index": idx,
            "node_type": getattr(child, "node_type", "unknown"),
            "value": getattr(child, "value", {}),
            "phoxel_runtime_status": child_status,
        })
    return stamp_runtime_surface({
        "trace_type": "execution_trace_stub",
        "root_type": getattr(ast, "node_type", "unknown"),
        "step_count": len(children),
        "confidence_summary": conf,
        "root_phoxel_runtime_status": root_status,
        "phoxel_runtime_status_explicit": bool(root_status) or any(bool(s) for s in step_statuses),
        "phoxel_runtime_status_rollup": _status_rollup(([root_status] if root_status else []) + step_statuses),
        "steps": steps,
    }, "runtime_execution_trace")
