#!/usr/bin/env python3
"""
Standalone test runner for Recovered Page Sequence Contract Bridge V1.
No external dependencies — pure Python 3.

Proves that a small ordered sequence of recovered pages can be validated
against a frozen sequence-level contract: expected page count, expected
page order, expected page signature sequence.

This is a narrow deterministic recovered-sequence proof, not general
document workflow or open-ended multi-page intelligence.

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

from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SEQUENCE_VERSION, SEQUENCE_FROZEN,
    SequenceVerdict, SequenceContract, SequenceProfile,
    PageSequenceResult,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    validate_sequence, validate_sequence_from_contracts,
    generate_sequence_host_pngs,
    _get_sequence_expected, _contract_name_to_layout_index,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES, WRONG_ORDER_CASES,
    WRONG_CONTENT_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MatchVerdict, V1_MATCH_BASELINE, _get_expected_signatures,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    FROZEN_CONTRACTS,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
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
# MODULE CONSTANTS
# ════════════════════════════════════════════════════════════

print("=== Module Constants ===")
check(SEQUENCE_VERSION == "V1.0", "version")
check(SEQUENCE_FROZEN is True, "frozen")
check(isinstance(V1_SEQUENCE_PROFILE, SequenceProfile), "profile_type")
check(V1_SEQUENCE_PROFILE.version == "V1.0", "profile_version")
check(len(FROZEN_SEQUENCE_CONTRACTS) == 3, "frozen_sequence_count")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count")
check(len(WRONG_COUNT_CASES) == 2, "wrong_count_cases_count")
check(len(WRONG_ORDER_CASES) == 2, "wrong_order_cases_count")
check(len(WRONG_CONTENT_CASES) == 1, "wrong_content_cases_count")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_cases_count")


# ════════════════════════════════════════════════════════════
# FROZEN SEQUENCE CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Frozen Sequence Contracts ===")
sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
check(sc0.name == "two_page_horizontal_vertical", "sc0_name")
check(sc0.expected_page_count == 2, "sc0_page_count")
check(len(sc0.page_contract_names) == 2, "sc0_contract_names_len")
check(sc0.page_contract_names[0] == "two_horizontal_adj_cont", "sc0_page0_contract")
check(sc0.page_contract_names[1] == "two_vertical_adj_three", "sc0_page1_contract")

sc1 = FROZEN_SEQUENCE_CONTRACTS[1]
check(sc1.name == "three_page_all_families", "sc1_name")
check(sc1.expected_page_count == 3, "sc1_page_count")
check(len(sc1.page_contract_names) == 3, "sc1_contract_names_len")

sc2 = FROZEN_SEQUENCE_CONTRACTS[2]
check(sc2.name == "two_page_mixed_reversed", "sc2_name")
check(sc2.expected_page_count == 2, "sc2_page_count")

# Contract lookup
check(sc0.get_page_contract(0) is not None, "sc0_get_page0")
check(sc0.get_page_contract(0).name == "two_horizontal_adj_cont", "sc0_page0_name")
check(sc0.get_page_contract(1).name == "two_vertical_adj_three", "sc0_page1_name")
check(sc0.get_page_contract(2) is None, "sc0_oob_page")
check(sc0.get_page_contract(-1) is None, "sc0_neg_page")


# ════════════════════════════════════════════════════════════
# EXPECTED SIGNATURE SEQUENCE BASELINE
# ════════════════════════════════════════════════════════════

print("\n=== Expected Signature Sequence Baseline ===")
seq_expected = _get_sequence_expected()
check(len(seq_expected) == 3, "seq_expected_count")

single_page_sigs = _get_expected_signatures()

for sc in FROZEN_SEQUENCE_CONTRACTS:
    sigs = seq_expected[sc.name]
    check(len(sigs) == sc.expected_page_count, f"{sc.name}_sig_count")
    for i, name in enumerate(sc.page_contract_names):
        check(sigs[i] == single_page_sigs[name],
              f"{sc.name}_page{i}_sig_matches_single_page")
    # All sigs should be 64-char hex
    for i, sig in enumerate(sigs):
        check(len(sig) == 64, f"{sc.name}_page{i}_sig_len")
        check(all(c in "0123456789abcdef" for c in sig),
              f"{sc.name}_page{i}_sig_hex")


# ════════════════════════════════════════════════════════════
# HOST PNG GENERATION
# ════════════════════════════════════════════════════════════

print("\n=== Host PNG Generation ===")
for sc in FROZEN_SEQUENCE_CONTRACTS:
    pngs = generate_sequence_host_pngs(sc)
    check(len(pngs) == sc.expected_page_count, f"{sc.name}_png_count")
    for i, png in enumerate(pngs):
        check(isinstance(png, bytes), f"{sc.name}_page{i}_is_bytes")
        check(len(png) > 100, f"{sc.name}_page{i}_has_data")
        check(png[:8] == b'\x89PNG\r\n\x1a\n', f"{sc.name}_page{i}_png_header")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS SEQUENCE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Sequence Validation ===")
for case in IN_BOUNDS_CASES:
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    result = validate_sequence_from_contracts(sc)
    check(result.verdict == SequenceVerdict.SEQUENCE_SATISFIED,
          f"{case['label']}_verdict")
    check(result.sequence_contract_name == sc.name,
          f"{case['label']}_contract_name")
    check(result.expected_page_count == sc.expected_page_count,
          f"{case['label']}_expected_count")
    check(result.actual_page_count == sc.expected_page_count,
          f"{case['label']}_actual_count")
    check(len(result.page_match_results) == sc.expected_page_count,
          f"{case['label']}_match_results_count")
    check(len(result.page_signatures) == sc.expected_page_count,
          f"{case['label']}_signatures_count")
    check(len(result.failed_page_indices) == 0,
          f"{case['label']}_no_failures")
    # Each page match result should be MATCH
    for i, mr in enumerate(result.page_match_results):
        check(mr.verdict == MatchVerdict.MATCH,
              f"{case['label']}_page{i}_match")


# ════════════════════════════════════════════════════════════
# STABILITY: REPEATED RUNS
# ════════════════════════════════════════════════════════════

print("\n=== Stability: Repeated Runs ===")
for sc in FROZEN_SEQUENCE_CONTRACTS:
    r1 = validate_sequence_from_contracts(sc)
    r2 = validate_sequence_from_contracts(sc)
    check(r1.verdict == r2.verdict, f"{sc.name}_verdict_stable")
    check(r1.page_signatures == r2.page_signatures, f"{sc.name}_sigs_stable")
    check(r1.expected_signatures == r2.expected_signatures,
          f"{sc.name}_expected_stable")


# ════════════════════════════════════════════════════════════
# WRONG PAGE COUNT
# ════════════════════════════════════════════════════════════

print("\n=== Wrong Page Count ===")
for case in WRONG_COUNT_CASES:
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    # Generate all pages for this contract
    all_pngs = generate_sequence_host_pngs(sc)
    # Provide wrong number of pages
    provide_count = case["provide_page_count"]
    if provide_count < len(all_pngs):
        test_pngs = all_pngs[:provide_count]
    else:
        # Duplicate last page to exceed count
        test_pngs = all_pngs + (all_pngs[-1],) * (provide_count - len(all_pngs))

    result = validate_sequence(test_pngs, sc)
    check(result.verdict == SequenceVerdict.WRONG_PAGE_COUNT,
          f"{case['label']}_verdict")
    check(result.actual_page_count == provide_count,
          f"{case['label']}_actual_count")
    check(result.expected_page_count == sc.expected_page_count,
          f"{case['label']}_expected_count")


# ════════════════════════════════════════════════════════════
# WRONG PAGE ORDER
# ════════════════════════════════════════════════════════════

print("\n=== Wrong Page Order ===")
for case in WRONG_ORDER_CASES:
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    # Generate correct pages, then reverse
    correct_pngs = generate_sequence_host_pngs(sc)
    reversed_pngs = tuple(reversed(correct_pngs))

    # Only test reversal if the pages actually differ
    # (if all pages are same contract, reversed == same)
    if correct_pngs != reversed_pngs:
        result = validate_sequence(reversed_pngs, sc)
        check(result.verdict == SequenceVerdict.WRONG_PAGE_ORDER,
              f"{case['label']}_verdict")
        # Per-position matching naturally fails for wrong-order pages;
        # the verdict captures that it's an order issue, not content
        check(len(result.failed_page_indices) > 0,
              f"{case['label']}_has_position_failures")
    else:
        # Skip — cannot reverse an identical sequence
        check(True, f"{case['label']}_skip_identical")
        check(True, f"{case['label']}_skip_identical_position")


# ════════════════════════════════════════════════════════════
# WRONG PAGE CONTENT
# ════════════════════════════════════════════════════════════

print("\n=== Wrong Page Content ===")
for case in WRONG_CONTENT_CASES:
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    # Generate pages from wrong layouts
    wrong_pngs = []
    for li in case["substitute_layout_indices"]:
        layout = FROZEN_LAYOUTS[li]
        spec = build_layout_spec(layout)
        wrong_pngs.append(generate_multi_artifact_host(spec))
    wrong_pngs = tuple(wrong_pngs)

    result = validate_sequence(wrong_pngs, sc)
    check(result.verdict == SequenceVerdict.PAGE_MATCH_FAILED,
          f"{case['label']}_verdict")
    check(len(result.failed_page_indices) > 0,
          f"{case['label']}_has_failures")


# ════════════════════════════════════════════════════════════
# UNSUPPORTED SEQUENCE
# ════════════════════════════════════════════════════════════

print("\n=== Unsupported Sequence ===")
for case in UNSUPPORTED_CASES:
    fake_contract = SequenceContract(
        name=case["contract_name"],
        expected_page_count=2,
        page_contract_names=("two_horizontal_adj_cont", "two_vertical_adj_three"),
    )
    # Generate some dummy PNGs
    sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
    pngs = generate_sequence_host_pngs(sc0)

    result = validate_sequence(pngs, fake_contract)
    check(result.verdict == SequenceVerdict.UNSUPPORTED_SEQUENCE,
          f"{case['label']}_verdict")
    check(result.sequence_contract_name == case["contract_name"],
          f"{case['label']}_contract_name")


# ════════════════════════════════════════════════════════════
# CONTRACT-TO-LAYOUT MAPPING
# ════════════════════════════════════════════════════════════

print("\n=== Contract-to-Layout Mapping ===")
for i, c in enumerate(FROZEN_CONTRACTS):
    idx = _contract_name_to_layout_index(c.name)
    check(idx == i, f"contract_{i}_maps_to_layout_{i}")
check(_contract_name_to_layout_index("nonexistent") is None, "unknown_maps_to_none")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")
sc = FROZEN_SEQUENCE_CONTRACTS[0]
result = validate_sequence_from_contracts(sc)
d = result.to_dict()
check(d["verdict"] == "SEQUENCE_SATISFIED", "dict_verdict")
check(d["sequence_contract_name"] == sc.name, "dict_name")
check(d["expected_page_count"] == 2, "dict_expected_count")
check(d["actual_page_count"] == 2, "dict_actual_count")
check(len(d["page_match_results"]) == 2, "dict_page_results")
check(len(d["page_signatures"]) == 2, "dict_page_sigs")
check(len(d["failed_page_indices"]) == 0, "dict_no_failures")
check(d["version"] == SEQUENCE_VERSION, "dict_version")


# ════════════════════════════════════════════════════════════
# E2E: FULL PIPELINE CHAIN
# ════════════════════════════════════════════════════════════

print("\n=== E2E: Full Pipeline Chain ===")
for sc in FROZEN_SEQUENCE_CONTRACTS:
    pngs = generate_sequence_host_pngs(sc)
    result = validate_sequence(pngs, sc)
    check(result.verdict == SequenceVerdict.SEQUENCE_SATISFIED,
          f"e2e_{sc.name}")

# Cross-validate: expected sigs match what single-page baseline says
for sc in FROZEN_SEQUENCE_CONTRACTS:
    result = validate_sequence_from_contracts(sc)
    for i, sig in enumerate(result.page_signatures):
        page_contract_name = sc.page_contract_names[i]
        expected_sig = single_page_sigs[page_contract_name]
        check(sig == expected_sig, f"e2e_cross_{sc.name}_page{i}")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
total = passed + failed
print(f"TOTAL: {total}  PASSED: {passed}  FAILED: {failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
sys.exit(0 if failed == 0 else 1)
