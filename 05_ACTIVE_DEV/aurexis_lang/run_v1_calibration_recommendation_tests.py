#!/usr/bin/env python3
"""
Aurexis Core — Calibration Recommendation Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.evidence_delta_analysis_bridge_v1 import (
    DeltaVerdict, PrimitiveRecord, ContractOutcome, SignatureOutcome,
    SubstrateOutput, DeltaSurface, analyze_deltas, PrimitiveDelta,
)
from aurexis_lang.calibration_recommendation_bridge_v1 import (
    RECOMMENDATION_VERSION, RECOMMENDATION_FROZEN,
    RecommendationKind, RecommendationPriority,
    CalibrationRecommendation, RecommendationVerdict,
    RecommendationSurface, generate_recommendations, make_empty_surface,
    EXPECTED_KIND_COUNT, EXPECTED_PRIORITY_COUNT, EXPECTED_VERDICT_COUNT,
    RECOMMENDATION_RULES_COUNT,
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
check(RECOMMENDATION_VERSION == "V1.0", "Version V1.0")
check(RECOMMENDATION_FROZEN is True, "Module frozen")

# ── 2. Kind enum ──
section("2. Kind Enum")
check(len(RecommendationKind) == EXPECTED_KIND_COUNT, f"Kind count == {EXPECTED_KIND_COUNT}")
check(RecommendationKind.THRESHOLD_ADJUSTMENT.value == "THRESHOLD_ADJUSTMENT", "THRESHOLD_ADJUSTMENT")
check(RecommendationKind.CAPTURE_GUIDANCE.value == "CAPTURE_GUIDANCE", "CAPTURE_GUIDANCE")

# ── 3. Priority enum ──
section("3. Priority Enum")
check(len(RecommendationPriority) == EXPECTED_PRIORITY_COUNT, f"Priority count == {EXPECTED_PRIORITY_COUNT}")
check(RecommendationPriority.CRITICAL.value == "CRITICAL", "CRITICAL priority")

# ── 4. Verdict enum ──
section("4. Verdict Enum")
check(len(RecommendationVerdict) == EXPECTED_VERDICT_COUNT, f"Verdict count == {EXPECTED_VERDICT_COUNT}")

# ── 5. No action needed — identical delta ──
section("5. No Action Needed — Identical Delta")
prims = (
    PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),
    PrimitiveRecord(name="B", kind="LINE", confidence=0.8, x=30.0, y=40.0),
)
contracts = (ContractOutcome(contract_name="set", passed=True),)
sigs = (SignatureOutcome(signature_name="s1", matched=True, similarity=0.95),)
expected = SubstrateOutput(label="expected", primitives=prims, contracts=contracts, signatures=sigs)
observed = SubstrateOutput(label="observed", primitives=prims, contracts=contracts, signatures=sigs)
delta = analyze_deltas(expected, observed)
rec_surface = generate_recommendations(delta)
check(rec_surface.verdict == RecommendationVerdict.NO_ACTION_NEEDED, "Identical → NO_ACTION_NEEDED")
check(rec_surface.total_count == 0, "0 recommendations")

# ── 6. Missing primitives → capture guidance ──
section("6. Missing Primitives → Capture Guidance")
obs_missing = SubstrateOutput(
    label="observed",
    primitives=(PrimitiveRecord(name="A", kind="POINT", confidence=0.9, x=10.0, y=20.0),),
    contracts=contracts, signatures=sigs,
)
delta2 = analyze_deltas(expected, obs_missing)
rec2 = generate_recommendations(delta2)
check(rec2.verdict != RecommendationVerdict.NO_ACTION_NEEDED, "Missing → not NO_ACTION")
kinds = [r.kind for r in rec2.recommendations]
check(RecommendationKind.CAPTURE_GUIDANCE in kinds, "CAPTURE_GUIDANCE issued")
check(all(r.advisory is True for r in rec2.recommendations), "All recommendations advisory")

# ── 7. Extra primitives → extractor profile ──
section("7. Extra Primitives → Extractor Profile")
obs_extra = SubstrateOutput(
    label="observed",
    primitives=prims + (PrimitiveRecord(name="C", kind="REGION", confidence=0.5),),
    contracts=contracts, signatures=sigs,
)
delta3 = analyze_deltas(expected, obs_extra)
rec3 = generate_recommendations(delta3)
kinds3 = [r.kind for r in rec3.recommendations]
check(RecommendationKind.EXTRACTOR_PROFILE in kinds3, "EXTRACTOR_PROFILE issued")

# ── 8. Large confidence delta → threshold adjustment ──
section("8. Large Confidence Delta → Threshold Adjustment")
obs_degraded = (
    PrimitiveRecord(name="A", kind="POINT", confidence=0.5, x=10.0, y=20.0),
    PrimitiveRecord(name="B", kind="LINE", confidence=0.3, x=30.0, y=40.0),
)
obs_deg = SubstrateOutput(label="observed", primitives=obs_degraded, contracts=contracts, signatures=sigs)
delta4 = analyze_deltas(expected, obs_deg)
rec4 = generate_recommendations(delta4)
kinds4 = [r.kind for r in rec4.recommendations]
check(RecommendationKind.THRESHOLD_ADJUSTMENT in kinds4, "THRESHOLD_ADJUSTMENT issued")

# ── 9. Contract failure → contract review ──
section("9. Contract Failure → Contract Review")
obs_contracts = (ContractOutcome(contract_name="set", passed=False),)
obs_cf = SubstrateOutput(label="observed", primitives=prims, contracts=obs_contracts, signatures=sigs)
delta5 = analyze_deltas(expected, obs_cf)
rec5 = generate_recommendations(delta5)
kinds5 = [r.kind for r in rec5.recommendations]
check(RecommendationKind.CONTRACT_REVIEW in kinds5, "CONTRACT_REVIEW issued")

# ── 10. Signature mismatch → signature review ──
section("10. Signature Mismatch → Signature Review")
obs_sigs = (SignatureOutcome(signature_name="s1", matched=False, similarity=0.3),)
obs_sm = SubstrateOutput(label="observed", primitives=prims, contracts=contracts, signatures=obs_sigs)
delta6 = analyze_deltas(expected, obs_sm)
rec6 = generate_recommendations(delta6)
kinds6 = [r.kind for r in rec6.recommendations]
check(RecommendationKind.SIGNATURE_REVIEW in kinds6, "SIGNATURE_REVIEW issued")

# ── 11. Critical advisory — many missing ──
section("11. Critical Advisory — Many Missing")
obs_empty = SubstrateOutput(label="observed", primitives=(), contracts=(), signatures=())
exp_many = SubstrateOutput(
    label="expected",
    primitives=tuple(PrimitiveRecord(name=f"P{i}", kind="POINT", confidence=0.9) for i in range(5)),
    contracts=contracts, signatures=sigs,
)
delta7 = analyze_deltas(exp_many, obs_empty)
rec7 = generate_recommendations(delta7)
check(rec7.verdict == RecommendationVerdict.CRITICAL_ADVISORY, "Many missing → CRITICAL_ADVISORY")
check(rec7.critical_count > 0, "Critical count > 0")

# ── 12. CalibrationRecommendation properties ──
section("12. CalibrationRecommendation Properties")
sample = CalibrationRecommendation(
    kind=RecommendationKind.THRESHOLD_ADJUSTMENT,
    priority=RecommendationPriority.HIGH,
    rationale="test rationale",
    suggested_action="test action",
    metric_name="test_metric",
    metric_value=0.15,
    threshold_current=0.05,
    threshold_suggested=0.18,
)
check(sample.advisory is True, "advisory always True")
d = sample.to_dict()
check(d["kind"] == "THRESHOLD_ADJUSTMENT", "to_dict kind")
check(d["priority"] == "HIGH", "to_dict priority")
check(d["metric_value"] == 0.15, "to_dict metric_value")

# ── 13. Surface serialization ──
section("13. Surface Serialization")
d2 = rec4.to_dict()
check("verdict" in d2, "to_dict has verdict")
check("recommendations" in d2, "to_dict has recommendations")
j = rec4.to_json()
check('"verdict"' in j, "to_json has verdict")

# ── 14. Surface hash determinism ──
section("14. Surface Hash Determinism")
delta_a = analyze_deltas(expected, observed)
rec_a = generate_recommendations(delta_a)
delta_b = analyze_deltas(expected, observed)
rec_b = generate_recommendations(delta_b)
check(rec_a.surface_hash == rec_b.surface_hash, "Surface hash deterministic")
check(len(rec_a.surface_hash) == 64, "Hash is SHA-256 length")

# ── 15. Summary text ──
section("15. Summary Text")
txt = rec4.to_summary_text()
check("Recommendation Surface" in txt, "Summary text has title")
check("THRESHOLD_ADJUSTMENT" in txt, "Summary text mentions kind")

# ── 16. make_empty_surface ──
section("16. make_empty_surface")
es = make_empty_surface()
check(es.verdict == RecommendationVerdict.NO_ACTION_NEEDED, "Empty surface verdict")
check(es.total_count == 0, "Empty surface total_count 0")

# ── 17. Rules count ──
section("17. Rules Count")
check(RECOMMENDATION_RULES_COUNT == 7, "7 recommendation rules")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  CALIBRATION RECOMMENDATION BRIDGE V1 — STANDALONE RESULTS")
print(f"  PASSED: {PASS_COUNT}  FAILED: {FAIL_COUNT}")
print(f"  TOTAL ASSERTIONS: {PASS_COUNT + FAIL_COUNT}")
if FAIL_COUNT == 0:
    print("  ✓ ALL TESTS PASSED")
else:
    print("  ✗ SOME TESTS FAILED")
print(f"{'='*60}")
sys.exit(0 if FAIL_COUNT == 0 else 1)
