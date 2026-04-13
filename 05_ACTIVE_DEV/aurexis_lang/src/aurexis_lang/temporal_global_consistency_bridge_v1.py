"""
Aurexis Core — Temporal Global Consistency Bridge V1

Bounded local-to-global coherence verification for the narrow V1
temporal transport branch.  Proves that a locally-validated temporal
payload structure is globally coherent across the layers of the
temporal pipeline — contract validation, signature generation, and
signature matching all agree and no layer contradicts any other.

What this proves:
  Given a temporal payload that has passed through the full temporal
  pipeline (decode, dispatch, contract validation, signature generation,
  signature matching), the system can verify that the results across
  all temporal layers are mutually consistent.  A temporal structure
  that is "locally valid but globally contradictory" is caught and
  rejected.

  Cross-layer checks:
  1. Match verdict agreement — the match verdict is MATCH
  2. Contract verdict agreement — the underlying contract is SATISFIED
  3. Signature equality — computed signature equals expected signature
  4. Canonical field consistency — payload, family, mode, fused flag
     are self-consistent across layers (payload family matches route
     table for the actual payload bits)
  5. Payload length consistency — reported payload_length == len(payload)
  6. Cross-case distinctness — all 6 expected temporal signatures in
     the frozen baseline are distinct from each other

What this does NOT prove:
  - Secure provenance or tamper-proof identity
  - General temporal fingerprinting
  - Full OCC identity stack
  - Open-ended transport provenance
  - Cryptographic security guarantees
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen TemporalConsistencyProfile defines exactly which
    cross-layer checks are performed.
  - check_temporal_consistency() runs the full temporal pipeline
    through signature match, then performs the cross-layer checks.
  - Fabricated "locally valid but globally contradictory"
    TemporalMatchResult instances provide negative test cases.
  - All operations are deterministic.

This is a narrow deterministic temporal cross-layer coherence proof,
not general temporal validation or secure attestation.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.temporal_payload_signature_match_bridge_v1 import (
    MATCH_VERSION, MATCH_FROZEN,
    TemporalMatchVerdict, TemporalMatchResult,
    ExpectedTemporalSignatureBaseline, V1_MATCH_BASELINE,
    match_temporal_signature,
    _get_expected_temporal_signatures,
    MATCH_CASES,
)
from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION, SignatureVerdict,
    sign_temporal_payload, SIGN_CASES,
)
from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    CONTRACT_VERSION, ContractVerdict,
    validate_temporal_contract, V1_CONTRACT_PROFILE,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

TEMPORAL_CONSISTENCY_V2_VERSION = "V1.0"
TEMPORAL_CONSISTENCY_V2_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONSISTENCY VERDICTS
# ════════════════════════════════════════════════════════════

class TemporalGlobalVerdict(str, Enum):
    """Overall outcome of a temporal global consistency check."""
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class TemporalConsistencyCheck(str, Enum):
    """Enumeration of individual temporal cross-layer checks."""
    MATCH_VERDICT_AGREEMENT = "MATCH_VERDICT_AGREEMENT"
    CONTRACT_VERDICT_AGREEMENT = "CONTRACT_VERDICT_AGREEMENT"
    SIGNATURE_EQUALITY = "SIGNATURE_EQUALITY"
    CANONICAL_FIELD_CONSISTENCY = "CANONICAL_FIELD_CONSISTENCY"
    PAYLOAD_LENGTH_CONSISTENCY = "PAYLOAD_LENGTH_CONSISTENCY"
    CROSS_CASE_DISTINCTNESS = "CROSS_CASE_DISTINCTNESS"


# ════════════════════════════════════════════════════════════
# INDIVIDUAL CHECK RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalCheckResult:
    """Result of a single temporal cross-layer consistency check."""
    check: TemporalConsistencyCheck = TemporalConsistencyCheck.MATCH_VERDICT_AGREEMENT
    passed: bool = False
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check.value,
            "passed": self.passed,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# CONSISTENCY PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalConsistencyProfile:
    """
    Frozen profile defining which temporal cross-layer checks are
    performed and in what order.
    """
    checks: Tuple[TemporalConsistencyCheck, ...] = (
        TemporalConsistencyCheck.MATCH_VERDICT_AGREEMENT,
        TemporalConsistencyCheck.CONTRACT_VERDICT_AGREEMENT,
        TemporalConsistencyCheck.SIGNATURE_EQUALITY,
        TemporalConsistencyCheck.CANONICAL_FIELD_CONSISTENCY,
        TemporalConsistencyCheck.PAYLOAD_LENGTH_CONSISTENCY,
        TemporalConsistencyCheck.CROSS_CASE_DISTINCTNESS,
    )
    require_all: bool = True
    version: str = TEMPORAL_CONSISTENCY_V2_VERSION


V1_TEMPORAL_GLOBAL_PROFILE = TemporalConsistencyProfile()


# ════════════════════════════════════════════════════════════
# CONSISTENCY RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalConsistencyResult:
    """Complete result of a temporal global consistency check."""
    verdict: TemporalGlobalVerdict = TemporalGlobalVerdict.ERROR
    case_label: str = ""
    contract_name: str = ""
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    check_results: Tuple[TemporalCheckResult, ...] = ()
    failed_checks: Tuple[str, ...] = ()
    match_result: Optional[TemporalMatchResult] = None
    version: str = TEMPORAL_CONSISTENCY_V2_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "case_label": self.case_label,
            "contract_name": self.contract_name,
            "checks_performed": self.checks_performed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "check_results": [cr.to_dict() for cr in self.check_results],
            "failed_checks": list(self.failed_checks),
            "match_result": self.match_result.to_dict() if self.match_result else None,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# ROUTE TABLE (from RS/CC transport bridges)
# ════════════════════════════════════════════════════════════

_ROUTE_TABLE = {
    "00": "adjacent_pair",
    "01": "containment",
    "10": "three_regions",
}


def _expected_family_for_payload(payload: Tuple[int, ...]) -> Optional[str]:
    """Derive the expected payload family from the first 2 bits."""
    if len(payload) < 2:
        return None
    prefix = f"{payload[0]}{payload[1]}"
    return _ROUTE_TABLE.get(prefix)


# ════════════════════════════════════════════════════════════
# INDIVIDUAL CHECK IMPLEMENTATIONS
# ════════════════════════════════════════════════════════════

def _check_match_verdict(mr: TemporalMatchResult) -> TemporalCheckResult:
    """Check 1: Match verdict must be MATCH."""
    passed = mr.verdict == TemporalMatchVerdict.MATCH
    detail = f"TemporalMatchVerdict is {mr.verdict.value}"
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.MATCH_VERDICT_AGREEMENT,
        passed=passed,
        detail=detail,
    )


def _check_contract_verdict(mr: TemporalMatchResult) -> TemporalCheckResult:
    """Check 2: The underlying sign verdict must indicate contract was satisfied."""
    passed = mr.sign_verdict == SignatureVerdict.SIGNED.value
    detail = f"sign_verdict is {mr.sign_verdict!r}"
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.CONTRACT_VERDICT_AGREEMENT,
        passed=passed,
        detail=detail,
    )


def _check_signature_equality(mr: TemporalMatchResult) -> TemporalCheckResult:
    """Check 3: Computed signature equals expected signature."""
    passed = (
        mr.computed_signature != "" and
        mr.expected_signature != "" and
        mr.computed_signature == mr.expected_signature
    )
    detail = (
        "computed == expected"
        if passed
        else f"computed={mr.computed_signature[:16]}... expected={mr.expected_signature[:16]}..."
    )
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.SIGNATURE_EQUALITY,
        passed=passed,
        detail=detail,
    )


def _check_canonical_field_consistency(mr: TemporalMatchResult) -> TemporalCheckResult:
    """
    Check 4: Canonical fields are self-consistent.
    The payload_family reported in the match result must match what
    the route table says for the actual payload bits.
    """
    expected_family = _expected_family_for_payload(mr.payload)
    if expected_family is None:
        return TemporalCheckResult(
            check=TemporalConsistencyCheck.CANONICAL_FIELD_CONSISTENCY,
            passed=False,
            detail=f"Cannot derive family from payload {mr.payload}",
        )

    passed = mr.payload_family == expected_family
    detail = (
        f"payload_family={mr.payload_family!r} matches route-derived={expected_family!r}"
        if passed
        else f"payload_family={mr.payload_family!r} != route-derived={expected_family!r}"
    )
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.CANONICAL_FIELD_CONSISTENCY,
        passed=passed,
        detail=detail,
    )


def _check_payload_length_consistency(mr: TemporalMatchResult) -> TemporalCheckResult:
    """Check 5: payload_length == len(payload)."""
    passed = mr.payload_length == len(mr.payload)
    detail = (
        f"payload_length={mr.payload_length} == len(payload)={len(mr.payload)}"
        if passed
        else f"payload_length={mr.payload_length} != len(payload)={len(mr.payload)}"
    )
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.PAYLOAD_LENGTH_CONSISTENCY,
        passed=passed,
        detail=detail,
    )


def _check_cross_case_distinctness(
    baseline: ExpectedTemporalSignatureBaseline,
) -> TemporalCheckResult:
    """
    Check 6: All expected signatures in the frozen baseline are distinct.
    This catches the degenerate case where the signature function produces
    collisions among the supported temporal structures.
    """
    sigs = _get_expected_temporal_signatures()
    values = list(sigs.values())
    distinct = len(values) == len(set(values))
    detail = (
        f"all {len(values)} expected sigs are distinct"
        if distinct
        else f"collision: {len(values)} sigs but only {len(set(values))} distinct"
    )
    return TemporalCheckResult(
        check=TemporalConsistencyCheck.CROSS_CASE_DISTINCTNESS,
        passed=distinct,
        detail=detail,
    )


# ════════════════════════════════════════════════════════════
# CHECK DISPATCHER
# ════════════════════════════════════════════════════════════

_CHECK_DISPATCH = {
    TemporalConsistencyCheck.MATCH_VERDICT_AGREEMENT: lambda mr, bl: _check_match_verdict(mr),
    TemporalConsistencyCheck.CONTRACT_VERDICT_AGREEMENT: lambda mr, bl: _check_contract_verdict(mr),
    TemporalConsistencyCheck.SIGNATURE_EQUALITY: lambda mr, bl: _check_signature_equality(mr),
    TemporalConsistencyCheck.CANONICAL_FIELD_CONSISTENCY: lambda mr, bl: _check_canonical_field_consistency(mr),
    TemporalConsistencyCheck.PAYLOAD_LENGTH_CONSISTENCY: lambda mr, bl: _check_payload_length_consistency(mr),
    TemporalConsistencyCheck.CROSS_CASE_DISTINCTNESS: lambda mr, bl: _check_cross_case_distinctness(bl),
}


# ════════════════════════════════════════════════════════════
# MAIN: CHECK TEMPORAL CONSISTENCY
# ════════════════════════════════════════════════════════════

def check_temporal_consistency(
    payload: Tuple[int, ...],
    contract_name: str,
    case_label: str,
    transport_mode: str = "rolling_shutter",
    baseline: ExpectedTemporalSignatureBaseline = V1_MATCH_BASELINE,
    profile: TemporalConsistencyProfile = V1_TEMPORAL_GLOBAL_PROFILE,
) -> TemporalConsistencyResult:
    """
    Full temporal global consistency check.

    Steps:
    1. Run signature match (which internally runs contract + signature)
    2. Execute each cross-layer check in the profile
    3. Aggregate results → CONSISTENT or INCONSISTENT

    Deterministic: same inputs → identical verdict.
    """
    result = TemporalConsistencyResult(
        case_label=case_label,
        contract_name=contract_name,
    )

    try:
        # Check baseline support
        if not baseline.is_supported(case_label):
            result.verdict = TemporalGlobalVerdict.UNSUPPORTED
            return result

        # Run signature match (full E2E)
        mr = match_temporal_signature(
            payload=payload,
            contract_name=contract_name,
            case_label=case_label,
            transport_mode=transport_mode,
            baseline=baseline,
        )
        result.match_result = mr

        # Run all checks
        check_results: List[TemporalCheckResult] = []
        failed: List[str] = []

        for check in profile.checks:
            handler = _CHECK_DISPATCH.get(check)
            if handler is None:
                cr = TemporalCheckResult(check=check, passed=False, detail="unknown check")
            else:
                cr = handler(mr, baseline)
            check_results.append(cr)
            if not cr.passed:
                failed.append(cr.check.value)

        result.check_results = tuple(check_results)
        result.checks_performed = len(check_results)
        result.checks_passed = sum(1 for cr in check_results if cr.passed)
        result.checks_failed = sum(1 for cr in check_results if not cr.passed)
        result.failed_checks = tuple(failed)

        if profile.require_all:
            result.verdict = (
                TemporalGlobalVerdict.CONSISTENT
                if result.checks_failed == 0
                else TemporalGlobalVerdict.INCONSISTENT
            )
        else:
            result.verdict = (
                TemporalGlobalVerdict.CONSISTENT
                if result.checks_passed > 0
                else TemporalGlobalVerdict.INCONSISTENT
            )

        return result

    except Exception:
        result.verdict = TemporalGlobalVerdict.ERROR
        return result


def check_temporal_consistency_from_match(
    match_result: TemporalMatchResult,
    baseline: ExpectedTemporalSignatureBaseline = V1_MATCH_BASELINE,
    profile: TemporalConsistencyProfile = V1_TEMPORAL_GLOBAL_PROFILE,
) -> TemporalConsistencyResult:
    """
    Check temporal consistency from an already-computed TemporalMatchResult.

    Convenience function when the caller already has a match result and
    doesn't want to re-run the full pipeline.
    """
    result = TemporalConsistencyResult(
        case_label=match_result.case_label,
        contract_name=match_result.contract_name,
        match_result=match_result,
    )

    try:
        check_results: List[TemporalCheckResult] = []
        failed: List[str] = []

        for check in profile.checks:
            handler = _CHECK_DISPATCH.get(check)
            if handler is None:
                cr = TemporalCheckResult(check=check, passed=False, detail="unknown check")
            else:
                cr = handler(match_result, baseline)
            check_results.append(cr)
            if not cr.passed:
                failed.append(cr.check.value)

        result.check_results = tuple(check_results)
        result.checks_performed = len(check_results)
        result.checks_passed = sum(1 for cr in check_results if cr.passed)
        result.checks_failed = sum(1 for cr in check_results if not cr.passed)
        result.failed_checks = tuple(failed)

        if profile.require_all:
            result.verdict = (
                TemporalGlobalVerdict.CONSISTENT
                if result.checks_failed == 0
                else TemporalGlobalVerdict.INCONSISTENT
            )
        else:
            result.verdict = (
                TemporalGlobalVerdict.CONSISTENT
                if result.checks_passed > 0
                else TemporalGlobalVerdict.INCONSISTENT
            )

        return result

    except Exception:
        result.verdict = TemporalGlobalVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# Consistent cases — reuse MATCH_CASES (all 6 should be globally consistent)
CONSISTENT_CASES = tuple(
    {
        "label": c["label"],
        "payload": c["payload"],
        "contract": c["contract"],
        "mode": c["mode"],
        "expected_verdict": "CONSISTENT",
    }
    for c in MATCH_CASES
)

# Contradictory cases — fabricated TemporalMatchResults that are locally
# plausible but globally inconsistent
CONTRADICTORY_CASES = (
    {
        "label": "contradictory_match_verdict",
        "description": "Match result says MISMATCH but other fields look normal",
        "fabricate": lambda: TemporalMatchResult(
            verdict=TemporalMatchVerdict.MISMATCH,
            computed_signature="a" * 64,
            expected_signature="b" * 64,
            case_label="rs_4bit_adj_sign",
            contract_name="rs_4bit_adjacent",
            payload=(0, 0, 1, 0),
            payload_length=4,
            payload_family="adjacent_pair",
            transport_mode="rolling_shutter",
            is_fused=False,
            sign_verdict="SIGNED",
        ),
        "expected_verdict": "INCONSISTENT",
        "expected_fails": ["MATCH_VERDICT_AGREEMENT", "SIGNATURE_EQUALITY"],
    },
    {
        "label": "contradictory_sign_verdict",
        "description": "Sign verdict says CONTRACT_NOT_SATISFIED but match says MATCH",
        "fabricate": lambda: TemporalMatchResult(
            verdict=TemporalMatchVerdict.MATCH,
            computed_signature="c" * 64,
            expected_signature="c" * 64,
            case_label="rs_4bit_adj_sign",
            contract_name="rs_4bit_adjacent",
            payload=(0, 0, 1, 0),
            payload_length=4,
            payload_family="adjacent_pair",
            transport_mode="rolling_shutter",
            is_fused=False,
            sign_verdict="CONTRACT_NOT_SATISFIED",
        ),
        "expected_verdict": "INCONSISTENT",
        "expected_fails": ["CONTRACT_VERDICT_AGREEMENT"],
    },
    {
        "label": "contradictory_payload_family",
        "description": "Payload bits route to adjacent_pair but family says containment",
        "fabricate": lambda: TemporalMatchResult(
            verdict=TemporalMatchVerdict.MATCH,
            computed_signature="d" * 64,
            expected_signature="d" * 64,
            case_label="rs_4bit_adj_sign",
            contract_name="rs_4bit_adjacent",
            payload=(0, 0, 1, 0),
            payload_length=4,
            payload_family="containment",  # WRONG — bits "00" → adjacent_pair
            transport_mode="rolling_shutter",
            is_fused=False,
            sign_verdict="SIGNED",
        ),
        "expected_verdict": "INCONSISTENT",
        "expected_fails": ["CANONICAL_FIELD_CONSISTENCY"],
    },
    {
        "label": "contradictory_payload_length",
        "description": "payload_length says 5 but payload has 4 elements",
        "fabricate": lambda: TemporalMatchResult(
            verdict=TemporalMatchVerdict.MATCH,
            computed_signature="e" * 64,
            expected_signature="e" * 64,
            case_label="rs_4bit_adj_sign",
            contract_name="rs_4bit_adjacent",
            payload=(0, 0, 1, 0),
            payload_length=5,  # WRONG — should be 4
            payload_family="adjacent_pair",
            transport_mode="rolling_shutter",
            is_fused=False,
            sign_verdict="SIGNED",
        ),
        "expected_verdict": "INCONSISTENT",
        "expected_fails": ["PAYLOAD_LENGTH_CONSISTENCY"],
    },
    {
        "label": "contradictory_signature_mismatch",
        "description": "Match says MATCH but computed != expected",
        "fabricate": lambda: TemporalMatchResult(
            verdict=TemporalMatchVerdict.MATCH,
            computed_signature="f" * 64,
            expected_signature="0" * 64,  # Different!
            case_label="rs_4bit_adj_sign",
            contract_name="rs_4bit_adjacent",
            payload=(0, 0, 1, 0),
            payload_length=4,
            payload_family="adjacent_pair",
            transport_mode="rolling_shutter",
            is_fused=False,
            sign_verdict="SIGNED",
        ),
        "expected_verdict": "INCONSISTENT",
        "expected_fails": ["SIGNATURE_EQUALITY"],
    },
)

# Unsupported cases
UNSUPPORTED_CASES = (
    {
        "label": "unsupported_case_label",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "case_label": "nonexistent_case",
        "mode": "rolling_shutter",
        "expected_verdict": "UNSUPPORTED",
    },
)
