#!/usr/bin/env python3
"""
Standalone test runner for Artifact Set Contract Bridge V1.
No external dependencies — pure Python 3.

Proves that a recovered ordered set of artifacts from a multi-artifact
host image can be checked against an explicit page-level contract
with honest acceptance or rejection.

This is a narrow deterministic recovered-set proof, not general
document intelligence or open-ended schema validation.

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

from aurexis_lang.artifact_set_contract_bridge_v1 import (
    CONTRACT_VERSION, CONTRACT_FROZEN,
    V1_CONTRACT_PROFILE, ContractProfile,
    PageContract, FROZEN_CONTRACTS,
    ContractVerdict, ContractResult,
    validate_contract, validate_contract_from_png,
    find_matching_contract,
    IN_BOUNDS_CASES, OUT_OF_BOUNDS_CASES,
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
check(CONTRACT_VERSION == "V1.0", "version")
check(CONTRACT_FROZEN is True, "frozen")
check(isinstance(V1_CONTRACT_PROFILE, ContractProfile), "profile_type")
check(len(FROZEN_CONTRACTS) == 5, "contract_count")
check(len(IN_BOUNDS_CASES) == 5, "in_bounds_count")
check(len(OUT_OF_BOUNDS_CASES) == 4, "oob_count")


# ════════════════════════════════════════════════════════════
# CONTRACT STRUCTURE
# ════════════════════════════════════════════════════════════

print("\n=== Contract Structure ===")

# All contracts have unique names
names = [c.name for c in FROZEN_CONTRACTS]
check(len(names) == len(set(names)), "unique_names")

# All contracts have positive expected_count
check(all(c.expected_count >= 2 for c in FROZEN_CONTRACTS), "min_count_2")

# All expected_families match expected_count
check(
    all(len(c.expected_families) == c.expected_count for c in FROZEN_CONTRACTS),
    "families_match_count"
)

# Contract families use only known artifact families
valid_families = {"adjacent_pair", "containment", "three_regions"}
all_valid = True
for c in FROZEN_CONTRACTS:
    for f in c.expected_families:
        if f not in valid_families:
            all_valid = False
check(all_valid, "all_families_known")

# Frozen dataclass
try:
    FROZEN_CONTRACTS[0].name  # read OK
    immutable = True
    try:
        FROZEN_CONTRACTS[0].name = "hacked"  # type: ignore
        immutable = False
    except (AttributeError, TypeError):
        pass
except Exception:
    immutable = False
check(immutable, "contract_frozen")


# ════════════════════════════════════════════════════════════
# IN-BOUNDS CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== In-Bounds Contract Validation ===")

for case in IN_BOUNDS_CASES:
    label = case["label"]
    layout = FROZEN_LAYOUTS[case["layout_index"]]
    contract = FROZEN_CONTRACTS[case["contract_index"]]

    # Generate host image
    spec = build_layout_spec(layout)
    png = generate_multi_artifact_host(spec)

    # Full end-to-end validation
    cr = validate_contract_from_png(png, contract)

    check(
        cr.verdict == ContractVerdict.SATISFIED,
        f"{label}_satisfied"
    )
    check(
        cr.recovered_count == contract.expected_count,
        f"{label}_count_match"
    )
    check(
        cr.recovered_families == contract.expected_families,
        f"{label}_families_match"
    )
    check(
        cr.contract_name == contract.name,
        f"{label}_name_match"
    )


# ════════════════════════════════════════════════════════════
# OUT-OF-BOUNDS CONTRACT VALIDATION
# ════════════════════════════════════════════════════════════

print("\n=== Out-of-Bounds Contract Validation ===")

for case in OUT_OF_BOUNDS_CASES:
    label = case["label"]
    layout = FROZEN_LAYOUTS[case["layout_index"]]
    contract = FROZEN_CONTRACTS[case["contract_index"]]
    expected_v = case["expected_verdict"]

    spec = build_layout_spec(layout)
    png = generate_multi_artifact_host(spec)
    cr = validate_contract_from_png(png, contract)

    check(
        cr.verdict.value == expected_v,
        f"oob_{label}_verdict"
    )
    check(
        cr.verdict != ContractVerdict.SATISFIED,
        f"oob_{label}_not_satisfied"
    )


# ════════════════════════════════════════════════════════════
# RECOVERY FAILURE
# ════════════════════════════════════════════════════════════

print("\n=== Recovery Failure ===")

# Validate with an empty recovery result → RECOVERY_FAILED
empty_recovery = MultiLayoutResult(
    verdict=MultiLayoutVerdict.NO_CANDIDATES,
    expected_count=0,
    found_count=0,
    dispatched_count=0,
    dispatched_families=(),
)
contract_for_empty = FROZEN_CONTRACTS[0]
cr_empty = validate_contract(empty_recovery, contract_for_empty)
check(cr_empty.verdict == ContractVerdict.RECOVERY_FAILED, "empty_recovery_failed")
check(cr_empty.recovered_count == 0, "empty_recovery_count_zero")

# Partial recovery (some dispatched but not all) → VIOLATED_COUNT
partial_recovery = MultiLayoutResult(
    verdict=MultiLayoutVerdict.PARTIAL_RECOVERY,
    expected_count=2,
    found_count=2,
    dispatched_count=1,
    dispatched_families=("adjacent_pair",),
)
contract_for_partial = FROZEN_CONTRACTS[0]  # expects 2
cr_partial = validate_contract(partial_recovery, contract_for_partial)
check(cr_partial.verdict == ContractVerdict.VIOLATED_COUNT, "partial_violated_count")


# ════════════════════════════════════════════════════════════
# FIND MATCHING CONTRACT
# ════════════════════════════════════════════════════════════

print("\n=== Find Matching Contract ===")

# Recover from each frozen layout and find its matching contract
for i, layout in enumerate(FROZEN_LAYOUTS):
    spec = build_layout_spec(layout)
    png = generate_multi_artifact_host(spec)
    recovery = multi_artifact_recover_and_dispatch(
        png, expected_families=layout["expected_families"])
    matched = find_matching_contract(recovery)
    check(matched is not None, f"layout_{i}_finds_contract")
    if matched is not None:
        check(
            matched.name == FROZEN_CONTRACTS[i].name,
            f"layout_{i}_correct_contract"
        )

# Empty recovery finds no contract
empty_match = find_matching_contract(empty_recovery)
check(empty_match is None, "empty_no_contract_match")


# ════════════════════════════════════════════════════════════
# DETERMINISM
# ════════════════════════════════════════════════════════════

print("\n=== Determinism ===")

layout_det = FROZEN_LAYOUTS[0]
contract_det = FROZEN_CONTRACTS[0]
spec_det = build_layout_spec(layout_det)
png_det = generate_multi_artifact_host(spec_det)

cr1 = validate_contract_from_png(png_det, contract_det)
cr2 = validate_contract_from_png(png_det, contract_det)
check(cr1.verdict == cr2.verdict, "det_verdict")
check(cr1.recovered_families == cr2.recovered_families, "det_families")
check(cr1.recovered_count == cr2.recovered_count, "det_count")
check(cr1.contract_name == cr2.contract_name, "det_name")


# ════════════════════════════════════════════════════════════
# SERIALIZATION
# ════════════════════════════════════════════════════════════

print("\n=== Serialization ===")

cr_ser = validate_contract_from_png(png_det, contract_det)
d = cr_ser.to_dict()
check(d["verdict"] == "SATISFIED", "ser_verdict")
check(d["contract_name"] == "two_horizontal_adj_cont", "ser_name")
check(d["expected_count"] == 2, "ser_expected_count")
check(d["recovered_count"] == 2, "ser_recovered_count")
check(d["version"] == "V1.0", "ser_version")
check(isinstance(d["expected_families"], list), "ser_expected_list")
check(isinstance(d["recovered_families"], list), "ser_recovered_list")


# ════════════════════════════════════════════════════════════
# CROSS-VALIDATION: EVERY LAYOUT × EVERY CONTRACT
# ════════════════════════════════════════════════════════════

print("\n=== Cross-Validation Matrix ===")

# Generate all host images once
host_pngs = []
for layout in FROZEN_LAYOUTS:
    spec = build_layout_spec(layout)
    host_pngs.append(generate_multi_artifact_host(spec))

# Each layout should ONLY satisfy its matching contract
for i in range(len(FROZEN_LAYOUTS)):
    for j in range(len(FROZEN_CONTRACTS)):
        cr = validate_contract_from_png(host_pngs[i], FROZEN_CONTRACTS[j])
        if i == j:
            check(
                cr.verdict == ContractVerdict.SATISFIED,
                f"cross_{i}_{j}_satisfied"
            )
        else:
            check(
                cr.verdict != ContractVerdict.SATISFIED,
                f"cross_{i}_{j}_not_satisfied"
            )


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════

print()
print("=" * 60)
total = passed + failed
print(f"Artifact Set Contract Bridge V1: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
