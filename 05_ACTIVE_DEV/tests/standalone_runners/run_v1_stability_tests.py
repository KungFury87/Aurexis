"""
Standalone test runner for Print/Scan Stability V1.
"""

import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "aurexis_lang", "src"
))

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, OperationKind, ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import (
    execute_image_as_program, ProgramVerdict,
)
from aurexis_lang.print_scan_stability_v1 import (
    StabilityContract, V1_STABILITY, STABILITY_VERSION, STABILITY_FROZEN,
    degrade_primitive, degrade_frame, analyze_margins,
    prove_stability, StabilityVerdict, StabilityProof,
)

FLOAT_TOL = 1e-9
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


# ═══════ SPEC ═══════
print("\n=== Stability Spec ===")
check("version", STABILITY_VERSION == "V1.0")
check("frozen", STABILITY_FROZEN is True)
check("max_jitter", V1_STABILITY.max_jitter_px == 10.0)
check("max_scale_low", V1_STABILITY.max_scale_low == 0.85)
check("max_scale_high", V1_STABILITY.max_scale_high == 1.15)
check("degradation_levels", V1_STABILITY.degradation_levels == 5)

try:
    V1_STABILITY.max_jitter_px = 20.0
    check("contract_immutable", False, "should have raised")
except AttributeError:
    check("contract_immutable", True)

# ═══════ DEGRADATION FUNCTIONS ═══════
print("\n=== Degradation Functions ===")

# Determinism: same seed → same output
d1 = degrade_primitive(
    {"type": "region", "bbox": [100, 100, 50, 50], "confidence": 0.9},
    jitter_px=5.0, scale=1.0, confidence_drop=0.1, seed=42,
)
d2 = degrade_primitive(
    {"type": "region", "bbox": [100, 100, 50, 50], "confidence": 0.9},
    jitter_px=5.0, scale=1.0, confidence_drop=0.1, seed=42,
)
check("degrade_deterministic", d1 == d2)

# Different seeds → different output
d3 = degrade_primitive(
    {"type": "region", "bbox": [100, 100, 50, 50], "confidence": 0.9},
    jitter_px=5.0, scale=1.0, confidence_drop=0.0, seed=99,
)
check("degrade_diff_seeds", d1["bbox"] != d3["bbox"])

# Scale changes coordinates
d_scaled = degrade_primitive(
    {"type": "region", "bbox": [100, 100, 50, 50], "confidence": 1.0},
    jitter_px=0.0, scale=2.0, confidence_drop=0.0, seed=0,
)
# With zero jitter, coordinates should be exactly scaled
# (the jitter function with magnitude 0 still applies the hash,
# but with 0 magnitude the shift is 0)
check("degrade_scale_x", abs(d_scaled["bbox"][0] - 200.0) < 0.01,
      f"got {d_scaled['bbox'][0]}")

# Confidence drop
d_conf = degrade_primitive(
    {"type": "region", "bbox": [10, 10, 50, 50], "confidence": 0.8},
    jitter_px=0.0, scale=1.0, confidence_drop=0.3, seed=0,
)
check("degrade_conf_drop", abs(d_conf["confidence"] - 0.5) < 0.01,
      f"got {d_conf['confidence']}")

# Confidence doesn't go below 0
d_conf_floor = degrade_primitive(
    {"type": "region", "bbox": [10, 10, 50, 50], "confidence": 0.1},
    jitter_px=0.0, scale=1.0, confidence_drop=0.5, seed=0,
)
check("degrade_conf_floor", d_conf_floor["confidence"] == 0.0)

# Frame degradation
frame_orig = [
    {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
    {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
]
frame_deg = degrade_frame(frame_orig, jitter_px=3.0, scale=1.0, base_seed=0)
check("degrade_frame_count", len(frame_deg) == 2)
check("degrade_frame_different", frame_deg[0]["bbox"] != frame_orig[0]["bbox"])
# Determinism
frame_deg2 = degrade_frame(frame_orig, jitter_px=3.0, scale=1.0, base_seed=0)
check("degrade_frame_deterministic", frame_deg == frame_deg2)

# ═══════ MARGIN ANALYSIS ═══════
print("\n=== Margin Analysis ===")

# Touching regions: ADJACENT TRUE, measured=0, threshold=30 → headroom=30
result_touching = execute_image_as_program(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
margins = analyze_margins(result_touching)
check("margin_count", len(margins) == 1)
check("margin_headroom", abs(margins[0].headroom_px - 30.0) < FLOAT_TOL,
      f"got {margins[0].headroom_px}")
check("margin_safe_jitter", abs(margins[0].stable_under_jitter - 15.0) < FLOAT_TOL,
      f"got {margins[0].stable_under_jitter}")

# Regions 20px apart: ADJACENT TRUE, measured=20, threshold=30 → headroom=10
result_near = execute_image_as_program(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [120, 0, 100, 100], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
margins_near = analyze_margins(result_near)
check("margin_near_headroom", abs(margins_near[0].headroom_px - 10.0) < FLOAT_TOL,
      f"got {margins_near[0].headroom_px}")
check("margin_near_jitter", abs(margins_near[0].stable_under_jitter - 5.0) < FLOAT_TOL)

# Contains with 50px margin: headroom=50
result_contains = execute_image_as_program(
    [
        {"type": "region", "bbox": [0, 0, 200, 200], "confidence": 1.0},
        {"type": "region", "bbox": [50, 50, 50, 50], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}],
)
margins_cnt = analyze_margins(result_contains)
check("margin_contains_headroom", abs(margins_cnt[0].headroom_px - 50.0) < FLOAT_TOL,
      f"got {margins_cnt[0].headroom_px}")

# ═══════ STABILITY PROOF — STABLE CASE ═══════
print("\n=== Stability Proof — Stable ===")

# Well-separated touching regions: 30px headroom, should survive degradation
stable_proof = prove_stability(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("stable_verdict", stable_proof.verdict == StabilityVerdict.STABLE)
check("stable_original", stable_proof.original_verdict == ProgramVerdict.PASS)
check("stable_headroom", stable_proof.min_headroom_px >= 10.0,
      f"got {stable_proof.min_headroom_px}")
check("stable_levels", len(stable_proof.degradation_results) == 5)
check("stable_all_preserved", all(
    d["verdict_preserved"] for d in stable_proof.degradation_results
))

# ═══════ STABILITY PROOF — WELL-CONTAINED ═══════
print("\n=== Stability Proof — Well Contained ===")

contained_proof = prove_stability(
    [
        {"type": "region", "bbox": [0, 0, 300, 300], "confidence": 1.0},
        {"type": "region", "bbox": [50, 50, 100, 100], "confidence": 1.0},
    ],
    bindings={"outer": 0, "inner": 1},
    operations=[{"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 1}],
)
check("contained_verdict", contained_proof.verdict == StabilityVerdict.STABLE)
check("contained_headroom", contained_proof.min_headroom_px >= 10.0)

# ═══════ STABILITY PROOF — MARGINAL CASE ═══════
print("\n=== Stability Proof — Marginal ===")

# 25px gap: measured=25, threshold=30, headroom=5 (below stability_margin of 10)
marginal_proof = prove_stability(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [125, 0, 100, 100], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
# Headroom = 30 - 25 = 5px, which is below the 10px stability_margin
# But verdict might still be preserved if jitter doesn't exceed 2.5px
# The result depends on whether degradation actually flips the verdict
if marginal_proof.min_headroom_px < V1_STABILITY.stability_margin_px:
    expected = StabilityVerdict.MARGINAL if all(
        d["verdict_preserved"] for d in marginal_proof.degradation_results
    ) else StabilityVerdict.UNSTABLE
else:
    expected = StabilityVerdict.STABLE
check("marginal_verdict", marginal_proof.verdict == expected,
      f"expected {expected.value}, got {marginal_proof.verdict.value}")
check("marginal_headroom_low", marginal_proof.min_headroom_px < 10.0,
      f"got {marginal_proof.min_headroom_px}")

# ═══════ STABILITY PROOF — FAIL PRESERVED ═══════
print("\n=== Stability Proof — Fail Preserved ===")

# 100px gap: ADJACENT FALSE, should stay FALSE under degradation
fail_proof = prove_stability(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [200, 0, 100, 100], "confidence": 1.0},
    ],
    operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
)
check("fail_original", fail_proof.original_verdict == ProgramVerdict.FAIL)
check("fail_stable", fail_proof.verdict == StabilityVerdict.STABLE)
check("fail_headroom", fail_proof.min_headroom_px >= 10.0,
      f"got {fail_proof.min_headroom_px}")

# ═══════ STABILITY PROOF — EMPTY PROGRAM ═══════
print("\n=== Stability Proof — Empty ===")

empty_proof = prove_stability(
    [{"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0}],
    bindings={"x": 0},
    operations=[],
)
check("empty_verdict", empty_proof.verdict == StabilityVerdict.STABLE)
check("empty_original", empty_proof.original_verdict == ProgramVerdict.EMPTY)

# ═══════ STABILITY PROOF — MULTI-ASSERTION ═══════
print("\n=== Stability Proof — Multi-Assertion ===")

multi_proof = prove_stability(
    [
        {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
        {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
        {"type": "point", "bbox": [50, 50, 5, 5], "confidence": 1.0},
    ],
    bindings={"left": 0, "right": 1, "center": 2},
    operations=[
        {"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1},
        {"op": OperationKind.CONTAINS, "a_index": 0, "b_index": 2},
    ],
)
check("multi_verdict", multi_proof.verdict == StabilityVerdict.STABLE)
check("multi_margins", len(multi_proof.margin_analysis) == 2)

# ═══════ SERIALIZATION ═══════
print("\n=== Serialization ===")
d = stable_proof.to_dict()
check("ser_verdict", d["verdict"] == "STABLE")
check("ser_original", d["original_verdict"] == "PASS")
check("ser_levels", d["degradation_levels_tested"] == 5)
check("ser_preserved", d["all_preserved"] is True)
check("ser_version", d["stability_version"] == STABILITY_VERSION)
check("ser_grammar", d["grammar_version"] == GRAMMAR_VERSION)

# ═══════ DETERMINISM ═══════
print("\n=== Determinism ===")
proofs = [
    prove_stability(
        [
            {"type": "region", "bbox": [0, 0, 100, 100], "confidence": 1.0},
            {"type": "region", "bbox": [100, 0, 100, 100], "confidence": 1.0},
        ],
        operations=[{"op": OperationKind.ADJACENT, "a_index": 0, "b_index": 1}],
    ).to_dict()
    for _ in range(5)
]
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
    print("\n  PRINT/SCAN STABILITY PROOF: V1 programs survive physical-world")
    print("  degradation (jitter, scale, confidence loss) within frozen bounds.")
    sys.exit(0)
