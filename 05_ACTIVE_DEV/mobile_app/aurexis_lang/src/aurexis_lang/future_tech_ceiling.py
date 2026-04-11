from typing import Dict, Any, List

BLOCKED_FUTURE_TECH_DRIFT = {
    'ontology_rewrite_required',
    'hardware_required_for_legality',
    'behavior_changes_with_hardware',
    'sensor_specific_semantics',
    'current_floor_invalidated',
}


def validate_future_tech_ceiling_criteria(claim: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    for key in BLOCKED_FUTURE_TECH_DRIFT:
        if claim.get(key, False):
            errors.append(key)

    allowed_improvements = {'confidence', 'precision', 'robustness', 'speed', 'tolerance'}
    improvements = set(claim.get('improves_only', []))
    if improvements and not improvements.issubset(allowed_improvements):
        errors.append('non_capability_improvement_claim')

    if claim.get('changes_law_shape', False):
        errors.append('changes_law_shape')

    return errors
