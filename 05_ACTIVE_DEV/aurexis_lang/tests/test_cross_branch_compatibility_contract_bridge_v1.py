"""
Pytest — Cross-Branch Compatibility Contract Bridge V1
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import pytest
from aurexis_lang.cross_branch_compatibility_contract_bridge_v1 import (
    COMPATIBILITY_VERSION, COMPATIBILITY_FROZEN,
    CompatibilityVerdict, CompatibilityResult,
    V1_COMPATIBILITY_PROFILE, FROZEN_RULES,
    check_rule, check_all_compatibility,
    make_incompatible_result, make_error_result,
    EXPECTED_RULE_COUNT, EXPECTED_COMPATIBLE_COUNT,
)

def test_version(): assert COMPATIBILITY_VERSION == "V1.0"
def test_frozen(): assert COMPATIBILITY_FROZEN is True
def test_rule_count(): assert V1_COMPATIBILITY_PROFILE.rule_count == 12
def test_expected_rule_count(): assert EXPECTED_RULE_COUNT == 12

def test_all_compatible():
    results = check_all_compatibility()
    assert len(results) == 12
    assert all(r.verdict == CompatibilityVerdict.COMPATIBLE for r in results)

def test_rule_names_unique():
    names = [r.name for r in FROZEN_RULES]
    assert len(set(names)) == len(names)

@pytest.mark.parametrize("idx", range(12))
def test_individual_rule(idx):
    result = check_rule(FROZEN_RULES[idx])
    assert result.passed

def test_make_incompatible():
    r = make_incompatible_result("test", "detail")
    assert r.verdict == CompatibilityVerdict.INCOMPATIBLE
    assert not r.passed

def test_make_error():
    r = make_error_result("test", "detail")
    assert r.verdict == CompatibilityVerdict.ERROR
    assert not r.passed

def test_compatible_passes():
    r = CompatibilityResult("t", CompatibilityVerdict.COMPATIBLE, "ok")
    assert r.passed

def test_warning_passes():
    r = CompatibilityResult("t", CompatibilityVerdict.WARNING, "warn")
    assert r.passed
