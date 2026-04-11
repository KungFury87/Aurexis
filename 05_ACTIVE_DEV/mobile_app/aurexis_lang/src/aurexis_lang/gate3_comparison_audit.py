"""Gate 3 authored-vs-real-capture comparison and earned-audit helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .evidence_tiers import EvidenceTier, normalize_evidence_tier
from .gate3_evidence_loop import GATE_3_STATUS

GATE_3_COMPARISON_RULES_VERSION = 'AUREXIS_GATE_3_AUTHORED_REAL_CAPTURE_COMPARISON_RULES_V1'
GATE_3_AUDIT_RULES_VERSION = 'AUREXIS_GATE_3_EARNED_EVIDENCE_AUDIT_V1'


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _collect_comparable_metrics(surface: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    if not surface:
        return {}
    comparable = surface.get('comparable_metrics', {})
    if isinstance(comparable, Mapping):
        out: Dict[str, float] = {}
        for key, value in comparable.items():
            f = _to_float(value)
            if f is not None:
                out[str(key)] = f
        return out
    return {}


def build_authored_reference_surface(summary: Mapping[str, Any]) -> Dict[str, Any]:
    total_scenes = max(1, int(summary.get('total_scenes', 1) or 1))
    total_primitives = float(summary.get('total_primitives', 0.0) or 0.0)
    total_executables = float(summary.get('total_executables', 0.0) or 0.0)
    consistency_rate = float(summary.get('overall_consistency_rate', 0.0) or 0.0)
    avg_processing = float(summary.get('average_processing_time_seconds', 0.0) or 0.0)
    return {
        'source_class': 'authored_reference',
        'evidence_tier': EvidenceTier.AUTHORED.value,
        'output_honesty_explicit': True,
        'comparable_metrics': {
            'primitive_density': total_primitives / total_scenes,
            'executable_density': total_executables / total_scenes,
            'consistency_rate': consistency_rate,
            'average_processing_time_seconds': avg_processing,
        },
    }


def build_real_capture_reference_surface(summary: Mapping[str, Any]) -> Dict[str, Any]:
    cv = dict(summary.get('cv_primitives', {}))
    conf = dict(summary.get('confidence', {}))
    return {
        'source_class': 'real_capture_reference',
        'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
        'output_honesty_explicit': bool(summary.get('output_honesty_explicit', True)),
        'comparable_metrics': {
            'primitive_density': float(cv.get('average', 0.0) or 0.0),
            'confidence_average': float(conf.get('average', 0.0) or 0.0),
            'batch_size': float(summary.get('batch_size', 0.0) or 0.0),
        },
    }


def compare_authored_real_capture_surfaces(
    *,
    authored_surface: Optional[Mapping[str, Any]],
    real_capture_surface: Optional[Mapping[str, Any]],
    gate3_evidence_loop: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    authored_metrics = _collect_comparable_metrics(authored_surface)
    real_metrics = _collect_comparable_metrics(real_capture_surface)
    authored_present = bool(authored_surface)
    real_present = bool(real_capture_surface)

    overlap = sorted(set(authored_metrics) & set(real_metrics))
    metric_deltas = {
        key: abs(authored_metrics[key] - real_metrics[key])
        for key in overlap
    }

    blocking_reasons = []
    if not authored_present:
        blocking_reasons.append('no_authored_reference')
    if not real_present:
        blocking_reasons.append('no_real_capture_reference')
    if not overlap:
        blocking_reasons.append('no_comparable_metrics_overlap')

    gate3_ready = bool((gate3_evidence_loop or {}).get('earned_candidate_ready', False))
    if gate3_evidence_loop and not gate3_ready:
        blocking_reasons.append('gate3_earned_candidate_not_ready')

    comparison_ready = authored_present and real_present and bool(overlap) and (not gate3_evidence_loop or gate3_ready)

    return {
        'gate_3_status': GATE_3_STATUS,
        'rules_version': GATE_3_COMPARISON_RULES_VERSION,
        'gate_clearance_authority': False,
        'authored_reference_present': authored_present,
        'real_capture_reference_present': real_present,
        'overlap_metric_count': len(overlap),
        'overlap_metrics': overlap,
        'metric_deltas': metric_deltas,
        'comparison_ready': bool(comparison_ready),
        'blocking_reasons': blocking_reasons,
    }


def audit_gate3_earned_evidence_scaffold(
    *,
    comparison_summary: Mapping[str, Any],
    gate3_evidence_loop: Mapping[str, Any],
) -> Dict[str, Any]:
    blocking_reasons = list(comparison_summary.get('blocking_reasons', []))
    loop_blocking = list(gate3_evidence_loop.get('blocking_reasons', []))
    for reason in loop_blocking:
        if reason not in blocking_reasons:
            blocking_reasons.append(reason)

    audit_ready = bool(comparison_summary.get('comparison_ready', False)) and bool(gate3_evidence_loop.get('earned_candidate_ready', False))
    if not comparison_summary.get('comparison_ready', False):
        if 'comparison_not_ready' not in blocking_reasons:
            blocking_reasons.append('comparison_not_ready')
    if not gate3_evidence_loop.get('earned_candidate_ready', False):
        if 'earned_candidate_not_ready' not in blocking_reasons:
            blocking_reasons.append('earned_candidate_not_ready')

    return {
        'gate_3_status': GATE_3_STATUS,
        'rules_version': GATE_3_AUDIT_RULES_VERSION,
        'gate_clearance_authority': False,
        'comparison_ready': bool(comparison_summary.get('comparison_ready', False)),
        'earned_candidate_ready': bool(gate3_evidence_loop.get('earned_candidate_ready', False)),
        'earned_audit_ready': bool(audit_ready),
        'source_counts': dict(gate3_evidence_loop.get('source_counts', {})),
        'overlap_metric_count': int(comparison_summary.get('overlap_metric_count', 0)),
        'blocking_reasons': blocking_reasons,
    }
