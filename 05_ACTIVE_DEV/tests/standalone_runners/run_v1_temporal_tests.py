"""
Standalone test runner for Temporal Law V1.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, ExecutionStatus, BoundingBox, VisualPrimitive,
)
from aurexis_lang.visual_executor_v1 import execute_frame
from aurexis_lang.visual_parse_rules_v1 import parse_frame_to_program
from aurexis_lang.visual_program_executor_v1 import (
    execute_program, execute_image_as_program, ProgramVerdict,
)
from aurexis_lang.temporal_law_v1 import (
    TemporalLaw, V1_TEMPORAL, TEMPORAL_VERSION, TEMPORAL_FROZEN,
    TemporalVerdict, track_bindings, analyze_assertion_drift,
    prove_temporal_consistency,
)

passed = 0
failed = 0
errors = []


def check(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        errors.append(f"{name}: {msg}")
        print(f"  FAIL  {name} — {msg}")


def _make_result(bbox_a, bbox_b, op=OperationKind.ADJACENT, conf=1.0, bindings=None):
    """Helper to create an ExecutionResult quickly."""
    raw = [
        {"type": "region", "bbox": list(bbox_a), "confidence": conf},
        {"type": "region", "bbox": list(bbox_b), "confidence": conf},
    ]
    return execute_image_as_program(
        raw, bindings=bindings,
        operations=[{"op": op, "a_index": 0, "b_index": 1}],
    )


# ═══════ SPEC ═══════
print("\n=== Temporal Law Spec ===")
check("version", TEMPORAL_VERSION == "V1.0")
check("frozen", TEMPORAL_FROZEN is True)
check("persistence_radius", V1_TEMPORAL.binding_persistence_radius_px == 40.0)
check("confirmation_window", V1_TEMPORAL.confirmation_window == 3)
check("drift_max", V1_TEMPORAL.assertion_drift_max_px == 15.0)
check("min_frames", V1_TEMPORAL.min_frames == 2)

try:
    V1_TEMPORAL.binding_persistence_radius_px = 100.0
    check("immutable", False, "should have raised")
except AttributeError:
    check("immutable", True)

# ═══════ INSUFFICIENT FRAMES ═══════
print("\n=== Insufficient Frames ===")
proof_0 = prove_temporal_consistency([])
check("insuff_0", proof_0.verdict == TemporalVerdict.INSUFFICIENT)
proof_1 = prove_temporal_consistency([_make_result([0,0,100,100], [100,0,100,100])])
check("insuff_1", proof_1.verdict == TemporalVerdict.INSUFFICIENT)

# ═══════ CONSISTENT — 2 identical frames ═══════
print("\n=== Consistent — 2 Frames ===")
r1 = _make_result([0,0,100,100], [100,0,100,100])
r2 = _make_result([0,0,100,100], [100,0,100,100])
proof_2 = prove_temporal_consistency([r1, r2])
check("consist_2_verdict", proof_2.verdict == TemporalVerdict.CONSISTENT)
check("consist_2_consecutive", proof_2.consecutive_same == 2)
check("consist_2_verdicts", proof_2.verdicts == ["PASS", "PASS"])

# ═══════ CONFIRMED — 3+ identical frames ═══════
print("\n=== Confirmed — 3 Frames ===")
results_3 = [_make_result([0,0,100,100], [100,0,100,100]) for _ in range(3)]
proof_3 = prove_temporal_consistency(results_3)
check("confirm_verdict", proof_3.verdict == TemporalVerdict.CONFIRMED)
check("confirm_consecutive", proof_3.consecutive_same == 3)

# 5 frames
results_5 = [_make_result([0,0,100,100], [100,0,100,100]) for _ in range(5)]
proof_5 = prove_temporal_consistency(results_5)
check("confirm_5_verdict", proof_5.verdict == TemporalVerdict.CONFIRMED)
check("confirm_5_consecutive", proof_5.consecutive_same == 5)

# ═══════ FLIPPED — verdict changes ═══════
print("\n=== Flipped — Verdict Changes ===")
r_pass = _make_result([0,0,100,100], [100,0,100,100])  # ADJACENT TRUE → PASS
r_fail = _make_result([0,0,100,100], [200,0,100,100])  # ADJACENT FALSE → FAIL
proof_flip = prove_temporal_consistency([r_pass, r_fail])
check("flip_verdict", proof_flip.verdict == TemporalVerdict.FLIPPED)
check("flip_verdicts", proof_flip.verdicts == ["PASS", "FAIL"])

# Flip in the middle
proof_flip3 = prove_temporal_consistency([r_pass, r_fail, r_pass])
check("flip3_verdict", proof_flip3.verdict == TemporalVerdict.FLIPPED)

# ═══════ BINDING TRACKING ═══════
print("\n=== Binding Tracking ===")
r_bind1 = _make_result([0,0,100,100], [100,0,100,100], bindings={"left": 0, "right": 1})
r_bind2 = _make_result([5,5,100,100], [105,5,100,100], bindings={"left": 0, "right": 1})
proof_bind = prove_temporal_consistency([r_bind1, r_bind2])
check("bind_tracked", "left" in proof_bind.binding_tracking)
check("bind_right_tracked", "right" in proof_bind.binding_tracking)
check("bind_frames_seen", proof_bind.binding_tracking["left"]["frames_seen"] == 2)
check("bind_no_lost", len(proof_bind.lost_bindings) == 0)

# Lost binding
r_bind3 = _make_result([0,0,100,100], [100,0,100,100], bindings={"left": 0})  # "right" missing
proof_lost = prove_temporal_consistency([r_bind1, r_bind3])
check("lost_detected", "right" in proof_lost.lost_bindings)

# ═══════ ASSERTION DRIFT — stable ═══════
print("\n=== Assertion Drift — Stable ===")
# Same measured values → no drift
stable_results = [_make_result([0,0,100,100], [100,0,100,100]) for _ in range(3)]
proof_stable = prove_temporal_consistency(stable_results)
check("drift_stable_no_drifting", len(proof_stable.drifting_assertions) == 0)

# ═══════ ASSERTION DRIFT — drifting ═══════
print("\n=== Assertion Drift — Drifting ===")
# First frame: 10px gap → measured=10
# Second frame: 30px gap → measured=30 (drift = 20 > 15 threshold)
r_near = _make_result([0,0,100,100], [110,0,100,100])    # measured=10
r_far = _make_result([0,0,100,100], [130,0,100,100])      # measured=30
proof_drift = prove_temporal_consistency([r_near, r_far])
check("drift_detected", len(proof_drift.drifting_assertions) > 0 or
      proof_drift.verdict == TemporalVerdict.DRIFTING,
      f"verdict={proof_drift.verdict.value}, drifting={proof_drift.drifting_assertions}")

# ═══════ FAIL CONFIRMED ═══════
print("\n=== Fail Confirmed ===")
fail_results = [_make_result([0,0,100,100], [200,0,100,100]) for _ in range(3)]
proof_fail_conf = prove_temporal_consistency(fail_results)
check("fail_confirmed", proof_fail_conf.verdict == TemporalVerdict.CONFIRMED)
check("fail_verdicts", all(v == "FAIL" for v in proof_fail_conf.verdicts))

# ═══════ SERIALIZATION ═══════
print("\n=== Serialization ===")
d = proof_3.to_dict()
check("ser_verdict", d["verdict"] == "CONFIRMED")
check("ser_frame_count", d["frame_count"] == 3)
check("ser_consecutive", d["consecutive_same"] == 3)
check("ser_version", d["temporal_version"] == TEMPORAL_VERSION)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
det_results = [_make_result([0,0,100,100], [100,0,100,100], bindings={"a": 0}) for _ in range(3)]
proofs = [prove_temporal_consistency(det_results).to_dict() for _ in range(5)]
check("det_all_same", all(p == proofs[0] for p in proofs))

# ═══════ SUMMARY ═══════
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
if errors:
    print("\nFAILURES:")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("\nALL TESTS PASSED ✓")
    sys.exit(0)
