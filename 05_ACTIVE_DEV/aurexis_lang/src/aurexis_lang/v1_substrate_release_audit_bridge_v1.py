"""
Aurexis Core — V1 Substrate Release Audit / Capstone Bridge V1

Release-level proof/audit that the V1 Substrate Candidate is
package-complete-enough as a unified bounded substrate.

What this proves:
  The V1 substrate candidate passes a deterministic release audit:
  all modules importable, all branches complete-enough, all
  compatibility rules pass, manifest is consistent, entrypoint
  routes succeed. This is the top-level integration capstone.

What this does NOT prove:
  - Full Aurexis Core completion
  - Production readiness
  - Real-world camera robustness
  - Security guarantees

Design:
  - AuditCheck: named audit check.
  - AuditVerdict: PASS, FAIL, SKIP, ERROR.
  - AuditResult: per-check result.
  - ReleaseAudit: complete audit profile.
  - run_release_audit(): run all audit checks.
  - V1_RELEASE_AUDIT: frozen audit configuration.

All checks are deterministic.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ── Version / Freeze ──
AUDIT_VERSION = "V1.0"
AUDIT_FROZEN = True


# ── Verdicts ──
class AuditVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


# ── Results ──
@dataclass(frozen=True)
class AuditResult:
    check_name: str
    verdict: AuditVerdict
    detail: str

    @property
    def passed(self) -> bool:
        return self.verdict == AuditVerdict.PASS


# ── Audit Checks ──
def _audit_manifest_loads() -> AuditResult:
    """Can the manifest module be imported and has correct counts?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import (
            V1_MANIFEST, EXPECTED_BRIDGE_COUNT, EXPECTED_BRANCH_COUNT,
        )
        if V1_MANIFEST.total_bridges != EXPECTED_BRIDGE_COUNT:
            return AuditResult("manifest_loads", AuditVerdict.FAIL,
                f"Expected {EXPECTED_BRIDGE_COUNT} bridges, got {V1_MANIFEST.total_bridges}")
        if V1_MANIFEST.total_branches != EXPECTED_BRANCH_COUNT:
            return AuditResult("manifest_loads", AuditVerdict.FAIL,
                f"Expected {EXPECTED_BRANCH_COUNT} branches, got {V1_MANIFEST.total_branches}")
        return AuditResult("manifest_loads", AuditVerdict.PASS,
            f"Manifest: {V1_MANIFEST.total_bridges} bridges, {V1_MANIFEST.total_branches} branches.")
    except Exception as e:
        return AuditResult("manifest_loads", AuditVerdict.ERROR, str(e))


def _audit_entrypoint_loads() -> AuditResult:
    """Can the entrypoint module be imported and configured?"""
    try:
        from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import (
            V1_ENTRYPOINT, EXPECTED_BRIDGE_REGISTRY_SIZE,
        )
        bridges = V1_ENTRYPOINT.list_bridges()
        if len(bridges) != EXPECTED_BRIDGE_REGISTRY_SIZE:
            return AuditResult("entrypoint_loads", AuditVerdict.FAIL,
                f"Expected {EXPECTED_BRIDGE_REGISTRY_SIZE} bridges, got {len(bridges)}")
        return AuditResult("entrypoint_loads", AuditVerdict.PASS,
            f"Entrypoint: {len(bridges)} bridges registered, version {V1_ENTRYPOINT.version}.")
    except Exception as e:
        return AuditResult("entrypoint_loads", AuditVerdict.ERROR, str(e))


def _audit_compatibility_passes() -> AuditResult:
    """Do all cross-branch compatibility rules pass?"""
    try:
        from aurexis_lang.cross_branch_compatibility_contract_bridge_v1 import (
            check_all_compatibility, EXPECTED_RULE_COUNT, CompatibilityVerdict,
        )
        results = check_all_compatibility()
        if len(results) != EXPECTED_RULE_COUNT:
            return AuditResult("compatibility_passes", AuditVerdict.FAIL,
                f"Expected {EXPECTED_RULE_COUNT} rules, got {len(results)}")
        failures = [r for r in results if r.verdict not in (CompatibilityVerdict.COMPATIBLE, CompatibilityVerdict.WARNING)]
        if failures:
            detail = "; ".join(f"{r.rule_name}: {r.verdict.value}" for r in failures)
            return AuditResult("compatibility_passes", AuditVerdict.FAIL, f"Failures: {detail}")
        return AuditResult("compatibility_passes", AuditVerdict.PASS,
            f"All {len(results)} compatibility rules passed.")
    except Exception as e:
        return AuditResult("compatibility_passes", AuditVerdict.ERROR, str(e))


def _audit_all_modules_importable() -> AuditResult:
    """Can all 52 V1 modules be imported?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import V1_MANIFEST, verify_manifest
        checks = verify_manifest(V1_MANIFEST)
        if checks.get("all_modules_importable", False):
            return AuditResult("all_modules_importable", AuditVerdict.PASS,
                f"All {V1_MANIFEST.total_modules} modules imported successfully.")
        return AuditResult("all_modules_importable", AuditVerdict.FAIL,
            "Some modules failed to import.")
    except Exception as e:
        return AuditResult("all_modules_importable", AuditVerdict.ERROR, str(e))


def _audit_all_routes_succeed() -> AuditResult:
    """Can the entrypoint route into all 5 branches successfully?"""
    try:
        from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import (
            V1_ENTRYPOINT, SubstrateRoute,
        )
        branch_routes = [
            SubstrateRoute.STATIC_SUBSTRATE,
            SubstrateRoute.TEMPORAL_TRANSPORT,
            SubstrateRoute.HIGHER_ORDER_COHERENCE,
            SubstrateRoute.VIEW_DEPENDENT,
            SubstrateRoute.VSA_CLEANUP,
        ]
        failures = []
        for route in branch_routes:
            result = V1_ENTRYPOINT.route(route)
            if not result.success:
                failures.append(f"{route.value}: {result.error}")
        if not failures:
            return AuditResult("all_routes_succeed", AuditVerdict.PASS,
                f"All 5 branch routes succeeded.")
        return AuditResult("all_routes_succeed", AuditVerdict.FAIL,
            f"Route failures: {'; '.join(failures)}")
    except Exception as e:
        return AuditResult("all_routes_succeed", AuditVerdict.ERROR, str(e))


def _audit_manifest_hash_deterministic() -> AuditResult:
    """Is the manifest hash deterministic?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import V1_MANIFEST
        h1 = V1_MANIFEST.manifest_hash()
        h2 = V1_MANIFEST.manifest_hash()
        if h1 == h2 and len(h1) == 64:
            return AuditResult("manifest_hash_deterministic", AuditVerdict.PASS,
                f"Hash: {h1[:16]}...")
        return AuditResult("manifest_hash_deterministic", AuditVerdict.FAIL,
            f"Hashes differ: {h1} vs {h2}")
    except Exception as e:
        return AuditResult("manifest_hash_deterministic", AuditVerdict.ERROR, str(e))


def _audit_entrypoint_hash_deterministic() -> AuditResult:
    """Is the entrypoint hash deterministic?"""
    try:
        from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import V1_ENTRYPOINT
        h1 = V1_ENTRYPOINT.entrypoint_hash()
        h2 = V1_ENTRYPOINT.entrypoint_hash()
        if h1 == h2 and len(h1) == 64:
            return AuditResult("entrypoint_hash_deterministic", AuditVerdict.PASS,
                f"Hash: {h1[:16]}...")
        return AuditResult("entrypoint_hash_deterministic", AuditVerdict.FAIL,
            f"Hashes differ: {h1} vs {h2}")
    except Exception as e:
        return AuditResult("entrypoint_hash_deterministic", AuditVerdict.ERROR, str(e))


def _audit_foundation_present() -> AuditResult:
    """Are all 12 foundation modules importable?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import FOUNDATION_MODULES
        failures = []
        for mod_name in FOUNDATION_MODULES:
            try:
                __import__(f"aurexis_lang.{mod_name}")
            except ImportError:
                failures.append(mod_name)
        if not failures:
            return AuditResult("foundation_present", AuditVerdict.PASS,
                f"All {len(FOUNDATION_MODULES)} foundation modules importable.")
        return AuditResult("foundation_present", AuditVerdict.FAIL,
            f"Missing: {failures}")
    except Exception as e:
        return AuditResult("foundation_present", AuditVerdict.ERROR, str(e))


def _audit_exclusions_documented() -> AuditResult:
    """Are excluded technologies documented in the manifest?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import V1_MANIFEST
        if len(V1_MANIFEST.exclusions) >= 4:
            names = [e.name for e in V1_MANIFEST.exclusions]
            return AuditResult("exclusions_documented", AuditVerdict.PASS,
                f"{len(V1_MANIFEST.exclusions)} exclusions documented.")
        return AuditResult("exclusions_documented", AuditVerdict.FAIL,
            f"Only {len(V1_MANIFEST.exclusions)} exclusions.")
    except Exception as e:
        return AuditResult("exclusions_documented", AuditVerdict.ERROR, str(e))


def _audit_version_consistent() -> AuditResult:
    """Do all integration modules report V1.0?"""
    try:
        from aurexis_lang.unified_capability_manifest_bridge_v1 import MANIFEST_VERSION
        from aurexis_lang.unified_substrate_entrypoint_bridge_v1 import ENTRYPOINT_VERSION
        from aurexis_lang.cross_branch_compatibility_contract_bridge_v1 import COMPATIBILITY_VERSION
        versions = [MANIFEST_VERSION, ENTRYPOINT_VERSION, COMPATIBILITY_VERSION, AUDIT_VERSION]
        if all(v == "V1.0" for v in versions):
            return AuditResult("version_consistent", AuditVerdict.PASS,
                "All 4 integration modules report V1.0.")
        return AuditResult("version_consistent", AuditVerdict.FAIL,
            f"Version mismatch: {versions}")
    except Exception as e:
        return AuditResult("version_consistent", AuditVerdict.ERROR, str(e))


# ── Audit Registry ──
AUDIT_CHECKS = (
    ("manifest_loads", _audit_manifest_loads),
    ("entrypoint_loads", _audit_entrypoint_loads),
    ("compatibility_passes", _audit_compatibility_passes),
    ("all_modules_importable", _audit_all_modules_importable),
    ("all_routes_succeed", _audit_all_routes_succeed),
    ("manifest_hash_deterministic", _audit_manifest_hash_deterministic),
    ("entrypoint_hash_deterministic", _audit_entrypoint_hash_deterministic),
    ("foundation_present", _audit_foundation_present),
    ("exclusions_documented", _audit_exclusions_documented),
    ("version_consistent", _audit_version_consistent),
)


@dataclass(frozen=True)
class ReleaseAudit:
    version: str
    frozen: bool
    check_count: int

    def audit_hash(self) -> str:
        raw = f"{self.version}:{self.check_count}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


V1_RELEASE_AUDIT = ReleaseAudit(
    version=AUDIT_VERSION,
    frozen=AUDIT_FROZEN,
    check_count=len(AUDIT_CHECKS),
)


def run_release_audit() -> Tuple[AuditResult, ...]:
    """Run the complete V1 release audit."""
    results = []
    for name, fn in AUDIT_CHECKS:
        try:
            results.append(fn())
        except Exception as e:
            results.append(AuditResult(name, AuditVerdict.ERROR, str(e)))
    return tuple(results)


def make_failing_audit(check_name: str, detail: str) -> AuditResult:
    """Fabricate a FAIL result for testing rejection paths."""
    return AuditResult(check_name, AuditVerdict.FAIL, detail)


def make_error_audit(check_name: str, detail: str) -> AuditResult:
    """Fabricate an ERROR result for testing error paths."""
    return AuditResult(check_name, AuditVerdict.ERROR, detail)


# ── Expected counts ──
EXPECTED_AUDIT_CHECK_COUNT = 10
EXPECTED_PASS_COUNT = 10  # all should pass on healthy install
VIOLATION_CASE_COUNT = 2  # make_failing_audit, make_error_audit
