#!/usr/bin/env python3
"""
Standalone test runner for Recovered Collection Global Consistency Bridge V1.
No external dependencies — pure Python 3.

Proves that a locally-validated recovered collection is globally coherent
across its constituent pieces via cross-layer consistency checks, and that
"locally valid but globally contradictory" fabricated results are caught
and rejected.

This is a narrow deterministic cross-layer coherence proof, not general
archive validation or secure attestation.

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

from aurexis_lang.recovered_collection_global_consistency_bridge_v1 import (
    GLOBAL_CONSISTENCY_VERSION, GLOBAL_CONSISTENCY_FROZEN,
    ConsistencyVerdict, ConsistencyCheck,
    ConsistencyCheckResult, ConsistencyResult,
    GlobalConsistencyProfile, V1_GLOBAL_CONSISTENCY_PROFILE,
    run_consistency_checks,
    check_collection_consistency, check_collection_consistency_from_contracts,
    IN_BOUNDS_CASES, UNSUPPORTED_CASES, CONTRADICTORY_CASES,
)
from aurexis_lang.recovered_sequence_collection_signature_match_bridge_v1 import (
    COLL_MATCH_VERSION, CollMatchVerdict, CollMatchResult,
    V1_COLL_MATCH_BASELINE,
    match_collection_signature_from_contracts,
)
from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    _get_expected_coll_sigs,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionContract, FROZEN_COLLECTION_CONTRACTS,
    generate_collection_host_png_groups,
    _get_collection_expected,
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

check(GLOBAL_CONSISTENCY_VERSION == "V1.0", "version_is_v1")
check(GLOBAL_CONSISTENCY_FROZEN is True, "frozen_is_true")
check(isinstance(V1_GLOBAL_CONSISTENCY_PROFILE, GlobalConsistencyProfile),
      "profile_is_correct_type")
check(V1_GLOBAL_CONSISTENCY_PROFILE.version == "V1.0", "profile_version_v1")
check(V1_GLOBAL_CONSISTENCY_PROFILE.require_all is True, "profile_require_all")
check(len(V1_GLOBAL_CONSISTENCY_PROFILE.checks) == 6, "profile_has_6_checks")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count_3")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_count_1")
check(len(CONTRADICTORY_CASES) == 6, "contradictory_count_6")


# ════════════════════════════════════════════════════════════
# SECTION 2: Enum and Profile Validation
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Enum and Profile Validation ===")

# ConsistencyVerdict
check(ConsistencyVerdict.CONSISTENT.value == "CONSISTENT", "verdict_consistent_val")
check(ConsistencyVerdict.INCONSISTENT.value == "INCONSISTENT", "verdict_inconsistent_val")
check(ConsistencyVerdict.UNSUPPORTED.value == "UNSUPPORTED", "verdict_unsupported_val")
check(ConsistencyVerdict.ERROR.value == "ERROR", "verdict_error_val")

# ConsistencyCheck
check(ConsistencyCheck.MATCH_VERDICT_AGREEMENT.value == "MATCH_VERDICT_AGREEMENT",
      "check_match_verdict_val")
check(ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT.value == "VALIDATION_VERDICT_AGREEMENT",
      "check_validation_verdict_val")
check(ConsistencyCheck.SIGNATURE_EQUALITY.value == "SIGNATURE_EQUALITY",
      "check_sig_equality_val")
check(ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN.value == "SEQUENCE_SIGNATURE_CHAIN",
      "check_seq_chain_val")
check(ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS.value == "PAIRWISE_SEQUENCE_DISTINCTNESS",
      "check_pairwise_val")
check(ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY.value == "CROSS_LAYER_COUNT_CONSISTENCY",
      "check_count_val")

# Profile frozen
immutable = True
try:
    V1_GLOBAL_CONSISTENCY_PROFILE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "profile_frozen_immutable")

# All 6 checks are in the profile
expected_checks = (
    ConsistencyCheck.MATCH_VERDICT_AGREEMENT,
    ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT,
    ConsistencyCheck.SIGNATURE_EQUALITY,
    ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN,
    ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS,
    ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY,
)
check(V1_GLOBAL_CONSISTENCY_PROFILE.checks == expected_checks,
      "profile_check_order_correct")


# ════════════════════════════════════════════════════════════
# SECTION 3: Pre-generate Host PNG Groups
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Pre-generating Host PNG Groups ===")

all_host_groups = {}
for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = generate_collection_host_png_groups(cc)
    all_host_groups[cc.name] = groups
    check(len(groups) == cc.expected_sequence_count,
          f"pre_gen_count_{cc.name}")
    check(all(isinstance(g, tuple) and len(g) > 0 for g in groups),
          f"pre_gen_valid_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 4: In-Bounds Consistency (All Frozen Contracts → CONSISTENT)
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: In-Bounds Consistency ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = all_host_groups[cc.name]

    cr = check_collection_consistency(groups, cc)
    check(cr.verdict == ConsistencyVerdict.CONSISTENT,
          f"consistent_{label}_verdict")
    check(cr.collection_contract_name == cc.name,
          f"consistent_{label}_name")
    check(cr.checks_performed == 6,
          f"consistent_{label}_checks_performed")
    check(cr.checks_passed == 6,
          f"consistent_{label}_checks_passed")
    check(cr.checks_failed == 0,
          f"consistent_{label}_checks_failed")
    check(len(cr.failed_checks) == 0,
          f"consistent_{label}_no_failures")
    check(cr.match_result is not None,
          f"consistent_{label}_has_match_result")
    check(cr.match_result.verdict == CollMatchVerdict.MATCH,
          f"consistent_{label}_match_verdict")

# From contracts convenience function
for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    cr = check_collection_consistency_from_contracts(cc)
    check(cr.verdict == ConsistencyVerdict.CONSISTENT,
          f"from_contracts_{label}_verdict")
    check(cr.checks_passed == 6,
          f"from_contracts_{label}_all_pass")


# ════════════════════════════════════════════════════════════
# SECTION 5: Stability / Determinism
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Stability / Determinism ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    groups = all_host_groups[cc.name]
    cr1 = check_collection_consistency(groups, cc)
    cr2 = check_collection_consistency(groups, cc)
    check(cr1.verdict == cr2.verdict,
          f"stable_verdict_{cc.name}")
    check(cr1.checks_passed == cr2.checks_passed,
          f"stable_checks_passed_{cc.name}")
    check(cr1.checks_failed == cr2.checks_failed,
          f"stable_checks_failed_{cc.name}")

cr_fc1 = check_collection_consistency_from_contracts(FROZEN_COLLECTION_CONTRACTS[0])
cr_fc2 = check_collection_consistency_from_contracts(FROZEN_COLLECTION_CONTRACTS[0])
check(cr_fc1.verdict == ConsistencyVerdict.CONSISTENT,
      "stable_from_contracts_consistent")
check(cr_fc1.checks_passed == cr_fc2.checks_passed,
      "stable_from_contracts_checks")


# ════════════════════════════════════════════════════════════
# SECTION 6: Unsupported → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: Unsupported ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = CollectionContract(
        name=case["contract_name"],
        expected_sequence_count=2,
        sequence_contract_names=("a", "b"),
    )
    cc0 = FROZEN_COLLECTION_CONTRACTS[0]
    groups = all_host_groups[cc0.name]
    cr = check_collection_consistency(groups, fake_contract)
    check(cr.verdict == ConsistencyVerdict.UNSUPPORTED,
          f"unsup_{label}_verdict")
    check(cr.checks_performed == 0,
          f"unsup_{label}_no_checks")


# ════════════════════════════════════════════════════════════
# SECTION 7: Locally Valid But Globally Contradictory
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Contradictory Cases ===")

for case in CONTRADICTORY_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    fabricated_mr = case["fabricator"]()
    expected_failed = case["expected_failed_checks"]

    cr = run_consistency_checks(fabricated_mr, cc)
    check(cr.verdict == ConsistencyVerdict.INCONSISTENT,
          f"contra_{label}_verdict")
    check(cr.checks_failed > 0,
          f"contra_{label}_has_failures")

    # Verify expected failed checks are present
    for expected_check in expected_failed:
        check(expected_check in cr.failed_checks,
              f"contra_{label}_fails_{expected_check}")

    # Verify the match_result is the fabricated one
    check(cr.match_result is fabricated_mr,
          f"contra_{label}_match_result_identity")


# ════════════════════════════════════════════════════════════
# SECTION 8: Individual Check Results Detail
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Individual Check Results ===")

# Run a consistent collection and inspect every check
cc0 = FROZEN_COLLECTION_CONTRACTS[0]
mr_ok = match_collection_signature_from_contracts(cc0)
cr_ok = run_consistency_checks(mr_ok, cc0)

check(len(cr_ok.check_results) == 6, "check_results_count_6")

for i, check_type in enumerate(expected_checks):
    cr_item = cr_ok.check_results[i]
    check(cr_item.check == check_type,
          f"check_order_{check_type.value}")
    check(cr_item.passed is True,
          f"check_passed_{check_type.value}")
    check(len(cr_item.detail) > 0,
          f"check_detail_{check_type.value}")


# ════════════════════════════════════════════════════════════
# SECTION 9: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Serialization ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = check_collection_consistency_from_contracts(cc)
    d = cr.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{cc.name}")
    check(d["verdict"] == "CONSISTENT", f"to_dict_verdict_{cc.name}")
    check(d["collection_contract_name"] == cc.name,
          f"to_dict_name_{cc.name}")
    check(d["checks_performed"] == 6, f"to_dict_performed_{cc.name}")
    check(d["checks_passed"] == 6, f"to_dict_passed_{cc.name}")
    check(d["checks_failed"] == 0, f"to_dict_failed_{cc.name}")
    check(isinstance(d["check_results"], list),
          f"to_dict_results_list_{cc.name}")
    check(len(d["check_results"]) == 6,
          f"to_dict_results_count_{cc.name}")
    check(len(d["failed_checks"]) == 0,
          f"to_dict_no_failures_{cc.name}")
    check(d["match_result"] is not None,
          f"to_dict_has_match_{cc.name}")
    check(d["version"] == "V1.0", f"to_dict_version_{cc.name}")

# Check ConsistencyCheckResult to_dict
cr_item_d = cr_ok.check_results[0].to_dict()
check(isinstance(cr_item_d, dict), "check_result_to_dict_is_dict")
check("check" in cr_item_d, "check_result_to_dict_has_check")
check("passed" in cr_item_d, "check_result_to_dict_has_passed")
check("detail" in cr_item_d, "check_result_to_dict_has_detail")


# ════════════════════════════════════════════════════════════
# SECTION 10: Cross-Layer Chain Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Cross-Layer Chain Verification ===")

# Verify that per-sequence sigs in consistency result match
# the per-sequence baseline
seq_expected = _get_expected_seq_sigs()
coll_expected = _get_collection_expected()
coll_sig_expected = _get_expected_coll_sigs()

for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = check_collection_consistency_from_contracts(cc)
    mr = cr.match_result

    # Per-sequence signatures match baseline
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(mr.sequence_signatures[i] == seq_expected[seq_name],
              f"chain_seq_sig_{cc.name}_seq{i}")

    # Collection signature matches coll sig baseline
    check(mr.computed_collection_signature == coll_sig_expected[cc.name],
          f"chain_coll_sig_{cc.name}")

    # Collection-level expected seq sigs match
    expected_seq = coll_expected.get(cc.name, ())
    check(mr.sequence_signatures == expected_seq,
          f"chain_coll_expected_seq_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 11: Custom Profile (Partial Checks)
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Custom Profile ===")

# Create a profile with only 2 checks
partial_profile = GlobalConsistencyProfile(
    checks=(
        ConsistencyCheck.MATCH_VERDICT_AGREEMENT,
        ConsistencyCheck.SIGNATURE_EQUALITY,
    ),
    require_all=True,
    version="V1.0",
)

cc0 = FROZEN_COLLECTION_CONTRACTS[0]
mr_ok = match_collection_signature_from_contracts(cc0)
cr_partial = run_consistency_checks(mr_ok, cc0, partial_profile)
check(cr_partial.verdict == ConsistencyVerdict.CONSISTENT,
      "partial_profile_consistent")
check(cr_partial.checks_performed == 2,
      "partial_profile_performed_2")
check(cr_partial.checks_passed == 2,
      "partial_profile_passed_2")

# Contradictory with partial profile that skips the failed check
# Use contradictory_duplicate_sigs — fails PAIRWISE_SEQUENCE_DISTINCTNESS
# But our partial profile doesn't include that check, so it should pass
dup_mr = CONTRADICTORY_CASES[4]["fabricator"]()  # contradictory_duplicate_sigs
cr_dup_partial = run_consistency_checks(dup_mr, cc0, partial_profile)
# This result should still be INCONSISTENT because SIGNATURE_EQUALITY check
# will fail (fabricated sigs don't match the real expected)
check(cr_dup_partial.checks_performed == 2,
      "partial_dup_performed_2")

# Use contradictory_match_verdict with a profile that only checks SIGNATURE_EQUALITY
sig_only_profile = GlobalConsistencyProfile(
    checks=(ConsistencyCheck.SIGNATURE_EQUALITY,),
    require_all=True,
    version="V1.0",
)
mismatch_mr = CONTRADICTORY_CASES[0]["fabricator"]()  # contradictory_match_verdict
cr_sig_only = run_consistency_checks(mismatch_mr, cc0, sig_only_profile)
# Sigs agree in this fabrication (both "a"*64), so SIGNATURE_EQUALITY passes
check(cr_sig_only.verdict == ConsistencyVerdict.CONSISTENT,
      "sig_only_passes_match_verdict_contradiction")
check(cr_sig_only.checks_passed == 1,
      "sig_only_passed_1")


# ════════════════════════════════════════════════════════════
# SECTION 12: E2E Full Pipeline Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: E2E Full Pipeline ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    host_groups = generate_collection_host_png_groups(cc)
    check(len(host_groups) == cc.expected_sequence_count,
          f"e2e_group_count_{cc.name}")

    cr = check_collection_consistency(host_groups, cc)
    check(cr.verdict == ConsistencyVerdict.CONSISTENT,
          f"e2e_consistent_{cc.name}")
    check(cr.checks_performed == 6,
          f"e2e_all_checks_{cc.name}")
    check(cr.checks_failed == 0,
          f"e2e_no_failures_{cc.name}")

# Wrong count E2E → pipeline fails → consistency catches it
cc_3seq = FROZEN_COLLECTION_CONTRACTS[1]
groups_3 = generate_collection_host_png_groups(cc_3seq)
cr_wrong = check_collection_consistency(groups_3[:2], cc_3seq)
check(cr_wrong.verdict == ConsistencyVerdict.INCONSISTENT,
      "e2e_wrong_count_inconsistent")
check(cr_wrong.checks_failed > 0,
      "e2e_wrong_count_has_failures")

# From contracts E2E
for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = check_collection_consistency_from_contracts(cc)
    check(cr.verdict == ConsistencyVerdict.CONSISTENT,
          f"e2e_from_contracts_{cc.name}")


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
