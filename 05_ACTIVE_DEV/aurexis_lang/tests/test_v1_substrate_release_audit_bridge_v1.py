"""
Pytest — V1 Substrate Release Audit Bridge V1
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.v1_substrate_release_audit_bridge_v1 import (
    AUDIT_VERSION, AUDIT_FROZEN,
    AuditVerdict, AuditResult,
    V1_RELEASE_AUDIT,
    run_release_audit,
    make_failing_audit, make_error_audit,
    EXPECTED_AUDIT_CHECK_COUNT, EXPECTED_PASS_COUNT,
)

def test_version(): assert AUDIT_VERSION == "V1.0"
def test_frozen(): assert AUDIT_FROZEN is True
def test_check_count(): assert V1_RELEASE_AUDIT.check_count == 10
def test_expected_count(): assert EXPECTED_AUDIT_CHECK_COUNT == 10

def test_audit_hash():
    assert V1_RELEASE_AUDIT.audit_hash() == V1_RELEASE_AUDIT.audit_hash()
    assert len(V1_RELEASE_AUDIT.audit_hash()) == 64

def test_all_pass():
    results = run_release_audit()
    assert len(results) == 10
    assert all(r.passed for r in results)

@pytest.mark.parametrize("idx", range(10))
def test_individual_check(idx):
    results = run_release_audit()
    assert results[idx].passed

def test_make_failing():
    r = make_failing_audit("test", "detail")
    assert r.verdict == AuditVerdict.FAIL
    assert not r.passed

def test_make_error():
    r = make_error_audit("test", "detail")
    assert r.verdict == AuditVerdict.ERROR
    assert not r.passed

def test_pass_passes():
    r = AuditResult("t", AuditVerdict.PASS, "ok")
    assert r.passed

def test_skip_not_pass():
    r = AuditResult("t", AuditVerdict.SKIP, "skip")
    assert not r.passed
