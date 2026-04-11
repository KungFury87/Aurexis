from .runtime_reporting import stamp_runtime_surface
from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses

from typing import Dict, Any


def _normalize_control_payload(keyword: str, raw: Any):
    payload = raw if isinstance(raw, dict) else {}
    has_context = isinstance(raw, dict)
    phoxel_runtime_status = extract_phoxel_runtime_status(raw) if isinstance(raw, dict) else {}
    if keyword == "for":
        base_value = payload.get("iterable") if payload else raw
    else:
        base_value = payload.get("condition") if payload else raw

    control_depth = int(payload.get("depth", 0)) if payload else 0
    parent_path = str(payload.get("parent_path", "root")) if payload else "root"
    return base_value, control_depth, parent_path, has_context, phoxel_runtime_status


def _with_path(metadata: Dict[str, Any], keyword: str, branch: str, depth: int, parent_path: str, has_context: bool, phoxel_runtime_status: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(metadata)
    if has_context:
        data["control_depth"] = depth
        data["parent_path"] = parent_path
        data["path_label"] = f"{parent_path}/{keyword}::{branch}"
    if phoxel_runtime_status:
        data["phoxel_runtime_status"] = phoxel_runtime_status
    return data


def resolve_control_step(control_keyword: str, condition_value: Any = None) -> Dict[str, Any]:
    keyword = str(control_keyword)
    value, depth, parent_path, has_context, phoxel_runtime_status = _normalize_control_payload(keyword, condition_value)
    if keyword == "if":
        if value is True:
            return _with_path({"keyword": "if", "resolved": True, "branch": "then"}, "if", "then", depth, parent_path, has_context, phoxel_runtime_status)
        if value is False:
            return _with_path({"keyword": "if", "resolved": True, "branch": "else"}, "if", "else", depth, parent_path, has_context, phoxel_runtime_status)
        return _with_path({"keyword": "if", "resolved": False, "branch": None, "reason": "unknown_condition"}, "if", "blocked", depth, parent_path, has_context, phoxel_runtime_status)

    if keyword == "while":
        if value is True:
            return _with_path({"keyword": "while", "resolved": True, "branch": "loop"}, "while", "loop", depth, parent_path, has_context, phoxel_runtime_status)
        if value is False:
            return _with_path({"keyword": "while", "resolved": True, "branch": "exit"}, "while", "exit", depth, parent_path, has_context, phoxel_runtime_status)
        return _with_path({"keyword": "while", "resolved": False, "branch": None, "reason": "unknown_condition"}, "while", "blocked", depth, parent_path, has_context, phoxel_runtime_status)

    if keyword == "for":
        iterable = value
        if isinstance(iterable, int):
            if iterable > 0:
                return _with_path({"keyword": "for", "resolved": True, "branch": "iterate"}, "for", "iterate", depth, parent_path, has_context, phoxel_runtime_status)
            return _with_path({"keyword": "for", "resolved": True, "branch": "skip"}, "for", "skip", depth, parent_path, has_context, phoxel_runtime_status)
        if isinstance(iterable, (list, tuple, set, dict, str)):
            branch = "iterate" if len(iterable) > 0 else "skip"
            return _with_path({"keyword": "for", "resolved": True, "branch": branch}, "for", branch, depth, parent_path, has_context, phoxel_runtime_status)
        if iterable is None:
            return _with_path({"keyword": "for", "resolved": False, "branch": None, "reason": "unknown_iterable"}, "for", "blocked", depth, parent_path, has_context, phoxel_runtime_status)
        return _with_path({"keyword": "for", "resolved": False, "branch": None, "reason": "unsupported_iterable"}, "for", "blocked", depth, parent_path, has_context, phoxel_runtime_status)

    return _with_path({"keyword": keyword, "resolved": False, "branch": None, "reason": "unsupported_control"}, keyword, "blocked", depth, parent_path, has_context, phoxel_runtime_status)


def summarize_control_resolution(steps):
    resolved = 0
    outputs = []
    status_rollup_items = []
    for step in steps:
        out = resolve_control_step(step.get("keyword", "unknown"), step.get("condition_value"))
        outputs.append(out)
        if isinstance(out.get('phoxel_runtime_status'), dict) and out.get('phoxel_runtime_status'):
            status_rollup_items.append(out['phoxel_runtime_status'])
        if out.get("resolved"):
            resolved += 1
    unresolved = len(outputs) - resolved
    blocked_reasons = sorted({str(out.get('reason')) for out in outputs if out.get('reason')})
    return stamp_runtime_surface({
        "outputs": outputs,
        "resolved_count": resolved,
        "unresolved_count": unresolved,
        "blocked_reasons": blocked_reasons,
        "control_surface_consistent": True,
        "phoxel_runtime_status_explicit": any(bool(item) for item in status_rollup_items),
        "phoxel_runtime_status_rollup": rollup_phoxel_runtime_statuses(status_rollup_items),
    }, 'runtime_control_resolution')
