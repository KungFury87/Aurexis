#!/usr/bin/env python3
"""
Aurexis Core — Evidence Delta Analysis Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.evidence_delta_analysis_bridge_v1 import (
    DELTA_ANALYSIS_VERSION, DELTA_ANALYSIS_FROZEN,
    DeltaVerdict, PrimitiveRecord, ContractOutcome, SignatureOutcome,
    SubstrateOutput, PrimitiveDelta, ContractDelta, SignatureDelta,
    DeltaSurface, analyze_deltas, make_error_surface,
    EXPECTED_VERDICT_COUNT, EXPECTED_DELTA_FIELDS,
    DEFAULT_CONFIDENCE_TOLERANCE, DEFAULT_POSITION_TOLERANCE,
)

PASS_COUNT = 0
FAIL_COUNT = 0

def section(name):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")

def check(cond, label):
    global PASS_COUNT, FAIL_COUNT
    s = "PASS" if cond else "FAIL"
    if cond: PASS_COUNT += 1
    else: FAIL_COUNT += 1
    print(f"  [{s}] {label}")

# ── 1. Module version and frozen state ──
section("1. Module Version and Frozen State")
check(DELTA_ANALYSIS_VERSION == "V1.0", "Version V1.0")
check(DELTA_ANALYSIS_FROZEN is True, "Module frozen")

# ── 2. Verdict enum ──
section("2. Verdict Enum")
check(len(DeltaVerdict) == EXPECTED_VERDICT_COUNT, f"Verdict count == {EXPECTED_VERDICT_COUNT}")
check(DeltaVerdict.IDENTICAL.value == "IDENTICAL", "IDENTICAL verdict")
check(DeltaVerdict.WITHIN_TOLERANCE.value == "WITHIN_TOLERANCE", "WITHIN_TOLERANCE verdict")

# ── 3. Identical outputs ──
section("3. Identical Outputs")
prims = (
    PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),
    PrimitiveRecord(name="B", kind="LINE", confidence=0.8, x=30.0, y=40.0),
)
contracts = (ContractOutcome(contract_name="set_contract", passed=True),)
sigs = (SignatureOutcome(signature_name="sig_1", matched=True, similarity=0.95),)
expected = SubstrateOutput(label="expected", primitives=prims, contracts=contracts, signatures=sigs)
observed = SubstrateOutput(label="observed", primitives=prims, contracts=contracts, signatures=sigs)
surface = analyze_deltas(expected, observed)
check(surface.verdict == DeltaVerdict.IDENTICAL, "Identical → IDENTICAL verdict")
check(surface.missing_primitive_count == 0, "No missing")
check(surface.extra_primitive_count == 0, "No extra")
check(surface.matched_primitive_count == 2, "2 matched")
check(surface.changed_contract_count == 0, "No contract changes")
check(surface.changed_signature_count == 0, "No signature changes")

# ── 4. Within tolerance ──
section("4. Within Tolerance")
obs_prims = (
    PrimitiveRecord(name="A", kind="POINT", confidence=0.88, x=10.5, y=20.5),
    PrimitiveRecord(name="B", kind="LINE", confidence=0.78, x=30.5, y=40.5),
)
observed2 = SubstrateOutput(label="observed", primitives=obs_prims, contracts=contracts, signatures=sigs)
surface2 = analyze_deltas(expected, observed2)
check(surface2.verdict == DeltaVerdict.WITHIN_TOLERANCE, "Small shift → WITHIN_TOLERANCE")
check(surface2.max_confidence_delta > 0, "Max confidence delta > 0")
check(surface2.max_confidence_delta <= 0.05, "Max confidence delta within tolerance")

# ── 5. Missing primitives ──
section("5. Missing Primitives")
obs_partial = SubstrateOutput(
    label="observed",
    primitives=(PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),),
    contracts=contracts, signatures=sigs,
)
surface3 = analyze_deltas(expected, obs_partial)
check(surface3.verdict == DeltaVerdict.MISSING_PRIMITIVES, "Missing B → MISSING_PRIMITIVES")
check(surface3.missing_primitive_count == 1, "1 missing")
check(surface3.matched_primitive_count == 1, "1 matched")

# ── 6. Extra primitives ──
section("6. Extra Primitives")
obs_extra = SubstrateOutput(
    label="observed",
    primitives=prims + (PrimitiveRecord(name="C", kind="REGION", confidence=0.5),),
    contracts=contracts, signatures=sigs,
)
surface4 = analyze_deltas(expected, obs_extra)
check(surface4.verdict == DeltaVerdict.EXTRA_PRIMITIVES, "Extra C → EXTRA_PRIMITIVES")
check(surface4.extra_primitive_count == 1, "1 extra")

# ── 7. Mixed — missing + extra ──
section("7. Mixed Deltas")
obs_mixed = SubstrateOutput(
    label="observed",
    primitives=(
        PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),
        PrimitiveRecord(name="C", kind="REGION", confidence=0.5),
    ),
    contracts=contracts, signatures=sigs,
)
surface5 = analyze_deltas(expected, obs_mixed)
check(surface5.verdict == DeltaVerdict.MIXED, "Missing B + extra C → MIXED")
check(surface5.missing_primitive_count == 1, "1 missing")
check(surface5.extra_primitive_count == 1, "1 extra")

# ── 8. Contract change ──
section("8. Contract Change")
obs_contracts = (ContractOutcome(contract_name="set_contract", passed=False),)
observed6 = SubstrateOutput(label="observed", primitives=prims, contracts=obs_contracts, signatures=sigs)
surface6 = analyze_deltas(expected, observed6)
check(surface6.changed_contract_count == 1, "1 contract changed")
check(surface6.verdict == DeltaVerdict.MIXED, "Contract change → MIXED")

# ── 9. Signature change ──
section("9. Signature Change")
obs_sigs = (SignatureOutcome(signature_name="sig_1", matched=False, similarity=0.3),)
observed7 = SubstrateOutput(label="observed", primitives=prims, contracts=contracts, signatures=obs_sigs)
surface7 = analyze_deltas(expected, observed7)
check(surface7.changed_signature_count == 1, "1 signature changed")

# ── 10. Large confidence delta ──
section("10. Large Confidence Delta")
obs_degraded = (
    PrimitiveRecord(name="A", kind="POINT", confidence=0.5, x=10.0, y=20.0),
    PrimitiveRecord(name="B", kind="LINE", confidence=0.3, x=30.0, y=40.0),
)
observed8 = SubstrateOutput(label="observed", primitives=obs_degraded, contracts=contracts, signatures=sigs)
surface8 = analyze_deltas(expected, observed8)
check(surface8.max_confidence_delta > 0.3, "Large confidence delta detected")
check(surface8.verdict == DeltaVerdict.MIXED, "Large delta → MIXED")

# ── 11. Analysis hash determinism ──
section("11. Analysis Hash Determinism")
s_a = analyze_deltas(expected, observed)
s_b = analyze_deltas(expected, observed)
check(s_a.analysis_hash == s_b.analysis_hash, "Analysis hash deterministic")
check(len(s_a.analysis_hash) == 64, "Hash is SHA-256 length")

# ── 12. Serialization ──
section("12. Serialization")
d = surface.to_dict()
check("verdict" in d, "to_dict has verdict")
check(d["missing_primitive_count"] == 0, "to_dict missing_primitive_count")
j = surface.to_json()
check('"verdict": "IDENTICAL"' in j, "to_json has IDENTICAL")

# ── 13. SubstrateOutput helpers ──
section("13. SubstrateOutput Helpers")
check(expected.primitive_names() == {"A", "B"}, "primitive_names correct")
check(expected.primitive_by_name("A").confidence == 0.9, "primitive_by_name A")
check(expected.primitive_by_name("Z") is None, "primitive_by_name Z → None")
check(expected.contract_by_name("set_contract").passed is True, "contract_by_name")
check(expected.signature_by_name("sig_1").matched is True, "signature_by_name")

# ── 14. make_error_surface ──
section("14. make_error_surface")
err = make_error_surface("test")
check(err.verdict == DeltaVerdict.ERROR, "Error surface verdict")

# ── 15. Default tolerances ──
section("15. Default Tolerances")
check(DEFAULT_CONFIDENCE_TOLERANCE == 0.05, "Default confidence tolerance 0.05")
check(DEFAULT_POSITION_TOLERANCE == 5.0, "Default position tolerance 5.0")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  EVIDENCE DELTA ANALYSIS BRIDGE V1 — STANDALONE RESULTS")
print(f"  PASSED: {PASS_COUNT}  FAILED: {FAIL_COUNT}")
print(f"  TOTAL ASSERTIONS: {PASS_COUNT + FAIL_COUNT}")
if FAIL_COUNT == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print(f"{'='*60}")
sys.exit(0 if FAIL_COUNT == 0 else 1)
