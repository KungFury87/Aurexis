#!/usr/bin/env python3
"""
Aurexis Core — Hypervector Binding / Bundling Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.vsa_cleanup_profile_bridge_v1 import FROZEN_SYMBOL_IDS
from aurexis_lang.hypervector_binding_bundling_bridge_v1 import (
    BINDING_VERSION, BINDING_FROZEN, DIMENSION,
    HyperVector, generate_atomic, bind, unbind, bundle, permute, inverse_permute,
    cosine_similarity, add_noise,
    Codebook, V1_CODEBOOK, build_codebook,
    encode_ordered_set, encode_bound_pair,
    EXPECTED_CODEBOOK_SIZE, EXPECTED_DIMENSION,
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
check(BINDING_VERSION == "V1.0", "Version V1.0")
check(BINDING_FROZEN is True, "Module frozen")
check(DIMENSION == 1024, f"Dimension = 1024 (got {DIMENSION})")

section("2. Codebook")
check(V1_CODEBOOK.size == EXPECTED_CODEBOOK_SIZE, f"Codebook has {EXPECTED_CODEBOOK_SIZE} entries")
check(V1_CODEBOOK.dimension == EXPECTED_DIMENSION, "Codebook dimension matches")
check(set(V1_CODEBOOK.all_symbol_ids) == set(FROZEN_SYMBOL_IDS), "Codebook contains all frozen symbols")

section("3. Atomic Vector Generation")
v1 = generate_atomic("SET_TWO_H_AC")
check(len(v1) == DIMENSION, "Atomic vector has correct dimension")
check(all(x in (-1, 1) for x in v1), "All elements are bipolar (+1/-1)")
v1b = generate_atomic("SET_TWO_H_AC")
check(v1 == v1b, "Deterministic: same symbol_id → same vector")
v2 = generate_atomic("SEQ_TWO_HV")
check(v1 != v2, "Different symbols → different vectors")

section("4. Cosine Similarity")
check(cosine_similarity(v1, v1) == 1.0, "Self-similarity = 1.0")
sim_diff = cosine_similarity(v1, v2)
check(abs(sim_diff) < 0.15, f"Different symbols nearly orthogonal (sim={sim_diff:.4f})")

section("5. Bind / Unbind")
bound = bind(v1, v2)
check(len(bound) == DIMENSION, "Bound vector correct dimension")
check(all(x in (-1, 1) for x in bound), "Bound vector is bipolar")
# Self-inverse property
unbound = unbind(bound, v2)
check(cosine_similarity(unbound, v1) == 1.0, "Unbind recovers v1 perfectly")
unbound2 = unbind(bound, v1)
check(cosine_similarity(unbound2, v2) == 1.0, "Unbind recovers v2 perfectly")
# Bound is dissimilar to both
check(abs(cosine_similarity(bound, v1)) < 0.15, "Bound dissimilar to v1")
check(abs(cosine_similarity(bound, v2)) < 0.15, "Bound dissimilar to v2")

section("6. Bundle")
b = bundle(v1, v2)
check(len(b) == DIMENSION, "Bundled vector correct dimension")
check(all(x in (-1, 1) for x in b), "Bundled vector is bipolar")
sim_b_v1 = cosine_similarity(b, v1)
sim_b_v2 = cosine_similarity(b, v2)
check(sim_b_v1 > 0.3, f"Bundle retains similarity to v1 ({sim_b_v1:.4f})")
check(sim_b_v2 > 0.3, f"Bundle retains similarity to v2 ({sim_b_v2:.4f})")

section("7. Bundle of Many")
vecs = [generate_atomic(sid) for sid in list(FROZEN_SYMBOL_IDS)[:5]]
b5 = bundle(*vecs)
for i, vec in enumerate(vecs):
    sim = cosine_similarity(b5, vec)
    check(sim > 0.05, f"Bundle-of-5 retains similarity to component {i} ({sim:.4f})")

section("8. Permute / Inverse Permute")
p1 = permute(v1, 1)
check(p1 != v1, "Permute(1) changes the vector")
check(abs(cosine_similarity(p1, v1)) < 0.15, "Permuted is dissimilar to original")
ip1 = inverse_permute(p1, 1)
check(cosine_similarity(ip1, v1) == 1.0, "Inverse permute recovers original")
# Multi-shift
p5 = permute(v1, 5)
ip5 = inverse_permute(p5, 5)
check(cosine_similarity(ip5, v1) == 1.0, "5-shift inverse permute recovers original")
# Identity shift
p0 = permute(v1, 0)
check(p0 == v1, "Permute(0) is identity")

section("9. Encode Ordered Set")
ordered = encode_ordered_set(FROZEN_SYMBOL_IDS[:3])
check(len(ordered) == DIMENSION, "Ordered set encoding has correct dimension")
check(all(x in (-1, 1) for x in ordered), "Ordered set encoding is bipolar")

section("10. Encode Bound Pair")
bp = encode_bound_pair("SET_TWO_H_AC", "SEQ_TWO_HV")
check(len(bp) == DIMENSION, "Bound pair has correct dimension")
# Unbind to recover
recovered = unbind(bp, generate_atomic("SEQ_TWO_HV"))
check(cosine_similarity(recovered, generate_atomic("SET_TWO_H_AC")) == 1.0, "Bound pair unbind recovers first")

section("11. Add Noise")
noisy_10 = add_noise(v1, 0.1, seed=42)
sim_10 = cosine_similarity(noisy_10, v1)
check(0.7 < sim_10 < 0.95, f"10% noise: similarity {sim_10:.4f}")
noisy_20 = add_noise(v1, 0.2, seed=42)
sim_20 = cosine_similarity(noisy_20, v1)
check(0.5 < sim_20 < 0.85, f"20% noise: similarity {sim_20:.4f}")
noisy_30 = add_noise(v1, 0.3, seed=42)
sim_30 = cosine_similarity(noisy_30, v1)
check(0.3 < sim_30 < 0.65, f"30% noise: similarity {sim_30:.4f}")
# Deterministic
noisy_10b = add_noise(v1, 0.1, seed=42)
check(noisy_10 == noisy_10b, "Noise is deterministic with same seed")

section("12. Codebook Serialization")
d = V1_CODEBOOK.to_dict()
check(d["size"] == EXPECTED_CODEBOOK_SIZE, "Codebook to_dict size")
check(d["dimension"] == DIMENSION, "Codebook to_dict dimension")

section("13. Codebook Lookup")
for sid in FROZEN_SYMBOL_IDS:
    vec = V1_CODEBOOK.get_vector(sid)
    check(vec is not None and len(vec) == DIMENSION, f"Codebook has {sid}")
check(V1_CODEBOOK.get_vector("NONEXISTENT") is None, "Unknown returns None")

section("14. Atomic Collision Resistance")
vecs_set = set()
for sid in FROZEN_SYMBOL_IDS:
    v = generate_atomic(sid)
    vecs_set.add(v)
check(len(vecs_set) == len(FROZEN_SYMBOL_IDS), "All atomic vectors distinct")

print(f"\n{'='*60}")
print(f"  RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed, {PASS_COUNT + FAIL_COUNT} total")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    print("  *** FAILURES DETECTED ***"); sys.exit(1)
else:
    print("  ALL PASS"); sys.exit(0)
