"""
Aurexis Core — Recovered Page Sequence Signature Match Bridge V1

Bounded expected-sequence-signature verification for the narrow V1 raster bridge.
Proves that a computed sequence-level signature can be compared against a
frozen expected-sequence-signature baseline and return a deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

What this proves:
  Given an ordered sequence of host images that has been validated through
  the full per-page pipeline (recovery, dispatch, contract, signature,
  signature match, sequence contract, sequence signature), the system can
  look up the correct expected sequence signature from a frozen baseline
  and return an honest match verdict.  Supported sequences match.  Changed
  order, content, or count produce honest mismatch or validation failure.
  Unsupported sequences fail with UNSUPPORTED.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General document fingerprinting
  - Cryptographic authentication
  - Arbitrary page counts or unknown sequence formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen ExpectedSequenceSignatureBaseline maps (sequence_contract_name
    → expected SHA-256 hex sequence signature) for exactly the 3 frozen
    sequence contracts.
  - match_sequence_signature() runs the full pipeline via sign_sequence,
    then looks up the expected value and returns MATCH/MISMATCH/UNSUPPORTED.
  - match_sequence_signature_from_contracts() chains the convenience
    end-to-end function from contracts.
  - If the sequence contract name is not in the baseline → UNSUPPORTED.
  - If signing fails (sequence not satisfied) → propagates the failure.
  - All operations are deterministic.

This is a narrow deterministic recovered-sequence match proof, not general
document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SEQ_SIG_VERSION, SEQ_SIG_FROZEN,
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    SeqSigVerdict, SeqSigResult,
    sign_sequence, sign_sequence_from_contracts,
    _get_expected_seq_sigs,
    IN_BOUNDS_CASES as SIG_IN_BOUNDS_CASES,
    WRONG_COUNT_CASES as SIG_WRONG_COUNT_CASES,
    WRONG_ORDER_CASES as SIG_WRONG_ORDER_CASES,
    UNSUPPORTED_CASES as SIG_UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceContract, SequenceProfile,
    FROZEN_SEQUENCE_CONTRACTS, V1_SEQUENCE_PROFILE,
    generate_sequence_host_pngs,
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

SEQ_MATCH_VERSION = "V1.0"
SEQ_MATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# SEQUENCE MATCH VERDICTS
# ════════════════════════════════════════════════════════════

class SeqMatchVerdict(str, Enum):
    """Outcome of a sequence signature match operation."""
    MATCH = "MATCH"                            # Sequence signature matches expected
    MISMATCH = "MISMATCH"                      # Sequence signature doesn't match
    UNSUPPORTED = "UNSUPPORTED"                # Sequence contract not in baseline
    SIGN_FAILED = "SIGN_FAILED"                # Sequence signature generation failed
    ERROR = "ERROR"                            # Unexpected error


# ════════════════════════════════════════════════════════════
# SEQUENCE MATCH RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class SeqMatchResult:
    """Complete result of a sequence signature match operation."""
    verdict: SeqMatchVerdict = SeqMatchVerdict.ERROR
    computed_sequence_signature: str = ""
    expected_sequence_signature: str = ""
    sequence_contract_name: str = ""
    sign_verdict: str = ""
    page_count: int = 0
    page_signatures: Tuple[str, ...] = ()
    sequence_validation_verdict: str = ""
    version: str = SEQ_MATCH_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "computed_sequence_signature": self.computed_sequence_signature,
            "expected_sequence_signature": self.expected_sequence_signature,
            "sequence_contract_name": self.sequence_contract_name,
            "sign_verdict": self.sign_verdict,
            "page_count": self.page_count,
            "page_signatures": list(self.page_signatures),
            "sequence_validation_verdict": self.sequence_validation_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED-SEQUENCE-SIGNATURE BASELINE
# ════════════════════════════════════════════════════════════
# These are the canonical expected SHA-256 sequence signatures
# for the 3 frozen sequence contracts.  They are built lazily
# from the deterministic pipeline on first access.
#
# The generation is deterministic: same code + same frozen
# contracts + same frozen layouts → identical sequence signatures
# every time.  This is not a security claim — it is a determinism
# claim for this narrow proof.

@dataclass(frozen=True)
class ExpectedSequenceSignatureBaseline:
    """
    Frozen profile defining the expected sequence signatures for the
    supported sequence contracts.

    This is a narrow baseline for exactly the 3 frozen sequence
    contracts, not a general sequence signature registry.
    """
    version: str = SEQ_MATCH_VERSION
    supported_sequence_contracts: Tuple[str, ...] = (
        "two_page_horizontal_vertical",
        "three_page_all_families",
        "two_page_mixed_reversed",
    )

    def get_expected(self, sequence_contract_name: str) -> Optional[str]:
        """
        Look up the expected sequence signature for a sequence contract name.
        Returns None if the sequence contract is not in the baseline.
        """
        sigs = _get_expected_seq_sigs()
        return sigs.get(sequence_contract_name)

    def is_supported(self, sequence_contract_name: str) -> bool:
        """Check if a sequence contract name is in the frozen baseline."""
        return sequence_contract_name in self.supported_sequence_contracts


V1_SEQ_MATCH_BASELINE = ExpectedSequenceSignatureBaseline()


# ════════════════════════════════════════════════════════════
# MATCH: COMPARE COMPUTED SEQUENCE SIGNATURE AGAINST EXPECTED
# ════════════════════════════════════════════════════════════

def match_sequence_signature(
    host_pngs: Tuple[bytes, ...],
    seq_contract: SequenceContract,
    baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SeqMatchResult:
    """
    Compare a computed sequence signature against the frozen
    expected-sequence-signature baseline.

    Steps:
    1. Check if the sequence contract is in the baseline → UNSUPPORTED if not
    2. Sign the sequence via sign_sequence (full pipeline)
    3. If signing failed → SIGN_FAILED
    4. Look up the expected sequence signature
    5. Compare → MATCH or MISMATCH

    Deterministic: same host_pngs + same seq_contract + same baseline
    → identical verdict.
    """
    result = SeqMatchResult(
        sequence_contract_name=seq_contract.name,
        page_count=len(host_pngs),
    )

    try:
        # Step 1: Check if sequence contract is in baseline
        if not baseline.is_supported(seq_contract.name):
            result.verdict = SeqMatchVerdict.UNSUPPORTED
            return result

        # Step 2: Sign the sequence (full pipeline)
        sr = sign_sequence(
            host_pngs, seq_contract, profile, seq_profile,
            match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )
        result.sign_verdict = sr.verdict.value
        result.computed_sequence_signature = sr.sequence_signature
        result.page_signatures = sr.page_signatures
        result.sequence_validation_verdict = sr.sequence_validation_verdict

        # Step 3: Check if signing succeeded (MATCH or SIGNED both ok)
        if sr.verdict not in (SeqSigVerdict.MATCH, SeqSigVerdict.SIGNED):
            result.verdict = SeqMatchVerdict.SIGN_FAILED
            return result

        # Step 4: Look up expected sequence signature
        expected = baseline.get_expected(seq_contract.name)
        if expected is None:
            # Should not happen if is_supported was true, but be safe
            result.verdict = SeqMatchVerdict.UNSUPPORTED
            return result
        result.expected_sequence_signature = expected

        # Step 5: Compare
        if sr.sequence_signature == expected:
            result.verdict = SeqMatchVerdict.MATCH
        else:
            result.verdict = SeqMatchVerdict.MISMATCH

        return result

    except Exception:
        result.verdict = SeqMatchVerdict.ERROR
        return result


def match_sequence_signature_from_contracts(
    seq_contract: SequenceContract,
    baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SeqMatchResult:
    """
    Full end-to-end: generate host PNGs from frozen layouts,
    then match the sequence signature against the frozen baseline.

    Convenience function for testing and verification.
    Deterministic: same seq_contract → identical result.
    """
    host_pngs = generate_sequence_host_pngs(seq_contract)
    return match_sequence_signature(
        host_pngs, seq_contract, baseline, profile, seq_profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen sequence contract → MATCH
IN_BOUNDS_CASES = (
    {
        "label": "two_page_hv_match",
        "seq_contract_index": 0,
        "expected_verdict": "MATCH",
    },
    {
        "label": "three_page_all_match",
        "seq_contract_index": 1,
        "expected_verdict": "MATCH",
    },
    {
        "label": "two_page_mixed_match",
        "seq_contract_index": 2,
        "expected_verdict": "MATCH",
    },
)

# Wrong page count: → SIGN_FAILED (sequence not satisfied)
WRONG_COUNT_CASES = (
    {
        "label": "two_pages_for_three_contract_match",
        "seq_contract_index": 1,
        "provide_page_count": 2,
        "expected_verdict": "SIGN_FAILED",
    },
    {
        "label": "three_pages_for_two_contract_match",
        "seq_contract_index": 0,
        "provide_page_count": 3,
        "expected_verdict": "SIGN_FAILED",
    },
)

# Wrong page order: → SIGN_FAILED (sequence contract catches it)
WRONG_ORDER_CASES = (
    {
        "label": "two_page_reversed_match",
        "seq_contract_index": 0,
        "reversed": True,
        "expected_verdict": "SIGN_FAILED",
    },
    {
        "label": "three_page_reversed_match",
        "seq_contract_index": 1,
        "reversed": True,
        "expected_verdict": "SIGN_FAILED",
    },
)

# Unsupported: sequence contract not in the frozen baseline
UNSUPPORTED_CASES = (
    {
        "label": "unknown_sequence_match",
        "contract_name": "nonexistent_sequence_contract",
        "expected_verdict": "UNSUPPORTED",
    },
)
