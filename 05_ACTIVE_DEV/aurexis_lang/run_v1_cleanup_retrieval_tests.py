#!/usr/bin/env python3
"""
Aurexis Core — Cleanup Retrieval Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import FROZEN_SYMBOL_IDS
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    V1_CODEBOOK, generate_atomic, add_noise, cosine_similarity, bundle,
)
from aurexis_lang.cleanup_retrieval_bridge_v1 import (
    RETRIEVAL_VERSION, RETRIEVAL_FROZEN,
    CleanupVerdict, CleanupResult, NoiseToleranceResult,
    cleanup_single, cleanup_top_k,
    verify_noise_tolerance, verify_all_noise_tolerance,
    make_random_query,
    HIGH_CONFIDENCE_THRESHOLD, MEDIUM_CONFIDENCE_THRESHOLD,
    SUPPORTED_NOISE_LEVELS,
    EXPECTED_CLEAN_MATCH_AT_0_NOISE, EXPECTED_CLEAN_MATCH_AT_10_NOISE,
    EXPECTED_CLEAN_MATCH_AT_20_NOISE,
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
check(RETRIEVAL_VERSION == "V1.0", "Version V1.0")
check(RETRIEVAL_FROZEN is True, "Module frozen")

section("2. Clean Retrieval (0% noise) — All Symbols")
for sid in FROZEN_SYMBOL_IDS:
    vec = V1_CODEBOOK.get_vector(sid)
    result = cleanup_single(vec)
    check(result.verdict == CleanupVerdict.CLEAN_MATCH, f"{sid}: CLEAN_MATCH")
    check(result.matched_symbol_id == sid, f"{sid}: correct symbol recovered")
    check(result.similarity == 1.0, f"{sid}: similarity = 1.0")

section("3. Noisy Retrieval (10% noise)")
for sid in FROZEN_SYMBOL_IDS:
    vec = V1_CODEBOOK.get_vector(sid)
    noisy = add_noise(vec, 0.1, seed=42)
    result = cleanup_single(noisy)
    check(result.matched_symbol_id == sid, f"{sid} @ 10%: correct recovery")
    check(result.verdict == CleanupVerdict.CLEAN_MATCH, f"{sid} @ 10%: CLEAN_MATCH")

section("4. Noisy Retrieval (20% noise)")
for sid in FROZEN_SYMBOL_IDS:
    vec = V1_CODEBOOK.get_vector(sid)
    noisy = add_noise(vec, 0.2, seed=43)
    result = cleanup_single(noisy)
    check(result.matched_symbol_id == sid, f"{sid} @ 20%: correct recovery")

section("5. Noisy Retrieval (30% noise)")
recovered_30 = 0
for sid in FROZEN_SYMBOL_IDS:
    vec = V1_CODEBOOK.get_vector(sid)
    noisy = add_noise(vec, 0.3, seed=44)
    result = cleanup_single(noisy)
    if result.matched_symbol_id == sid:
        recovered_30 += 1
    check(result.matched_symbol_id == sid, f"{sid} @ 30%: correct recovery (sim={result.similarity:.4f})")
check(recovered_30 >= 8, f"At least 8/11 recovered at 30% noise ({recovered_30}/11)")

section("6. Random Noise Query (should not match)")
rq = make_random_query()
result = cleanup_single(rq)
check(result.verdict in (CleanupVerdict.NO_MATCH, CleanupVerdict.WEAK_MATCH),
      f"Random query: {result.verdict.value} (sim={result.similarity:.4f})")

section("7. Top-K Retrieval")
vec = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
top3 = cleanup_top_k(vec, k=3)
check(len(top3) == 3, "Top-3 returns 3 entries")
check(top3[0][0] == FROZEN_SYMBOL_IDS[0], f"Top-1 is {FROZEN_SYMBOL_IDS[0]}")
check(top3[0][1] == 1.0, "Top-1 similarity = 1.0")

section("8. Verify Noise Tolerance — Individual")
r = verify_noise_tolerance(FROZEN_SYMBOL_IDS[0], 0.0)
check(r.recovered_correctly is True, "0% noise: correct")
check(r.cleanup_verdict == CleanupVerdict.CLEAN_MATCH, "0% noise: CLEAN_MATCH")
r2 = verify_noise_tolerance(FROZEN_SYMBOL_IDS[0], 0.2, seed=43)
check(r2.recovered_correctly is True, "20% noise: correct")

section("9. Verify All Noise Tolerance — Batch")
all_results = verify_all_noise_tolerance()
total = len(all_results)
correct = sum(1 for r in all_results if r.recovered_correctly)
check(total == len(FROZEN_SYMBOL_IDS) * len(SUPPORTED_NOISE_LEVELS),
      f"Batch has {total} results (expected {len(FROZEN_SYMBOL_IDS) * len(SUPPORTED_NOISE_LEVELS)})")
# At 0% noise, all should recover
at_0 = [r for r in all_results if r.noise_fraction == 0.0]
check(all(r.recovered_correctly for r in at_0), f"All {len(at_0)} recover at 0% noise")
# At 10%, all should recover
at_10 = [r for r in all_results if r.noise_fraction == 0.1]
check(all(r.recovered_correctly for r in at_10), f"All {len(at_10)} recover at 10% noise")
# At 20%, all should recover
at_20 = [r for r in all_results if r.noise_fraction == 0.2]
check(sum(1 for r in at_20 if r.recovered_correctly) >= 10, f">=10/11 recover at 20% noise")
print(f"  Total correct across all noise levels: {correct}/{total}")

section("10. CleanupResult Serialization")
vec = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
result = cleanup_single(vec)
d = result.to_dict()
check(d["verdict"] == "CLEAN_MATCH", "to_dict verdict")
check(d["matched_symbol_id"] == FROZEN_SYMBOL_IDS[0], "to_dict symbol")
check(d["version"] == RETRIEVAL_VERSION, "to_dict version")

section("11. NoiseToleranceResult Serialization")
r = verify_noise_tolerance(FROZEN_SYMBOL_IDS[0], 0.1)
rd = r.to_dict()
check(rd["symbol_id"] == FROZEN_SYMBOL_IDS[0], "Noise to_dict symbol")
check(rd["noise_fraction"] == 0.1, "Noise to_dict fraction")
check(rd["recovered_correctly"] is True, "Noise to_dict recovered")

section("12. Immutability")
try:
    result.verdict = CleanupVerdict.ERROR
    check(False, "CleanupResult should be immutable")
except (AttributeError, TypeError):
    check(True, "CleanupResult is immutable")

section("13. Bundle Cleanup")
# Bundle 2 symbols and see if we can recover one via unbind
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import bind, unbind
v_a = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[0])
v_b = V1_CODEBOOK.get_vector(FROZEN_SYMBOL_IDS[1])
bound = bind(v_a, v_b)
recovered = unbind(bound, v_b)
cr = cleanup_single(recovered)
check(cr.matched_symbol_id == FROZEN_SYMBOL_IDS[0], f"Unbind+cleanup recovers {FROZEN_SYMBOL_IDS[0]}")
check(cr.verdict == CleanupVerdict.CLEAN_MATCH, "Unbind+cleanup is CLEAN_MATCH")

print(f"\n{'='*60}")
print(f"  RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed, {PASS_COUNT + FAIL_COUNT} total")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    print("  *** FAILURES DETECTED ***"); sys.exit(1)
else:
    print("  ALL PASS"); sys.exit(0)
