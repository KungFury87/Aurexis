#!/usr/bin/env python3
"""
Aurexis Core — VSA Consistency / Contract Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import (
    V1_CLEANUP_PROFILE, FROZEN_SYMBOL_IDS, FROZEN_TARGETS,
)
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    V1_CODEBOOK, generate_atomic, add_noise,
)
from aurexis_lang.cleanup_retrieval_bridge_v1 import CleanupVerdict
from aurexis_lang.vsa_consistency_contract_bridge_v1 import (
    CONSISTENCY_VERSION, CONSISTENCY_FROZEN,
    ConsistencyVerdict, ConsistencyResult,
    check_consistency, check_all_consistency,
    make_mismatch_query, make_random_noise_query,
    EXPECTED_CONSISTENT_COUNT, VIOLATION_CASE_COUNT,
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

section("1. Module Version and Frozen State")
check(CONSISTENCY_VERSION == "V1.0", "Version V1.0")
check(CONSISTENCY_FROZEN is True, "Module frozen")
check(EXPECTED_CONSISTENT_COUNT == 11, "Expected 11 consistent")
check(VIOLATION_CASE_COUNT == 3, "3 violation cases")

section("2. Clean Consistency (0% noise) — All Targets")
results = check_all_consistency(noise_fraction=0.0)
check(len(results) == EXPECTED_CONSISTENT_COUNT, f"Batch returns {EXPECTED_CONSISTENT_COUNT} results")
for r in results:
    check(r.consistency_verdict == ConsistencyVerdict.CONSISTENT,
          f"{r.substrate_name}: CONSISTENT (sim={r.vsa_similarity:.4f})")

section("3. Noisy Consistency (10% noise)")
results_10 = check_all_consistency(noise_fraction=0.1, seed=42)
consistent_10 = sum(1 for r in results_10 if r.consistency_verdict == ConsistencyVerdict.CONSISTENT)
check(consistent_10 == EXPECTED_CONSISTENT_COUNT, f"All {EXPECTED_CONSISTENT_COUNT} consistent at 10% noise")

section("4. Noisy Consistency (20% noise)")
results_20 = check_all_consistency(noise_fraction=0.2, seed=43)
consistent_20 = sum(1 for r in results_20 if r.consistency_verdict == ConsistencyVerdict.CONSISTENT)
check(consistent_20 >= 10, f">=10 consistent at 20% noise ({consistent_20}/11)")

section("5. Individual Target Consistency")
for target in FROZEN_TARGETS:
    vec = V1_CODEBOOK.get_vector(target.symbol_id)
    r = check_consistency(target.substrate_name, vec)
    check(r.consistency_verdict == ConsistencyVerdict.CONSISTENT,
          f"{target.substrate_name} → {target.symbol_id}: CONSISTENT")
    check(r.expected_symbol_id == target.symbol_id, f"Expected symbol matches")
    check(r.vsa_recovered_symbol_id == target.symbol_id, f"Recovered symbol matches")

section("6. Violation: Mismatch")
# Use SET_TWO_H_AC's substrate name but provide SEQ_TWO_HV's vector
target = FROZEN_TARGETS[0]
wrong_target = FROZEN_TARGETS[5]  # a sequence target
wrong_vec = make_mismatch_query(target.symbol_id, wrong_target.symbol_id)
r = check_consistency(target.substrate_name, wrong_vec)
check(r.consistency_verdict == ConsistencyVerdict.MISMATCH, "Mismatch detected")
check(r.expected_symbol_id == target.symbol_id, "Expected symbol correct")
check(r.vsa_recovered_symbol_id == wrong_target.symbol_id, "Wrong symbol recovered")

section("7. Violation: VSA Failed (random noise)")
random_vec = make_random_noise_query()
r = check_consistency(FROZEN_TARGETS[0].substrate_name, random_vec)
check(r.consistency_verdict in (ConsistencyVerdict.VSA_FAILED, ConsistencyVerdict.MISMATCH),
      f"Random noise: {r.consistency_verdict.value}")

section("8. Violation: Unknown Target")
vec = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
r = check_consistency("nonexistent_substrate_name", vec)
check(r.consistency_verdict == ConsistencyVerdict.UNKNOWN_TARGET, "Unknown target detected")

section("9. ConsistencyResult Serialization")
vec = V1_CODEBOOK.get_vector(FROZEN_TARGETS[0].symbol_id)
r = check_consistency(FROZEN_TARGETS[0].substrate_name, vec)
d = r.to_dict()
check(d["consistency_verdict"] == "CONSISTENT", "to_dict verdict")
check(d["substrate_name"] == FROZEN_TARGETS[0].substrate_name, "to_dict substrate_name")
check(d["expected_symbol_id"] == FROZEN_TARGETS[0].symbol_id, "to_dict expected_symbol")
check(d["version"] == CONSISTENCY_VERSION, "to_dict version")

section("10. Immutability")
try:
    r.consistency_verdict = ConsistencyVerdict.ERROR
    check(False, "ConsistencyResult should be immutable")
except (AttributeError, TypeError):
    check(True, "ConsistencyResult is immutable")

section("11. Cross-Kind Consistency")
# Check each kind separately
from aurexis_lang.vsa_cleanup_profile_bridge_v1 import CleanupTargetKind
for kind in CleanupTargetKind:
    targets_k = V1_CLEANUP_PROFILE.get_targets_by_kind(kind)
    for t in targets_k:
        vec = V1_CODEBOOK.get_vector(t.symbol_id)
        r = check_consistency(t.substrate_name, vec)
        check(r.consistency_verdict == ConsistencyVerdict.CONSISTENT,
              f"{kind.value}/{t.substrate_name}: CONSISTENT")

section("12. Mismatch Within Same Kind")
# Swap two set contract vectors
t0 = FROZEN_TARGETS[0]
t1 = FROZEN_TARGETS[1]
swapped_vec = V1_CODEBOOK.get_vector(t1.symbol_id)
r = check_consistency(t0.substrate_name, swapped_vec)
check(r.consistency_verdict == ConsistencyVerdict.MISMATCH, "Same-kind mismatch detected")

print(f"\n{'='*60}")
print(f"  RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed, {PASS_COUNT + FAIL_COUNT} total")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    print("  *** FAILURES DETECTED ***"); sys.exit(1)
else:
    print("  ALL PASS"); sys.exit(0)
