from typing import Dict, Any, List

ALLOWED_MOBILE_DEMO_EVIDENCE = {'real-capture', 'earned'}


def validate_narrow_mobile_demonstration_target(claim: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    required_truthy = [
        'pc_preparation_supported',
        'phone_capture_supported',
        'scope_is_narrow',
        'output_honesty_explicit',
        'no_hidden_exotic_hardware',
    ]
    for key in required_truthy:
        if not claim.get(key, False):
            errors.append(f'missing_{key}')

    evidence_tier = claim.get('evidence_tier')
    if evidence_tier not in ALLOWED_MOBILE_DEMO_EVIDENCE:
        errors.append('insufficient_mobile_demo_evidence')

    if claim.get('app_store_ready_claim', False):
        errors.append('app_store_ready_claim')
    if claim.get('general_vision_claim', False):
        errors.append('general_vision_claim')
    if claim.get('production_ready_claim', False):
        errors.append('production_ready_claim')

    return errors
