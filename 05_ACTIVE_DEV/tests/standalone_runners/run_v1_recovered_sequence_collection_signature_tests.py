#!/usr/bin/env python3
"""
Standalone test runner for Recovered Sequence Collection Signature Bridge V1.
No external dependencies — pure Python 3.

Proves that a validated ordered collection of recovered page sequences
can be reduced to a single deterministic collection-level SHA-256
fingerprint, and that changes in sequence order, sequence content, or
sequence count produce honest signature mismatch.

This is a narrow deterministic recovered-collection identity proof, not
general archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import sys
import os
import hashlib

# ── Path setup ─────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'aurexis_lang', 'src')
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    COLL_SIG_VERSION, COLL_SIG_FROZEN,
    CollectionSignatureProfile, V1_COLL_SIG_PROFILE,
    canonicalize_collection, compute_collection_signature,
    CollSigVerdict, CollSigResult,
    _get_expected_coll_sigs, _build_expected_coll_sig,
    sign_collection, sign_collection_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionVerdict, CollectionContract, CollectionProfile,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    validate_collection_from_contracts,
    generate_collection_host_png_groups,
    _get_collection_expected,
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

check(COLL_SIG_VERSION == "V1.0", "coll_sig_version_is_v1")
check(COLL_SIG_FROZEN is True, "coll_sig_frozen_is_true")
check(isinstance(V1_COLL_SIG_PROFILE, CollectionSignatureProfile), "profile_is_correct_type")
check(V1_COLL_SIG_PROFILE.hash_algorithm == "sha256", "hash_algorithm_is_sha256")
check(V1_COLL_SIG_PROFILE.version == "V1.0", "profile_version_is_v1")
check(len(V1_COLL_SIG_PROFILE.canonical_fields) == 3, "canonical_fields_count_3")
check("collection_contract_name" in V1_COLL_SIG_PROFILE.canonical_fields, "field_coll_contract_name")
check("sequence_count" in V1_COLL_SIG_PROFILE.canonical_fields, "field_sequence_count")
check("ordered_sequence_signatures" in V1_COLL_SIG_PROFILE.canonical_fields, "field_ordered_seq_sigs")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_cases_count_3")
check(len(WRONG_COUNT_CASES) == 2, "wrong_count_cases_count_2")
check(len(WRONG_ORDER_CASES) == 2, "wrong_order_cases_count_2")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_cases_count_1")


# ════════════════════════════════════════════════════════════
# SECTION 2: Frozen Collection Contracts Available
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Frozen Collection Contracts ===")

check(len(FROZEN_COLLECTION_CONTRACTS) == 3, "three_frozen_coll_contracts")
check(FROZEN_COLLECTION_CONTRACTS[0].name == "two_seq_hv_mixed", "coll_contract_0_name")
check(FROZEN_COLLECTION_CONTRACTS[1].name == "three_seq_all", "coll_contract_1_name")
check(FROZEN_COLLECTION_CONTRACTS[2].name == "two_seq_all_mixed", "coll_contract_2_name")
check(FROZEN_COLLECTION_CONTRACTS[0].expected_sequence_count == 2, "coll_contract_0_count_2")
check(FROZEN_COLLECTION_CONTRACTS[1].expected_sequence_count == 3, "coll_contract_1_count_3")
check(FROZEN_COLLECTION_CONTRACTS[2].expected_sequence_count == 2, "coll_contract_2_count_2")


# ════════════════════════════════════════════════════════════
# SECTION 3: Canonicalization Tests
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Canonicalization ===")

# Valid canonicalization
dummy_sigs = ("a" * 64, "b" * 64)
canon = canonicalize_collection("test_collection", 2, dummy_sigs)
check(canon is not None, "canonicalize_valid_returns_string")
check("coll_contract=test_collection" in canon, "canon_has_coll_contract_name")
check("seq_count=2" in canon, "canon_has_seq_count")
check("seq_sigs=" in canon, "canon_has_seq_sigs")
check("version=V1.0" in canon, "canon_has_version")
check(("a" * 64) in canon, "canon_has_first_sig")
check(("b" * 64) in canon, "canon_has_second_sig")

# Count mismatch
canon_bad_count = canonicalize_collection("test", 3, dummy_sigs)
check(canon_bad_count is None, "canonicalize_count_mismatch_returns_none")

# Empty sequences
canon_empty = canonicalize_collection("test", 0, ())
check(canon_empty is None, "canonicalize_empty_returns_none")

# Short signature (not 64 chars)
canon_short = canonicalize_collection("test", 1, ("abc",))
check(canon_short is None, "canonicalize_short_sig_returns_none")

# Empty string signature
canon_empty_sig = canonicalize_collection("test", 1, ("",))
check(canon_empty_sig is None, "canonicalize_empty_sig_returns_none")

# Determinism: same inputs → same output
canon2 = canonicalize_collection("test_collection", 2, dummy_sigs)
check(canon == canon2, "canonicalize_deterministic")

# Different inputs → different output
diff_sigs = ("c" * 64, "d" * 64)
canon_diff = canonicalize_collection("test_collection", 2, diff_sigs)
check(canon_diff != canon, "canonicalize_different_sigs_different_output")

# Different contract name → different output
canon_diff_name = canonicalize_collection("other_collection", 2, dummy_sigs)
check(canon_diff_name != canon, "canonicalize_different_name_different_output")

# Three sequences
three_sigs = ("a" * 64, "b" * 64, "c" * 64)
canon_three = canonicalize_collection("test_3", 3, three_sigs)
check(canon_three is not None, "canonicalize_three_seqs_works")
check("seq_count=3" in canon_three, "canon_three_has_count_3")


# ════════════════════════════════════════════════════════════
# SECTION 4: Signature Computation Tests
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: Signature Computation ===")

sig = compute_collection_signature("test canonical form")
check(isinstance(sig, str), "compute_returns_string")
check(len(sig) == 64, "compute_returns_64_chars")
check(sig == hashlib.sha256(b"test canonical form").hexdigest(), "compute_matches_stdlib_sha256")

# Determinism
sig2 = compute_collection_signature("test canonical form")
check(sig == sig2, "compute_deterministic")

# Different input → different output
sig3 = compute_collection_signature("different canonical form")
check(sig3 != sig, "compute_different_input_different_sig")


# ════════════════════════════════════════════════════════════
# SECTION 5: Expected Collection Signatures
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Expected Collection Signatures ===")

expected_coll_sigs = _get_expected_coll_sigs()
check(isinstance(expected_coll_sigs, dict), "expected_coll_sigs_is_dict")
check(len(expected_coll_sigs) == 3, "expected_coll_sigs_has_3_entries")

for cc in FROZEN_COLLECTION_CONTRACTS:
    check(cc.name in expected_coll_sigs, f"expected_coll_sig_exists_{cc.name}")
    sig = expected_coll_sigs[cc.name]
    check(isinstance(sig, str), f"expected_coll_sig_is_str_{cc.name}")
    check(len(sig) == 64, f"expected_coll_sig_64_chars_{cc.name}")

# All expected sigs are distinct
all_sigs = list(expected_coll_sigs.values())
check(len(set(all_sigs)) == len(all_sigs), "expected_coll_sigs_all_distinct")

# Idempotent: calling again returns same values
expected_coll_sigs2 = _get_expected_coll_sigs()
for cc in FROZEN_COLLECTION_CONTRACTS:
    check(expected_coll_sigs[cc.name] == expected_coll_sigs2[cc.name],
          f"expected_coll_sig_idempotent_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 6: End-to-End In-Bounds Signing (MATCH)
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: In-Bounds Signing ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    result = sign_collection_from_contracts(cc)

    check(result.verdict == CollSigVerdict.MATCH,
          f"verdict_match_{label}")
    check(result.collection_signature != "",
          f"sig_nonempty_{label}")
    check(len(result.collection_signature) == 64,
          f"sig_64_chars_{label}")
    check(result.canonical_form != "",
          f"canonical_nonempty_{label}")
    check(result.expected_signature != "",
          f"expected_nonempty_{label}")
    check(result.collection_signature == result.expected_signature,
          f"sig_equals_expected_{label}")
    check(result.collection_contract_name == cc.name,
          f"contract_name_correct_{label}")
    check(result.sequence_count == cc.expected_sequence_count,
          f"seq_count_correct_{label}")
    check(len(result.sequence_signatures) == cc.expected_sequence_count,
          f"seq_sigs_count_{label}")
    check(result.collection_validation_verdict == "COLLECTION_SATISFIED",
          f"coll_validation_satisfied_{label}")


# ════════════════════════════════════════════════════════════
# SECTION 7: Stability (repeated runs produce same signature)
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Stability ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    r1 = sign_collection_from_contracts(cc)
    r2 = sign_collection_from_contracts(cc)
    check(r1.collection_signature == r2.collection_signature,
          f"stability_sig_identical_{cc.name}")
    check(r1.canonical_form == r2.canonical_form,
          f"stability_canonical_identical_{cc.name}")
    check(r1.verdict == r2.verdict,
          f"stability_verdict_identical_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 8: Wrong Sequence Count → COLLECTION_NOT_SATISFIED
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Wrong Sequence Count ===")

for case in WRONG_COUNT_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = generate_collection_host_png_groups(cc)
    provide = case["provide_count"]
    if provide < len(groups):
        test_groups = groups[:provide]
    else:
        test_groups = groups + (groups[-1],) * (provide - len(groups))
    result = sign_collection(test_groups, cc)
    check(result.verdict == CollSigVerdict.COLLECTION_NOT_SATISFIED,
          f"verdict_not_satisfied_{label}")
    check(result.collection_signature == "",
          f"sig_empty_{label}")


# ════════════════════════════════════════════════════════════
# SECTION 9: Wrong Sequence Order → COLLECTION_NOT_SATISFIED
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Wrong Sequence Order ===")

for case in WRONG_ORDER_CASES:
    label = case["label"]
    cc = FROZEN_COLLECTION_CONTRACTS[case["coll_contract_index"]]
    groups = generate_collection_host_png_groups(cc)
    reversed_groups = tuple(reversed(groups))
    result = sign_collection(reversed_groups, cc)
    check(result.verdict == CollSigVerdict.COLLECTION_NOT_SATISFIED,
          f"verdict_not_satisfied_{label}")
    check(result.collection_signature == "",
          f"sig_empty_on_wrong_order_{label}")
    check(result.collection_validation_verdict in (
        "WRONG_SEQUENCE_ORDER", "SEQUENCE_MATCH_FAILED"),
          f"coll_validation_detected_issue_{label}")


# ════════════════════════════════════════════════════════════
# SECTION 10: Unsupported Collection → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Unsupported Collection ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = CollectionContract(
        name=case["contract_name"],
        expected_sequence_count=2,
        sequence_contract_names=("a", "b"),
    )
    # Use any two host PNG groups
    cc0 = FROZEN_COLLECTION_CONTRACTS[0]
    groups = generate_collection_host_png_groups(cc0)
    result = sign_collection(groups, fake_contract)
    check(result.verdict == CollSigVerdict.UNSUPPORTED,
          f"verdict_unsupported_{label}")
    check(result.collection_signature == "",
          f"sig_empty_unsupported_{label}")


# ════════════════════════════════════════════════════════════
# SECTION 11: Cross-Collection Signature Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Cross-Collection Distinctness ===")

all_coll_sigs = []
for cc in FROZEN_COLLECTION_CONTRACTS:
    r = sign_collection_from_contracts(cc)
    all_coll_sigs.append(r.collection_signature)

check(len(set(all_coll_sigs)) == len(all_coll_sigs),
      "all_collection_signatures_distinct")

# Each pair is different
for i in range(len(all_coll_sigs)):
    for j in range(i + 1, len(all_coll_sigs)):
        check(all_coll_sigs[i] != all_coll_sigs[j],
              f"coll_sig_distinct_{i}_vs_{j}")


# ════════════════════════════════════════════════════════════
# SECTION 12: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: Serialization ===")

for cc in FROZEN_COLLECTION_CONTRACTS:
    r = sign_collection_from_contracts(cc)
    d = r.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{cc.name}")
    check(d["verdict"] == "MATCH", f"to_dict_verdict_{cc.name}")
    check(d["collection_signature"] == r.collection_signature, f"to_dict_sig_{cc.name}")
    check(d["collection_contract_name"] == cc.name, f"to_dict_name_{cc.name}")
    check(d["sequence_count"] == cc.expected_sequence_count, f"to_dict_count_{cc.name}")
    check(isinstance(d["sequence_signatures"], list), f"to_dict_seq_sigs_list_{cc.name}")
    check(len(d["sequence_signatures"]) == cc.expected_sequence_count, f"to_dict_seq_sigs_count_{cc.name}")
    check(d["canonical_form"] == r.canonical_form, f"to_dict_canonical_{cc.name}")
    check(d["expected_signature"] == r.expected_signature, f"to_dict_expected_{cc.name}")
    check(d["version"] == "V1.0", f"to_dict_version_{cc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 13: Expected Signature Baseline Consistency
# ════════════════════════════════════════════════════════════

print("\n=== Section 13: Baseline Consistency ===")

# The expected collection signature should be reproducible from
# the deterministic pipeline
for cc in FROZEN_COLLECTION_CONTRACTS:
    expected = _get_expected_coll_sigs()[cc.name]
    # Rebuild independently
    rebuilt = _build_expected_coll_sig(cc)
    check(expected == rebuilt, f"baseline_reproducible_{cc.name}")

# Verify that sequence signatures used in the collection come from
# the per-sequence expected baseline
seq_expected_sigs = _get_expected_seq_sigs()
for cc in FROZEN_COLLECTION_CONTRACTS:
    cr = validate_collection_from_contracts(cc)
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(cr.sequence_signatures[i] == seq_expected_sigs[seq_name],
              f"seq_sig_from_baseline_{cc.name}_seq{i}")


# ════════════════════════════════════════════════════════════
# SECTION 14: E2E Full Pipeline Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 14: E2E Full Pipeline ===")

# Verify the full chain: host_png_groups → per-sequence recovery →
# per-sequence signature → collection contract → collection signature
for cc in FROZEN_COLLECTION_CONTRACTS:
    # Generate host PNG groups
    groups = generate_collection_host_png_groups(cc)
    check(len(groups) == cc.expected_sequence_count,
          f"e2e_group_count_{cc.name}")

    # Sign from host PNGs
    r = sign_collection(groups, cc)
    check(r.verdict == CollSigVerdict.MATCH,
          f"e2e_verdict_match_{cc.name}")
    check(r.collection_signature == _get_expected_coll_sigs()[cc.name],
          f"e2e_sig_matches_expected_{cc.name}")

    # Verify sequence signatures match per-sequence baseline
    for i, seq_name in enumerate(cc.sequence_contract_names):
        check(r.sequence_signatures[i] == seq_expected_sigs[seq_name],
              f"e2e_seq_sig_baseline_{cc.name}_seq{i}")

    # Canonical form should contain the contract name and seq count
    check(cc.name in r.canonical_form,
          f"e2e_canonical_has_name_{cc.name}")
    check(f"seq_count={cc.expected_sequence_count}" in r.canonical_form,
          f"e2e_canonical_has_count_{cc.name}")


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
