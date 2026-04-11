from typing import Dict, Any, List
from copy import deepcopy

from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses
from .runtime_reporting import stamp_runtime_surface


def _walk_outputs(outputs, env, timeline, start_index=1):
    idx = start_index
    for step in outputs:
        op = step.get('op')
        step_status = extract_phoxel_runtime_status(step)
        before_snapshot = deepcopy(env)
        if op == 'assign' and step.get('resolved'):
            target = step.get('target')
            if target is not None:
                env[target] = step.get('value')
        after_snapshot = deepcopy(env)
        mutated_keys = sorted({str(k) for k, v in after_snapshot.items() if before_snapshot.get(k) != v})
        item = {
            'step_index': idx,
            'op': op,
            'resolved': bool(step.get('resolved', False)),
            'reason': step.get('reason'),
            'environment_snapshot': after_snapshot,
            'mutation_applied': bool(mutated_keys),
            'mutated_keys': mutated_keys,
        }
        if step_status:
            item['phoxel_runtime_status'] = step_status
        timeline.append(item)
        idx += 1
        if op in {'block', 'control'}:
            idx = _walk_outputs(step.get('nested_output_steps', []), env, timeline, idx)
    return idx


def propagate_execution_state(result: Dict[str, Any]) -> Dict[str, Any]:
    env = {}
    timeline: List[Dict[str, Any]] = []
    _walk_outputs(result.get('output_steps', []), env, timeline)

    blocked = [t for t in timeline if not t['resolved']]
    timeline_statuses = [item.get('phoxel_runtime_status', {}) for item in timeline if isinstance(item, dict)]
    mutation_steps = [item for item in timeline if item.get('mutation_applied')]
    mutated_targets = sorted({key for item in mutation_steps for key in item.get('mutated_keys', [])})
    return stamp_runtime_surface({
        'timeline': timeline,
        'final_environment': env,
        'blocked_step_count': len(blocked),
        'blocked_reasons': sorted({str(t.get('reason')) for t in blocked if t.get('reason')}),
        'statefully_resolved': bool(len(blocked) == 0),
        'mutation_summary': {
            'mutation_step_count': len(mutation_steps),
            'mutated_targets': mutated_targets,
            'mutation_applied_count': len(mutation_steps),
        },
        'phoxel_runtime_status_explicit': any(bool(status) for status in timeline_statuses),
        'phoxel_runtime_status_rollup': rollup_phoxel_runtime_statuses(timeline_statuses),
    }, 'runtime_state_propagation')
