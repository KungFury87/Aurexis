#!/usr/bin/env python3
"""
Standalone test runner for Recovered Page Sequence Signature Bridge V1.
No external dependencies — pure Python 3.

Proves that a validated ordered page sequence can be reduced to a
deterministic sequence-level signature/fingerprint, and that changes
in page order, page content, or page count produce honest signature
mismatch or validation failure.

This is a narrow deterministic recovered-sequence identity proof, not
general document fingerprinting or secure provenance.

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

from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SEQ_SIG_VERSION, SEQ_SIG_FROZEN,
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    SeqSigVerdict, SeqSigResult,
    canonicalize_sequence, compute_sequence_signature,
    sign_sequence, sign_sequence_from_contracts,
    _get_expected_seq_sigs, _build_expected_seq_sig,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SEQUENCE_VERSION, SEQUENCE_FROZEN,
    SequenceVerdict, SequenceContract, SequenceProfile,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    validate_sequence_from_contracts,
    generate_sequence_host_pngs,
    _get_sequence_expected,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MatchVerdict, V1_MATCH_BASELINE, _get_expected_signatures,
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
# SECTION 1: Module Constants
# ════════════════════════════════════════════════════════════

print("=== Section 1: Module Constants ===")

check(SEQ_SIG_VERSION == "V1.0", "seq_sig_version_is_v1")
check(SEQ_SIG_FROZEN is True, "seq_sig_frozen_is_true")
check(isinstance(V1_SEQ_SIG_PROFILE, SequenceSignatureProfile), "profile_is_correct_type")
check(V1_SEQ_SIG_PROFILE.hash_algorithm == "sha256", "hash_algorithm_is_sha256")
check(V1_SEQ_SIG_PROFILE.version == "V1.0", "profile_version_is_v1")
check(len(V1_SEQ_SIG_PROFILE.canonical_fields) == 3, "canonical_fields_count_3")
check("sequence_contract_name" in V1_SEQ_SIG_PROFILE.canonical_fields, "field_seq_contract_name")
check("page_count" in V1_SEQ_SIG_PROFILE.canonical_fields, "field_page_count")
check("ordered_page_signatures" in V1_SEQ_SIG_PROFILE.canonical_fields, "field_ordered_page_sigs")

# ════════════════════════════════════════════════════════════
# SECTION 2: Frozen Sequence Contracts Available
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Frozen Sequence Contracts ===")

check(len(FROZEN_SEQUENCE_CONTRACTS) == 3, "three_frozen_seq_contracts")
check(FROZEN_SEQUENCE_CONTRACTS[0].name == "two_page_horizontal_vertical", "seq_contract_0_name")
check(FROZEN_SEQUENCE_CONTRACTS[1].name == "three_page_all_families", "seq_contract_1_name")
check(FROZEN_SEQUENCE_CONTRACTS[2].name == "two_page_mixed_reversed", "seq_contract_2_name")
check(FROZEN_SEQUENCE_CONTRACTS[0].expected_page_count == 2, "seq_contract_0_count_2")
check(FROZEN_SEQUENCE_CONTRACTS[1].expected_page_count == 3, "seq_contract_1_count_3")
check(FROZEN_SEQUENCE_CONTRACTS[2].expected_page_count == 2, "seq_contract_2_count_2")

# ════════════════════════════════════════════════════════════
# SECTION 3: Canonicalization Tests
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Canonicalization ===")

# Valid canonicalization
dummy_sigs = ("a" * 64, "b" * 64)
canon = canonicalize_sequence("test_contract", 2, dummy_sigs)
check(canon is not None, "canonicalize_valid_returns_string")
check("seq_contract=test_contract" in canon, "canon_has_contract_name")
check("page_count=2" in canon, "canon_has_page_count")
check("page_sigs=" in canon, "canon_has_page_sigs")
check("version=V1.0" in canon, "canon_has_version")
check(("a" * 64) in canon, "canon_has_first_sig")
check(("b" * 64) in canon, "canon_has_second_sig")

# Count mismatch
canon_bad_count = canonicalize_sequence("test", 3, dummy_sigs)
check(canon_bad_count is None, "canonicalize_count_mismatch_returns_none")

# Empty signatures
canon_empty = canonicalize_sequence("test", 0, ())
check(canon_empty is None, "canonicalize_empty_returns_none")

# Short signature (not 64 chars)
canon_short = canonicalize_sequence("test", 1, ("abc",))
check(canon_short is None, "canonicalize_short_sig_returns_none")

# Empty string signature
canon_empty_sig = canonicalize_sequence("test", 1, ("",))
check(canon_empty_sig is None, "canonicalize_empty_sig_returns_none")

# Determinism: same inputs → same output
canon2 = canonicalize_sequence("test_contract", 2, dummy_sigs)
check(canon == canon2, "canonicalize_deterministic")

# Different inputs → different output
diff_sigs = ("c" * 64, "d" * 64)
canon_diff = canonicalize_sequence("test_contract", 2, diff_sigs)
check(canon_diff != canon, "canonicalize_different_sigs_different_output")

# Different contract name → different output
canon_diff_name = canonicalize_sequence("other_contract", 2, dummy_sigs)
check(canon_diff_name != canon, "canonicalize_different_name_different_output")

# Three pages
three_sigs = ("a" * 64, "b" * 64, "c" * 64)
canon_three = canonicalize_sequence("test_3", 3, three_sigs)
check(canon_three is not None, "canonicalize_three_pages_works")
check("page_count=3" in canon_three, "canon_three_has_count_3")

# ════════════════════════════════════════════════════════════
# SECTION 4: Signature Computation Tests
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: Signature Computation ===")

sig = compute_sequence_signature("test canonical form")
check(isinstance(sig, str), "compute_returns_string")
check(len(sig) == 64, "compute_returns_64_chars")
check(sig == hashlib.sha256(b"test canonical form").hexdigest(), "compute_matches_stdlib_sha256")

# Determinism
sig2 = compute_sequence_signature("test canonical form")
check(sig == sig2, "compute_deterministic")

# Different input → different output
sig3 = compute_sequence_signature("different canonical form")
check(sig3 != sig, "compute_different_input_different_sig")

# ════════════════════════════════════════════════════════════
# SECTION 5: Expected Sequence Signatures
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Expected Sequence Signatures ===")

expected_sigs = _get_expected_seq_sigs()
check(isinstance(expected_sigs, dict), "expected_sigs_is_dict")
check(len(expected_sigs) == 3, "expected_sigs_has_3_entries")

for sc in FROZEN_SEQUENCE_CONTRACTS:
    check(sc.name in expected_sigs, f"expected_sig_exists_{sc.name}")
    sig = expected_sigs[sc.name]
    check(isinstance(sig, str), f"expected_sig_is_str_{sc.name}")
    check(len(sig) == 64, f"expected_sig_64_chars_{sc.name}")

# All expected sigs are distinct
all_sigs = list(expected_sigs.values())
check(len(set(all_sigs)) == len(all_sigs), "expected_sigs_all_distinct")

# Idempotent: calling again returns same values
expected_sigs2 = _get_expected_seq_sigs()
for sc in FROZEN_SEQUENCE_CONTRACTS:
    check(expected_sigs[sc.name] == expected_sigs2[sc.name],
          f"expected_sig_idempotent_{sc.name}")

# ════════════════════════════════════════════════════════════
# SECTION 6: End-to-End In-Bounds Signing (MATCH)
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: In-Bounds Signing ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    result = sign_sequence_from_contracts(sc)

    check(result.verdict == SeqSigVerdict.MATCH,
          f"verdict_match_{label}")
    check(result.sequence_signature != "",
          f"sig_nonempty_{label}")
    check(len(result.sequence_signature) == 64,
          f"sig_64_chars_{label}")
    check(result.canonical_form != "",
          f"canonical_nonempty_{label}")
    check(result.expected_signature != "",
          f"expected_nonempty_{label}")
    check(result.sequence_signature == result.expected_signature,
          f"sig_equals_expected_{label}")
    check(result.sequence_contract_name == sc.name,
          f"contract_name_correct_{label}")
    check(result.page_count == sc.expected_page_count,
          f"page_count_correct_{label}")
    check(len(result.page_signatures) == sc.expected_page_count,
          f"page_sigs_count_{label}")
    check(result.sequence_validation_verdict == "SEQUENCE_SATISFIED",
          f"seq_validation_satisfied_{label}")

# ════════════════════════════════════════════════════════════
# SECTION 7: Stability (repeated runs produce same signature)
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Stability ===")

for sc in FROZEN_SEQUENCE_CONTRACTS:
    r1 = sign_sequence_from_contracts(sc)
    r2 = sign_sequence_from_contracts(sc)
    check(r1.sequence_signature == r2.sequence_signature,
          f"stability_sig_identical_{sc.name}")
    check(r1.canonical_form == r2.canonical_form,
          f"stability_canonical_identical_{sc.name}")
    check(r1.verdict == r2.verdict,
          f"stability_verdict_identical_{sc.name}")

# ════════════════════════════════════════════════════════════
# SECTION 8: Wrong Page Count → SEQUENCE_NOT_SATISFIED
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Wrong Page Count ===")

for case in WRONG_COUNT_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    # Generate host PNGs from a different contract to get wrong count
    all_pngs = generate_sequence_host_pngs(sc)
    # Take only the requested number of pages
    provide_count = case["provide_page_count"]
    if provide_count < len(all_pngs):
        test_pngs = all_pngs[:provide_count]
    else:
        # Need more pages — duplicate the last one
        test_pngs = all_pngs + (all_pngs[-1],) * (provide_count - len(all_pngs))

    result = sign_sequence(test_pngs, sc)
    check(result.verdict == SeqSigVerdict.SEQUENCE_NOT_SATISFIED,
          f"verdict_not_satisfied_{label}")
    check(result.sequence_signature == "",
          f"sig_empty_{label}")

# ════════════════════════════════════════════════════════════
# SECTION 9: Wrong Page Order → SEQUENCE_NOT_SATISFIED
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Wrong Page Order ===")

for case in WRONG_ORDER_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    pngs = generate_sequence_host_pngs(sc)
    reversed_pngs = tuple(reversed(pngs))
    result = sign_sequence(reversed_pngs, sc)
    check(result.verdict == SeqSigVerdict.SEQUENCE_NOT_SATISFIED,
          f"verdict_not_satisfied_{label}")
    check(result.sequence_signature == "",
          f"sig_empty_on_wrong_order_{label}")
    # The underlying sequence validation should have detected the issue
    check(result.sequence_validation_verdict in ("WRONG_PAGE_ORDER", "PAGE_MATCH_FAILED"),
          f"seq_validation_detected_issue_{label}")

# ════════════════════════════════════════════════════════════
# SECTION 10: Unsupported Sequence → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Section 10: Unsupported Sequence ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = SequenceContract(
        name=case["contract_name"],
        expected_page_count=2,
        page_contract_names=("a", "b"),
    )
    # Use any two host PNGs
    sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
    pngs = generate_sequence_host_pngs(sc0)
    result = sign_sequence(pngs, fake_contract)
    check(result.verdict == SeqSigVerdict.UNSUPPORTED,
          f"verdict_unsupported_{label}")
    check(result.sequence_signature == "",
          f"sig_empty_unsupported_{label}")

# ════════════════════════════════════════════════════════════
# SECTION 11: Cross-Contract Signature Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Cross-Contract Distinctness ===")

all_seq_sigs = []
for sc in FROZEN_SEQUENCE_CONTRACTS:
    r = sign_sequence_from_contracts(sc)
    all_seq_sigs.append(r.sequence_signature)

check(len(set(all_seq_sigs)) == len(all_seq_sigs),
      "all_sequence_signatures_distinct")

# Each pair is different
for i in range(len(all_seq_sigs)):
    for j in range(i + 1, len(all_seq_sigs)):
        check(all_seq_sigs[i] != all_seq_sigs[j],
              f"sig_distinct_{i}_vs_{j}")

# ════════════════════════════════════════════════════════════
# SECTION 12: Serialization (to_dict)
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: Serialization ===")

for sc in FROZEN_SEQUENCE_CONTRACTS:
    r = sign_sequence_from_contracts(sc)
    d = r.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{sc.name}")
    check(d["verdict"] == "MATCH", f"to_dict_verdict_{sc.name}")
    check(d["sequence_signature"] == r.sequence_signature, f"to_dict_sig_{sc.name}")
    check(d["sequence_contract_name"] == sc.name, f"to_dict_name_{sc.name}")
    check(d["page_count"] == sc.expected_page_count, f"to_dict_count_{sc.name}")
    check(isinstance(d["page_signatures"], list), f"to_dict_page_sigs_list_{sc.name}")
    check(len(d["page_signatures"]) == sc.expected_page_count, f"to_dict_page_sigs_count_{sc.name}")

# ════════════════════════════════════════════════════════════
# SECTION 13: Expected Signature Baseline Consistency
# ════════════════════════════════════════════════════════════

print("\n=== Section 13: Baseline Consistency ===")

# The expected sequence signature should be reproducible from
# the deterministic pipeline
for sc in FROZEN_SEQUENCE_CONTRACTS:
    expected = _get_expected_seq_sigs()[sc.name]
    # Rebuild independently
    rebuilt = _build_expected_seq_sig(sc)
    check(expected == rebuilt, f"baseline_reproducible_{sc.name}")

# Verify page-level signatures used in the sequence come from
# the single-page baseline
page_expected = _get_expected_signatures()
seq_expected = _get_sequence_expected()
for sc in FROZEN_SEQUENCE_CONTRACTS:
    seq_page_sigs = seq_expected[sc.name]
    for i, pname in enumerate(sc.page_contract_names):
        check(seq_page_sigs[i] == page_expected.get(pname, ""),
              f"page_sig_from_baseline_{sc.name}_page{i}")

# ════════════════════════════════════════════════════════════
# SECTION 14: E2E Full Pipeline Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 14: E2E Full Pipeline ===")

# Verify the full chain: host_png → recovery → dispatch → contract →
# per-page signature → per-page match → sequence contract → sequence signature
for sc in FROZEN_SEQUENCE_CONTRACTS:
    # Generate host PNGs
    host_pngs = generate_sequence_host_pngs(sc)
    check(len(host_pngs) == sc.expected_page_count,
          f"e2e_host_count_{sc.name}")

    # Sign from host PNGs
    r = sign_sequence(host_pngs, sc)
    check(r.verdict == SeqSigVerdict.MATCH,
          f"e2e_verdict_match_{sc.name}")
    check(r.sequence_signature == _get_expected_seq_sigs()[sc.name],
          f"e2e_sig_matches_expected_{sc.name}")

    # Verify page signatures match single-page baseline
    for i, psig in enumerate(r.page_signatures):
        pname = sc.page_contract_names[i]
        check(psig == page_expected.get(pname, ""),
              f"e2e_page_sig_baseline_{sc.name}_p{i}")

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
