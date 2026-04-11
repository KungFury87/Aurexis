"""Gate 2 runtime-obedience helpers.

These helpers verify that the active runtime chain obeys frozen Gate 1 law
consistently across resolution, interpretation, state propagation, and branch-state
reporting. The output is authored/runtime evidence for Gate 2 work, not gate-clearing
physical proof.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

from .evidence_tiers import EvidenceTier, stamp_result
from .runtime_reporting import RUNTIME_ALIGNMENT_TARGET, RUNTIME_EVIDENCE_SCOPE, RUNTIME_GATE_STATUS, RUNTIME_REPORTING_RULES_VERSION, RUNTIME_STAGE_METADATA_VERSION


def _collect_unresolved_reasons(outputs: Iterable[Dict[str, Any]], reasons: Set[str]) -> None:
    for step in outputs or []:
        if not bool(step.get('resolved', False)):
            reason = step.get('reason')
            if reason:
                reasons.add(str(reason))
        nested = step.get('nested_output_steps', [])
        if nested:
            _collect_unresolved_reasons(nested, reasons)


def _collect_assignment_trace(outputs: Iterable[Dict[str, Any]], assignments: List[Tuple[str, Any]]) -> None:
    for step in outputs or []:
        if step.get('op') == 'assign' and bool(step.get('resolved', False)):
            target = step.get('target')
            if target is not None:
                assignments.append((str(target), step.get('value')))
        nested = step.get('nested_output_steps', [])
        if nested:
            _collect_assignment_trace(nested, assignments)


def _collect_propagated_blocked_reasons(timeline: Iterable[Dict[str, Any]]) -> Set[str]:
    reasons: Set[str] = set()
    for item in timeline or []:
        if not bool(item.get('resolved', False)):
            reason = item.get('reason')
            if reason:
                reasons.add(str(reason))
    return reasons


def _build_propagated_assignment_trace(timeline: Iterable[Dict[str, Any]]) -> List[Tuple[str, Any]]:
    trace: List[Tuple[str, Any]] = []
    previous_snapshot: Dict[str, Any] = {}
    for item in timeline or []:
        snapshot = dict(item.get('environment_snapshot', {}) or {})
        if item.get('op') == 'assign' and bool(item.get('resolved', False)):
            changed_keys = [k for k, v in snapshot.items() if previous_snapshot.get(k) != v]
            if changed_keys:
                target = changed_keys[-1]
                trace.append((str(target), snapshot.get(target)))
        previous_snapshot = snapshot
    return trace


def _latest_assignment_map(assignments: List[Tuple[str, Any]]) -> Dict[str, Any]:
    latest: Dict[str, Any] = {}
    for target, value in assignments:
        latest[str(target)] = value
    return latest


def _surface_phoxel_explicit(surface: Dict[str, Any] | None) -> bool:
    return bool((surface or {}).get('phoxel_runtime_status_explicit', False))


def _surface_phoxel_rollup(surface: Dict[str, Any] | None) -> Dict[str, Any]:
    return dict((surface or {}).get('phoxel_runtime_status_rollup', {}) or {})


def _surface_explicit_count(surface: Dict[str, Any] | None) -> int:
    rollup = _surface_phoxel_rollup(surface)
    return int(rollup.get('explicit_count', 0) or 0)


def _mutation_summary_consistent(resolution_assignments: List[Tuple[str, Any]], propagated: Dict[str, Any]) -> bool:
    summary = dict(propagated.get('mutation_summary', {}) or {})
    mutated_targets = {str(v) for v in summary.get('mutated_targets', []) if v is not None}
    assignment_targets = {str(target) for target, _ in resolution_assignments}
    return int(summary.get('mutation_step_count', 0) or 0) >= len(resolution_assignments) and assignment_targets.issubset(mutated_targets)


def _phoxel_surface_mismatch_summary(*, control_summary: Dict[str, Any] | None = None, control_state_machine: Dict[str, Any] | None = None, control_transitions: Dict[str, Any] | None = None, execution_plan_surface: Dict[str, Any] | None = None, execution_trace_surface: Dict[str, Any] | None = None, propagated: Dict[str, Any] | None = None, branch: Dict[str, Any] | None = None) -> Dict[str, Any]:
    surfaces = {
        'control_summary': control_summary,
        'control_state_machine': control_state_machine,
        'control_transitions': control_transitions,
        'execution_plan_surface': execution_plan_surface,
        'execution_trace_surface': execution_trace_surface,
        'propagation': propagated,
        'branch': branch,
    }
    explicit_map = {name: _surface_phoxel_explicit(surface) for name, surface in surfaces.items() if surface is not None}
    count_map = {name: _surface_explicit_count(surface) for name, surface in surfaces.items() if surface is not None}
    explicit_values = set(explicit_map.values())
    positive_counts = {name: count for name, count in count_map.items() if count > 0}
    mismatch_surfaces = sorted(name for name, explicit in explicit_map.items() if explicit is not True)
    return {
        'explicit_map': explicit_map,
        'explicit_count_map': count_map,
        'explicit_alignment': len(explicit_values) <= 1,
        'positive_count_surfaces': sorted(positive_counts.keys()),
        'explicit_mismatch_surfaces': mismatch_surfaces,
    }

def _extract_runtime_surface_metadata(surface: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'report_scope': surface.get('report_scope'),
        'gate_2_status': surface.get('gate_2_status'),
        'reporting_rules_version': surface.get('reporting_rules_version'),
        'evidence_scope': surface.get('evidence_scope'),
        'stage_metadata_version': surface.get('stage_metadata_version'),
        'report_surface_alignment_target': surface.get('report_surface_alignment_target'),
        'partial_reporting_explicit': surface.get('partial_reporting_explicit'),
        'stage_metadata_complete': surface.get('stage_metadata_complete'),
        'gate_clearance_authority': surface.get('gate_clearance_authority'),
        'world_authority_primary': surface.get('world_authority_primary'),
        'image_access_primary': surface.get('image_access_primary'),
    }


def _runtime_surface_metadata_consistent(*surfaces: Dict[str, Any]) -> bool:
    expected = {
        'gate_2_status': RUNTIME_GATE_STATUS,
        'reporting_rules_version': RUNTIME_REPORTING_RULES_VERSION,
        'evidence_scope': RUNTIME_EVIDENCE_SCOPE,
        'stage_metadata_version': RUNTIME_STAGE_METADATA_VERSION,
        'report_surface_alignment_target': RUNTIME_ALIGNMENT_TARGET,
        'partial_reporting_explicit': True,
        'stage_metadata_complete': True,
        'gate_clearance_authority': False,
        'world_authority_primary': True,
        'image_access_primary': True,
    }
    for surface in surfaces:
        metadata = _extract_runtime_surface_metadata(surface)
        if metadata['gate_2_status'] != expected['gate_2_status']:
            return False
        if metadata['reporting_rules_version'] != expected['reporting_rules_version']:
            return False
        if metadata['evidence_scope'] != expected['evidence_scope']:
            return False
        if metadata['stage_metadata_version'] != expected['stage_metadata_version']:
            return False
        if metadata['report_surface_alignment_target'] != expected['report_surface_alignment_target']:
            return False
        if metadata['partial_reporting_explicit'] is not expected['partial_reporting_explicit']:
            return False
        if metadata['stage_metadata_complete'] is not expected['stage_metadata_complete']:
            return False
        if metadata['gate_clearance_authority'] is not expected['gate_clearance_authority']:
            return False
        if metadata['world_authority_primary'] is not expected['world_authority_primary']:
            return False
        if metadata['image_access_primary'] is not expected['image_access_primary']:
            return False
        if not str(metadata.get('report_scope') or '').startswith('runtime_'):
            return False
    return True



def _edge_case_reason_set(*reason_sets: Set[str]) -> Set[str]:
    combined: Set[str] = set()
    for reasons in reason_sets:
        for reason in reasons:
            if reason in {
                'missing_target',
                'unsupported_step',
                'unsupported_iterable',
                'unknown_iterable',
                'non_numeric_operands',
                'non_boolean_operands',
                'comparison_not_supported',
                'division_by_zero',
                'incomplete_expression',
            } or str(reason).startswith('unsupported_operator:'):
                combined.add(str(reason))
    return combined



def evaluate_runtime_obedience(
    resolution: Dict[str, Any],
    interpreted: Dict[str, Any],
    propagated: Dict[str, Any],
    branch: Dict[str, Any],
    control_summary: Dict[str, Any] | None = None,
    control_state_machine: Dict[str, Any] | None = None,
    deeper_execution: Dict[str, Any] | None = None,
    control_transitions: Dict[str, Any] | None = None,
    execution_plan_surface: Dict[str, Any] | None = None,
    execution_trace_surface: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    resolution_env = dict(resolution.get('final_environment', {}) or {})
    interpreted_env = dict(interpreted.get('final_environment', {}) or {})
    propagated_env = dict(propagated.get('final_environment', {}) or {})
    branch_env = dict(branch.get('base_environment', {}) or {})

    resolution_reasons: Set[str] = set()
    _collect_unresolved_reasons(resolution.get('output_steps', []), resolution_reasons)
    interpreted_reasons = {str(v) for v in interpreted.get('blocked_reasons', []) if v}
    propagated_reasons = _collect_propagated_blocked_reasons(propagated.get('timeline', []))
    branch_reasons = {str(v.get('reason')) for v in branch.get('branch_states', []) if v.get('reason')}

    resolution_assignments: List[Tuple[str, Any]] = []
    _collect_assignment_trace(resolution.get('output_steps', []), resolution_assignments)
    propagated_assignments = _build_propagated_assignment_trace(propagated.get('timeline', []))

    edge_case_reasons = _edge_case_reason_set(resolution_reasons)
    deeper_reasons: Set[str] = set()
    if deeper_execution is not None:
        _collect_unresolved_reasons(deeper_execution.get('output_steps', []), deeper_reasons)
    latest_resolution_assignments = _latest_assignment_map(resolution_assignments)
    latest_propagated_assignments = _latest_assignment_map(propagated_assignments)

    checks = {
        'environment_consistent': resolution_env == interpreted_env == propagated_env == branch_env,
        'blocked_reasons_preserved': resolution_reasons.issubset(interpreted_reasons | propagated_reasons | branch_reasons),
        'statuses_explicit': (
            isinstance(resolution.get('fully_resolved'), bool)
            and interpreted.get('outcome') in {'complete', 'partial', 'blocked'}
            and isinstance(propagated.get('statefully_resolved'), bool)
            and isinstance(branch.get('blocked_branch_count'), int)
        ),
        'state_mutation_consistent': propagated_env == resolution_env and resolution_assignments == propagated_assignments,
        'honest_partiality': (
            (bool(resolution.get('fully_resolved')) and interpreted.get('outcome') == 'complete' and not interpreted.get('blocked_reasons'))
            or (not bool(resolution.get('fully_resolved')) and interpreted.get('outcome') in {'partial', 'blocked'})
        ),
        'failure_reasons_propagated': resolution_reasons.issubset(interpreted_reasons) and resolution_reasons.issubset(propagated_reasons | branch_reasons),
        'mixed_path_state_consistent': (
            all(resolution_env.get(target) == value for target, value in latest_resolution_assignments.items())
            and all(propagated_env.get(target) == value for target, value in latest_propagated_assignments.items())
            and (not resolution_reasons or interpreted.get('outcome') in {'partial', 'blocked'})
        ),
        'report_surface_alignment': _runtime_surface_metadata_consistent(resolution, interpreted, propagated, branch),
        'multi_branch_reason_consistent': len((propagated_reasons | branch_reasons) - resolution_reasons) >= 0 and resolution_reasons.issubset(propagated_reasons | branch_reasons | interpreted_reasons),
        'interpreter_edge_case_honest': edge_case_reasons.issubset(interpreted_reasons | propagated_reasons | branch_reasons),
        'stage_metadata_complete': _runtime_surface_metadata_consistent(resolution, interpreted, propagated, branch),
        'control_surface_alignment': True if control_summary is None or control_state_machine is None else _runtime_surface_metadata_consistent(control_summary, control_state_machine),
        'control_phoxel_surface_alignment': True if control_summary is None or control_state_machine is None or control_transitions is None else (
            _surface_phoxel_explicit(control_summary) == _surface_phoxel_explicit(control_state_machine) == _surface_phoxel_explicit(control_transitions)
            and _surface_explicit_count(control_summary) == _surface_explicit_count(control_state_machine) == _surface_explicit_count(control_transitions)
        ),
        'deeper_runtime_surface_alignment': True if deeper_execution is None else _runtime_surface_metadata_consistent(deeper_execution),
        'control_transition_surface_alignment': True if control_transitions is None else _runtime_surface_metadata_consistent(control_transitions),
        'planning_trace_surface_alignment': True if execution_plan_surface is None or execution_trace_surface is None else _runtime_surface_metadata_consistent(execution_plan_surface, execution_trace_surface),
        'nested_control_pattern_honest': True if execution_plan_surface is None or execution_trace_surface is None else (
            bool(execution_plan_surface.get('partial_reporting_explicit', False)) is True
            and bool(execution_trace_surface.get('partial_reporting_explicit', False)) is True
            and execution_plan_surface.get('gate_2_status') == 'IN_PROGRESS'
            and execution_trace_surface.get('gate_2_status') == 'IN_PROGRESS'
            and (not resolution_reasons or interpreted.get('outcome') in {'partial', 'blocked'})
        ),
        'nested_loop_control_honest': True if control_summary is None or control_state_machine is None else (
            int(control_summary.get('unresolved_count', 0)) == int(control_state_machine.get('blocked_transition_count', 0))
            and bool(control_summary.get('partial_reporting_explicit', False)) is True
            and bool(control_state_machine.get('partial_reporting_explicit', False)) is True
        ),
        'mutation_edge_case_honest': (
            all(resolution_env.get(target) == value for target, value in latest_resolution_assignments.items())
            and all(propagated_env.get(target) == value for target, value in latest_propagated_assignments.items())
            and (not resolution_reasons or interpreted.get('outcome') in {'partial', 'blocked'})
        ),
        'mutation_summary_consistent': _mutation_summary_consistent(resolution_assignments, propagated),
        'nested_loop_failure_honest': True if deeper_execution is None else deeper_reasons.issubset(interpreted_reasons | propagated_reasons | branch_reasons),
    }
    return {
        'checks': checks,
        'all_checks_pass': all(checks.values()),
        'resolution_reasons': sorted(resolution_reasons),
        'interpreted_reasons': sorted(interpreted_reasons),
        'propagated_reasons': sorted(propagated_reasons),
        'branch_reasons': sorted(branch_reasons),
        'resolution_assignment_trace': resolution_assignments,
        'propagated_assignment_trace': propagated_assignments,
        'final_environment': resolution_env,
        'outcome': interpreted.get('outcome'),
        'blocked_branch_count': int(branch.get('blocked_branch_count', 0)),
        'mutation_summary': dict(propagated.get('mutation_summary', {}) or {}),
        'phoxel_surface_mismatches': _phoxel_surface_mismatch_summary(
            control_summary=control_summary,
            control_state_machine=control_state_machine,
            control_transitions=control_transitions,
            execution_plan_surface=execution_plan_surface,
            execution_trace_surface=execution_trace_surface,
            propagated=propagated,
            branch=branch,
        ),
        'surface_metadata': {
            'resolution': _extract_runtime_surface_metadata(resolution),
            'interpretation': _extract_runtime_surface_metadata(interpreted),
            'propagation': _extract_runtime_surface_metadata(propagated),
            'branch': _extract_runtime_surface_metadata(branch),
            'control_resolution': _extract_runtime_surface_metadata(control_summary) if control_summary else None,
            'control_state_machine': _extract_runtime_surface_metadata(control_state_machine) if control_state_machine else None,
            'deeper_execution': _extract_runtime_surface_metadata(deeper_execution) if deeper_execution else None,
            'control_transitions': _extract_runtime_surface_metadata(control_transitions) if control_transitions else None,
            'execution_plan_surface': _extract_runtime_surface_metadata(execution_plan_surface) if execution_plan_surface else None,
            'execution_trace_surface': _extract_runtime_surface_metadata(execution_trace_surface) if execution_trace_surface else None,
        },
    }


def build_runtime_obedience_report(
    resolution: Dict[str, Any],
    interpreted: Dict[str, Any],
    propagated: Dict[str, Any],
    branch: Dict[str, Any],
    control_summary: Dict[str, Any] | None = None,
    control_state_machine: Dict[str, Any] | None = None,
    deeper_execution: Dict[str, Any] | None = None,
    control_transitions: Dict[str, Any] | None = None,
    execution_plan_surface: Dict[str, Any] | None = None,
    execution_trace_surface: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report = evaluate_runtime_obedience(
        resolution,
        interpreted,
        propagated,
        branch,
        control_summary,
        control_state_machine,
        deeper_execution,
        control_transitions,
        execution_plan_surface,
        execution_trace_surface,
    )
    report['report_scope'] = 'gate_2_runtime_obedience'
    report['gate_clearance_authority'] = False
    report['world_authority_primary'] = True
    report['image_access_primary'] = True
    report['reporting_rules_version'] = RUNTIME_REPORTING_RULES_VERSION
    report['report_surface_consistency'] = {
        'evidence_scope': RUNTIME_EVIDENCE_SCOPE,
        'gate_status': RUNTIME_GATE_STATUS,
        'mixed_path_reporting_explicit': True,
        'stage_metadata_version': RUNTIME_STAGE_METADATA_VERSION,
        'report_surface_alignment_target': RUNTIME_ALIGNMENT_TARGET,
        'stage_metadata_complete': True,
        'execution_plan_phoxel_runtime_status_explicit': bool((execution_plan_surface or {}).get('phoxel_runtime_status_explicit', False)),
        'execution_plan_phoxel_runtime_rollup': (execution_plan_surface or {}).get('phoxel_runtime_status_rollup', {}),
        'execution_trace_phoxel_runtime_status_explicit': bool((execution_trace_surface or {}).get('phoxel_runtime_status_explicit', False)),
        'execution_trace_phoxel_runtime_rollup': (execution_trace_surface or {}).get('phoxel_runtime_status_rollup', {}),
        'propagation_phoxel_runtime_status_explicit': bool((propagated or {}).get('phoxel_runtime_status_explicit', False)),
        'propagation_phoxel_runtime_rollup': (propagated or {}).get('phoxel_runtime_status_rollup', {}),
        'propagation_mutation_summary': dict((propagated or {}).get('mutation_summary', {}) or {}),
        'branch_phoxel_runtime_status_explicit': bool((branch or {}).get('phoxel_runtime_status_explicit', False)),
        'branch_phoxel_runtime_rollup': (branch or {}).get('phoxel_runtime_status_rollup', {}),
        'branch_transition_summary': dict((branch or {}).get('branch_transition_summary', {}) or {}),
        'control_resolution_phoxel_runtime_status_explicit': bool((control_summary or {}).get('phoxel_runtime_status_explicit', False)),
        'control_resolution_phoxel_runtime_rollup': (control_summary or {}).get('phoxel_runtime_status_rollup', {}),
        'control_state_machine_phoxel_runtime_status_explicit': bool((control_state_machine or {}).get('phoxel_runtime_status_explicit', False)),
        'control_state_machine_phoxel_runtime_rollup': (control_state_machine or {}).get('phoxel_runtime_status_rollup', {}),
        'control_transitions_phoxel_runtime_status_explicit': bool((control_transitions or {}).get('phoxel_runtime_status_explicit', False)),
        'control_transitions_phoxel_runtime_rollup': (control_transitions or {}).get('phoxel_runtime_status_rollup', {}),
        'phoxel_surface_mismatches': report.get('phoxel_surface_mismatches', {}),
    }
    return stamp_result(
        report,
        EvidenceTier.AUTHORED,
        source_tiers=[EvidenceTier.AUTHORED],
        earned_proof=False,
        note='Gate 2 runtime-obedience report is authored/runtime evidence only, not gate-clearing physical proof.',
        requires_real_capture=False,
    )
