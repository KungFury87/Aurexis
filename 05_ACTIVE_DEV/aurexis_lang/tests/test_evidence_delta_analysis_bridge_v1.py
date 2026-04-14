"""
Aurexis Core — Evidence Delta Analysis Bridge V1 — pytest suite
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.evidence_delta_analysis_bridge_v1 import (
    DELTA_ANALYSIS_VERSION, DELTA_ANALYSIS_FROZEN,
    DeltaVerdict, PrimitiveRecord, ContractOutcome, SignatureOutcome,
    SubstrateOutput, DeltaSurface, analyze_deltas, make_error_surface,
    EXPECTED_VERDICT_COUNT,
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
    assert DELTA_ANALYSIS_VERSION == "V1.0"

def test_frozen():
    assert DELTA_ANALYSIS_FROZEN is True

def test_verdict_count():
    assert len(DeltaVerdict) == EXPECTED_VERDICT_COUNT

def test_identical():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.verdict == DeltaVerdict.IDENTICAL

def test_within_tolerance():
    e = _expected()
    shifted = (
        PrimitiveRecord(name="A", kind="POINT", confidence=0.88, x=10.5, y=20.5),
        PrimitiveRecord(name="B", kind="LINE", confidence=0.78, x=30.5, y=40.5),
    )
    o = SubstrateOutput(label="observed", primitives=shifted, contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.verdict == DeltaVerdict.WITHIN_TOLERANCE

def test_missing():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=(_prims()[0],), contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.verdict == DeltaVerdict.MISSING_PRIMITIVES
    assert s.missing_primitive_count == 1

def test_extra():
    e = _expected()
    extra = _prims() + (PrimitiveRecord(name="C", kind="REGION", confidence=0.5),)
    o = SubstrateOutput(label="observed", primitives=extra, contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.verdict == DeltaVerdict.EXTRA_PRIMITIVES

def test_mixed():
    e = _expected()
    mixed = (PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),
             PrimitiveRecord(name="C", kind="REGION", confidence=0.5))
    o = SubstrateOutput(label="observed", primitives=mixed, contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.verdict == DeltaVerdict.MIXED

def test_contract_change():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(),
                        contracts=(ContractOutcome(contract_name="set", passed=False),), signatures=_sigs())
    s = analyze_deltas(e, o)
    assert s.changed_contract_count == 1

def test_signature_change():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(),
                        signatures=(SignatureOutcome(signature_name="s1", matched=False, similarity=0.3),))
    s = analyze_deltas(e, o)
    assert s.changed_signature_count == 1

def test_hash_deterministic():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(), signatures=_sigs())
    s1 = analyze_deltas(e, o)
    s2 = analyze_deltas(e, o)
    assert s1.analysis_hash == s2.analysis_hash

def test_serialization():
    e = _expected()
    o = SubstrateOutput(label="observed", primitives=_prims(), contracts=_contracts(), signatures=_sigs())
    s = analyze_deltas(e, o)
    d = s.to_dict()
    assert "verdict" in d
    assert '"verdict"' in s.to_json()

def test_substrate_output_helpers():
    e = _expected()
    assert e.primitive_names() == {"A", "B"}
    assert e.primitive_by_name("A").confidence == 0.9
    assert e.primitive_by_name("Z") is None

def test_make_error_surface():
    s = make_error_surface("x")
    assert s.verdict == DeltaVerdict.ERROR
