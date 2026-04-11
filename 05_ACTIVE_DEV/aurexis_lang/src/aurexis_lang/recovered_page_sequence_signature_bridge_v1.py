"""
Aurexis Core — Recovered Page Sequence Signature Bridge V1

Bounded multi-page fingerprint proof for the narrow V1 raster bridge.
Proves that a validated ordered page sequence (after per-page recovery,
dispatch, contract validation, signature generation, signature match,
and sequence contract validation) can be reduced to a single deterministic
sequence-level signature/fingerprint, and that changes in page order,
page content, or page count produce honest signature mismatch.

What this proves:
  Given an ordered sequence of host images that has been validated through
  the full per-page pipeline and then validated against a frozen sequence
  contract, the system can generate a deterministic SHA-256 fingerprint
  for the whole ordered page sequence.  The same sequence always produces
  the same fingerprint.  A different sequence (different order, different
  pages, different count) produces a different fingerprint or fails
  honestly.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General document fingerprinting
  - Cryptographic authentication
  - Arbitrary page counts or unknown sequence formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen SequenceSignatureProfile defines exactly which inputs
    participate in the sequence signature: ordered per-page signatures,
    sequence contract name, and page count.
  - Canonical form: deterministic text built from these inputs in a
    fixed format.
  - Signature: SHA-256 hex digest of the canonical form (stdlib only).
  - A frozen expected-signature baseline maps each supported sequence
    contract to its expected sequence signature.
  - Match: computed sequence signature == expected sequence signature.
  - If the sequence contract was not satisfied, signature generation
    fails honestly — no signature for invalid sequences.
  - All operations are deterministic.

This is a narrow deterministic recovered-sequence identity proof, not
general document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SEQUENCE_VERSION, SEQUENCE_FROZEN,
    SequenceVerdict, SequenceContract, SequenceProfile,
    PageSequenceResult,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    validate_sequence, validate_sequence_from_contracts,
    generate_sequence_host_pngs,
    _get_sequence_expected,
    IN_BOUNDS_CASES as SEQ_IN_BOUNDS_CASES,
)
from aurexis_lang.recovered_set_signature_match_bridge_v1 import (
    MatchVerdict, V1_MATCH_BASELINE, ExpectedSignatureBaseline,
    _get_expected_signatures,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile,
    generate_multi_artifact_host, build_layout_spec,
    FROZEN_LAYOUTS,
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

SEQ_SIG_VERSION = "V1.0"
SEQ_SIG_FROZEN = True


# ════════════════════════════════════════════════════════════
# SEQUENCE SIGNATURE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SequenceSignatureProfile:
    """
    Frozen profile defining exactly which inputs participate in the
    sequence-level signature.

    canonical_fields: ordered tuple of field names included in the
        canonical form.
    hash_algorithm: name of the stdlib hash function used.
    version: signature format version — changing this invalidates
        all prior sequence signatures.
    """
    canonical_fields: Tuple[str, ...] = (
        "sequence_contract_name",
        "page_count",
        "ordered_page_signatures",
    )
    hash_algorithm: str = "sha256"
    version: str = SEQ_SIG_VERSION


V1_SEQ_SIG_PROFILE = SequenceSignatureProfile()


# ════════════════════════════════════════════════════════════
# CANONICALIZATION
# ════════════════════════════════════════════════════════════

def canonicalize_sequence(
    sequence_contract_name: str,
    page_count: int,
    ordered_page_signatures: Tuple[str, ...],
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
) -> Optional[str]:
    """
    Build a deterministic canonical string from a validated page sequence.

    The canonical form includes exactly the fields listed in the
    signature profile, serialized in a fixed format:

        seq_contract=<sequence_contract_name>
        page_count=<N>
        page_sigs=<sig0>,<sig1>,...
        version=<seq_sig_version>

    Returns None if inputs are invalid (empty signatures, count mismatch).

    Deterministic: same inputs → identical canonical string.
    """
    # Guard: page count must match signature count
    if page_count != len(ordered_page_signatures):
        return None
    if page_count == 0:
        return None
    # Guard: all signatures must be non-empty 64-char hex
    for sig in ordered_page_signatures:
        if not sig or len(sig) != 64:
            return None

    lines = []
    lines.append(f"seq_contract={sequence_contract_name}")
    lines.append(f"page_count={page_count}")
    lines.append(f"page_sigs={','.join(ordered_page_signatures)}")
    lines.append(f"version={profile.version}")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# SIGNATURE GENERATION
# ════════════════════════════════════════════════════════════

def compute_sequence_signature(
    canonical_form: str,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
) -> str:
    """
    Compute the SHA-256 hex digest of a canonical sequence form string.

    Uses only stdlib hashlib.  No cryptographic security claims
    beyond deterministic identity — this is a fingerprint, not
    a proof of authenticity.

    Deterministic: same canonical_form → identical signature.
    """
    return hashlib.sha256(canonical_form.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# SEQUENCE SIGNATURE VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class SeqSigVerdict(str, Enum):
    """Outcome of a sequence signature operation."""
    SIGNED = "SIGNED"                            # Signature generated
    MATCH = "MATCH"                              # Matches expected
    MISMATCH = "MISMATCH"                        # Does not match expected
    SEQUENCE_NOT_SATISFIED = "SEQUENCE_NOT_SATISFIED"  # Sequence validation failed
    CANONICALIZATION_FAILED = "CANONICALIZATION_FAILED"  # Could not canonicalize
    UNSUPPORTED = "UNSUPPORTED"                  # Sequence not in profile
    ERROR = "ERROR"                              # Unexpected error


@dataclass
class SeqSigResult:
    """Complete result of a sequence signature operation."""
    verdict: SeqSigVerdict = SeqSigVerdict.ERROR
    sequence_signature: str = ""
    canonical_form: str = ""
    expected_signature: str = ""
    sequence_contract_name: str = ""
    page_count: int = 0
    page_signatures: Tuple[str, ...] = ()
    sequence_validation_verdict: str = ""
    version: str = SEQ_SIG_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "sequence_signature": self.sequence_signature,
            "canonical_form": self.canonical_form,
            "expected_signature": self.expected_signature,
            "sequence_contract_name": self.sequence_contract_name,
            "page_count": self.page_count,
            "page_signatures": list(self.page_signatures),
            "sequence_validation_verdict": self.sequence_validation_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED SEQUENCE SIGNATURES
# ════════════════════════════════════════════════════════════
# These are the expected sequence-level signatures for each frozen
# sequence contract.  They are computed lazily from the deterministic
# pipeline on first access.

_EXPECTED_SEQ_SIGS: Optional[Dict[str, str]] = None


def _build_expected_seq_sig(
    seq_contract: SequenceContract,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
) -> str:
    """
    Build the expected sequence signature for a sequence contract
    by running the full pipeline: generate host PNGs → validate
    sequence → extract page signatures → canonicalize → hash.
    """
    seq_result = validate_sequence_from_contracts(seq_contract)
    if seq_result.verdict != SequenceVerdict.SEQUENCE_SATISFIED:
        raise RuntimeError(
            f"Cannot build expected sig for {seq_contract.name}: "
            f"sequence validation gave {seq_result.verdict.value}"
        )
    canonical = canonicalize_sequence(
        seq_contract.name,
        seq_contract.expected_page_count,
        seq_result.page_signatures,
        profile,
    )
    if canonical is None:
        raise RuntimeError(
            f"Cannot build expected sig for {seq_contract.name}: "
            f"canonicalization failed"
        )
    return compute_sequence_signature(canonical, profile)


def _get_expected_seq_sigs() -> Dict[str, str]:
    """Get or build the frozen expected sequence signatures."""
    global _EXPECTED_SEQ_SIGS
    if _EXPECTED_SEQ_SIGS is None:
        _EXPECTED_SEQ_SIGS = {}
        for sc in FROZEN_SEQUENCE_CONTRACTS:
            _EXPECTED_SEQ_SIGS[sc.name] = _build_expected_seq_sig(sc)
    return _EXPECTED_SEQ_SIGS


# ════════════════════════════════════════════════════════════
# SEQUENCE SIGNATURE FROM HOST PNGS
# ════════════════════════════════════════════════════════════

def sign_sequence(
    host_pngs: Tuple[bytes, ...],
    seq_contract: SequenceContract,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SeqSigResult:
    """
    Full pipeline: validate sequence → extract page signatures →
    canonicalize → compute sequence signature → compare to expected.

    Steps:
    1. Validate sequence against contract → if not SEQUENCE_SATISFIED,
       fail with SEQUENCE_NOT_SATISFIED or UNSUPPORTED
    2. Extract ordered page signatures from the validation result
    3. Canonicalize the sequence
    4. Compute sequence signature
    5. Look up expected sequence signature
    6. Compare: MATCH or MISMATCH

    Deterministic: same host_pngs + same seq_contract → identical result.
    """
    result = SeqSigResult(
        sequence_contract_name=seq_contract.name,
        page_count=len(host_pngs),
    )

    try:
        # Step 1: Validate the sequence
        seq_result = validate_sequence(
            host_pngs, seq_contract, seq_profile,
            match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )
        result.sequence_validation_verdict = seq_result.verdict.value
        result.page_signatures = seq_result.page_signatures

        if seq_result.verdict == SequenceVerdict.UNSUPPORTED_SEQUENCE:
            result.verdict = SeqSigVerdict.UNSUPPORTED
            return result

        if seq_result.verdict != SequenceVerdict.SEQUENCE_SATISFIED:
            result.verdict = SeqSigVerdict.SEQUENCE_NOT_SATISFIED
            return result

        # Step 2: Canonicalize
        canonical = canonicalize_sequence(
            seq_contract.name,
            seq_contract.expected_page_count,
            seq_result.page_signatures,
            profile,
        )
        if canonical is None:
            result.verdict = SeqSigVerdict.CANONICALIZATION_FAILED
            return result

        result.canonical_form = canonical

        # Step 3: Compute sequence signature
        seq_sig = compute_sequence_signature(canonical, profile)
        result.sequence_signature = seq_sig

        # Step 4: Look up expected and compare
        expected_sigs = _get_expected_seq_sigs()
        expected = expected_sigs.get(seq_contract.name, "")
        result.expected_signature = expected

        if not expected:
            # No expected — just report as SIGNED (no baseline to compare)
            result.verdict = SeqSigVerdict.SIGNED
            return result

        if seq_sig == expected:
            result.verdict = SeqSigVerdict.MATCH
        else:
            result.verdict = SeqSigVerdict.MISMATCH

        return result

    except Exception as e:
        result.verdict = SeqSigVerdict.ERROR
        return result


def sign_sequence_from_contracts(
    seq_contract: SequenceContract,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SeqSigResult:
    """
    Full end-to-end: generate host PNGs from frozen layouts,
    then sign the sequence.

    Convenience function for testing and verification.
    Deterministic: same seq_contract → identical result.
    """
    host_pngs = generate_sequence_host_pngs(seq_contract)
    return sign_sequence(
        host_pngs, seq_contract, profile, seq_profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen sequence contract → MATCH
IN_BOUNDS_CASES = (
    {
        "label": "two_page_hv_sig",
        "seq_contract_index": 0,
        "expected_verdict": "MATCH",
    },
    {
        "label": "three_page_all_sig",
        "seq_contract_index": 1,
        "expected_verdict": "MATCH",
    },
    {
        "label": "two_page_mixed_sig",
        "seq_contract_index": 2,
        "expected_verdict": "MATCH",
    },
)

# Wrong page count: → SEQUENCE_NOT_SATISFIED
WRONG_COUNT_CASES = (
    {
        "label": "two_pages_for_three_contract_sig",
        "seq_contract_index": 1,
        "provide_page_count": 2,
        "expected_verdict": "SEQUENCE_NOT_SATISFIED",
    },
    {
        "label": "three_pages_for_two_contract_sig",
        "seq_contract_index": 0,
        "provide_page_count": 3,
        "expected_verdict": "SEQUENCE_NOT_SATISFIED",
    },
)

# Wrong page order: → SEQUENCE_NOT_SATISFIED (sequence contract catches it)
WRONG_ORDER_CASES = (
    {
        "label": "two_page_reversed_sig",
        "seq_contract_index": 0,
        "reversed": True,
        "expected_verdict": "SEQUENCE_NOT_SATISFIED",
    },
    {
        "label": "three_page_reversed_sig",
        "seq_contract_index": 1,
        "reversed": True,
        "expected_verdict": "SEQUENCE_NOT_SATISFIED",
    },
)

# Unsupported sequence contract: → UNSUPPORTED
UNSUPPORTED_CASES = (
    {
        "label": "unknown_sequence_sig",
        "contract_name": "nonexistent_sequence_contract",
        "expected_verdict": "UNSUPPORTED",
    },
)
