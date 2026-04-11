"""
Aurexis Core — Recovered Set Signature Bridge V1

Bounded page/set fingerprint proof for the narrow V1 raster bridge.
Proves that a validated recovered artifact set (after multi-artifact
recovery, dispatch, and contract validation) can be reduced to a
deterministic SHA-256 signature, and that changed content produces
an honest signature mismatch.

What this proves:
  Given a host image that has been recovered, dispatched, and validated
  against a frozen page-level contract, the system can generate a
  deterministic signature from the ordered recovery results.  The same
  host image always produces the same signature.  A different host
  image (different artifacts, different order, different decode
  outcomes) produces a different signature.

What this does NOT prove:
  - Secure provenance or tamper-proof guarantees
  - General document fingerprinting
  - Cryptographic authentication of arbitrary content
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - Canonical form: deterministic text built from contract_name +
    ordered dispatched families + ordered per-artifact execution
    verdicts + signature version
  - Signature: SHA-256 hex digest of the canonical form (stdlib only)
  - Verification: recompute signature from recovered set and compare
    against expected value
  - Frozen profile defines exactly which inputs participate
  - If the contract was not satisfied, signature generation fails
    honestly — no signature for invalid recovered sets
  - All operations are deterministic

This is a narrow deterministic recovered-set identity proof, not
general document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.artifact_set_contract_bridge_v1 import (
    PageContract, ContractResult, ContractVerdict,
    ContractProfile, V1_CONTRACT_PROFILE, FROZEN_CONTRACTS,
    validate_contract, validate_contract_from_png,
)
from aurexis_lang.multi_artifact_layout_bridge_v1 import (
    MultiLayoutResult, MultiLayoutVerdict,
    multi_artifact_recover_and_dispatch,
    generate_multi_artifact_host, build_layout_spec,
    V1_MULTI_LAYOUT_PROFILE, MultiLayoutProfile,
    FROZEN_LAYOUTS,
)
from aurexis_lang.capture_tolerance_bridge_v1 import (
    V1_TOLERANCE_PROFILE, ToleranceProfile,
)
from aurexis_lang.artifact_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE, DispatchProfile, DispatchVerdict,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

SIGNATURE_VERSION = "V1.0"
SIGNATURE_FROZEN = True


# ════════════════════════════════════════════════════════════
# FROZEN SIGNATURE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SignatureProfile:
    """
    Frozen profile defining exactly which inputs participate in the
    recovered-set signature.

    canonical_fields: ordered tuple of field names included in the
        canonical form.  Each field is extracted from the recovery
        result and contract, then serialized deterministically.
    hash_algorithm: name of the stdlib hash function used.
    version: signature format version — changing this invalidates
        all prior signatures.
    """
    canonical_fields: Tuple[str, ...] = (
        "contract_name",
        "dispatched_families",
        "execution_verdicts",
    )
    hash_algorithm: str = "sha256"
    version: str = SIGNATURE_VERSION


V1_SIGNATURE_PROFILE = SignatureProfile()


# ════════════════════════════════════════════════════════════
# CANONICALIZATION
# ════════════════════════════════════════════════════════════

def canonicalize_recovered_set(
    recovery_result: MultiLayoutResult,
    contract: PageContract,
    profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> Optional[str]:
    """
    Build a deterministic canonical string from a validated recovered set.

    The canonical form includes exactly the fields listed in the
    signature profile, serialized in a fixed format:

        contract=<contract_name>
        families=<family1>,<family2>,...
        verdicts=<verdict1>,<verdict2>,...
        version=<signature_version>

    Returns None if the recovery result cannot be canonicalized
    (e.g., no dispatched artifacts, or contract was not satisfied).

    Deterministic: same inputs → identical canonical string.
    """
    # Guard: must have dispatched artifacts
    if recovery_result.dispatched_count == 0:
        return None
    if not recovery_result.dispatched_families:
        return None

    # Extract per-candidate execution verdicts in order
    execution_verdicts = []
    for candidate in recovery_result.candidates:
        dr = candidate.dispatch_result
        if dr and dr.verdict == DispatchVerdict.DISPATCHED:
            ev = dr.execution_verdict if dr.execution_verdict else "UNKNOWN"
            execution_verdicts.append(ev)

    # Guard: must have execution verdicts for all dispatched artifacts
    if len(execution_verdicts) != recovery_result.dispatched_count:
        return None

    # Build canonical string
    lines = []
    lines.append(f"contract={contract.name}")
    lines.append(f"families={','.join(recovery_result.dispatched_families)}")
    lines.append(f"verdicts={','.join(execution_verdicts)}")
    lines.append(f"version={profile.version}")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# SIGNATURE GENERATION
# ════════════════════════════════════════════════════════════

def compute_signature(
    canonical_form: str,
    profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> str:
    """
    Compute the SHA-256 hex digest of a canonical form string.

    Uses only stdlib hashlib.  No cryptographic security claims
    beyond deterministic identity — this is a fingerprint, not
    a proof of authenticity.

    Deterministic: same canonical_form → identical signature.
    """
    return hashlib.sha256(canonical_form.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# SIGNATURE VERDICTS AND RESULTS
# ════════════════════════════════════════════════════════════

class SignatureVerdict(str, Enum):
    """Outcome of recovered-set signature operation."""
    SIGNED = "SIGNED"                      # Signature generated successfully
    VERIFIED = "VERIFIED"                  # Signature matches expected value
    MISMATCH = "MISMATCH"                  # Signature does not match expected
    CONTRACT_NOT_SATISFIED = "CONTRACT_NOT_SATISFIED"  # Contract failed
    CANONICALIZATION_FAILED = "CANONICALIZATION_FAILED"  # Could not canonicalize
    ERROR = "ERROR"                        # Unexpected error


@dataclass
class SignatureResult:
    """Complete result of a recovered-set signature operation."""
    verdict: SignatureVerdict = SignatureVerdict.ERROR
    signature: str = ""
    canonical_form: str = ""
    contract_name: str = ""
    contract_verdict: str = ""
    dispatched_families: Tuple[str, ...] = ()
    version: str = SIGNATURE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "signature": self.signature,
            "canonical_form": self.canonical_form,
            "contract_name": self.contract_name,
            "contract_verdict": self.contract_verdict,
            "dispatched_families": list(self.dispatched_families),
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# SIGN: GENERATE SIGNATURE FROM RECOVERY + CONTRACT
# ════════════════════════════════════════════════════════════

def sign_recovered_set(
    recovery_result: MultiLayoutResult,
    contract: PageContract,
    profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SignatureResult:
    """
    Generate a deterministic signature for a validated recovered set.

    Steps:
    1. Validate recovery result against contract
    2. If contract not satisfied → CONTRACT_NOT_SATISFIED
    3. Canonicalize the recovered set
    4. Compute SHA-256 of the canonical form
    5. Return SIGNED with the signature

    Deterministic: same recovery_result + same contract → identical signature.
    """
    result = SignatureResult(
        contract_name=contract.name,
        dispatched_families=recovery_result.dispatched_families,
    )

    # Step 1: Validate contract
    cr = validate_contract(recovery_result, contract)
    result.contract_verdict = cr.verdict.value

    if cr.verdict != ContractVerdict.SATISFIED:
        result.verdict = SignatureVerdict.CONTRACT_NOT_SATISFIED
        return result

    # Step 2: Canonicalize
    canonical = canonicalize_recovered_set(recovery_result, contract, profile)
    if canonical is None:
        result.verdict = SignatureVerdict.CANONICALIZATION_FAILED
        return result
    result.canonical_form = canonical

    # Step 3: Compute signature
    result.signature = compute_signature(canonical, profile)
    result.verdict = SignatureVerdict.SIGNED
    return result


def sign_from_png(
    host_png: bytes,
    contract: PageContract,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SignatureResult:
    """
    Full end-to-end signature generation from a host image.

      host_png → multi-artifact recovery → contract validation →
      canonicalize → SHA-256 signature

    Convenience function that chains the full pipeline.

    Deterministic: same host_png + same contract → identical signature.
    """
    recovery = multi_artifact_recover_and_dispatch(
        host_png,
        expected_families=contract.expected_families,
        profile=layout_profile,
        tolerance=tolerance,
        dispatch_profile=dispatch_profile,
    )
    return sign_recovered_set(recovery, contract, signature_profile)


# ════════════════════════════════════════════════════════════
# VERIFY: CHECK SIGNATURE AGAINST EXPECTED VALUE
# ════════════════════════════════════════════════════════════

def verify_signature(
    recovery_result: MultiLayoutResult,
    contract: PageContract,
    expected_signature: str,
    profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SignatureResult:
    """
    Verify that a recovered set produces the expected signature.

    Steps:
    1. Generate signature via sign_recovered_set
    2. If signing failed → propagate the failure verdict
    3. Compare generated signature against expected_signature
    4. Return VERIFIED on match, MISMATCH on difference

    Deterministic: same inputs → identical verdict.
    """
    sr = sign_recovered_set(recovery_result, contract, profile)

    if sr.verdict != SignatureVerdict.SIGNED:
        return sr

    if sr.signature == expected_signature:
        sr.verdict = SignatureVerdict.VERIFIED
    else:
        sr.verdict = SignatureVerdict.MISMATCH

    return sr


def verify_from_png(
    host_png: bytes,
    contract: PageContract,
    expected_signature: str,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> SignatureResult:
    """
    Full end-to-end signature verification from a host image.

      host_png → recovery → contract → sign → compare

    Deterministic: same host_png + same contract + same expected_signature
    → identical verdict.
    """
    recovery = multi_artifact_recover_and_dispatch(
        host_png,
        expected_families=contract.expected_families,
        profile=layout_profile,
        tolerance=tolerance,
        dispatch_profile=dispatch_profile,
    )
    return verify_signature(recovery, contract, expected_signature, signature_profile)


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen layout + matching contract → stable signature
IN_BOUNDS_CASES = (
    {"label": "two_horizontal", "layout_index": 0, "contract_index": 0},
    {"label": "two_vertical", "layout_index": 1, "contract_index": 1},
    {"label": "three_in_row", "layout_index": 2, "contract_index": 2},
    {"label": "two_horizontal_mixed", "layout_index": 3, "contract_index": 3},
    {"label": "two_vertical_reversed", "layout_index": 4, "contract_index": 4},
)

# Out-of-bounds: mismatched layout/contract → signature must fail
OUT_OF_BOUNDS_CASES = (
    {
        "label": "wrong_count",
        "description": "Two-artifact layout against three-artifact contract",
        "layout_index": 0,
        "contract_index": 2,
    },
    {
        "label": "wrong_family",
        "description": "Layout families don't match contract families",
        "layout_index": 0,
        "contract_index": 3,
    },
    {
        "label": "wrong_order",
        "description": "Reversed order doesn't match non-reversed contract",
        "layout_index": 4,
        "contract_index": 1,
    },
)
