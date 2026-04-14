"""
Aurexis Core — Recovered Sequence Collection Signature Bridge V1

Bounded multi-sequence fingerprint proof for the narrow V1 raster bridge.
Proves that a validated ordered collection of recovered page sequences
(after per-sequence recovery, signature match, and collection contract
validation) can be reduced to a single deterministic collection-level
SHA-256 fingerprint, and that changes in sequence order, sequence
content, or sequence count produce honest signature mismatch.

What this proves:
  Given an ordered collection of host-image groups that has been
  validated through the full per-sequence pipeline and then validated
  against a frozen collection contract, the system can generate a
  deterministic SHA-256 fingerprint for the whole ordered collection.
  The same collection always produces the same fingerprint.  A different
  collection (different order, different sequences, different count)
  produces a different fingerprint or fails honestly.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General archive fingerprinting
  - Cryptographic authentication
  - Arbitrary collection counts or unknown formats
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen CollectionSignatureProfile defines exactly which inputs
    participate in the collection signature: ordered per-sequence
    signatures, collection contract name, and sequence count.
  - Canonical form: deterministic text built from these inputs in a
    fixed format.
  - Signature: SHA-256 hex digest of the canonical form (stdlib only).
  - A frozen expected-signature baseline maps each supported collection
    contract to its expected collection signature.
  - Match: computed collection signature == expected collection signature.
  - If the collection contract was not satisfied, signature generation
    fails honestly — no signature for invalid collections.
  - All operations are deterministic.

This is a narrow deterministic recovered-collection identity proof, not
general archive fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.recovered_sequence_collection_contract_bridge_v1 import (
    COLLECTION_VERSION, COLLECTION_FROZEN,
    CollectionVerdict, CollectionContract, CollectionProfile, CollectionResult,
    FROZEN_COLLECTION_CONTRACTS, V1_COLLECTION_PROFILE,
    validate_collection, validate_collection_from_contracts,
    generate_collection_host_png_groups,
    _get_collection_expected,
)
from aurexis_lang.recovered_page_sequence_signature_match_bridge_v1 import (
    SeqMatchVerdict, SeqMatchResult,
    ExpectedSequenceSignatureBaseline, V1_SEQ_MATCH_BASELINE,
)
from aurexis_lang.recovered_page_sequence_signature_bridge_v1 import (
    SequenceSignatureProfile, V1_SEQ_SIG_PROFILE,
    _get_expected_seq_sigs,
)
from aurexis_lang.recovered_page_sequence_contract_bridge_v1 import (
    SequenceContract, SequenceProfile, V1_SEQUENCE_PROFILE,
    FROZEN_SEQUENCE_CONTRACTS,
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

COLL_SIG_VERSION = "V1.0"
COLL_SIG_FROZEN = True


# ════════════════════════════════════════════════════════════
# COLLECTION SIGNATURE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CollectionSignatureProfile:
    """
    Frozen profile defining exactly which inputs participate in the
    collection-level signature.

    canonical_fields: ordered tuple of field names included in the
        canonical form.
    hash_algorithm: name of the stdlib hash function used.
    version: signature format version — changing this invalidates
        all prior collection signatures.
    """
    canonical_fields: Tuple[str, ...] = (
        "collection_contract_name",
        "sequence_count",
        "ordered_sequence_signatures",
    )
    hash_algorithm: str = "sha256"
    version: str = COLL_SIG_VERSION


V1_COLL_SIG_PROFILE = CollectionSignatureProfile()


# ════════════════════════════════════════════════════════════
# CANONICALIZATION
# ════════════════════════════════════════════════════════════

def canonicalize_collection(
    collection_contract_name: str,
    sequence_count: int,
    ordered_sequence_signatures: Tuple[str, ...],
    profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
) -> Optional[str]:
    """
    Build a deterministic canonical string from a validated collection.

    The canonical form includes exactly the fields listed in the
    signature profile, serialized in a fixed format:

        coll_contract=<collection_contract_name>
        seq_count=<N>
        seq_sigs=<sig0>,<sig1>,...
        version=<coll_sig_version>

    Returns None if inputs are invalid (empty signatures, count mismatch).

    Deterministic: same inputs → identical canonical string.
    """
    if sequence_count != len(ordered_sequence_signatures):
        return None
    if sequence_count == 0:
        return None
    for sig in ordered_sequence_signatures:
        if not sig or len(sig) != 64:
            return None

    lines = []
    lines.append(f"coll_contract={collection_contract_name}")
    lines.append(f"seq_count={sequence_count}")
    lines.append(f"seq_sigs={','.join(ordered_sequence_signatures)}")
    lines.append(f"version={profile.version}")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# SIGNATURE GENERATION
# ════════════════════════════════════════════════════════════

def compute_collection_signature(
    canonical_form: str,
    profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
) -> str:
    """
    Compute the SHA-256 hex digest of a canonical collection form string.

    Uses only stdlib hashlib.  No cryptographic security claims
    beyond deterministic identity — this is a fingerprint, not
    a proof of authenticity.

    Deterministic: same canonical_form → identical signature.
    """
    return hashlib.sha256(canonical_form.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# COLLECTION SIGNATURE VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class CollSigVerdict(str, Enum):
    """Outcome of a collection signature operation."""
    SIGNED = "SIGNED"
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    COLLECTION_NOT_SATISFIED = "COLLECTION_NOT_SATISFIED"
    CANONICALIZATION_FAILED = "CANONICALIZATION_FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


@dataclass
class CollSigResult:
    """Complete result of a collection signature operation."""
    verdict: CollSigVerdict = CollSigVerdict.ERROR
    collection_signature: str = ""
    canonical_form: str = ""
    expected_signature: str = ""
    collection_contract_name: str = ""
    sequence_count: int = 0
    sequence_signatures: Tuple[str, ...] = ()
    collection_validation_verdict: str = ""
    version: str = COLL_SIG_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "collection_signature": self.collection_signature,
            "canonical_form": self.canonical_form,
            "expected_signature": self.expected_signature,
            "collection_contract_name": self.collection_contract_name,
            "sequence_count": self.sequence_count,
            "sequence_signatures": list(self.sequence_signatures),
            "collection_validation_verdict": self.collection_validation_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED COLLECTION SIGNATURES
# ════════════════════════════════════════════════════════════

_EXPECTED_COLL_SIGS: Optional[Dict[str, str]] = None


def _build_expected_coll_sig(
    coll_contract: CollectionContract,
    profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
) -> str:
    """
    Build the expected collection signature for a collection contract
    by running the full pipeline: validate collection → extract sequence
    signatures → canonicalize → hash.
    """
    cr = validate_collection_from_contracts(coll_contract)
    if cr.verdict != CollectionVerdict.COLLECTION_SATISFIED:
        raise RuntimeError(
            f"Cannot build expected sig for {coll_contract.name}: "
            f"collection validation gave {cr.verdict.value}"
        )
    canonical = canonicalize_collection(
        coll_contract.name,
        coll_contract.expected_sequence_count,
        cr.sequence_signatures,
        profile,
    )
    if canonical is None:
        raise RuntimeError(
            f"Cannot build expected sig for {coll_contract.name}: "
            f"canonicalization failed"
        )
    return compute_collection_signature(canonical, profile)


def _get_expected_coll_sigs() -> Dict[str, str]:
    """Get or build the frozen expected collection signatures."""
    global _EXPECTED_COLL_SIGS
    if _EXPECTED_COLL_SIGS is None:
        _EXPECTED_COLL_SIGS = {}
        for cc in FROZEN_COLLECTION_CONTRACTS:
            _EXPECTED_COLL_SIGS[cc.name] = _build_expected_coll_sig(cc)
    return _EXPECTED_COLL_SIGS


# ════════════════════════════════════════════════════════════
# COLLECTION SIGNATURE FROM HOST PNG GROUPS
# ════════════════════════════════════════════════════════════

def sign_collection(
    host_png_groups: Tuple[Tuple[bytes, ...], ...],
    coll_contract: CollectionContract,
    profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
    coll_profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> CollSigResult:
    """
    Full pipeline: validate collection → extract sequence signatures →
    canonicalize → compute collection signature → compare to expected.

    Steps:
    1. Validate collection against contract → if not COLLECTION_SATISFIED,
       fail with COLLECTION_NOT_SATISFIED or UNSUPPORTED
    2. Extract ordered sequence signatures from the validation result
    3. Canonicalize the collection
    4. Compute collection signature
    5. Look up expected collection signature
    6. Compare: MATCH or MISMATCH

    Deterministic: same inputs + same contract → identical result.
    """
    result = CollSigResult(
        collection_contract_name=coll_contract.name,
        sequence_count=len(host_png_groups),
    )

    try:
        # Step 1: Validate the collection
        cr = validate_collection(
            host_png_groups, coll_contract, coll_profile,
            seq_match_baseline, seq_sig_profile, seq_profile,
            match_baseline, layout_profile, tolerance,
            dispatch_profile, signature_profile,
        )
        result.collection_validation_verdict = cr.verdict.value
        result.sequence_signatures = cr.sequence_signatures

        if cr.verdict == CollectionVerdict.UNSUPPORTED_COLLECTION:
            result.verdict = CollSigVerdict.UNSUPPORTED
            return result

        if cr.verdict != CollectionVerdict.COLLECTION_SATISFIED:
            result.verdict = CollSigVerdict.COLLECTION_NOT_SATISFIED
            return result

        # Step 2: Canonicalize
        canonical = canonicalize_collection(
            coll_contract.name,
            coll_contract.expected_sequence_count,
            cr.sequence_signatures,
            profile,
        )
        if canonical is None:
            result.verdict = CollSigVerdict.CANONICALIZATION_FAILED
            return result

        result.canonical_form = canonical

        # Step 3: Compute collection signature
        coll_sig = compute_collection_signature(canonical, profile)
        result.collection_signature = coll_sig

        # Step 4: Look up expected and compare
        expected_sigs = _get_expected_coll_sigs()
        expected = expected_sigs.get(coll_contract.name, "")
        result.expected_signature = expected

        if not expected:
            result.verdict = CollSigVerdict.SIGNED
            return result

        if coll_sig == expected:
            result.verdict = CollSigVerdict.MATCH
        else:
            result.verdict = CollSigVerdict.MISMATCH

        return result

    except Exception:
        result.verdict = CollSigVerdict.ERROR
        return result


def sign_collection_from_contracts(
    coll_contract: CollectionContract,
    profile: CollectionSignatureProfile = V1_COLL_SIG_PROFILE,
    coll_profile: CollectionProfile = V1_COLLECTION_PROFILE,
    seq_match_baseline: ExpectedSequenceSignatureBaseline = V1_SEQ_MATCH_BASELINE,
    seq_sig_profile: SequenceSignatureProfile = V1_SEQ_SIG_PROFILE,
    seq_profile: SequenceProfile = V1_SEQUENCE_PROFILE,
    match_baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> CollSigResult:
    """
    Full end-to-end: generate host PNG groups from frozen layouts,
    then sign the collection.

    Convenience function for testing and verification.
    Deterministic: same coll_contract → identical result.
    """
    host_png_groups = generate_collection_host_png_groups(coll_contract)
    return sign_collection(
        host_png_groups, coll_contract, profile, coll_profile,
        seq_match_baseline, seq_sig_profile, seq_profile,
        match_baseline, layout_profile, tolerance,
        dispatch_profile, signature_profile,
    )


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen collection contract → MATCH
IN_BOUNDS_CASES = (
    {
        "label": "two_seq_hv_mixed_sig",
        "coll_contract_index": 0,
        "expected_verdict": "MATCH",
    },
    {
        "label": "three_seq_all_sig",
        "coll_contract_index": 1,
        "expected_verdict": "MATCH",
    },
    {
        "label": "two_seq_all_mixed_sig",
        "coll_contract_index": 2,
        "expected_verdict": "MATCH",
    },
)

# Wrong sequence count: → COLLECTION_NOT_SATISFIED
WRONG_COUNT_CASES = (
    {
        "label": "two_groups_for_three_contract_sig",
        "coll_contract_index": 1,
        "provide_count": 2,
        "expected_verdict": "COLLECTION_NOT_SATISFIED",
    },
    {
        "label": "three_groups_for_two_contract_sig",
        "coll_contract_index": 0,
        "provide_count": 3,
        "expected_verdict": "COLLECTION_NOT_SATISFIED",
    },
)

# Wrong sequence order: → COLLECTION_NOT_SATISFIED
WRONG_ORDER_CASES = (
    {
        "label": "two_seq_reversed_sig",
        "coll_contract_index": 0,
        "reversed": True,
        "expected_verdict": "COLLECTION_NOT_SATISFIED",
    },
    {
        "label": "three_seq_reversed_sig",
        "coll_contract_index": 1,
        "reversed": True,
        "expected_verdict": "COLLECTION_NOT_SATISFIED",
    },
)

# Unsupported collection: → UNSUPPORTED
UNSUPPORTED_CASES = (
    {
        "label": "unknown_collection_sig",
        "contract_name": "nonexistent_collection_contract",
        "expected_verdict": "UNSUPPORTED",
    },
)
