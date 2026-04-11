from typing import Dict, Any, List

from .runtime_reporting import stamp_runtime_surface


def _collect_outputs(outputs: List[Dict[str, Any]], produced_values: List[Any], blocked_reasons: List[str]):
    for step in outputs:
        op = step.get('op')
        if op == 'assign' and step.get('resolved'):
            produced_values.append(step.get('value'))
        elif op == 'binary_expr':
            if step.get('resolved'):
                produced_values.append(step.get('result'))
            else:
                blocked_reasons.append(step.get('reason') or 'binary_expr_unresolved')
        elif op in {'block', 'control'}:
            if not step.get('resolved', False):
                default_reason = 'block_unresolved' if op == 'block' else 'control_unresolved'
                blocked_reasons.append(step.get('reason') or default_reason)
            _collect_outputs(step.get('nested_output_steps', []), produced_values, blocked_reasons)
        elif not step.get('resolved', False):
            blocked_reasons.append(step.get('reason') or f"{step.get('op', 'unknown')}_unresolved")


def interpret_execution_result(result: Dict[str, Any]) -> Dict[str, Any]:
    outputs = result.get('output_steps', [])
    produced_values: List[Any] = []
    blocked_reasons: List[str] = []
    _collect_outputs(outputs, produced_values, blocked_reasons)

    fully_resolved = bool(result.get('fully_resolved', False))
    outcome = 'complete' if fully_resolved else ('partial' if produced_values else 'blocked')

    return stamp_runtime_surface({
        'outcome': outcome,
        'produced_values': produced_values,
        'blocked_reasons': sorted(set(blocked_reasons)),
        'final_environment': result.get('final_environment', {}),
        'fully_resolved': fully_resolved,
    }, 'runtime_interpretation')
