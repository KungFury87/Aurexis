"""
Aurexis Core — Temporal Payload Signature Bridge V1

Bounded temporal fingerprint proof for the narrow V1 temporal transport
branch.  Proves that a validated recovered temporal payload structure
(after decode, dispatch, and contract validation) can be reduced to a
deterministic signature/fingerprint.

What this proves:
  Given a validated recovered temporal payload structure (a contract-
  satisfied TemporalContractResult), the system can:
  1. Extract the canonical structural identity from the validated result:
     contract name, payload bits, payload family (route), transport mode,
     fused flag, and payload length.
  2. Canonicalize these fields into a deterministic byte string.
  3. Compute a SHA-256 fingerprint of the canonical form.
  4. Return a TemporalSignatureResult containing the signature, the
     canonical inputs, and an honest verdict.
  5. Guarantee that:
     - Identical validated structures produce identical signatures.
     - Changed payload content, payload family, transport mode,
       contract name, or fused flag produce different signatures.
     - Structures that failed contract validation cannot be signed
       (honest rejection).

  Supported temporal structures are those that pass one of the 5 frozen
  contracts in the temporal payload contract bridge.

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
  - A frozen TemporalSignatureProfile defines exactly which fields
    participate in the canonical signature form.
  - The canonical form is a deterministic string built from the
    validated contract result fields.
  - The signature is SHA-256 of the canonical UTF-8 bytes.
  - A TemporalSignatureResult records: verdict, signature, canonical
    inputs, and the underlying contract result.
  - All operations are deterministic and use only stdlib + existing bridges.

This is a narrow deterministic temporal fingerprint proof, not general
temporal fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.temporal_payload_contract_bridge_v1 import (
    CONTRACT_VERSION,
    ContractVerdict,
    TemporalContractProfile,
    TemporalContractResult,
    V1_CONTRACT_PROFILE,
    validate_temporal_contract,
    FROZEN_CONTRACTS,
    CONTRACT_MAP,
    SATISFY_CASES as CONTRACT_SATISFY_CASES,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

SIGNATURE_VERSION = "V1.0"
SIGNATURE_FROZEN = True


# ════════════════════════════════════════════════════════════
# SIGNATURE VERDICTS
# ════════════════════════════════════════════════════════════

class SignatureVerdict(str, Enum):
    """Outcome of a temporal payload signature operation."""
    SIGNED = "SIGNED"                          # Signature computed successfully
    CONTRACT_NOT_SATISFIED = "CONTRACT_NOT_SATISFIED"  # Underlying contract failed
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"            # No payload provided
    UNSUPPORTED_CONTRACT = "UNSUPPORTED_CONTRACT"  # Contract not recognized
    ERROR = "ERROR"                            # Unexpected error


# ════════════════════════════════════════════════════════════
# FROZEN SIGNATURE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalSignatureProfile:
    """
    Frozen profile defining what participates in the temporal signature.

    canonical_fields: the ordered tuple of field names included in
        the canonical signature form.
    hash_algorithm: the hash algorithm used for signature computation.
    contract_profile: the contract profile for validation.
    version: profile version string.
    """
    canonical_fields: Tuple[str, ...] = (
        "contract_name",
        "payload_bits",
        "payload_length",
        "payload_family",
        "transport_mode",
        "is_fused",
    )
    hash_algorithm: str = "sha256"
    contract_profile: TemporalContractProfile = V1_CONTRACT_PROFILE
    version: str = SIGNATURE_VERSION


V1_SIGNATURE_PROFILE = TemporalSignatureProfile()


# ════════════════════════════════════════════════════════════
# SIGNATURE RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalSignatureResult:
    """Complete result of a temporal payload signature operation."""
    verdict: SignatureVerdict = SignatureVerdict.ERROR
    temporal_signature: str = ""
    contract_name: str = ""
    payload: Tuple[int, ...] = ()
    payload_length: int = 0
    payload_family: str = ""
    transport_mode: str = ""
    is_fused: bool = False
    contract_verdict: str = ""
    version: str = SIGNATURE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "temporal_signature": self.temporal_signature,
            "contract_name": self.contract_name,
            "payload": list(self.payload),
            "payload_length": self.payload_length,
            "payload_family": self.payload_family,
            "transport_mode": self.transport_mode,
            "is_fused": self.is_fused,
            "contract_verdict": self.contract_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CANONICAL FORM + SIGNATURE COMPUTATION
# ════════════════════════════════════════════════════════════

def compute_temporal_signature(
    contract_name: str,
    payload: Tuple[int, ...],
    payload_family: str,
    transport_mode: str,
    is_fused: bool,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a validated
    temporal payload structure.

    Canonical form (newline-separated, UTF-8):
        temporal_sig_contract=<contract_name>
        temporal_sig_payload=<comma-separated bits>
        temporal_sig_length=<int>
        temporal_sig_family=<family>
        temporal_sig_mode=<mode>
        temporal_sig_fused=<True|False>
        temporal_sig_version=<version>

    Deterministic: same inputs → identical signature.
    """
    bits_str = ",".join(str(b) for b in payload)
    canonical = (
        f"temporal_sig_contract={contract_name}\n"
        f"temporal_sig_payload={bits_str}\n"
        f"temporal_sig_length={len(payload)}\n"
        f"temporal_sig_family={payload_family}\n"
        f"temporal_sig_mode={transport_mode}\n"
        f"temporal_sig_fused={is_fused}\n"
        f"temporal_sig_version={SIGNATURE_VERSION}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# END-TO-END: PAYLOAD → CONTRACT → SIGNATURE
# ════════════════════════════════════════════════════════════

def sign_temporal_payload(
    payload: Tuple[int, ...],
    contract_name: str,
    transport_mode: str = "rolling_shutter",
    profile: TemporalSignatureProfile = V1_SIGNATURE_PROFILE,
) -> TemporalSignatureResult:
    """
    Full end-to-end temporal payload signature generation.

    Steps:
    1. Validate the payload against the named contract via the
       existing contract bridge.
    2. If contract validation fails, return honest rejection.
    3. Extract canonical fields from the validated result.
    4. Compute the deterministic temporal signature.
    5. Return TemporalSignatureResult with full audit trail.

    Deterministic: same inputs → identical result.
    """
    result = TemporalSignatureResult(contract_name=contract_name)

    try:
        # Step 1: Validate
        if len(payload) == 0:
            result.verdict = SignatureVerdict.EMPTY_PAYLOAD
            return result

        if contract_name not in CONTRACT_MAP:
            result.verdict = SignatureVerdict.UNSUPPORTED_CONTRACT
            return result

        contract_result = validate_temporal_contract(
            payload, contract_name, transport_mode,
            profile.contract_profile,
        )

        result.contract_verdict = contract_result.verdict.value

        # Step 2: Check contract outcome
        if contract_result.verdict != ContractVerdict.CONTRACT_SATISFIED:
            result.verdict = SignatureVerdict.CONTRACT_NOT_SATISFIED
            result.payload = contract_result.payload
            result.payload_length = contract_result.payload_length
            result.payload_family = contract_result.payload_family
            result.transport_mode = contract_result.transport_mode
            result.is_fused = contract_result.is_fused
            return result

        # Step 3: Extract canonical fields
        result.payload = contract_result.payload
        result.payload_length = contract_result.payload_length
        result.payload_family = contract_result.payload_family
        result.transport_mode = contract_result.transport_mode
        result.is_fused = contract_result.is_fused

        # Step 4: Compute signature
        result.temporal_signature = compute_temporal_signature(
            contract_name,
            contract_result.payload,
            contract_result.payload_family,
            contract_result.transport_mode,
            contract_result.is_fused,
        )

        result.verdict = SignatureVerdict.SIGNED
        return result

    except Exception:
        result.verdict = SignatureVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# CONVENIENCE: SIGN FROM CONTRACT RESULT DIRECTLY
# ════════════════════════════════════════════════════════════

def sign_from_contract_result(
    contract_result: TemporalContractResult,
) -> TemporalSignatureResult:
    """
    Compute a temporal signature from an already-validated contract result.

    This is a convenience function for when the caller already has a
    TemporalContractResult and doesn't want to re-run validation.

    Returns SIGNED if the contract was satisfied, CONTRACT_NOT_SATISFIED
    otherwise.
    """
    result = TemporalSignatureResult(
        contract_name=contract_result.contract_name,
        payload=contract_result.payload,
        payload_length=contract_result.payload_length,
        payload_family=contract_result.payload_family,
        transport_mode=contract_result.transport_mode,
        is_fused=contract_result.is_fused,
        contract_verdict=contract_result.verdict.value,
    )

    if contract_result.verdict != ContractVerdict.CONTRACT_SATISFIED:
        result.verdict = SignatureVerdict.CONTRACT_NOT_SATISFIED
        return result

    result.temporal_signature = compute_temporal_signature(
        contract_result.contract_name,
        contract_result.payload,
        contract_result.payload_family,
        contract_result.transport_mode,
        contract_result.is_fused,
    )
    result.verdict = SignatureVerdict.SIGNED
    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# Cases that should produce a valid signature (reuse contract satisfy cases)
SIGN_CASES = (
    {
        "label": "rs_4bit_adj_sign",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "SIGNED",
    },
    {
        "label": "cc_3bit_adj_sign",
        "payload": (0, 0, 1),
        "contract": "cc_any_family",
        "mode": "complementary_color",
        "expected_verdict": "SIGNED",
    },
    {
        "label": "cc_6bit_cont_sign",
        "payload": (0, 1, 0, 1, 1, 0),
        "contract": "cc_any_family",
        "mode": "complementary_color",
        "expected_verdict": "SIGNED",
    },
    {
        "label": "rs_containment_sign",
        "payload": (0, 1, 1, 0),
        "contract": "either_containment",
        "mode": "rolling_shutter",
        "expected_verdict": "SIGNED",
    },
    {
        "label": "fused_adj_sign",
        "payload": (0, 0, 1, 0),
        "contract": "fused_any_family",
        "mode": "fused",
        "expected_verdict": "SIGNED",
    },
    {
        "label": "rs_5bit_three_sign",
        "payload": (1, 0, 1, 0, 1),
        "contract": "rs_large_three_regions",
        "mode": "rolling_shutter",
        "expected_verdict": "SIGNED",
    },
)

# Cases that should fail — contract not satisfied
REJECT_CASES = (
    {
        "label": "wrong_mode_reject",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "complementary_color",
        "expected_verdict": "CONTRACT_NOT_SATISFIED",
    },
    {
        "label": "wrong_family_reject",
        "payload": (0, 1, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "CONTRACT_NOT_SATISFIED",
    },
    {
        "label": "wrong_length_reject",
        "payload": (1, 0, 1, 0, 1),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "CONTRACT_NOT_SATISFIED",
    },
)

# OOB cases
OOB_CASES = (
    {
        "label": "empty_payload",
        "payload": (),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "EMPTY_PAYLOAD",
    },
    {
        "label": "unsupported_contract",
        "payload": (0, 0, 1, 0),
        "contract": "nonexistent",
        "mode": "rolling_shutter",
        "expected_verdict": "UNSUPPORTED_CONTRACT",
    },
)

# Signature difference cases — same contract, different payloads
DIFFERENCE_CASES = (
    {
        "label": "different_payload_bits",
        "payload_a": (0, 1, 1, 0),
        "payload_b": (0, 1, 0, 1, 0),
        "contract_a": "either_containment",
        "contract_b": "either_containment",
        "mode_a": "rolling_shutter",
        "mode_b": "rolling_shutter",
        "description": "Same contract+mode, different containment payloads → different sigs",
    },
    {
        "label": "different_transport_mode",
        "payload_a": (0, 1, 1, 0),
        "payload_b": (0, 1, 1, 0),
        "contract_a": "either_containment",
        "contract_b": "either_containment",
        "mode_a": "rolling_shutter",
        "mode_b": "complementary_color",
        "description": "Same contract+payload, different modes → different sigs",
    },
    {
        "label": "different_contract",
        "payload_a": (0, 0, 1, 0),
        "payload_b": (0, 0, 1, 0),
        "contract_a": "rs_4bit_adjacent",
        "contract_b": "cc_any_family",
        "mode_a": "rolling_shutter",
        "mode_b": "complementary_color",
        "description": "Same payload, different contracts+modes → different sigs",
    },
)
