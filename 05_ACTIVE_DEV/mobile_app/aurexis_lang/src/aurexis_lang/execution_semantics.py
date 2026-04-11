from enum import Enum
from typing import Dict, Any, List

from .phoxel_runtime_status import extract_phoxel_runtime_status, rollup_phoxel_runtime_statuses
from .runtime_reporting import stamp_runtime_surface


def _node_type_label(node_type: Any) -> str:
    if isinstance(node_type, Enum):
        return str(node_type.value)
    return str(node_type)


def _extract_value(node: Any) -> Any:
    value = getattr(node, 'value', {}) or {}
    if isinstance(value, dict):
        if 'name' in value:
            return value.get('name')
        if 'identifier' in value:
            return value.get('identifier')
        if 'value' in value:
            return value.get('value')
        if 'keyword' in value:
            return value.get('keyword')
    return value


def _extract_assignment_target(node: Any) -> Any:
    value = getattr(node, 'value', {}) or {}
    if isinstance(value, dict):
        if 'name' in value:
            return value.get('name')
        if 'identifier' in value:
            return value.get('identifier')
    return None


def _plan_node(child: Any) -> Dict[str, Any]:
    node_type = _node_type_label(getattr(child, 'node_type', 'unknown'))
    if node_type in {'Assignment', 'assignment'}:
        target = None
        value = None
        if len(getattr(child, 'children', [])) >= 2:
            left = child.children[0]
            right = child.children[1]
            target = _extract_assignment_target(left)
            right_type = _node_type_label(getattr(right, 'node_type', 'value'))
            if right_type in {'BinaryExpression', 'binary_expression'}:
                value = {'parts': [_extract_value(c) for c in getattr(right, 'children', [])]}
            else:
                value = _extract_value(right)
        status = extract_phoxel_runtime_status(child)
        step = {
            'step_type': 'assignment',
            'target': target,
            'value': value,
            'resolvable': target is not None,
        }
        if status:
            step['phoxel_runtime_status'] = status
        return step
    if node_type in {'BinaryExpression', 'binary_expression'}:
        vals = [_extract_value(c) for c in getattr(child, 'children', [])]
        status = extract_phoxel_runtime_status(child)
        step = {
            'step_type': 'binary_expression',
            'parts': vals,
            'resolvable': True,
        }
        if status:
            step['phoxel_runtime_status'] = status
        return step
    if node_type in {'Control', 'control'}:
        raw_value = getattr(child, 'value', {}) or {}
        keyword = _extract_value(child)
        condition_value = raw_value.get('condition_value') if isinstance(raw_value, dict) else None
        if condition_value is None and isinstance(raw_value, dict) and 'value' in raw_value:
            condition_value = raw_value.get('value')
        body_steps = [_plan_node(c) for c in getattr(child, 'children', [])]
        status = extract_phoxel_runtime_status(child)
        step = {
            'step_type': 'control',
            'keyword': keyword,
            'condition_value': condition_value,
            'body_steps': body_steps,
            'resolvable': False,
        }
        if status:
            step['phoxel_runtime_status'] = status
        return step
    if node_type in {'Block', 'block'}:
        nested_steps = [_plan_node(c) for c in getattr(child, 'children', [])]
        status = extract_phoxel_runtime_status(child)
        step = {
            'step_type': 'block',
            'child_count': len(nested_steps),
            'nested_steps': nested_steps,
            'resolvable': all(step.get('resolvable', False) for step in nested_steps) if nested_steps else False,
        }
        if status:
            step['phoxel_runtime_status'] = status
        return step
    status = extract_phoxel_runtime_status(child)
    step = {
        'step_type': 'unresolved',
        'node_type': node_type,
        'resolvable': False,
    }
    if status:
        step['phoxel_runtime_status'] = status
    return step


def ast_to_execution_plan(ast) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    env: Dict[str, Any] = {}
    unresolved = 0

    for child in getattr(ast, 'children', []):
        step = _plan_node(child)
        steps.append(step)
        if step['step_type'] == 'assignment' and step.get('target') is not None:
            env[step['target']] = step.get('value')
        if not step.get('resolvable', False):
            unresolved += 1

    step_statuses = [step.get('phoxel_runtime_status', {}) for step in steps if isinstance(step, dict)]

    return stamp_runtime_surface({
        'step_count': len(steps),
        'execution_steps': steps,
        'environment': env,
        'unresolved_count': unresolved,
        'fully_resolvable': unresolved == 0,
        'phoxel_runtime_status_explicit': any(bool(status) for status in step_statuses),
        'phoxel_runtime_status_rollup': rollup_phoxel_runtime_statuses(step_statuses),
    }, 'runtime_execution_plan')
