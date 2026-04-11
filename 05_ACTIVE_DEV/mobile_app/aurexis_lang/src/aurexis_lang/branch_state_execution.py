from typing import Dict, Any, List
from copy import deepcopy

from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses
from .runtime_reporting import stamp_runtime_surface


def _walk_branch_outputs(outputs, base_env, branch_states):
    blocked = 0
    for step in outputs:
        op = step.get('op')
        step_status = extract_phoxel_runtime_status(step)
        if op == 'assign' and step.get('resolved'):
            target = step.get('target')
            if target is not None:
                base_env[target] = step.get('value')
        elif op in {'block', 'control'}:
            if not step.get('resolved', False):
                blocked += 1
                default_reason = 'block_unresolved' if op == 'block' else 'control_unresolved'
                item = {
                    'reason': step.get('reason') or default_reason,
                    'branch_label': step.get('path_label') or step.get('keyword') or op,
                    'environment_snapshot': deepcopy(base_env),
                }
                if step_status:
                    item['phoxel_runtime_status'] = step_status
                branch_states.append(item)
            b = _walk_branch_outputs(step.get('nested_output_steps', []), base_env, branch_states)
            blocked += b
        elif not step.get('resolved', False):
            blocked += 1
            item = {
                'reason': step.get('reason') or f"{op}_unresolved",
                'branch_label': step.get('path_label') or op,
                'environment_snapshot': deepcopy(base_env),
            }
            if step_status:
                item['phoxel_runtime_status'] = step_status
            branch_states.append(item)
    return blocked


def run_branch_state_execution(result: Dict[str, Any]) -> Dict[str, Any]:
    base_env = {}
    branch_states: List[Dict[str, Any]] = []
    blocked = _walk_branch_outputs(result.get('output_steps', []), base_env, branch_states)

    branch_statuses = [state.get('phoxel_runtime_status', {}) for state in branch_states if isinstance(state, dict)]
    blocked_labels = sorted({str(s.get('branch_label')) for s in branch_states if s.get('branch_label')})
    return stamp_runtime_surface({
        'base_environment': base_env,
        'branch_candidate_count': len(branch_states),
        'branch_states': branch_states,
        'blocked_branch_count': blocked,
        'blocked_reasons': sorted({str(s.get('reason')) for s in branch_states if s.get('reason')}),
        'branch_transition_summary': {
            'blocked_branch_labels': blocked_labels,
            'blocked_branch_count': blocked,
            'candidate_branch_count': len(branch_states),
        },
        'branch_resolution_confidence': 1.0 if blocked == 0 else max(0.0, 1.0 - (0.2 * blocked)),
        'phoxel_runtime_status_explicit': any(bool(status) for status in branch_statuses),
        'phoxel_runtime_status_rollup': rollup_phoxel_runtime_statuses(branch_statuses),
    }, 'runtime_branch_state')
