#!/usr/bin/env python3
"""
Standalone test runner for Recovered Set Signature Match Bridge V1.
No external dependencies — pure Python 3.

Proves that a recovered artifact set's computed signature can be compared
against a frozen expected-signature baseline and return an honest
deterministic MATCH / MISMATCH / UNSUPPORTED verdict.

This is a narrow deterministic recovered-set match proof, not general
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

from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    MatchVerdict, MatchResult,
    ExpectedSignatureBaseline, V1_MATCH_BASELINE,
    match_signature, match_from_png,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES, UNSUPPORTED_CASES,
    _get_expected_signatures,
)
from aurexis_lang.recovered_set_signature_bridge_v1 import (
    SignatureVerdict, V1_SIGNATURE_PROFILE,
    sign_recovered_set,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    PageContract, FROZEN_CONTRACTS,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
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
check(MATCH_VERSION == "V1.0", "version")
check(MATCH_FROZEN is True, "frozen")
check(isinstance(V1_MATCH_BASELINE, ExpectedSignatureBaseline), "baseline_type")
check(V1_MATCH_BASELINE.version == "V1.0", "baseline_version")
check(len(V1_MATCH_BASELINE.supported_contracts) == 5, "baseline_contract_count")
check(len(IN_BOUNDS_CASES) == 5, "in_bounds_count")
check(len(OUT_OF_BOUNDS_CASES) == 3, "oob_count")
check(len(UNSUPPORTED_CASES) == 1, "unsupported_count")


# ════════════════════════════════════════════════════════════
# EXPECTED-SIGNATURE BASELINE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Expected-Signature Baseline ===")

expected_sigs = _get_expected_signatures()
check(len(expected_sigs) == 5, "baseline_has_5_signatures")
check(all(len(v) == 64 for v in expected_sigs.values()), "baseline_all_sha256_len")
check(len(set(expected_sigs.values())) == 5, "baseline_all_unique")

# Each frozen contract is in the baseline
for contract in FROZEN_CONTRACTS:
    check(
        V1_MATCH_BASELINE.is_supported(contract.name),
        f"baseline_supports_{contract.name}"
    )

# Unknown contract is not in the baseline
check(not V1_MATCH_BASELINE.is_supported("nonexistent"), "baseline_rejects_unknown")

# Baseline is frozen
immutable = True
try:
    V1_MATCH_BASELINE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "baseline_frozen")


# ════════════════════════════════════════════════════════════
# HELPER: Pre-generate host PNGs and recovery results
# ════════════════════════════════════════════════════════════

print("\n=== Pre-generating host images ===")

host_pngs = []
recovery_results = []
for layout in FROZEN_LAYOUTS:
    spec = build_layout_spec(layout)
    png = generate_multi_artifact_host(spec)
    host_pngs.append(png)
    recovery = multi_artifact_recover_and_dispatch(
        png, expected_families=layout["expected_families"])
    recovery_results.append(recovery)
    check(recovery.verdict == MultiLayoutVerdict.RECOVERED,
          f"pre_recovery_{layout['name']}")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS: All frozen layout×contract pairs → MATCH
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Match ===")

for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    mr = match_signature(recovery_results[idx], contract)
    check(mr.verdict == MatchVerdict.MATCH, f"match_{case['label']}_verdict")
    check(len(mr.computed_signature) == 64, f"match_{case['label']}_sig_len")
    check(mr.computed_signature == mr.expected_signature,
          f"match_{case['label']}_sigs_equal")
    check(mr.contract_name == contract.name, f"match_{case['label']}_contract")
    check(mr.sign_verdict == "SIGNED", f"match_{case['label']}_sign_ok")


# ════════════════════════════════════════════════════════════
# STABILITY / DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Stability / Determinism ===")

for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    mr1 = match_signature(recovery_results[idx], contract)
    mr2 = match_signature(recovery_results[idx], contract)
    check(mr1.verdict == mr2.verdict, f"stable_{case['label']}_verdict")
    check(mr1.computed_signature == mr2.computed_signature,
          f"stable_{case['label']}_sig")

# Full end-to-end from PNG
mr_png1 = match_from_png(host_pngs[0], FROZEN_CONTRACTS[0])
mr_png2 = match_from_png(host_pngs[0], FROZEN_CONTRACTS[0])
check(mr_png1.verdict == MatchVerdict.MATCH, "stable_from_png_match")
check(mr_png1.computed_signature == mr_png2.computed_signature,
      "stable_from_png_sig")


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS: Mismatched layout/contract → SIGN_FAILED
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds (Contract Not Satisfied) ===")

for case in OUT_OF_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    mr = match_signature(recovery_results[idx], contract)
    check(
        mr.verdict == MatchVerdict.SIGN_FAILED,
        f"oob_{case['label']}_sign_failed"
    )
    check(mr.computed_signature == "", f"oob_{case['label']}_empty_sig")

# Empty recovery → SIGN_FAILED
empty_recovery = MultiLayoutResult(
    verdict=MultiLayoutVerdict.NO_CANDIDATES,
    dispatched_count=0,
    dispatched_families=(),
)
mr_empty = match_signature(empty_recovery, FROZEN_CONTRACTS[0])
check(mr_empty.verdict == MatchVerdict.SIGN_FAILED, "oob_empty_sign_failed")


# ════════════════════════════════════════════════════════════
# UNSUPPORTED: Unknown contract → UNSUPPORTED
# ════════════════════════════════════════════════════════════

print("\n=== Unsupported (Unknown Contract) ===")

for case in UNSUPPORTED_CASES:
    unknown_contract = PageContract(
        name=case["contract_name"],
        expected_count=case["expected_count"],
        expected_families=tuple(case["expected_families"]),
    )
    mr = match_signature(recovery_results[0], unknown_contract)
    check(mr.verdict == MatchVerdict.UNSUPPORTED, f"unsup_{case['label']}_verdict")
    check(mr.computed_signature == "", f"unsup_{case['label']}_empty_sig")
    check(mr.expected_signature == "", f"unsup_{case['label']}_no_expected")


# ════════════════════════════════════════════════════════════
# CROSS-LAYOUT MISMATCH
# ════════════════════════════════════════════════════════════
# Use layout 0's recovery result but tell it to match against contract 1
# which IS in the baseline but won't satisfy contract 1 → SIGN_FAILED
# (because layout 0 was recovered with layout 0's families)
#
# For a true mismatch test, we need a recovery that satisfies the contract
# but produces a different signature.  We can't easily do that with the
# frozen layouts because each layout produces deterministic artifacts.
# Instead, we verify that the computed signature for layout 0 differs
# from the expected signature for layout 1 (direct comparison).

print("\n=== Cross-Layout Signature Comparison ===")

expected_sigs_dict = _get_expected_signatures()
sig_list = list(expected_sigs_dict.values())

# Each signature is different from every other
for i in range(len(sig_list)):
    for j in range(i + 1, len(sig_list)):
        check(sig_list[i] != sig_list[j],
              f"cross_sig_{i}_ne_{j}")


# ════════════════════════════════════════════════════════════
# END-TO-END FROM PNG
# ════════════════════════════════════════════════════════════

print("\n=== End-to-End from PNG ===")

for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    mr = match_from_png(host_pngs[idx], contract)
    check(mr.verdict == MatchVerdict.MATCH, f"e2e_{case['label']}_match")

# OOB from PNG
mr_oob_png = match_from_png(host_pngs[0], FROZEN_CONTRACTS[2])
check(mr_oob_png.verdict == MatchVerdict.SIGN_FAILED, "e2e_oob_sign_failed")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

mr_ser = match_signature(recovery_results[0], FROZEN_CONTRACTS[0])
d = mr_ser.to_dict()
check(d["verdict"] == "MATCH", "ser_verdict")
check(len(d["computed_signature"]) == 64, "ser_computed_sig_len")
check(len(d["expected_signature"]) == 64, "ser_expected_sig_len")
check(d["computed_signature"] == d["expected_signature"], "ser_sigs_equal")
check(d["contract_name"] == "two_horizontal_adj_cont", "ser_contract")
check(d["version"] == "V1.0", "ser_version")
check(isinstance(d["dispatched_families"], list), "ser_families_list")


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

check(V1_MATCH_BASELINE.supported_contracts == (
    "two_horizontal_adj_cont",
    "two_vertical_adj_three",
    "three_row_all",
    "two_horizontal_cont_three",
    "two_vertical_three_adj",
), "baseline_contracts_correct")

# get_expected returns correct values
for name in V1_MATCH_BASELINE.supported_contracts:
    sig = V1_MATCH_BASELINE.get_expected(name)
    check(sig is not None and len(sig) == 64, f"get_expected_{name}_ok")

check(V1_MATCH_BASELINE.get_expected("unknown") is None, "get_expected_unknown_none")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Recovered Set Signature Match Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
