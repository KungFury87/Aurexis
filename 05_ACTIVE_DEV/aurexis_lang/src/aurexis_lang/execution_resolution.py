from typing import Dict, Any, List, Tuple

from .phoxel_runtime_status import collect_step_phoxel_runtime_statuses, extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses
from .runtime_reporting import stamp_runtime_surface


def _try_scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == 'true':
            return True
        if lowered == 'false':
            return False
        try:
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                return value
    return value


def _resolve_operand(raw, env):
    if isinstance(raw, str) and raw in env:
        return env[raw]
    return _try_scalar(raw)


def _evaluate_binary(parts, env):
    if len(parts) < 3:
        return False, None, 'incomplete_expression'
    left, op, right = parts[0], parts[1], parts[2]
    left_val = _resolve_operand(left, env)
    right_val = _resolve_operand(right, env)

    numeric_ops = {'+', '-', '*', '/'}
    compare_ops = {'==', '!=', '>', '<', '>=', '<='}
    boolean_ops = {'and', 'or', '&&', '||'}

    if op in numeric_ops:
        if not isinstance(left_val, (int, float)) or not isinstance(right_val, (int, float)):
            return False, None, 'non_numeric_operands'
        if op == '+':
            return True, left_val + right_val, None
        if op == '-':
            return True, left_val - right_val, None
        if op == '*':
            return True, left_val * right_val, None
        if op == '/':
            if right_val == 0:
                return False, None, 'division_by_zero'
            return True, left_val / right_val, None

    if op in compare_ops:
        try:
            if op == '==':
                return True, left_val == right_val, None
            if op == '!=':
                return True, left_val != right_val, None
            if op == '>':
                return True, left_val > right_val, None
            if op == '<':
                return True, left_val < right_val, None
            if op == '>=':
                return True, left_val >= right_val, None
            if op == '<=':
                return True, left_val <= right_val, None
        except Exception:
            return False, None, 'comparison_not_supported'

    if op in boolean_ops:
        if not isinstance(left_val, bool) or not isinstance(right_val, bool):
            return False, None, 'non_boolean_operands'
        if op in {'and', '&&'}:
            return True, left_val and right_val, None
        return True, left_val or right_val, None

    return False, None, f'unsupported_operator:{op}'


def _evaluate_value(raw: Any, env: Dict[str, Any]) -> Tuple[bool, Any, Any]:
    if isinstance(raw, dict) and 'parts' in raw:
        return _evaluate_binary(raw.get('parts', []), env)
    if isinstance(raw, list) and len(raw) >= 3:
        return _evaluate_binary(raw, env)
    return True, _resolve_operand(raw, env), None


def _control_condition(step: Dict[str, Any], env: Dict[str, Any]) -> Tuple[bool, Any, Any]:
    if 'condition_value' not in step:
        return False, None, 'blocked_control_branch'
    condition_value = step.get('condition_value')
    if condition_value is None:
        return False, None, 'blocked_control_branch'
    resolved, value, reason = _evaluate_value(condition_value, env)
    if not resolved:
        return False, None, reason or 'unknown_condition'
    if not isinstance(value, bool):
        return False, None, 'unknown_condition'
    return True, value, None


def _normalize_iterable(iterable):
    if isinstance(iterable, int):
        return list(range(iterable)) if iterable > 0 else []
    if isinstance(iterable, dict):
        return list(iterable.items())
    if isinstance(iterable, (list, tuple, set, str)):
        return list(iterable)
    return None


def _run_control_step(step: Dict[str, Any], env: Dict[str, Any]):
    keyword = str(step.get('keyword', 'unknown'))
    output = {'op': 'control', 'keyword': keyword, 'resolved': False, 'nested_output_steps': []}
    nested_result = {'output_steps': [], 'resolved_count': 0, 'unresolved_count': 0}

    if keyword == 'if':
        cond_ok, cond_value, cond_reason = _control_condition(step, env)
        if not cond_ok:
            output['reason'] = cond_reason or 'unknown_condition'
            return output, nested_result
        branch = 'then' if cond_value else 'else'
        nested_steps = list(step.get(f'{branch}_steps') or ([] if not cond_value else step.get('body_steps', [])))
        nested_result = _run_steps(nested_steps, env) if nested_steps else {'output_steps': [], 'resolved_count': 0, 'unresolved_count': 0}
        output.update({
            'branch': branch,
            'path_label': f'if::{branch}',
            'nested_output_steps': nested_result['output_steps'],
            'nested_resolved_count': nested_result['resolved_count'],
            'nested_unresolved_count': nested_result['unresolved_count'],
        })
        output['resolved'] = nested_result['unresolved_count'] == 0
        if not output['resolved']:
            output['reason'] = 'blocked_control_branch'
        return output, nested_result

    if keyword == 'while':
        body_steps = list(step.get('body_steps', []))
        max_iterations = int(step.get('max_iterations', step.get('iteration_limit', 3)))
        all_outputs = []
        resolved_total = 0
        unresolved_total = 0
        iterations = 0
        exit_branch = 'exit'
        while True:
            cond_ok, cond_value, cond_reason = _control_condition(step, env)
            if not cond_ok:
                output['reason'] = cond_reason or 'unknown_condition'
                output['iterations'] = iterations
                output['branch'] = 'blocked'
                output['path_label'] = 'while::blocked'
                output['nested_output_steps'] = all_outputs
                output['nested_resolved_count'] = resolved_total
                output['nested_unresolved_count'] = unresolved_total
                return output, {'output_steps': all_outputs, 'resolved_count': resolved_total, 'unresolved_count': unresolved_total}
            if not cond_value:
                exit_branch = 'loop' if iterations > 0 else 'exit'
                break
            iter_result = _run_steps(body_steps, env)
            all_outputs.extend(iter_result['output_steps'])
            resolved_total += iter_result['resolved_count']
            unresolved_total += iter_result['unresolved_count']
            iterations += 1
            if iter_result['unresolved_count'] > 0:
                output.update({
                    'branch': 'loop',
                    'path_label': 'while::loop',
                    'iterations': iterations,
                    'nested_output_steps': all_outputs,
                    'nested_resolved_count': resolved_total,
                    'nested_unresolved_count': unresolved_total,
                    'reason': 'blocked_control_branch',
                })
                return output, {'output_steps': all_outputs, 'resolved_count': resolved_total, 'unresolved_count': unresolved_total}
            if iterations >= max_iterations:
                exit_branch = 'loop_limit'
                break
        output.update({
            'resolved': True,
            'branch': exit_branch,
            'path_label': f'while::{exit_branch}',
            'iterations': iterations,
            'nested_output_steps': all_outputs,
            'nested_resolved_count': resolved_total,
            'nested_unresolved_count': unresolved_total,
        })
        return output, {'output_steps': all_outputs, 'resolved_count': resolved_total, 'unresolved_count': unresolved_total}

    if keyword == 'for':
        raw_iterable = step.get('iterable')
        resolved, iterable_value, reason = _evaluate_value(raw_iterable, env)
        if not resolved:
            output['reason'] = reason or 'unknown_iterable'
            return output, nested_result
        items = _normalize_iterable(iterable_value)
        if items is None:
            output['reason'] = 'unsupported_iterable'
            return output, nested_result
        if len(items) == 0:
            output.update({
                'resolved': True,
                'branch': 'skip',
                'path_label': 'for::skip',
                'nested_output_steps': [],
                'nested_resolved_count': 0,
                'nested_unresolved_count': 0,
                'iterations': 0,
            })
            return output, nested_result
        body_steps = list(step.get('body_steps', []))
        loop_variable = step.get('loop_variable')
        all_outputs = []
        resolved_total = 0
        unresolved_total = 0
        for index, item in enumerate(items):
            if loop_variable is not None:
                env[loop_variable] = item
            env['_loop_index'] = index
            iter_result = _run_steps(body_steps, env)
            all_outputs.extend(iter_result['output_steps'])
            resolved_total += iter_result['resolved_count']
            unresolved_total += iter_result['unresolved_count']
            if iter_result['unresolved_count'] > 0:
                output.update({
                    'branch': 'iterate',
                    'path_label': 'for::iterate',
                    'iterations': index + 1,
                    'nested_output_steps': all_outputs,
                    'nested_resolved_count': resolved_total,
                    'nested_unresolved_count': unresolved_total,
                    'reason': 'blocked_control_branch',
                })
                return output, {'output_steps': all_outputs, 'resolved_count': resolved_total, 'unresolved_count': unresolved_total}
        output.update({
            'resolved': True,
            'branch': 'iterate',
            'path_label': 'for::iterate',
            'iterations': len(items),
            'nested_output_steps': all_outputs,
            'nested_resolved_count': resolved_total,
            'nested_unresolved_count': unresolved_total,
        })
        return output, {'output_steps': all_outputs, 'resolved_count': resolved_total, 'unresolved_count': unresolved_total}

    output['reason'] = 'unsupported_control'
    return output, nested_result


def _run_steps(steps: List[Dict[str, Any]], env: Dict[str, Any]):
    outputs: List[Dict[str, Any]] = []
    resolved_total = 0
    unresolved_total = 0

    for step in steps:
        step_type = step.get('step_type')
        step_status = extract_phoxel_runtime_status(step)
        if step_type == 'assignment':
            target = step.get('target')
            value_spec = step['value'] if 'value' in step else step.get('value_expr')
            resolved, value, reason = _evaluate_value(value_spec, env)
            if target is not None and resolved:
                env[target] = value
                item = {'op': 'assign', 'target': target, 'value': value, 'resolved': True}
                if step_status:
                    item['phoxel_runtime_status'] = step_status
                outputs.append(item)
                resolved_total += 1
            else:
                failure_reason = 'missing_target' if target is None else (reason or 'unresolved_assignment')
                item = {'op': 'assign', 'target': target, 'resolved': False, 'reason': failure_reason}
                if step_status:
                    item['phoxel_runtime_status'] = step_status
                outputs.append(item)
                unresolved_total += 1
        elif step_type == 'binary_expression':
            parts = step.get('parts', [])
            resolved, result, reason = _evaluate_binary(parts, env)
            item = {'op': 'binary_expr', 'parts': parts, 'result': result, 'resolved': bool(resolved)}
            if step_status:
                item['phoxel_runtime_status'] = step_status
            if reason:
                item['reason'] = reason
            outputs.append(item)
            if resolved:
                resolved_total += 1
            else:
                unresolved_total += 1
        elif step_type == 'block':
            nested_steps = step.get('nested_steps', [])
            nested_result = _run_steps(nested_steps, env)
            block_resolved = bool(nested_steps) and nested_result['unresolved_count'] == 0
            item = {
                'op': 'block',
                'resolved': bool(block_resolved),
                'reason': None if block_resolved else ('blocked_control_branch' if not nested_steps else 'blocked_nested_block'),
                'nested_output_steps': nested_result['output_steps'],
                'nested_resolved_count': nested_result['resolved_count'],
                'nested_unresolved_count': nested_result['unresolved_count'],
            }
            nested_statuses = collect_step_phoxel_runtime_statuses(nested_result['output_steps'])
            if step_status:
                item['phoxel_runtime_status'] = step_status
            if nested_statuses:
                item['phoxel_runtime_status_rollup'] = rollup_phoxel_runtime_statuses(nested_statuses)
            outputs.append(item)
            resolved_total += nested_result['resolved_count']
            unresolved_total += nested_result['unresolved_count']
            if block_resolved:
                resolved_total += 1
            else:
                unresolved_total += 1
        elif step_type == 'control':
            control_output, nested_result = _run_control_step(step, env)
            if step_status and 'phoxel_runtime_status' not in control_output:
                control_output['phoxel_runtime_status'] = step_status
            nested_statuses = collect_step_phoxel_runtime_statuses(control_output.get('nested_output_steps', []))
            if nested_statuses:
                control_output['phoxel_runtime_status_rollup'] = rollup_phoxel_runtime_statuses(nested_statuses)
            outputs.append(control_output)
            resolved_total += nested_result['resolved_count']
            unresolved_total += nested_result['unresolved_count']
            if control_output.get('resolved'):
                resolved_total += 1
            else:
                unresolved_total += 1
        else:
            item = {'op': step_type or 'unknown', 'resolved': False, 'reason': 'unsupported_step'}
            if step_status:
                item['phoxel_runtime_status'] = step_status
            outputs.append(item)
            unresolved_total += 1

    return {
        'output_steps': outputs,
        'resolved_count': int(resolved_total),
        'unresolved_count': int(unresolved_total),
    }


def run_execution_resolution(plan: Dict[str, Any]) -> Dict[str, Any]:
    env: Dict[str, Any] = {}
    nested = _run_steps(plan.get('execution_steps', []), env)
    output_statuses = collect_step_phoxel_runtime_statuses(nested['output_steps'])
    return stamp_runtime_surface({
        'final_environment': env,
        'output_steps': nested['output_steps'],
        'resolved_count': nested['resolved_count'],
        'unresolved_count': nested['unresolved_count'],
        'fully_resolved': bool(nested['unresolved_count'] == 0),
        'phoxel_runtime_status_explicit': bool(output_statuses),
        'phoxel_runtime_status_rollup': rollup_phoxel_runtime_statuses(output_statuses),
    }, 'runtime_resolution')
