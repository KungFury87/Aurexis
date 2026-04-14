#!/usr/bin/env python3
"""
Standalone test runner for Recovered Sequence Collection Contract Bridge V1.
No external dependencies — pure Python 3.

Proves that a small ordered collection of recovered page sequences can be
validated against a frozen collection-level contract, with honest failure
for wrong count, wrong order, wrong content, and unsupported collections.

This is a narrow deterministic recovered-collection proof, not general
archive management or open-ended multi-sequence intelligence.

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

from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionVerdict, CollectionResult,
    CollectionContract, CollectionProfile,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    validate_collection, validate_collection_from_contracts,
    generate_collection_host_png_groups,
    _get_collection_expected,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, WRONG_CONTENT_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SeqMatchVerdict,
    match_sequence_signature_from_contracts,
    V1_SEQ_MATCH_BASELINE,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    FROZEN_SEQUENCE_CONTRACTS,
    generate_sequence_host_pngs,
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

check(COLLECTION_VERSION == "V1.0", "version_is_v1")
check(COLLECTION_FROZEN is True, "frozen_is_true")
check(isinstance(V1_COLLECTION_PROFILE, CollectionProfile), "profile_type")
check(V1_COLLECTION_PROFILE.version == "V1.0", "profile_version")
check(len(V1_COLLECTION_PROFILE.contracts) == 3, "profile_has_3_contracts")
check(len(FROZEN_COLLECTION_CONTRACTS) == 3, "frozen_has_3_contracts")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count_3")
check(len(WRONG_COUNT_CASES) == 2, "wrong_count_count_2")
check(len(WRONG_ORDER_CASES) == 2, "wrong_order_count_2")
check(len(WRONG_CONTENT_CASES) == 1, "wrong_content_count_1")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_count_1")


# ════════════════════════════════════════════════════════════
# SECTION 2: Frozen Collection Contract Definitions
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Frozen Collection Contracts ===")

cc0 = FROZEN_COLLECTION_CONTRACTS[0]
cc1 = FROZEN_COLLECTION_CONTRACTS[1]
cc2 = FROZEN_COLLECTION_CONTRACTS[2]

check(cc0.name == "two_seq_hv_mixed", "cc0_name")
check(cc0.expected_sequence_count == 2, "cc0_count")
check(cc0.sequence_contract_names == (
    "two_page_horizontal_vertical",
    "two_page_mixed_reversed",
), "cc0_seq_names")

check(cc1.name == "three_seq_all", "cc1_name")
check(cc1.expected_sequence_count == 3, "cc1_count")
check(cc1.sequence_contract_names == (
    "two_page_horizontal_vertical",
    "three_page_all_families",
    "two_page_mixed_reversed",
), "cc1_seq_names")

check(cc2.name == "two_seq_all_mixed", "cc2_name")
check(cc2.expected_sequence_count == 2, "cc2_count")
check(cc2.sequence_contract_names == (
    "three_page_all_families",
    "two_page_mixed_reversed",
), "cc2_seq_names")

# Immutability
immutable = True
try:
    cc0.name = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "collection_contract_frozen")

# get_sequence_contract works
for cc in FROZEN_COLLECTION_CONTRACTS:
    for i in range(cc.expected_sequence_count):
        sc = cc.get_sequence_contract(i)
        check(sc is not None, f"get_seq_contract_{cc.name}_{i}")
    check(cc.get_sequence_contract(-1) is None, f"get_seq_contract_{cc.name}_neg")
    check(cc.get_sequence_contract(cc.expected_sequence_count) is None,
          f"get_seq_contract_{cc.name}_oob")


# ════════════════════════════════════════════════════════════
# SECTION 3: Expected Collection Signatures
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Expected Collection Signatures ===")

coll_expected = _get_collection_expected()
check(len(coll_expected) == 3, "expected_has_3_entries")

seq_sigs = _get_expected_seq_sigs()
for cc in FROZEN_COLLECTION_CONTRACTS:
    expected = coll_expected[cc.name]
    check(len(expected) == cc.expected_sequence_count,
          f"expected_count_{cc.name}")
    # Each expected sig should match the sequence-level expected sig
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(expected[i] == seq_sigs[seq_name],
              f"expected_matches_seq_baseline_{cc.name}_{i}")


# ════════════════════════════════════════════════════════════
# SECTION 4: Host PNG Group Generation
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: Host PNG Group Generation ===")

all_groups = {}
for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = generate_collection_host_png_groups(cc)
    all_groups[cc.name] = groups
    check(len(groups) == cc.expected_sequence_count,
          f"groups_count_{cc.name}")
    for i, group in enumerate(groups):
        sc = cc.get_sequence_contract(i)
        check(len(group) == sc.expected_page_count,
              f"group_page_count_{cc.name}_{i}")
        check(all(isinstance(p, bytes) and len(p) > 0 for p in group),
              f"group_valid_bytes_{cc.name}_{i}")


# ════════════════════════════════════════════════════════════
# SECTION 5: In-Bounds Validation (COLLECTION_SATISFIED)
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: In-Bounds Validation ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = all_groups[cc.name]

    cr = validate_collection(groups, cc)
    check(cr.verdict == CollectionVerdict.COLLECTION_SATISFIED,
          f"inb_{label}_verdict")
    check(cr.collection_contract_name == cc.name,
          f"inb_{label}_name")
    check(cr.expected_sequence_count == cc.expected_sequence_count,
          f"inb_{label}_expected_count")
    check(cr.actual_sequence_count == cc.expected_sequence_count,
          f"inb_{label}_actual_count")
    check(len(cr.sequence_match_results) == cc.expected_sequence_count,
          f"inb_{label}_result_count")
    check(len(cr.sequence_signatures) == cc.expected_sequence_count,
          f"inb_{label}_sig_count")
    check(cr.sequence_signatures == cr.expected_sequence_signatures,
          f"inb_{label}_sigs_match")
    check(len(cr.failed_sequence_indices) == 0,
          f"inb_{label}_no_failures")
    # Each sequence match result should be MATCH
    for i, mr in enumerate(cr.sequence_match_results):
        check(mr.verdict == SeqMatchVerdict.MATCH,
              f"inb_{label}_seq{i}_match")

# From contracts convenience
for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    cr = validate_collection_from_contracts(cc)
    check(cr.verdict == CollectionVerdict.COLLECTION_SATISFIED,
          f"inb_from_contracts_{label}_verdict")
    check(cr.sequence_signatures == cr.expected_sequence_signatures,
          f"inb_from_contracts_{label}_sigs_match")


# ════════════════════════════════════════════════════════════
# SECTION 6: Stability / Determinism
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: Stability / Determinism ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    cr1 = validate_collection_from_contracts(cc)
    cr2 = validate_collection_from_contracts(cc)
    check(cr1.verdict == cr2.verdict,
          f"stable_verdict_{cc.name}")
    check(cr1.sequence_signatures == cr2.sequence_signatures,
          f"stable_sigs_{cc.name}")
    check(cr1.expected_sequence_signatures == cr2.expected_sequence_signatures,
          f"stable_expected_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 7: Wrong Sequence Count
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Wrong Sequence Count ===")

for case in WRONG_COUNT_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = all_groups[cc.name]
    provide = case["provide_count"]
    if provide < len(groups):
        test_groups = groups[:provide]
    else:
        test_groups = groups + (groups[-1],) * (provide - len(groups))
    cr = validate_collection(test_groups, cc)
    check(cr.verdict == CollectionVerdict.WRONG_SEQUENCE_COUNT,
          f"wc_{label}_verdict")
    check(cr.actual_sequence_count == provide,
          f"wc_{label}_actual_count")


# ════════════════════════════════════════════════════════════
# SECTION 8: Wrong Sequence Order
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Wrong Sequence Order ===")

for case in WRONG_ORDER_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = all_groups[cc.name]
    reversed_groups = tuple(reversed(groups))
    cr = validate_collection(reversed_groups, cc)
    check(cr.verdict == CollectionVerdict.WRONG_SEQUENCE_ORDER,
          f"wo_{label}_verdict")
    check(len(cr.failed_sequence_indices) > 0,
          f"wo_{label}_has_failures")


# ════════════════════════════════════════════════════════════
# SECTION 9: Wrong Sequence Content
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Wrong Sequence Content ===")

for case in WRONG_CONTENT_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    # Substitute with different sequence groups
    sub_indices = case["substitute_seq_indices"]
    sub_groups = []
    for idx in sub_indices:
        sc = FROZEN_SEQUENCE_CONTRACTS[idx]
        sub_groups.append(generate_sequence_host_pngs(sc))
    cr = validate_collection(tuple(sub_groups), cc)
    check(cr.verdict == CollectionVerdict.SEQUENCE_MATCH_FAILED,
          f"wcon_{label}_verdict")


# ════════════════════════════════════════════════════════════
# SECTION 10: Unsupported Collection
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Unsupported Collection ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = CollectionContract(
        name=case["contract_name"],
        expected_sequence_count=2,
        sequence_contract_names=("a", "b"),
    )
    groups = all_groups[FROZEN_COLLECTION_CONTRACTS[0].name]
    cr = validate_collection(groups, fake_contract)
    check(cr.verdict == CollectionVerdict.UNSUPPORTED_COLLECTION,
          f"unsup_{label}_verdict")
    check(len(cr.sequence_match_results) == 0,
          f"unsup_{label}_no_results")


# ════════════════════════════════════════════════════════════
# SECTION 11: Cross-Collection Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Cross-Collection Distinctness ===")

all_sig_tuples = []
for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = validate_collection_from_contracts(cc)
    all_sig_tuples.append(cr.sequence_signatures)

check(len(set(all_sig_tuples)) == len(all_sig_tuples),
      "all_collections_distinct_sig_tuples")

# Pairwise
for i in range(len(all_sig_tuples)):
    for j in range(i + 1, len(all_sig_tuples)):
        check(all_sig_tuples[i] != all_sig_tuples[j],
              f"sig_tuple_distinct_{i}_vs_{j}")


# ════════════════════════════════════════════════════════════
# SECTION 12: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: Serialization ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = validate_collection_from_contracts(cc)
    d = cr.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{cc.name}")
    check(d["verdict"] == "COLLECTION_SATISFIED",
          f"to_dict_verdict_{cc.name}")
    check(d["collection_contract_name"] == cc.name,
          f"to_dict_name_{cc.name}")
    check(d["expected_sequence_count"] == cc.expected_sequence_count,
          f"to_dict_expected_count_{cc.name}")
    check(isinstance(d["sequence_match_results"], list),
          f"to_dict_results_list_{cc.name}")
    check(len(d["sequence_match_results"]) == cc.expected_sequence_count,
          f"to_dict_results_count_{cc.name}")
    check(isinstance(d["sequence_signatures"], list),
          f"to_dict_sigs_list_{cc.name}")
    check(d["version"] == "V1.0",
          f"to_dict_version_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 13: Baseline Consistency
# ════════════════════════════════════════════════════════════

print("\n=== Section 13: Baseline Consistency ===")

# Each sequence signature in a satisfied collection should match
# the standalone sequence signature match result
for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = validate_collection_from_contracts(cc)
    for i, seq_name in enumerate(cc.sequence_contract_names):
        sc = None
        for s in FROZEN_SEQUENCE_CONTRACTS:
            if s.name == seq_name:
                sc = s
                break
        standalone_mr = match_sequence_signature_from_contracts(sc)
        check(cr.sequence_signatures[i] == standalone_mr.computed_sequence_signature,
              f"baseline_match_{cc.name}_seq{i}")


# ════════════════════════════════════════════════════════════
# SECTION 14: E2E Full Pipeline
# ════════════════════════════════════════════════════════════

print("\n=== Section 14: E2E Full Pipeline ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = generate_collection_host_png_groups(cc)
    cr = validate_collection(groups, cc)
    check(cr.verdict == CollectionVerdict.COLLECTION_SATISFIED,
          f"e2e_{cc.name}_satisfied")
    # Verify each sequence group count
    check(len(groups) == cc.expected_sequence_count,
          f"e2e_{cc.name}_group_count")
    # Verify sigs match expected
    check(cr.sequence_signatures == cr.expected_sequence_signatures,
          f"e2e_{cc.name}_sigs_match")


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
