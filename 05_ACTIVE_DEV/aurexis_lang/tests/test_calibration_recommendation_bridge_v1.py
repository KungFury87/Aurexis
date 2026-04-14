"""
Aurexis Core — Calibration Recommendation Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.evidence_delta_analysis_bridge_v1 import (
    DeltaVerdict, PrimitiveRecord, ContractOutcome, SignatureOutcome,
    SubstrateOutput, analyze_deltas,
)
from aurexis_lang.calibration_recommendation_bridge_v1 import (
    RECOMMENDATION_VERSION, RECOMMENDATION_FROZEN,
    RecommendationKind, RecommendationPriority,
    CalibrationRecommendation, RecommendationVerdict,
    RecommendationSurface, generate_recommendations, make_empty_surface,
    EXPECTED_KIND_COUNT, EXPECTED_PRIORITY_COUNT, EXPECTED_VERDICT_COUNT,
)


def _prims():
    return (
        PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),
        PrimitiveRecord(name="B", kind="LINE", confidence=0.8, x=30.0, y=40.0),
    )

def _contracts():
    return (ContractOutcome(contract_name="set", passed=True),)

def _sigs():
    return (SignatureOutcome(signature_name="s1", matched=True, similarity=0.95),)

def _expected():
    return SubstrateOutput(label="expected", primitives=_prims(), contracts=_contracts(), signatures=_sigs())


def test_version():
    assert RECOMMENDATION_VERSION == "V1.0"

def test_frozen():
    assert RECOMMENDATION_FROZEN is True

def test_kind_count():
    assert len(RecommendationKind) == EXPECTED_KIND_COUNT

def test_priority_count():
    assert len(RecommendationPriority) == EXPECTED_PRIORITY_COUNT

def test_verdict_count():
    assert len(RecommendationVerdict) == EXPECTED_VERDICT_COUNT

def test_no_action_needed():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    assert rec.verdict == RecommendationVerdict.NO_ACTION_NEEDED

def test_missing_triggers_capture_guidance():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=(_prims()[0],), contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    kinds = [r.kind for r in rec.recommendations]
    assert RecommendationKind.CAPTURE_GUIDANCE in kinds

def test_extra_triggers_extractor_profile():
    e = _expected()
    extra = _prims() + (PrimitiveRecord(name="C", kind="REGION", confidence=0.5),)
    o = SubstrateOutput(label="observed", primitives=extra, contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    kinds = [r.kind for r in rec.recommendations]
    assert RecommendationKind.EXTRACTOR_PROFILE in kinds

def test_confidence_triggers_threshold():
    e = _expected()
    degraded = (PrimitiveRecord(name="A", kind="POINT", confidence=0.5, x=10.0, y=20.0),
                PrimitiveRecord(name="B", kind="LINE", confidence=0.3, x=30.0, y=40.0))
    o = SubstrateOutput(label="observed", primitives=degraded, contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    kinds = [r.kind for r in rec.recommendations]
    assert RecommendationKind.THRESHOLD_ADJUSTMENT in kinds

def test_contract_triggers_review():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(),
                        contracts=(ContractOutcome(contract_name="set", passed=False),), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    kinds = [r.kind for r in rec.recommendations]
    assert RecommendationKind.CONTRACT_REVIEW in kinds

def test_signature_triggers_review():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(),
                        signatures=(SignatureOutcome(signature_name="s1", matched=False, similarity=0.3),))
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    kinds = [r.kind for r in rec.recommendations]
    assert RecommendationKind.SIGNATURE_REVIEW in kinds

def test_critical_advisory():
    many = tuple(PrimitiveRecord(name=f"P{i}", kind="POINT", confidence=0.9) for i in range(5))
    e = SubstrateOutput(label="expected", primitives=many, contracts=_contracts(), signatures=_sigs())
    o = SubstrateOutput(label="observed", primitives=(), contracts=(), signatures=())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    assert rec.verdict == RecommendationVerdict.CRITICAL_ADVISORY

def test_all_advisory():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=(_prims()[0],), contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    assert all(r.advisory is True for r in rec.recommendations)

def test_surface_hash_deterministic():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(), signatures=_sigs())
    d = analyze_deltas(e, o)
    r1 = generate_recommendations(d)
    r2 = generate_recommendations(d)
    assert r1.surface_hash == r2.surface_hash

def test_serialization():
    e = _expected()
    degraded = (PrimitiveRecord(name="A", kind="POINT", confidence=0.5, x=10.0, y=20.0),
                PrimitiveRecord(name="B", kind="LINE", confidence=0.3, x=30.0, y=40.0))
    o = SubstrateOutput(label="observed", primitives=degraded, contracts=_contracts(), signatures=_sigs())
    delta = analyze_deltas(e, o)
    rec = generate_recommendations(delta)
    d = rec.to_dict()
    assert "recommendations" in d
    assert '"verdict"' in rec.to_json()

def test_make_empty_surface():
    s = make_empty_surface()
    assert s.verdict == RecommendationVerdict.NO_ACTION_NEEDED
