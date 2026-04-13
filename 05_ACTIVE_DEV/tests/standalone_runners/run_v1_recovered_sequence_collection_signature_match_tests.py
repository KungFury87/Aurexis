#!/usr/bin/env python3
"""
Standalone test runner for Recovered Sequence Collection Signature Match Bridge V1.
No external dependencies — pure Python 3.

Proves that a computed collection-level signature can be compared against a
frozen expected-collection-signature baseline and return an honest deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-collection match proof, not general
archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os

# ── Path setup ─────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'aurexis_lang', 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurexis_lang.recovered_sequence_collection_signature_match_bridge_v1 import (
    COLL_MATCH_VERSION, COLL_MATCH_FROZEN,
    CollMatchVerdict, CollMatchResult,
    ExpectedCollectionSignatureBaseline, V1_COLL_MATCH_BASELINE,
    match_collection_signature, match_collection_signature_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    COLL_SIG_VERSION, CollSigVerdict,
    sign_collection_from_contracts,
    _get_expected_coll_sigs,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionContract, FROZEN_COLLECTION_CONTRACTS,
    generate_collection_host_png_groups,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    _get_expected_seq_sigs,
)


passed = 0
failed = 0


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}")


# ════════════════════════════════════════════════════════════
# SECTION 1: Module Constants
# ════════════════════════════════════════════════════════════

print("=== Section 1: Module Constants ===")

check(COLL_MATCH_VERSION == "V1.0", "coll_match_version_is_v1")
check(COLL_MATCH_FROZEN is True, "coll_match_frozen_is_true")
check(isinstance(V1_COLL_MATCH_BASELINE, ExpectedCollectionSignatureBaseline),
      "baseline_is_correct_type")
check(V1_COLL_MATCH_BASELINE.version == "V1.0", "baseline_version_is_v1")
check(len(V1_COLL_MATCH_BASELINE.supported_collection_contracts) == 3,
      "baseline_has_3_contracts")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count_3")
check(len(WRONG_COUNT_CASES) == 2, "wrong_count_count_2")
check(len(WRONG_ORDER_CASES) == 2, "wrong_order_count_2")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_count_1")


# ════════════════════════════════════════════════════════════
# SECTION 2: Expected-Collection-Signature Baseline Validation
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Baseline Validation ===")

expected_coll_sigs = _get_expected_coll_sigs()
check(len(expected_coll_sigs) == 3, "baseline_has_3_signatures")
check(all(len(v) == 64 for v in expected_coll_sigs.values()),
      "baseline_all_sha256_len")
check(len(set(expected_coll_sigs.values())) == 3, "baseline_all_unique")

# Each frozen collection contract is in the baseline
for cc in FROZEN_COLLECTION_CONTRACTS:
    check(V1_COLL_MATCH_BASELINE.is_supported(cc.name),
          f"baseline_supports_{cc.name}")

# Unknown contract is not in the baseline
check(not V1_COLL_MATCH_BASELINE.is_supported("nonexistent"),
      "baseline_rejects_unknown")

# Baseline is frozen (immutable)
immutable = True
try:
    V1_COLL_MATCH_BASELINE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "baseline_frozen_immutable")

# get_expected returns correct values
for cc in FROZEN_COLLECTION_CONTRACTS:
    sig = V1_COLL_MATCH_BASELINE.get_expected(cc.name)
    check(sig is not None and len(sig) == 64,
          f"get_expected_valid_{cc.name}")
    check(sig == expected_coll_sigs[cc.name],
          f"get_expected_matches_cache_{cc.name}")

check(V1_COLL_MATCH_BASELINE.get_expected("unknown") is None,
      "get_expected_unknown_none")


# ════════════════════════════════════════════════════════════
# SECTION 3: Pre-generate Host PNG Groups for All Collection Contracts
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Pre-generating Host PNG Groups ===")

all_host_groups = {}
for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = generate_collection_host_png_groups(cc)
    all_host_groups[cc.name] = groups
    check(len(groups) == cc.expected_sequence_count,
          f"pre_gen_count_{cc.name}")
    check(all(isinstance(g, tuple) and len(g) > 0 for g in groups),
          f"pre_gen_valid_groups_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 4: In-Bounds Match (All Frozen Contracts → MATCH)
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: In-Bounds Match ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = all_host_groups[cc.name]

    mr = match_collection_signature(groups, cc)
    check(mr.verdict == CollMatchVerdict.MATCH,
          f"match_{label}_verdict")
    check(len(mr.computed_collection_signature) == 64,
          f"match_{label}_sig_len")
    check(mr.computed_collection_signature == mr.expected_collection_signature,
          f"match_{label}_sigs_equal")
    check(mr.collection_contract_name == cc.name,
          f"match_{label}_contract_name")
    check(mr.sequence_count == cc.expected_sequence_count,
          f"match_{label}_seq_count")
    check(len(mr.sequence_signatures) == cc.expected_sequence_count,
          f"match_{label}_seq_sigs_count")
    check(mr.sign_verdict in ("MATCH", "SIGNED"),
          f"match_{label}_sign_ok")

# From contracts convenience function
for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    mr = match_collection_signature_from_contracts(cc)
    check(mr.verdict == CollMatchVerdict.MATCH,
          f"match_from_contracts_{label}_verdict")
    check(mr.computed_collection_signature == mr.expected_collection_signature,
          f"match_from_contracts_{label}_sigs_equal")
    check(mr.collection_contract_name == cc.name,
          f"match_from_contracts_{label}_name")


# ════════════════════════════════════════════════════════════
# SECTION 5: Stability / Determinism
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Stability / Determinism ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = all_host_groups[cc.name]
    mr1 = match_collection_signature(groups, cc)
    mr2 = match_collection_signature(groups, cc)
    check(mr1.verdict == mr2.verdict,
          f"stable_verdict_{cc.name}")
    check(mr1.computed_collection_signature == mr2.computed_collection_signature,
          f"stable_sig_{cc.name}")
    check(mr1.expected_collection_signature == mr2.expected_collection_signature,
          f"stable_expected_{cc.name}")

# From contracts determinism
mr_fc1 = match_collection_signature_from_contracts(FROZEN_COLLECTION_CONTRACTS[0])
mr_fc2 = match_collection_signature_from_contracts(FROZEN_COLLECTION_CONTRACTS[0])
check(mr_fc1.verdict == CollMatchVerdict.MATCH, "stable_from_contracts_match")
check(mr_fc1.computed_collection_signature == mr_fc2.computed_collection_signature,
      "stable_from_contracts_sig")


# ════════════════════════════════════════════════════════════
# SECTION 6: Wrong Sequence Count → SIGN_FAILED
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: Wrong Sequence Count ===")

for case in WRONG_COUNT_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    correct_groups = all_host_groups[cc.name]
    provide_count = case["provide_count"]
    if provide_count < len(correct_groups):
        test_groups = correct_groups[:provide_count]
    else:
        test_groups = correct_groups + (correct_groups[-1],) * (provide_count - len(correct_groups))

    mr = match_collection_signature(test_groups, cc)
    check(mr.verdict == CollMatchVerdict.SIGN_FAILED,
          f"wrong_count_{label}_verdict")
    check(mr.computed_collection_signature == "",
          f"wrong_count_{label}_empty_sig")


# ════════════════════════════════════════════════════════════
# SECTION 7: Wrong Sequence Order → SIGN_FAILED
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Wrong Sequence Order ===")

for case in WRONG_ORDER_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    correct_groups = all_host_groups[cc.name]
    reversed_groups = tuple(reversed(correct_groups))

    mr = match_collection_signature(reversed_groups, cc)
    check(mr.verdict == CollMatchVerdict.SIGN_FAILED,
          f"wrong_order_{label}_verdict")
    check(mr.computed_collection_signature == "",
          f"wrong_order_{label}_empty_sig")
    check(mr.collection_validation_verdict in (
        "WRONG_SEQUENCE_ORDER", "SEQUENCE_MATCH_FAILED"),
          f"wrong_order_{label}_coll_detected")


# ════════════════════════════════════════════════════════════
# SECTION 8: Unsupported → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Unsupported ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = CollectionContract(
        name=case["contract_name"],
        expected_sequence_count=2,
        sequence_contract_names=("a", "b"),
    )
    # Use any host PNG groups
    cc0 = FROZEN_COLLECTION_CONTRACTS[0]
    groups = all_host_groups[cc0.name]
    mr = match_collection_signature(groups, fake_contract)
    check(mr.verdict == CollMatchVerdict.UNSUPPORTED,
          f"unsup_{label}_verdict")
    check(mr.computed_collection_signature == "",
          f"unsup_{label}_empty_sig")
    check(mr.expected_collection_signature == "",
          f"unsup_{label}_no_expected")


# ════════════════════════════════════════════════════════════
# SECTION 9: Cross-Collection Signature Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Cross-Collection Distinctness ===")

all_match_sigs = []
for cc in FROZEN_COLLECTION_CONTRACTS:
    mr = match_collection_signature_from_contracts(cc)
    all_match_sigs.append(mr.computed_collection_signature)

check(len(set(all_match_sigs)) == len(all_match_sigs),
      "all_match_sigs_distinct")

for i in range(len(all_match_sigs)):
    for j in range(i + 1, len(all_match_sigs)):
        check(all_match_sigs[i] != all_match_sigs[j],
              f"match_sig_distinct_{i}_vs_{j}")


# ════════════════════════════════════════════════════════════
# SECTION 10: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Serialization ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    mr = match_collection_signature_from_contracts(cc)
    d = mr.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{cc.name}")
    check(d["verdict"] == "MATCH", f"to_dict_verdict_{cc.name}")
    check(d["computed_collection_signature"] == mr.computed_collection_signature,
          f"to_dict_computed_sig_{cc.name}")
    check(d["expected_collection_signature"] == mr.expected_collection_signature,
          f"to_dict_expected_sig_{cc.name}")
    check(d["collection_contract_name"] == cc.name,
          f"to_dict_contract_name_{cc.name}")
    check(d["sequence_count"] == cc.expected_sequence_count,
          f"to_dict_seq_count_{cc.name}")
    check(isinstance(d["sequence_signatures"], list),
          f"to_dict_seq_sigs_list_{cc.name}")
    check(len(d["sequence_signatures"]) == cc.expected_sequence_count,
          f"to_dict_seq_sigs_count_{cc.name}")
    check(d["version"] == "V1.0",
          f"to_dict_version_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 11: Baseline Consistency with Underlying Pipeline
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Baseline Consistency ===")

# The expected collection signatures in the match baseline should equal
# the expected collection signatures from the signature bridge
sig_bridge_expected = _get_expected_coll_sigs()
for cc in FROZEN_COLLECTION_CONTRACTS:
    baseline_sig = V1_COLL_MATCH_BASELINE.get_expected(cc.name)
    bridge_sig = sig_bridge_expected[cc.name]
    check(baseline_sig == bridge_sig,
          f"baseline_matches_bridge_{cc.name}")

# The match result's computed signature should equal the sign result's signature
for cc in FROZEN_COLLECTION_CONTRACTS:
    mr = match_collection_signature_from_contracts(cc)
    sr = sign_collection_from_contracts(cc)
    check(mr.computed_collection_signature == sr.collection_signature,
          f"match_sig_equals_sign_sig_{cc.name}")
    check(mr.sequence_signatures == sr.sequence_signatures,
          f"match_seq_sigs_equals_sign_seq_sigs_{cc.name}")

# Verify that the sequence-level signatures in a matched collection
# come from the per-sequence expected baseline
seq_expected = _get_expected_seq_sigs()
for cc in FROZEN_COLLECTION_CONTRACTS:
    mr = match_collection_signature_from_contracts(cc)
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(mr.sequence_signatures[i] == seq_expected[seq_name],
              f"seq_sig_from_baseline_{cc.name}_seq{i}")


# ════════════════════════════════════════════════════════════
# SECTION 12: E2E Full Pipeline Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: E2E Full Pipeline ===")

# Verify the full chain: host_png_groups → per-sequence recovery →
# per-sequence contract → per-sequence signature → per-sequence match →
# collection contract → collection signature → collection signature match
for cc in FROZEN_COLLECTION_CONTRACTS:
    host_groups = generate_collection_host_png_groups(cc)
    check(len(host_groups) == cc.expected_sequence_count,
          f"e2e_group_count_{cc.name}")

    mr = match_collection_signature(host_groups, cc)
    check(mr.verdict == CollMatchVerdict.MATCH,
          f"e2e_verdict_match_{cc.name}")
    check(mr.computed_collection_signature == sig_bridge_expected[cc.name],
          f"e2e_sig_matches_bridge_expected_{cc.name}")

    # Verify sequence signatures chain back to per-sequence baseline
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(mr.sequence_signatures[i] == seq_expected[seq_name],
              f"e2e_seq_sig_baseline_{cc.name}_seq{i}")

# Wrong count E2E
cc_3seq = FROZEN_COLLECTION_CONTRACTS[1]
groups_3 = generate_collection_host_png_groups(cc_3seq)
mr_wrong = match_collection_signature(groups_3[:2], cc_3seq)
check(mr_wrong.verdict == CollMatchVerdict.SIGN_FAILED,
      "e2e_wrong_count_sign_failed")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
total = passed + failed
print(f"TOTAL: {total} assertions — {passed} passed, {failed} failed")
if failed:
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: ALL PASS")
    sys.exit(0)
