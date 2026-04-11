"""Gate 3 earned-evidence loop helpers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

from .evidence_tiers import EvidenceTier, normalize_evidence_tier

GATE_3_STATUS = 'IN_PROGRESS'
GATE_3_RULES_VERSION = 'AUREXIS_GATE_3_EARNED_EVIDENCE_LOOP_RULES_V1'
GATE_3_SEPARATION_VERSION = 'AUREXIS_GATE_3_EVIDENCE_SEPARATION_RULES_V1'


def _count_sources(values: Iterable[Any]) -> Dict[str, int]:
    counts = {tier.value: 0 for tier in EvidenceTier}
    for value in values:
        try:
            tier = normalize_evidence_tier(value)
        except Exception:
            continue
        counts[tier.value] += 1
    return counts


def evaluate_gate3_evidence_loop(
    *,
    source_tiers: Iterable[Any],
    evidence_validated: bool,
    multi_frame_consistent: bool,
    output_honesty_explicit: bool,
    gate2_complete: bool,
) -> Dict[str, Any]:
    counts = _count_sources(source_tiers)
    authored_present = counts[EvidenceTier.AUTHORED.value] > 0
    real_capture_present = counts[EvidenceTier.REAL_CAPTURE.value] > 0
    lab_present = counts[EvidenceTier.LAB.value] > 0
    earned_present = counts[EvidenceTier.EARNED.value] > 0

    blocking_reasons = []
    if not gate2_complete:
        blocking_reasons.append('gate2_not_complete')
    if not authored_present:
        blocking_reasons.append('no_authored_inputs')
    if not real_capture_present:
        blocking_reasons.append('no_real_capture_inputs')
    if not output_honesty_explicit:
        blocking_reasons.append('output_honesty_not_explicit')
    if not evidence_validated:
        blocking_reasons.append('evidence_not_validated')
    if not multi_frame_consistent:
        blocking_reasons.append('multi_frame_consistency_missing')
    if lab_present and not real_capture_present:
        blocking_reasons.append('lab_not_upgradeable_without_real_capture')

    earned_candidate_ready = (
        gate2_complete
        and authored_present
        and real_capture_present
        and output_honesty_explicit
        and evidence_validated
        and multi_frame_consistent
    )

    return {
        'gate_3_status': GATE_3_STATUS,
        'rules_version': GATE_3_RULES_VERSION,
        'separation_rules_version': GATE_3_SEPARATION_VERSION,
        'gate_clearance_authority': False,
        'output_honesty_explicit': bool(output_honesty_explicit),
        'source_counts': counts,
        'authored_present': authored_present,
        'real_capture_present': real_capture_present,
        'lab_present': lab_present,
        'earned_present': earned_present,
        'evidence_validated': bool(evidence_validated),
        'multi_frame_consistent': bool(multi_frame_consistent),
        'earned_candidate_ready': bool(earned_candidate_ready),
        'blocking_reasons': blocking_reasons,
    }


def stamp_gate3_surface(summary: Mapping[str, Any], *, source_class: str, evidence_tier: Any) -> Dict[str, Any]:
    stamped = dict(summary)
    stamped['source_class'] = source_class
    stamped['evidence_tier'] = normalize_evidence_tier(evidence_tier).value
    stamped['gate_3_status'] = GATE_3_STATUS
    stamped['gate_clearance_authority'] = False
    stamped['output_honesty_explicit'] = bool(stamped.get('output_honesty_explicit', True))
    return stamped
