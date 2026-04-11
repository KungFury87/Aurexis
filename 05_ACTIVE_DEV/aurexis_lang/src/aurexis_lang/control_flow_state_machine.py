from .runtime_reporting import stamp_runtime_surface
from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses

from typing import Dict, Any, List

def step_state_machine(transitions: List[Dict[str, Any]]) -> Dict[str, Any]:
    state = "start"
    timeline = []
    blocked = 0
    statuses = []

    for idx, item in enumerate(transitions, start=1):
        event = item.get("event", "unknown")
        resolved = bool(item.get("resolved", False))
        next_state = item.get("next_state") if resolved else None
        status = extract_phoxel_runtime_status(item)
        if status:
            statuses.append(status)
        if resolved and next_state is not None:
            state = next_state
        else:
            blocked += 1
        entry = {
            "step_index": idx,
            "event": event,
            "resolved": resolved,
            "next_state": next_state,
            "current_state_after_step": state,
        }
        if status:
            entry['phoxel_runtime_status'] = status
        timeline.append(entry)

    blocked_reasons = ['blocked_transition'] * blocked if blocked else []
    return stamp_runtime_surface({
        "final_state": state,
        "timeline": timeline,
        "blocked_transition_count": blocked,
        "blocked_reasons": blocked_reasons,
        "fully_transitioned": blocked == 0,
        "control_surface_consistent": True,
        "phoxel_runtime_status_explicit": any(bool(status) for status in statuses),
        "phoxel_runtime_status_rollup": rollup_phoxel_runtime_statuses(statuses),
    }, 'runtime_control_state_machine')

def control_steps_to_transitions(control_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    transitions = []
    for out in control_summary.get("outputs", []):
        event = out.get("path_label") or out.get("keyword", "unknown")
        next_state = None
        if out.get("resolved"):
            next_state = out.get("path_label") or f"{out.get('keyword', 'unknown')}::{out.get('branch', 'blocked')}"
        item = {
            "event": event,
            "resolved": out.get("resolved", False),
            "next_state": next_state,
            "reason": out.get("reason"),
        }
        status = extract_phoxel_runtime_status(out)
        if status:
            item['phoxel_runtime_status'] = status
        transitions.append(item)
    return transitions


def summarize_control_transitions(control_summary: Dict[str, Any]) -> Dict[str, Any]:
    transitions = control_steps_to_transitions(control_summary)
    blocked_reasons = sorted({str(item.get('reason')) for item in transitions if item.get('reason')})
    statuses = [item.get('phoxel_runtime_status', {}) for item in transitions if isinstance(item, dict)]
    return stamp_runtime_surface({
        "transitions": transitions,
        "transition_count": len(transitions),
        "blocked_transition_count": sum(1 for item in transitions if not item.get('resolved', False)),
        "blocked_reasons": blocked_reasons,
        "control_surface_consistent": True,
        "phoxel_runtime_status_explicit": any(bool(status) for status in statuses),
        "phoxel_runtime_status_rollup": rollup_phoxel_runtime_statuses(statuses),
    }, 'runtime_control_transitions')
