#!/usr/bin/env python3
"""
Standalone test runner for Recovered Set Signature Bridge V1.
No external dependencies — pure Python 3.

Proves that a validated recovered artifact set can be reduced to a
deterministic SHA-256 signature, and that changed content produces
an honest signature mismatch.

This is a narrow deterministic recovered-set identity proof, not
general document fingerprinting or secure provenance.

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

from aurexis_lang.recovered_set_signature_bridge_v1 import (
    SIGNATURE_VERSION, SIGNATURE_FROZEN,
    V1_SIGNATURE_PROFILE, SignatureProfile,
    SignatureVerdict, SignatureResult,
    canonicalize_recovered_set, compute_signature,
    sign_recovered_set, sign_from_png,
    verify_signature, verify_from_png,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    FROZEN_CONTRACTS, ContractVerdict,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import DispatchVerdict


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
check(SIGNATURE_VERSION == "V1.0", "version")
check(SIGNATURE_FROZEN is True, "frozen")
check(isinstance(V1_SIGNATURE_PROFILE, SignatureProfile), "profile_type")
check(V1_SIGNATURE_PROFILE.hash_algorithm == "sha256", "hash_algo")
check(len(IN_BOUNDS_CASES) == 5, "in_bounds_count")
check(len(OUT_OF_BOUNDS_CASES) == 3, "oob_count")


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
# CANONICALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Canonicalization ===")

# Valid canonicalization for each in-bounds case
for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    canonical = canonicalize_recovered_set(recovery_results[idx], contract)
    check(canonical is not None, f"canon_{case['label']}_not_none")
    if canonical:
        check(f"contract={contract.name}" in canonical,
              f"canon_{case['label']}_has_contract")
        check("families=" in canonical, f"canon_{case['label']}_has_families")
        check("verdicts=" in canonical, f"canon_{case['label']}_has_verdicts")
        check(f"version={SIGNATURE_VERSION}" in canonical,
              f"canon_{case['label']}_has_version")

# Empty recovery → None
empty_recovery = MultiLayoutResult(
    verdict=MultiLayoutVerdict.NO_CANDIDATES,
    dispatched_count=0,
    dispatched_families=(),
)
check(
    canonicalize_recovered_set(empty_recovery, FROZEN_CONTRACTS[0]) is None,
    "canon_empty_is_none"
)


# ════════════════════════════════════════════════════════════
# SIGNATURE GENERATION (IN-BOUNDS)
# ════════════════════════════════════════════════════════════

print("\n=== Signature Generation ===")

signatures = []
for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    sr = sign_recovered_set(recovery_results[idx], contract)
    check(sr.verdict == SignatureVerdict.SIGNED, f"sign_{case['label']}_signed")
    check(len(sr.signature) == 64, f"sign_{case['label']}_sha256_len")
    check(sr.contract_name == contract.name, f"sign_{case['label']}_contract")
    signatures.append(sr.signature)

# All signatures are distinct
check(len(set(signatures)) == len(signatures), "all_signatures_unique")


# ════════════════════════════════════════════════════════════
# STABILITY (REPEATED RUNS)
# ════════════════════════════════════════════════════════════

print("\n=== Stability / Determinism ===")

for case in IN_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    sr1 = sign_recovered_set(recovery_results[idx], contract)
    sr2 = sign_recovered_set(recovery_results[idx], contract)
    check(sr1.signature == sr2.signature, f"stable_{case['label']}")

# Full end-to-end from PNG
sr_png1 = sign_from_png(host_pngs[0], FROZEN_CONTRACTS[0])
sr_png2 = sign_from_png(host_pngs[0], FROZEN_CONTRACTS[0])
check(sr_png1.signature == sr_png2.signature, "stable_from_png")
check(sr_png1.signature == signatures[0], "png_matches_direct")


# ════════════════════════════════════════════════════════════
# VERIFICATION (MATCH AND MISMATCH)
# ════════════════════════════════════════════════════════════

print("\n=== Verification ===")

# Correct signature → VERIFIED
for i, case in enumerate(IN_BOUNDS_CASES):
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    vr = verify_signature(recovery_results[idx], contract, signatures[i])
    check(vr.verdict == SignatureVerdict.VERIFIED, f"verify_{case['label']}_ok")

# Wrong signature → MISMATCH
vr_wrong = verify_signature(
    recovery_results[0], FROZEN_CONTRACTS[0], "0" * 64)
check(vr_wrong.verdict == SignatureVerdict.MISMATCH, "verify_wrong_sig_mismatch")

# Signature from layout 0 used to verify layout 1 → MISMATCH
vr_cross = verify_signature(
    recovery_results[1], FROZEN_CONTRACTS[1], signatures[0])
check(vr_cross.verdict == SignatureVerdict.MISMATCH, "verify_cross_layout_mismatch")

# Full end-to-end verification from PNG
vr_png = verify_from_png(host_pngs[0], FROZEN_CONTRACTS[0], signatures[0])
check(vr_png.verdict == SignatureVerdict.VERIFIED, "verify_from_png_ok")


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS (contract not satisfied → no signature)
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds ===")

for case in OUT_OF_BOUNDS_CASES:
    idx = case["layout_index"]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    sr = sign_recovered_set(recovery_results[idx], contract)
    check(
        sr.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED,
        f"oob_{case['label']}_not_signed"
    )
    check(sr.signature == "", f"oob_{case['label']}_empty_sig")

# Empty recovery → no signature
sr_empty = sign_recovered_set(empty_recovery, FROZEN_CONTRACTS[0])
check(
    sr_empty.verdict == SignatureVerdict.CONTRACT_NOT_SATISFIED,
    "oob_empty_not_signed"
)


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

sr_ser = sign_recovered_set(recovery_results[0], FROZEN_CONTRACTS[0])
d = sr_ser.to_dict()
check(d["verdict"] == "SIGNED", "ser_verdict")
check(len(d["signature"]) == 64, "ser_sig_len")
check(d["contract_name"] == "two_horizontal_adj_cont", "ser_contract")
check(d["version"] == "V1.0", "ser_version")
check(isinstance(d["dispatched_families"], list), "ser_families_list")
check(isinstance(d["canonical_form"], str), "ser_canonical_str")
check(len(d["canonical_form"]) > 0, "ser_canonical_nonempty")


# ════════════════════════════════════════════════════════════
# PROFILE VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Profile Validation ===")

check(
    V1_SIGNATURE_PROFILE.canonical_fields == (
        "contract_name", "dispatched_families", "execution_verdicts"),
    "profile_fields"
)
check(V1_SIGNATURE_PROFILE.hash_algorithm == "sha256", "profile_hash")
check(V1_SIGNATURE_PROFILE.version == "V1.0", "profile_version")

# Profile is frozen
immutable = True
try:
    V1_SIGNATURE_PROFILE.version = "hacked"  # type: ignore
    immutable = False
except (AttributeError, TypeError):
    pass
check(immutable, "profile_frozen")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Recovered Set Signature Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
