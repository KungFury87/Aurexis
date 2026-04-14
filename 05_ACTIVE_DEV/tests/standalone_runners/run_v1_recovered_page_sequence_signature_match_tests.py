#!/usr/bin/env python3
"""
Standalone test runner for Recovered Page Sequence Signature Match Bridge V1.
No external dependencies — pure Python 3.

Proves that a computed sequence-level signature can be compared against a
frozen expected-sequence-signature baseline and return an honest deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-sequence match proof, not general
document fingerprinting or secure provenance.

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

from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SEQ_MATCH_VERSION, SEQ_MATCH_FROZEN,
    SeqMatchVerdict, SeqMatchResult,
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
    match_sequence_signature, match_sequence_signature_from_contracts,
    IN_BOUNDS_CASES, WRONG_COUNT_CASES,
    WRONG_ORDER_CASES, UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SEQ_SIG_VERSION, SeqSigVerdict,
    sign_sequence_from_contracts,
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceContract, FROZEN_SEQUENCE_CONTRACTS,
    generate_sequence_host_pngs,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    _get_expected_signatures,
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

check(SEQ_MATCH_VERSION == "V1.0", "seq_match_version_is_v1")
check(SEQ_MATCH_FROZEN is True, "seq_match_frozen_is_true")
check(isinstance(V1_SEQ_MATCH_BASELINE, ExpectedSequenceSignatureBaseline),
      "baseline_is_correct_type")
check(V1_SEQ_MATCH_BASELINE.version == "V1.0", "baseline_version_is_v1")
check(len(V1_SEQ_MATCH_BASELINE.supported_sequence_contracts) == 3,
      "baseline_has_3_contracts")
check(len(IN_BOUNDS_CASES) == 3, "in_bounds_count_3")
check(len(WRONG_COUNT_CASES) == 2, "wrong_count_count_2")
check(len(WRONG_ORDER_CASES) == 2, "wrong_order_count_2")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_count_1")


# ════════════════════════════════════════════════════════════
# SECTION 2: Expected-Sequence-Signature Baseline Validation
# ════════════════════════════════════════════════════════════

print("\n=== Section 2: Baseline Validation ===")

expected_seq_sigs = _get_expected_seq_sigs()
check(len(expected_seq_sigs) == 3, "baseline_has_3_signatures")
check(all(len(v) == 64 for v in expected_seq_sigs.values()),
      "baseline_all_sha256_len")
check(len(set(expected_seq_sigs.values())) == 3, "baseline_all_unique")

# Each frozen sequence contract is in the baseline
for sc in FROZEN_SEQUENCE_CONTRACTS:
    check(V1_SEQ_MATCH_BASELINE.is_supported(sc.name),
          f"baseline_supports_{sc.name}")

# Unknown contract is not in the baseline
check(not V1_SEQ_MATCH_BASELINE.is_supported("nonexistent"),
      "baseline_rejects_unknown")

# Baseline is frozen (immutable)
immutable = True
try:
    V1_SEQ_MATCH_BASELINE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "baseline_frozen_immutable")

# get_expected returns correct values
for sc in FROZEN_SEQUENCE_CONTRACTS:
    sig = V1_SEQ_MATCH_BASELINE.get_expected(sc.name)
    check(sig is not None and len(sig) == 64,
          f"get_expected_valid_{sc.name}")
    check(sig == expected_seq_sigs[sc.name],
          f"get_expected_matches_cache_{sc.name}")

check(V1_SEQ_MATCH_BASELINE.get_expected("unknown") is None,
      "get_expected_unknown_none")


# ════════════════════════════════════════════════════════════
# SECTION 3: Pre-generate Host PNGs for All Sequence Contracts
# ════════════════════════════════════════════════════════════

print("\n=== Section 3: Pre-generating Host PNGs ===")

all_host_pngs = {}
for sc in FROZEN_SEQUENCE_CONTRACTS:
    pngs = generate_sequence_host_pngs(sc)
    all_host_pngs[sc.name] = pngs
    check(len(pngs) == sc.expected_page_count,
          f"pre_gen_count_{sc.name}")
    check(all(isinstance(p, bytes) and len(p) > 0 for p in pngs),
          f"pre_gen_valid_bytes_{sc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 4: In-Bounds Match (All Frozen Contracts → MATCH)
# ════════════════════════════════════════════════════════════

print("\n=== Section 4: In-Bounds Match ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    pngs = all_host_pngs[sc.name]

    mr = match_sequence_signature(pngs, sc)
    check(mr.verdict == SeqMatchVerdict.MATCH,
          f"match_{label}_verdict")
    check(len(mr.computed_sequence_signature) == 64,
          f"match_{label}_sig_len")
    check(mr.computed_sequence_signature == mr.expected_sequence_signature,
          f"match_{label}_sigs_equal")
    check(mr.sequence_contract_name == sc.name,
          f"match_{label}_contract_name")
    check(mr.page_count == sc.expected_page_count,
          f"match_{label}_page_count")
    check(len(mr.page_signatures) == sc.expected_page_count,
          f"match_{label}_page_sigs_count")
    check(mr.sign_verdict in ("MATCH", "SIGNED"),
          f"match_{label}_sign_ok")

# From contracts convenience function
for case in IN_BOUNDS_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    mr = match_sequence_signature_from_contracts(sc)
    check(mr.verdict == SeqMatchVerdict.MATCH,
          f"match_from_contracts_{label}_verdict")
    check(mr.computed_sequence_signature == mr.expected_sequence_signature,
          f"match_from_contracts_{label}_sigs_equal")
    check(mr.sequence_contract_name == sc.name,
          f"match_from_contracts_{label}_name")


# ════════════════════════════════════════════════════════════
# SECTION 5: Stability / Determinism
# ════════════════════════════════════════════════════════════

print("\n=== Section 5: Stability / Determinism ===")

for sc in FROZEN_SEQUENCE_CONTRACTS:
    pngs = all_host_pngs[sc.name]
    mr1 = match_sequence_signature(pngs, sc)
    mr2 = match_sequence_signature(pngs, sc)
    check(mr1.verdict == mr2.verdict,
          f"stable_verdict_{sc.name}")
    check(mr1.computed_sequence_signature == mr2.computed_sequence_signature,
          f"stable_sig_{sc.name}")
    check(mr1.expected_sequence_signature == mr2.expected_sequence_signature,
          f"stable_expected_{sc.name}")

# From contracts determinism
mr_fc1 = match_sequence_signature_from_contracts(FROZEN_SEQUENCE_CONTRACTS[0])
mr_fc2 = match_sequence_signature_from_contracts(FROZEN_SEQUENCE_CONTRACTS[0])
check(mr_fc1.verdict == SeqMatchVerdict.MATCH, "stable_from_contracts_match")
check(mr_fc1.computed_sequence_signature == mr_fc2.computed_sequence_signature,
      "stable_from_contracts_sig")


# ════════════════════════════════════════════════════════════
# SECTION 6: Wrong Page Count → SIGN_FAILED
# ════════════════════════════════════════════════════════════

print("\n=== Section 6: Wrong Page Count ===")

for case in WRONG_COUNT_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    correct_pngs = all_host_pngs[sc.name]
    provide_count = case["provide_page_count"]
    if provide_count < len(correct_pngs):
        test_pngs = correct_pngs[:provide_count]
    else:
        test_pngs = correct_pngs + (correct_pngs[-1],) * (provide_count - len(correct_pngs))

    mr = match_sequence_signature(test_pngs, sc)
    check(mr.verdict == SeqMatchVerdict.SIGN_FAILED,
          f"wrong_count_{label}_verdict")
    check(mr.computed_sequence_signature == "",
          f"wrong_count_{label}_empty_sig")


# ════════════════════════════════════════════════════════════
# SECTION 7: Wrong Page Order → SIGN_FAILED
# ════════════════════════════════════════════════════════════

print("\n=== Section 7: Wrong Page Order ===")

for case in WRONG_ORDER_CASES:
    label = case["label"]
    sc = FROZEN_SEQUENCE_CONTRACTS[case["seq_contract_index"]]
    correct_pngs = all_host_pngs[sc.name]
    reversed_pngs = tuple(reversed(correct_pngs))

    mr = match_sequence_signature(reversed_pngs, sc)
    check(mr.verdict == SeqMatchVerdict.SIGN_FAILED,
          f"wrong_order_{label}_verdict")
    check(mr.computed_sequence_signature == "",
          f"wrong_order_{label}_empty_sig")
    check(mr.sequence_validation_verdict in ("WRONG_PAGE_ORDER", "PAGE_MATCH_FAILED"),
          f"wrong_order_{label}_seq_detected")


# ════════════════════════════════════════════════════════════
# SECTION 8: Unsupported → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Section 8: Unsupported ===")

for case in UNSUPPORTED_CASES:
    label = case["label"]
    fake_contract = SequenceContract(
        name=case["contract_name"],
        expected_page_count=2,
        page_contract_names=("a", "b"),
    )
    # Use any host PNGs
    sc0 = FROZEN_SEQUENCE_CONTRACTS[0]
    pngs = all_host_pngs[sc0.name]
    mr = match_sequence_signature(pngs, fake_contract)
    check(mr.verdict == SeqMatchVerdict.UNSUPPORTED,
          f"unsup_{label}_verdict")
    check(mr.computed_sequence_signature == "",
          f"unsup_{label}_empty_sig")
    check(mr.expected_sequence_signature == "",
          f"unsup_{label}_no_expected")


# ════════════════════════════════════════════════════════════
# SECTION 9: Cross-Contract Signature Distinctness
# ════════════════════════════════════════════════════════════

print("\n=== Section 9: Cross-Contract Distinctness ===")

all_match_sigs = []
for sc in FROZEN_SEQUENCE_CONTRACTS:
    mr = match_sequence_signature_from_contracts(sc)
    all_match_sigs.append(mr.computed_sequence_signature)

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

for sc in FROZEN_SEQUENCE_CONTRACTS:
    mr = match_sequence_signature_from_contracts(sc)
    d = mr.to_dict()
    check(isinstance(d, dict), f"to_dict_is_dict_{sc.name}")
    check(d["verdict"] == "MATCH", f"to_dict_verdict_{sc.name}")
    check(d["computed_sequence_signature"] == mr.computed_sequence_signature,
          f"to_dict_computed_sig_{sc.name}")
    check(d["expected_sequence_signature"] == mr.expected_sequence_signature,
          f"to_dict_expected_sig_{sc.name}")
    check(d["sequence_contract_name"] == sc.name,
          f"to_dict_contract_name_{sc.name}")
    check(d["page_count"] == sc.expected_page_count,
          f"to_dict_page_count_{sc.name}")
    check(isinstance(d["page_signatures"], list),
          f"to_dict_page_sigs_list_{sc.name}")
    check(len(d["page_signatures"]) == sc.expected_page_count,
          f"to_dict_page_sigs_count_{sc.name}")
    check(d["version"] == "V1.0",
          f"to_dict_version_{sc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 11: Baseline Consistency with Underlying Pipeline
# ════════════════════════════════════════════════════════════

print("\n=== Section 11: Baseline Consistency ===")

# The expected sequence signatures in the match baseline should equal
# the expected sequence signatures from the signature bridge
sig_bridge_expected = _get_expected_seq_sigs()
for sc in FROZEN_SEQUENCE_CONTRACTS:
    baseline_sig = V1_SEQ_MATCH_BASELINE.get_expected(sc.name)
    bridge_sig = sig_bridge_expected[sc.name]
    check(baseline_sig == bridge_sig,
          f"baseline_matches_bridge_{sc.name}")

# The match result's computed signature should equal the sign result's signature
for sc in FROZEN_SEQUENCE_CONTRACTS:
    mr = match_sequence_signature_from_contracts(sc)
    sr = sign_sequence_from_contracts(sc)
    check(mr.computed_sequence_signature == sr.sequence_signature,
          f"match_sig_equals_sign_sig_{sc.name}")
    check(mr.page_signatures == sr.page_signatures,
          f"match_page_sigs_equals_sign_page_sigs_{sc.name}")


# ════════════════════════════════════════════════════════════
# SECTION 12: E2E Full Pipeline Verification
# ════════════════════════════════════════════════════════════

print("\n=== Section 12: E2E Full Pipeline ===")

# Verify the full chain: host_png → recovery → dispatch → contract →
# per-page signature → per-page match → sequence contract →
# sequence signature → sequence signature match
for sc in FROZEN_SEQUENCE_CONTRACTS:
    host_pngs = generate_sequence_host_pngs(sc)
    check(len(host_pngs) == sc.expected_page_count,
          f"e2e_host_count_{sc.name}")

    mr = match_sequence_signature(host_pngs, sc)
    check(mr.verdict == SeqMatchVerdict.MATCH,
          f"e2e_verdict_match_{sc.name}")
    check(mr.computed_sequence_signature == sig_bridge_expected[sc.name],
          f"e2e_sig_matches_bridge_expected_{sc.name}")

    # Verify page signatures chain back to single-page baseline
    page_expected = _get_expected_signatures()
    for i, psig in enumerate(mr.page_signatures):
        pname = sc.page_contract_names[i]
        check(psig == page_expected.get(pname, ""),
              f"e2e_page_sig_baseline_{sc.name}_p{i}")

# Wrong count E2E
sc_3page = FROZEN_SEQUENCE_CONTRACTS[1]
pngs_3 = generate_sequence_host_pngs(sc_3page)
mr_wrong = match_sequence_signature(pngs_3[:2], sc_3page)
check(mr_wrong.verdict == SeqMatchVerdict.SIGN_FAILED,
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
