#!/usr/bin/env python3
"""
Aurexis Core — Cross-Branch Compatibility Contract Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.cross_branch_compatibility_contract_bridge_v1 import (
    COMPATIBILITY_VERSION, COMPATIBILITY_FROZEN,
    CompatibilityVerdict, CompatibilityResult,
    CompatibilityRule, CompatibilityProfile,
    V1_COMPATIBILITY_PROFILE, FROZEN_RULES,
    check_rule, check_all_compatibility,
    make_incompatible_result, make_error_result,
    EXPECTED_RULE_COUNT, EXPECTED_COMPATIBLE_COUNT,
    VIOLATION_CASE_COUNT,
)

PASS_COUNT = 0
FAIL_COUNT = 0

def section(name):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")

def check(cond, label):
    global PASS_COUNT, FAIL_COUNT
    s = "PASS" if cond else "FAIL"
    if cond: PASS_COUNT += 1
    else: FAIL_COUNT += 1
    print(f"  [{s}] {label}")

section("1. Module Version and Frozen State")
check(COMPATIBILITY_VERSION == "V1.0", "Version V1.0")
check(COMPATIBILITY_FROZEN is True, "Module frozen")

section("2. Expected Counts")
check(EXPECTED_RULE_COUNT == 12, f"12 rules expected (got {EXPECTED_RULE_COUNT})")
check(EXPECTED_COMPATIBLE_COUNT == 12, "All 12 should be compatible")
check(VIOLATION_CASE_COUNT == 2, "2 violation case makers")

section("3. Profile Configuration")
check(V1_COMPATIBILITY_PROFILE.rule_count == 12, f"Profile has 12 rules (got {V1_COMPATIBILITY_PROFILE.rule_count})")
check(V1_COMPATIBILITY_PROFILE.version == "V1.0", "Profile version V1.0")
check(V1_COMPATIBILITY_PROFILE.frozen is True, "Profile frozen")

section("4. Rule Names Unique")
names = [r.name for r in FROZEN_RULES]
check(len(set(names)) == len(names), "All rule names unique")
check(len(names) == 12, "12 rule names")

section("5. Run All Compatibility Checks")
results = check_all_compatibility()
check(len(results) == 12, f"12 results (got {len(results)})")
compatible = [r for r in results if r.verdict == CompatibilityVerdict.COMPATIBLE]
check(len(compatible) == 12, f"All 12 COMPATIBLE (got {len(compatible)})")

section("6. Individual Rule Results")
for r in results:
    check(r.passed, f"{r.rule_name}: {r.verdict.value}")

section("7. Module Namespace Check Detail")
ns_result = [r for r in results if r.rule_name == "module_namespace_no_collision"][0]
check("52" in ns_result.detail or "unique" in ns_result.detail.lower(), "Namespace check mentions module count")

section("8. VSA Auxiliary Check Detail")
vsa_result = [r for r in results if r.rule_name == "vsa_auxiliary_precedence"][0]
check("auxiliary" in vsa_result.detail.lower() or "frozen" in vsa_result.detail.lower(), "VSA check confirms auxiliary status")

section("9. Fabricated Incompatible Result")
inc = make_incompatible_result("test_rule", "Test failure")
check(inc.verdict == CompatibilityVerdict.INCOMPATIBLE, "Fabricated result is INCOMPATIBLE")
check(inc.rule_name == "test_rule", "Fabricated rule name correct")
check(not inc.passed, "Fabricated result does not pass")

section("10. Fabricated Error Result")
err = make_error_result("test_error", "Test error")
check(err.verdict == CompatibilityVerdict.ERROR, "Fabricated error is ERROR")
check(not err.passed, "Error result does not pass")

section("11. Check Single Rule")
rule = FROZEN_RULES[0]  # module_namespace_no_collision
single = check_rule(rule)
check(single.verdict == CompatibilityVerdict.COMPATIBLE, f"Single rule check: {single.rule_name} COMPATIBLE")

section("12. Result Passed Property")
compat = CompatibilityResult("test", CompatibilityVerdict.COMPATIBLE, "ok")
warn = CompatibilityResult("test", CompatibilityVerdict.WARNING, "warn")
incompat = CompatibilityResult("test", CompatibilityVerdict.INCOMPATIBLE, "fail")
err = CompatibilityResult("test", CompatibilityVerdict.ERROR, "err")
check(compat.passed, "COMPATIBLE passes")
check(warn.passed, "WARNING passes (soft pass)")
check(not incompat.passed, "INCOMPATIBLE does not pass")
check(not err.passed, "ERROR does not pass")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  TOTAL: {PASS_COUNT} passed, {FAIL_COUNT} failed")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    sys.exit(1)
