"""
Aurexis Core — Recovered Sequence Collection Signature Match Bridge V1

Bounded expected-collection-signature verification for the narrow V1 raster bridge.
Proves that a computed collection-level signature can be compared against a
frozen expected-collection-signature baseline and return a deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

What this proves:
  Given an ordered collection of host-image groups that has been validated
  through the full per-sequence pipeline (recovery, dispatch, per-page
  contract, per-page signature, per-page signature match, sequence contract,
  sequence signature, sequence signature match, collection contract,
  collection signature), the system can look up the correct expected
  collection signature from a frozen baseline and return an honest match
  verdict.  Supported collections match.  Changed order, content, or count
  produce honest mismatch or validation failure.  Unsupported collections
  fail with UNSUPPORTED.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General archive fingerprinting
  - Cryptographic authentication
  - Arbitrary collection counts or unknown formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen ExpectedCollectionSignatureBaseline maps
    (collection_contract_name → expected SHA-256 hex collection signature)
    for exactly the 3 frozen collection contracts.
  - match_collection_signature() runs the full pipeline via sign_collection,
    then looks up the expected value and returns MATCH/MISMATCH/UNSUPPORTED.
  - match_collection_signature_from_contracts() chains the convenience
    end-to-end function from contracts.
  - If the collection contract name is not in the baseline → UNSUPPORTED.
  - If signing fails (collection not satisfied) → propagates the failure.
  - All operations are deterministic.

This is a narrow deterministic recovered-collection match proof, not general
archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.recovered_sequence_collection_signature_bridge_v1 import (
    COLL_SIG_VERSION, COLL_SIG_FROZEN,
    CollectionSignatureProfile, V1_COLL_SIG_PROFILE,
    CollSigVerdict, CollSigResult,
    sign_collection, sign_collection_from_contracts,
    _get_expected_coll_sigs,
    IN_BOUNDS_CASES as SIG_IN_BOUNDS_CASES,
    WRONG_COUNT_CASES as SIG_WRONG_COUNT_CASES,
    WRONG_ORDER_CASES as SIG_WRONG_ORDER_CASES,
    UNSUPPORTED_CASES as SIG_UNSUPPORTED_CASES,
)
from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    CollectionContract, CollectionProfile,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    generate_collection_host_png_groups,
)
from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
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

COLL_MATCH_VERSION = "V1.0"
COLL_MATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# COLLECTION MATCH VERDICTS
# ════════════════════════════════════════════════════════════

class CollMatchVerdict(str, Enum):
    """Outcome of a collection signature match operation."""
    MATCH = "MATCH"                                    # Collection signature matches expected
    MISMATCH = "MISMATCH"                              # Collection signature doesn't match
    UNSUPPORTED = "UNSUPPORTED"                        # Collection contract not in baseline
    SIGN_FAILED = "SIGN_FAILED"                        # Collection signature generation failed
    ERROR = "ERROR"                                    # Unexpected error


# ════════════════════════════════════════════════════════════
# COLLECTION MATCH RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class CollMatchResult:
    """Complete result of a collection signature match operation."""
    verdict: CollMatchVerdict = CollMatchVerdict.ERROR
    computed_collection_signature: str = ""
    expected_collection_signature: str = ""
    collection_contract_name: str = ""
    sign_verdict: str = ""
    sequence_count: int = 0
    sequence_signatures: Tuple[str, ...] = ()
    collection_validation_verdict: str = ""
    version: str = COLL_MATCH_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "computed_collection_signature": self.computed_collection_signature,
            "expected_collection_signature": self.expected_collection_signature,
            "collection_contract_name": self.collection_contract_name,
            "sign_verdict": self.sign_verdict,
            "sequence_count": self.sequence_count,
            "sequence_signatures": list(self.sequence_signatures),
            "collection_validation_verdict": self.collection_validation_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED-COLLECTION-SIGNATURE BASELINE
# ════════════════════════════════════════════════════════════
# These are the canonical expected SHA-256 collection signatures
# for the 3 frozen collection contracts.  They are built lazily
# from the deterministic pipeline on first access via the
# collection signature bridge.
#
# The generation is deterministic: same code + same frozen
# contracts + same frozen layouts → identical collection
# signatures every time.  This is not a security claim — it is
# a determinism claim for this narrow proof.

@dataclass(frozen=True)
class ExpectedCollectionSignatureBaseline:
    """
    Frozen profile defining the expected collection signatures for the
    supported collection contracts.

    This is a narrow baseline for exactly the 3 frozen collection
    contracts, not a general collection signature registry.
    """
    version: str = COLL_MATCH_VERSION
    supported_collection_contracts: Tuple[str, ...] = (
        "two_seq_hv_mixed",
        "three_seq_all",
        "two_seq_all_mixed",
    )

    def get_expected(self, collection_contract_name: str) -> Optional[str]:
        """
        Look up the expected collection signature for a collection contract name.
        Returns None if the collection contract is not in the baseline.
        """
        sigs = _get_expected_coll_sigs()
        return sigs.get(collection_contract_name)

    def is_supported(self, collection_contract_name: str) -> bool:
        """Check if a collection contract name is in the frozen baseline."""
        return collection_contract_name in self.supported_collection_contracts


V1_COLL_MATCH_BASELINE = ExpectedCollectionSignatureBaseline()


# ════════════════════════════════════════════════════════════
# MATCH: COMPARE COMPUTED COLLECTION SIGNATURE AGAINST EXPECTED
# ════════════════════════════════════════════════════════════

def match_collection_signature(
    host_png_groups: Tuple[Tuple[bytes, ...], ...],
    coll_contract: CollectionContract,
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
) -> CollMatchResult:
    """
    Compare a computed collection signature against the frozen
    expected-collection-signature baseline.

    Steps:
    1. Check if the collection contract is in the baseline → UNSUPPORTED if not
    2. Sign the collection via sign_collection (full pipeline)
    3. If signing failed → SIGN_FAILED
    4. Look up the expected collection signature
    5. Compare → MATCH or MISMATCH

    Deterministic: same host_png_groups + same coll_contract + same baseline
    → identical verdict.
    """
    result = CollMatchResult(
        collection_contract_name=coll_contract.name,
        sequence_count=len(host_png_groups),
    )

    try:
        # Step 1: Check if collection contract is in baseline
        if not baseline.is_supported(coll_contract.name):
            result.verdict = CollMatchVerdict.UNSUPPORTED
            return result

        # Step 2: Sign the collection (full pipeline)
        sr = sign_collection(
            host_png_groups, coll_contract, coll_sig_profile,
            coll_profile, seq_match_baseline, seq_sig_profile,
            seq_profile, match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )
        result.sign_verdict = sr.verdict.value
        result.computed_collection_signature = sr.collection_signature
        result.sequence_signatures = sr.sequence_signatures
        result.collection_validation_verdict = sr.collection_validation_verdict

        # Step 3: Check if signing succeeded (MATCH or SIGNED both ok)
        if sr.verdict not in (CollSigVerdict.MATCH, CollSigVerdict.SIGNED):
            result.verdict = CollMatchVerdict.SIGN_FAILED
            return result

        # Step 4: Look up expected collection signature
        expected = baseline.get_expected(coll_contract.name)
        if expected is None:
            # Should not happen if is_supported was true, but be safe
            result.verdict = CollMatchVerdict.UNSUPPORTED
            return result
        result.expected_collection_signature = expected

        # Step 5: Compare
        if sr.collection_signature == expected:
            result.verdict = CollMatchVerdict.MATCH
        else:
            result.verdict = CollMatchVerdict.MISMATCH

        return result

    except Exception:
        result.verdict = CollMatchVerdict.ERROR
        return result


def match_collection_signature_from_contracts(
    coll_contract: CollectionContract,
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
) -> CollMatchResult:
    """
    Full end-to-end: generate host PNG groups from frozen layouts,
    then match the collection signature against the frozen baseline.

    Convenience function for testing and verification.
    Deterministic: same coll_contract → identical result.
    """
    host_png_groups = generate_collection_host_png_groups(coll_contract)
    return match_collection_signature(
        host_png_groups, coll_contract, baseline, coll_sig_profile,
        coll_profile, seq_match_baseline, seq_sig_profile, seq_profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen collection contract → MATCH
IN_BOUNDS_CASES = (
    {
        "label": "two_seq_hv_mixed_match",
        "coll_contract_index": 0,
        "expected_verdict": "MATCH",
    },
    {
        "label": "three_seq_all_match",
        "coll_contract_index": 1,
        "expected_verdict": "MATCH",
    },
    {
        "label": "two_seq_all_mixed_match",
        "coll_contract_index": 2,
        "expected_verdict": "MATCH",
    },
)

# Wrong sequence count: → SIGN_FAILED (collection not satisfied)
WRONG_COUNT_CASES = (
    {
        "label": "two_groups_for_three_contract_match",
        "coll_contract_index": 1,
        "provide_count": 2,
        "expected_verdict": "SIGN_FAILED",
    },
    {
        "label": "three_groups_for_two_contract_match",
        "coll_contract_index": 0,
        "provide_count": 3,
        "expected_verdict": "SIGN_FAILED",
    },
)

# Wrong sequence order: → SIGN_FAILED (collection contract catches it)
WRONG_ORDER_CASES = (
    {
        "label": "two_seq_reversed_match",
        "coll_contract_index": 0,
        "reversed": True,
        "expected_verdict": "SIGN_FAILED",
    },
    {
        "label": "three_seq_reversed_match",
        "coll_contract_index": 1,
        "reversed": True,
        "expected_verdict": "SIGN_FAILED",
    },
)

# Unsupported: collection contract not in the frozen baseline
UNSUPPORTED_CASES = (
    {
        "label": "unknown_collection_match",
        "contract_name": "nonexistent_collection_contract",
        "expected_verdict": "UNSUPPORTED",
    },
)
