"""
Aurexis Core — Recovered Collection Global Consistency Bridge V1

Bounded local-to-global coherence verification for the narrow V1 raster bridge.
Proves that a locally-validated recovered collection is globally coherent across
its constituent pieces via cross-layer consistency checks.

What this proves:
  Given a collection that has passed through the full pipeline (per-page
  recovery, dispatch, contract, signature, signature match, sequence contract,
  sequence signature, sequence signature match, collection contract, collection
  signature, collection signature match), the system can verify that the
  results across all layers are mutually consistent — i.e., that no layer
  contradicts any other.  A collection that is "locally valid but globally
  contradictory" is caught and rejected.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General archive coherence checking
  - Cryptographic authentication
  - Arbitrary collection counts or unknown formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen GlobalConsistencyProfile defines exactly which cross-layer
    checks are performed:
      1. Match verdict agreement (CollMatchVerdict == MATCH)
      2. Validation verdict agreement (collection_validation_verdict ==
         "COLLECTION_SATISFIED")
      3. Signature equality (computed == expected collection signature)
      4. Sequence signature chain consistency (each per-sequence sig
         matches the expected per-sequence sig from the baseline)
      5. Pairwise sequence distinctness (all per-sequence signatures
         within a collection are distinct)
      6. Cross-layer count consistency (sequence_count ==
         len(sequence_signatures) == expected_sequence_count from contract)
  - check_collection_consistency() runs the full pipeline through
    collection signature match, then performs the cross-layer checks.
  - check_collection_consistency_from_contracts() chains the convenience
    end-to-end function from contracts.
  - Fabricated "locally valid but globally contradictory" CollMatchResult
    instances provide negative test cases.
  - All operations are deterministic.

This is a narrow deterministic cross-layer coherence proof, not general
archive validation or secure attestation.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.recovered_sequence_collection_signature_match_bridge_v1 import (
    COLL_MATCH_VERSION, COLL_MATCH_FROZEN,
    CollMatchVerdict, CollMatchResult,
    ExpectedCollectionSignatureBaseline, V1_COLL_MATCH_BASELINE,
    match_collection_signature, match_collection_signature_from_contracts,
)
from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    COLL_SIG_VERSION, COLL_SIG_FROZEN,
    CollectionSignatureProfile, V1_COLL_SIG_PROFILE,
    CollSigVerdict, CollSigResult,
    _get_expected_coll_sigs,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionVerdict, CollectionContract, CollectionProfile, CollectionResult,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    generate_collection_host_png_groups,
    _get_collection_expected,
)
from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceProfile, V1_SEQUENCE_PROFILE,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    ExpectedSignatureBaseline, V1_MATCH_BASELINE,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    V1_TOLERANCE_PROFILE, ToleranceProfile,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE, DispatchProfile,
)
from aurexis_lang.recovered_set_signature_bridge_v1 import (
    V1_SIGNATURE_PROFILE, SignatureProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

GLOBAL_CONSISTENCY_VERSION = "V1.0"
GLOBAL_CONSISTENCY_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONSISTENCY VERDICTS
# ════════════════════════════════════════════════════════════

class ConsistencyVerdict(str, Enum):
    """Overall outcome of a global consistency check."""
    CONSISTENT = "CONSISTENT"            # All cross-layer checks passed
    INCONSISTENT = "INCONSISTENT"        # One or more cross-layer checks failed
    UNSUPPORTED = "UNSUPPORTED"          # Collection contract not in baseline
    ERROR = "ERROR"                      # Unexpected error


class ConsistencyCheck(str, Enum):
    """Enumeration of individual cross-layer consistency checks."""
    MATCH_VERDICT_AGREEMENT = "MATCH_VERDICT_AGREEMENT"
    VALIDATION_VERDICT_AGREEMENT = "VALIDATION_VERDICT_AGREEMENT"
    SIGNATURE_EQUALITY = "SIGNATURE_EQUALITY"
    SEQUENCE_SIGNATURE_CHAIN = "SEQUENCE_SIGNATURE_CHAIN"
    PAIRWISE_SEQUENCE_DISTINCTNESS = "PAIRWISE_SEQUENCE_DISTINCTNESS"
    CROSS_LAYER_COUNT_CONSISTENCY = "CROSS_LAYER_COUNT_CONSISTENCY"


# ════════════════════════════════════════════════════════════
# INDIVIDUAL CHECK RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class ConsistencyCheckResult:
    """Result of a single cross-layer consistency check."""
    check: ConsistencyCheck = ConsistencyCheck.MATCH_VERDICT_AGREEMENT
    passed: bool = False
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check.value,
            "passed": self.passed,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# GLOBAL CONSISTENCY PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GlobalConsistencyProfile:
    """
    Frozen profile defining which cross-layer consistency checks are
    performed and in what order.

    checks: ordered tuple of ConsistencyCheck enums to execute.
    require_all: if True (default), every check must pass for
        CONSISTENT verdict.  If False, any single pass suffices.
    version: profile version — changing invalidates prior results.
    """
    checks: Tuple[ConsistencyCheck, ...] = (
        ConsistencyCheck.MATCH_VERDICT_AGREEMENT,
        ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT,
        ConsistencyCheck.SIGNATURE_EQUALITY,
        ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN,
        ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS,
        ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY,
    )
    require_all: bool = True
    version: str = GLOBAL_CONSISTENCY_VERSION


V1_GLOBAL_CONSISTENCY_PROFILE = GlobalConsistencyProfile()


# ════════════════════════════════════════════════════════════
# CONSISTENCY RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class ConsistencyResult:
    """Complete result of a global consistency check."""
    verdict: ConsistencyVerdict = ConsistencyVerdict.ERROR
    collection_contract_name: str = ""
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    check_results: Tuple[ConsistencyCheckResult, ...] = ()
    failed_checks: Tuple[str, ...] = ()
    match_result: Optional[CollMatchResult] = None
    version: str = GLOBAL_CONSISTENCY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "collection_contract_name": self.collection_contract_name,
            "checks_performed": self.checks_performed,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "check_results": [cr.to_dict() for cr in self.check_results],
            "failed_checks": list(self.failed_checks),
            "match_result": self.match_result.to_dict() if self.match_result else None,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# INDIVIDUAL CHECK IMPLEMENTATIONS
# ════════════════════════════════════════════════════════════

def _check_match_verdict_agreement(
    mr: CollMatchResult,
) -> ConsistencyCheckResult:
    """
    Check 1: The collection-level match verdict must be MATCH.
    A globally consistent collection must have passed matching.
    """
    passed = mr.verdict == CollMatchVerdict.MATCH
    detail = (
        f"CollMatchVerdict is {mr.verdict.value}"
        if not passed
        else "CollMatchVerdict is MATCH"
    )
    return ConsistencyCheckResult(
        check=ConsistencyCheck.MATCH_VERDICT_AGREEMENT,
        passed=passed,
        detail=detail,
    )


def _check_validation_verdict_agreement(
    mr: CollMatchResult,
) -> ConsistencyCheckResult:
    """
    Check 2: The collection validation verdict (from the contract
    layer) must be COLLECTION_SATISFIED.
    """
    expected = CollectionVerdict.COLLECTION_SATISFIED.value
    passed = mr.collection_validation_verdict == expected
    detail = (
        f"collection_validation_verdict is {mr.collection_validation_verdict!r}, "
        f"expected {expected!r}"
        if not passed
        else f"collection_validation_verdict is {expected!r}"
    )
    return ConsistencyCheckResult(
        check=ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT,
        passed=passed,
        detail=detail,
    )


def _check_signature_equality(
    mr: CollMatchResult,
) -> ConsistencyCheckResult:
    """
    Check 3: The computed collection signature must equal the
    expected collection signature.  This is redundant with check 1
    when the match layer is honest, but catches fabricated results
    where verdict says MATCH but signatures disagree.
    """
    passed = (
        bool(mr.computed_collection_signature)
        and bool(mr.expected_collection_signature)
        and mr.computed_collection_signature == mr.expected_collection_signature
    )
    if not passed:
        if not mr.computed_collection_signature:
            detail = "computed_collection_signature is empty"
        elif not mr.expected_collection_signature:
            detail = "expected_collection_signature is empty"
        else:
            detail = (
                f"computed {mr.computed_collection_signature[:16]}... != "
                f"expected {mr.expected_collection_signature[:16]}..."
            )
    else:
        detail = "computed == expected collection signature"
    return ConsistencyCheckResult(
        check=ConsistencyCheck.SIGNATURE_EQUALITY,
        passed=passed,
        detail=detail,
    )


def _check_sequence_signature_chain(
    mr: CollMatchResult,
    coll_contract: CollectionContract,
) -> ConsistencyCheckResult:
    """
    Check 4: Each per-sequence signature in the match result must
    match the expected per-sequence signature from the frozen
    baseline.
    """
    coll_expected = _get_collection_expected()
    expected_seq_sigs = coll_expected.get(coll_contract.name, ())

    if not expected_seq_sigs:
        return ConsistencyCheckResult(
            check=ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN,
            passed=False,
            detail=f"No expected sequence signatures for {coll_contract.name}",
        )

    if len(mr.sequence_signatures) != len(expected_seq_sigs):
        return ConsistencyCheckResult(
            check=ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN,
            passed=False,
            detail=(
                f"sequence_signatures count {len(mr.sequence_signatures)} != "
                f"expected {len(expected_seq_sigs)}"
            ),
        )

    mismatched = []
    for i, (actual, expected) in enumerate(
        zip(mr.sequence_signatures, expected_seq_sigs)
    ):
        if actual != expected:
            mismatched.append(i)

    passed = len(mismatched) == 0
    if passed:
        detail = f"All {len(mr.sequence_signatures)} sequence signatures match expected"
    else:
        detail = (
            f"Sequence signature mismatch at indices: {mismatched}"
        )
    return ConsistencyCheckResult(
        check=ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN,
        passed=passed,
        detail=detail,
    )


def _check_pairwise_sequence_distinctness(
    mr: CollMatchResult,
) -> ConsistencyCheckResult:
    """
    Check 5: All per-sequence signatures within a collection must
    be pairwise distinct.  Duplicate signatures indicate either a
    degenerate collection or a pipeline error.
    """
    sigs = mr.sequence_signatures
    if len(sigs) == 0:
        return ConsistencyCheckResult(
            check=ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS,
            passed=False,
            detail="No sequence signatures to check",
        )

    unique = set(sigs)
    passed = len(unique) == len(sigs)
    if passed:
        detail = f"All {len(sigs)} sequence signatures are distinct"
    else:
        duplicates = [s for s in unique if sigs.count(s) > 1]
        detail = (
            f"{len(sigs) - len(unique)} duplicate(s) found among "
            f"{len(sigs)} sequence signatures"
        )
    return ConsistencyCheckResult(
        check=ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS,
        passed=passed,
        detail=detail,
    )


def _check_cross_layer_count_consistency(
    mr: CollMatchResult,
    coll_contract: CollectionContract,
) -> ConsistencyCheckResult:
    """
    Check 6: The sequence count in the match result must equal the
    number of sequence signatures AND the expected_sequence_count
    from the collection contract.  Any disagreement indicates a
    cross-layer inconsistency.
    """
    expected = coll_contract.expected_sequence_count
    actual_count = mr.sequence_count
    sig_count = len(mr.sequence_signatures)

    passed = (actual_count == expected) and (sig_count == expected)

    if passed:
        detail = f"sequence_count={actual_count}, len(sequence_signatures)={sig_count}, expected={expected} — all agree"
    else:
        detail = (
            f"sequence_count={actual_count}, "
            f"len(sequence_signatures)={sig_count}, "
            f"expected_from_contract={expected} — disagreement"
        )
    return ConsistencyCheckResult(
        check=ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY,
        passed=passed,
        detail=detail,
    )


# ════════════════════════════════════════════════════════════
# CHECK DISPATCHER
# ════════════════════════════════════════════════════════════

_CHECK_DISPATCH = {
    ConsistencyCheck.MATCH_VERDICT_AGREEMENT: lambda mr, cc: _check_match_verdict_agreement(mr),
    ConsistencyCheck.VALIDATION_VERDICT_AGREEMENT: lambda mr, cc: _check_validation_verdict_agreement(mr),
    ConsistencyCheck.SIGNATURE_EQUALITY: lambda mr, cc: _check_signature_equality(mr),
    ConsistencyCheck.SEQUENCE_SIGNATURE_CHAIN: lambda mr, cc: _check_sequence_signature_chain(mr, cc),
    ConsistencyCheck.PAIRWISE_SEQUENCE_DISTINCTNESS: lambda mr, cc: _check_pairwise_sequence_distinctness(mr),
    ConsistencyCheck.CROSS_LAYER_COUNT_CONSISTENCY: lambda mr, cc: _check_cross_layer_count_consistency(mr, cc),
}


def run_consistency_checks(
    mr: CollMatchResult,
    coll_contract: CollectionContract,
    profile: GlobalConsistencyProfile = V1_GLOBAL_CONSISTENCY_PROFILE,
) -> ConsistencyResult:
    """
    Run all cross-layer consistency checks on a CollMatchResult.

    This is the core logic layer — it does NOT run the pipeline itself,
    it only inspects the match result.  This allows testing with
    fabricated "locally valid but globally contradictory" results.

    Deterministic: same mr + same contract + same profile → identical result.
    """
    result = ConsistencyResult(
        collection_contract_name=coll_contract.name,
        match_result=mr,
    )

    try:
        check_results: List[ConsistencyCheckResult] = []
        failed_names: List[str] = []

        for check in profile.checks:
            dispatcher = _CHECK_DISPATCH.get(check)
            if dispatcher is None:
                cr = ConsistencyCheckResult(
                    check=check, passed=False, detail="Unknown check type"
                )
            else:
                cr = dispatcher(mr, coll_contract)
            check_results.append(cr)
            if not cr.passed:
                failed_names.append(check.value)

        result.check_results = tuple(check_results)
        result.checks_performed = len(check_results)
        result.checks_passed = sum(1 for cr in check_results if cr.passed)
        result.checks_failed = sum(1 for cr in check_results if not cr.passed)
        result.failed_checks = tuple(failed_names)

        if profile.require_all:
            result.verdict = (
                ConsistencyVerdict.CONSISTENT
                if result.checks_failed == 0
                else ConsistencyVerdict.INCONSISTENT
            )
        else:
            result.verdict = (
                ConsistencyVerdict.CONSISTENT
                if result.checks_passed > 0
                else ConsistencyVerdict.INCONSISTENT
            )

        return result

    except Exception:
        result.verdict = ConsistencyVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# FULL PIPELINE: CHECK COLLECTION CONSISTENCY
# ════════════════════════════════════════════════════════════

def check_collection_consistency(
    host_png_groups: Tuple[Tuple[bytes, ...], ...],
    coll_contract: CollectionContract,
    consistency_profile: GlobalConsistencyProfile = V1_GLOBAL_CONSISTENCY_PROFILE,
    baseline: ExpectedCollectionSignatureBaseline = V1_COLL_MATCH_BASELINE,
    coll_sig_profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
    coll_profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> ConsistencyResult:
    """
    Full pipeline: run collection signature match, then perform
    cross-layer consistency checks on the result.

    Steps:
    1. Check if the collection contract is supported → UNSUPPORTED if not
    2. Run match_collection_signature (full pipeline)
    3. Run consistency checks on the match result
    4. Return ConsistencyResult with overall verdict

    Deterministic: same inputs + same profiles → identical result.
    """
    result = ConsistencyResult(
        collection_contract_name=coll_contract.name,
    )

    try:
        # Step 1: Check if supported
        if not baseline.is_supported(coll_contract.name):
            result.verdict = ConsistencyVerdict.UNSUPPORTED
            return result

        # Step 2: Run collection signature match
        mr = match_collection_signature(
            host_png_groups, coll_contract, baseline, coll_sig_profile,
            coll_profile, seq_match_baseline, seq_sig_profile, seq_profile,
            match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )

        # Step 3: Run consistency checks
        return run_consistency_checks(mr, coll_contract, consistency_profile)

    except Exception:
        result.verdict = ConsistencyVerdict.ERROR
        return result


def check_collection_consistency_from_contracts(
    coll_contract: CollectionContract,
    consistency_profile: GlobalConsistencyProfile = V1_GLOBAL_CONSISTENCY_PROFILE,
    baseline: ExpectedCollectionSignatureBaseline = V1_COLL_MATCH_BASELINE,
    coll_sig_profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
    coll_profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> ConsistencyResult:
    """
    Full end-to-end: generate host PNG groups from frozen layouts,
    then check global consistency.

    Convenience function for testing and verification.
    Deterministic: same coll_contract → identical result.
    """
    host_png_groups = generate_collection_host_png_groups(coll_contract)
    return check_collection_consistency(
        host_png_groups, coll_contract, consistency_profile, baseline,
        coll_sig_profile, coll_profile, seq_match_baseline, seq_sig_profile,
        seq_profile, match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES: IN-BOUNDS (CONSISTENT)
# ════════════════════════════════════════════════════════════

IN_BOUNDS_CASES = (
    {
        "label": "two_seq_hv_mixed_consistent",
        "coll_contract_index": 0,
        "expected_verdict": "CONSISTENT",
    },
    {
        "label": "three_seq_all_consistent",
        "coll_contract_index": 1,
        "expected_verdict": "CONSISTENT",
    },
    {
        "label": "two_seq_all_mixed_consistent",
        "coll_contract_index": 2,
        "expected_verdict": "CONSISTENT",
    },
)


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES: UNSUPPORTED
# ════════════════════════════════════════════════════════════

UNSUPPORTED_CASES = (
    {
        "label": "unknown_collection_consistency",
        "contract_name": "nonexistent_collection_contract",
        "expected_verdict": "UNSUPPORTED",
    },
)


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES: LOCALLY VALID BUT GLOBALLY CONTRADICTORY
# ════════════════════════════════════════════════════════════
# These are fabricated CollMatchResult instances where individual
# fields claim success but cross-layer facts disagree.  They test
# that the global consistency checker catches the contradictions.

def _make_contradictory_match_verdict() -> CollMatchResult:
    """
    Fabricated result: verdict says MISMATCH, but signatures actually
    agree and validation says COLLECTION_SATISFIED.  Global consistency
    should catch that match_verdict != MATCH.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MISMATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="a" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=2,
        sequence_signatures=("b" * 64, "c" * 64),
        collection_validation_verdict="COLLECTION_SATISFIED",
        version=COLL_MATCH_VERSION,
    )


def _make_contradictory_validation_verdict() -> CollMatchResult:
    """
    Fabricated result: match verdict says MATCH, but
    collection_validation_verdict says WRONG_SEQUENCE_COUNT.
    Global consistency should catch the validation disagreement.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="a" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=2,
        sequence_signatures=("b" * 64, "c" * 64),
        collection_validation_verdict="WRONG_SEQUENCE_COUNT",
        version=COLL_MATCH_VERSION,
    )


def _make_contradictory_signature_equality() -> CollMatchResult:
    """
    Fabricated result: match verdict says MATCH, but computed
    collection signature differs from expected.  Global consistency
    should catch the signature disagreement.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="f" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=2,
        sequence_signatures=("b" * 64, "c" * 64),
        collection_validation_verdict="COLLECTION_SATISFIED",
        version=COLL_MATCH_VERSION,
    )


def _make_contradictory_count() -> CollMatchResult:
    """
    Fabricated result: match verdict says MATCH, but sequence_count
    (3) disagrees with len(sequence_signatures) (2) and with the
    contract's expected_sequence_count (2).  Global consistency
    should catch the count disagreement.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="a" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=3,
        sequence_signatures=("b" * 64, "c" * 64),
        collection_validation_verdict="COLLECTION_SATISFIED",
        version=COLL_MATCH_VERSION,
    )


def _make_contradictory_duplicate_sigs() -> CollMatchResult:
    """
    Fabricated result: match verdict says MATCH, but two sequence
    signatures are identical.  Global consistency should catch
    the pairwise distinctness violation.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="a" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=2,
        sequence_signatures=("b" * 64, "b" * 64),
        collection_validation_verdict="COLLECTION_SATISFIED",
        version=COLL_MATCH_VERSION,
    )


def _make_contradictory_chain_mismatch() -> CollMatchResult:
    """
    Fabricated result: match verdict says MATCH, but the per-sequence
    signatures do not match the expected per-sequence signatures from
    the baseline.  Global consistency should catch the chain mismatch.
    """
    return CollMatchResult(
        verdict=CollMatchVerdict.MATCH,
        computed_collection_signature="a" * 64,
        expected_collection_signature="a" * 64,
        collection_contract_name="two_seq_hv_mixed",
        sign_verdict="MATCH",
        sequence_count=2,
        sequence_signatures=("d" * 64, "e" * 64),
        collection_validation_verdict="COLLECTION_SATISFIED",
        version=COLL_MATCH_VERSION,
    )


CONTRADICTORY_CASES = (
    {
        "label": "contradictory_match_verdict",
        "fabricator": _make_contradictory_match_verdict,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("MATCH_VERDICT_AGREEMENT",),
        "description": "Verdict says MISMATCH but signatures agree",
    },
    {
        "label": "contradictory_validation_verdict",
        "fabricator": _make_contradictory_validation_verdict,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("VALIDATION_VERDICT_AGREEMENT",),
        "description": "Verdict says MATCH but validation says WRONG_SEQUENCE_COUNT",
    },
    {
        "label": "contradictory_signature_equality",
        "fabricator": _make_contradictory_signature_equality,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("SIGNATURE_EQUALITY",),
        "description": "Verdict says MATCH but computed != expected signature",
    },
    {
        "label": "contradictory_count",
        "fabricator": _make_contradictory_count,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("CROSS_LAYER_COUNT_CONSISTENCY",),
        "description": "Verdict says MATCH but sequence_count != len(sequence_signatures)",
    },
    {
        "label": "contradictory_duplicate_sigs",
        "fabricator": _make_contradictory_duplicate_sigs,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("PAIRWISE_SEQUENCE_DISTINCTNESS",),
        "description": "Verdict says MATCH but two sequence sigs are identical",
    },
    {
        "label": "contradictory_chain_mismatch",
        "fabricator": _make_contradictory_chain_mismatch,
        "coll_contract_index": 0,
        "expected_verdict": "INCONSISTENT",
        "expected_failed_checks": ("SEQUENCE_SIGNATURE_CHAIN",),
        "description": "Verdict says MATCH but per-seq sigs don't match baseline",
    },
)
