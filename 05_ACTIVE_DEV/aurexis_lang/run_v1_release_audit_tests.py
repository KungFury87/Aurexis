#!/usr/bin/env python3
"""
Aurexis Core — V1 Substrate Release Audit Bridge V1 — Standalone Test Runner
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from aurexis_lang.v1_substrate_release_audit_bridge_v1 import (
    AUDIT_VERSION, AUDIT_FROZEN,
    AuditVerdict, AuditResult,
    ReleaseAudit, V1_RELEASE_AUDIT,
    run_release_audit,
    make_failing_audit, make_error_audit,
    EXPECTED_AUDIT_CHECK_COUNT, EXPECTED_PASS_COUNT,
    VIOLATION_CASE_COUNT, AUDIT_CHECKS,
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
check(AUDIT_VERSION == "V1.0", "Version V1.0")
check(AUDIT_FROZEN is True, "Module frozen")

section("2. Expected Counts")
check(EXPECTED_AUDIT_CHECK_COUNT == 10, f"10 audit checks (got {EXPECTED_AUDIT_CHECK_COUNT})")
check(EXPECTED_PASS_COUNT == 10, "All 10 should pass")
check(VIOLATION_CASE_COUNT == 2, "2 violation case makers")

section("3. Release Audit Configuration")
check(V1_RELEASE_AUDIT.version == "V1.0", "Audit version V1.0")
check(V1_RELEASE_AUDIT.frozen is True, "Audit frozen")
check(V1_RELEASE_AUDIT.check_count == 10, f"10 check slots (got {V1_RELEASE_AUDIT.check_count})")

section("4. Audit Hash Deterministic")
h1 = V1_RELEASE_AUDIT.audit_hash()
h2 = V1_RELEASE_AUDIT.audit_hash()
check(h1 == h2, "Audit hash deterministic")
check(len(h1) == 64, "Hash is 64 hex chars")

section("5. Run Full Release Audit")
results = run_release_audit()
check(len(results) == 10, f"10 results (got {len(results)})")
passed = [r for r in results if r.passed]
check(len(passed) == 10, f"All 10 passed (got {len(passed)})")

section("6. Individual Audit Results")
for r in results:
    check(r.passed, f"{r.check_name}: {r.verdict.value}")

section("7. Audit Check Names")
names = [name for name, fn in AUDIT_CHECKS]
check(len(set(names)) == len(names), "All check names unique")
check("manifest_loads" in names, "manifest_loads check present")
check("entrypoint_loads" in names, "entrypoint_loads check present")
check("compatibility_passes" in names, "compatibility_passes check present")
check("all_modules_importable" in names, "all_modules_importable check present")
check("all_routes_succeed" in names, "all_routes_succeed check present")

section("8. Fabricated Failing Audit")
fail = make_failing_audit("test_check", "Intentional failure")
check(fail.verdict == AuditVerdict.FAIL, "Fabricated FAIL verdict")
check(fail.check_name == "test_check", "Fabricated check name")
check(not fail.passed, "Fabricated FAIL does not pass")

section("9. Fabricated Error Audit")
err = make_error_audit("test_error", "Intentional error")
check(err.verdict == AuditVerdict.ERROR, "Fabricated ERROR verdict")
check(not err.passed, "Fabricated ERROR does not pass")

section("10. AuditResult Passed Property")
p = AuditResult("t", AuditVerdict.PASS, "ok")
f = AuditResult("t", AuditVerdict.FAIL, "fail")
s = AuditResult("t", AuditVerdict.SKIP, "skip")
e = AuditResult("t", AuditVerdict.ERROR, "err")
check(p.passed, "PASS passes")
check(not f.passed, "FAIL does not pass")
check(not s.passed, "SKIP does not pass")
check(not e.passed, "ERROR does not pass")

section("11. Manifest Detail Content")
manifest_result = [r for r in results if r.check_name == "manifest_loads"][0]
check("40" in manifest_result.detail, "Manifest detail mentions 40 bridges")
check("5" in manifest_result.detail, "Manifest detail mentions 5 branches")

section("12. Version Consistency Detail")
ver_result = [r for r in results if r.check_name == "version_consistent"][0]
check("V1.0" in ver_result.detail, "Version detail mentions V1.0")

# ── Summary ──
print(f"\n{'='*60}")
print(f"  TOTAL: {PASS_COUNT} passed, {FAIL_COUNT} failed")
print(f"{'='*60}")
if FAIL_COUNT > 0:
    sys.exit(1)
