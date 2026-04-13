"""
Aurexis Core — Temporal Payload Contract Bridge V1

Bounded temporal structure validation proof for the narrow V1 temporal
transport branch.  Proves that a recovered temporal payload structure
(after decode and routing through the existing dispatch path) can be
checked against an explicit frozen transport-level contract and return
an honest deterministic verdict.

What this proves:
  Given a recovered temporal payload structure (from any supported
  transport mode: rolling-shutter, complementary-color, or fused),
  the system can:
  1. Generate and dispatch the temporal payload through the existing
     transport/decode/route pipeline.
  2. Extract the structural properties of the recovered result:
     payload length, payload family (route), transport mode.
  3. Validate those structural properties against an explicit frozen
     temporal contract that specifies:
     - exact allowed payload lengths
     - exact allowed payload families (routes)
     - exact allowed transport modes
     - optional: fused-channel requirement
  4. Return a deterministic contract verdict:
     - CONTRACT_SATISFIED: all structural constraints met
     - WRONG_PAYLOAD_LENGTH: payload length not in contract
     - WRONG_PAYLOAD_FAMILY: route not in allowed families
     - WRONG_TRANSPORT_MODE: mode not in allowed modes
     - FUSED_REQUIRED: contract requires fused channel but
       source was single-channel
     - DECODE_FAILED: underlying decode/dispatch failed
     - EMPTY_PAYLOAD: no payload provided
     - UNSUPPORTED_CONTRACT: contract name not recognized
     - ERROR: unexpected error

  Supported contracts are a small frozen family, not an open-ended
  schema language.

What this does NOT prove:
  - General protocol verifier
  - Full OCC contract stack
  - Open-ended temporal schema language
  - Noise-tolerant real-world validation
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen TemporalContractProfile lists the supported contract
    family.
  - Each TemporalContract defines: name, allowed payload lengths,
    allowed payload families, allowed transport modes, and whether
    fused-channel agreement is required.
  - Validation takes a payload + transport mode + optional fused flag,
    generates/dispatches, and checks the recovered structure against
    the contract.
  - A TemporalContractResult records: verdict, contract name,
    recovered structure details, and a deterministic signature.
  - All operations are deterministic and use only stdlib + existing bridges.

This is a narrow deterministic temporal contract proof, not general
protocol validation or full temporal schema.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from aurexis_lang.temporal_transport_dispatch_bridge_v1 import (
    V1_DISPATCH_PROFILE,
    TemporalDispatchProfile,
    TemporalDispatchResult,
    DispatchVerdict,
    dispatch_temporal_signal,
    generate_rs_signal,
    generate_cc_signal,
)

from aurexis_lang.combined_temporal_fusion_bridge_v1 import (
    V1_FUSION_PROFILE,
    FusionProfile,
    FusionVerdict,
    FusionResult,
    fused_decode,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CONTRACT_VERSION = "V1.0"
CONTRACT_FROZEN = True


# ════════════════════════════════════════════════════════════
# CONTRACT VERDICTS
# ════════════════════════════════════════════════════════════

class ContractVerdict(str, Enum):
    """Outcome of a temporal payload contract validation."""
    CONTRACT_SATISFIED = "CONTRACT_SATISFIED"
    WRONG_PAYLOAD_LENGTH = "WRONG_PAYLOAD_LENGTH"
    WRONG_PAYLOAD_FAMILY = "WRONG_PAYLOAD_FAMILY"
    WRONG_TRANSPORT_MODE = "WRONG_TRANSPORT_MODE"
    FUSED_REQUIRED = "FUSED_REQUIRED"
    DECODE_FAILED = "DECODE_FAILED"
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"
    UNSUPPORTED_CONTRACT = "UNSUPPORTED_CONTRACT"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# TEMPORAL CONTRACT DEFINITION
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalContract:
    """
    A single frozen temporal payload contract.

    name: unique contract identifier.
    allowed_payload_lengths: tuple of int bit lengths accepted.
    allowed_payload_families: tuple of route names accepted
        (e.g., "adjacent_pair", "containment", "three_regions").
    allowed_transport_modes: tuple of mode names accepted
        (e.g., "rolling_shutter", "complementary_color", "fused").
    require_fused: if True, the payload must come from fused decode
        (both RS and CC channels agreed).
    """
    name: str = ""
    allowed_payload_lengths: Tuple[int, ...] = ()
    allowed_payload_families: Tuple[str, ...] = ()
    allowed_transport_modes: Tuple[str, ...] = ()
    require_fused: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "allowed_payload_lengths": list(self.allowed_payload_lengths),
            "allowed_payload_families": list(self.allowed_payload_families),
            "allowed_transport_modes": list(self.allowed_transport_modes),
            "require_fused": self.require_fused,
        }


# ════════════════════════════════════════════════════════════
# FROZEN CONTRACT FAMILY
# ════════════════════════════════════════════════════════════

# Contract 1: RS-only, 4-bit adjacent pair
RS_4BIT_ADJACENT = TemporalContract(
    name="rs_4bit_adjacent",
    allowed_payload_lengths=(4,),
    allowed_payload_families=("adjacent_pair",),
    allowed_transport_modes=("rolling_shutter",),
    require_fused=False,
)

# Contract 2: CC-only, 3-6 bit, any family
CC_ANY_FAMILY = TemporalContract(
    name="cc_any_family",
    allowed_payload_lengths=(3, 4, 5, 6),
    allowed_payload_families=("adjacent_pair", "containment", "three_regions"),
    allowed_transport_modes=("complementary_color",),
    require_fused=False,
)

# Contract 3: Either mode, 4-6 bit, containment only
EITHER_CONTAINMENT = TemporalContract(
    name="either_containment",
    allowed_payload_lengths=(4, 5, 6),
    allowed_payload_families=("containment",),
    allowed_transport_modes=("rolling_shutter", "complementary_color", "fused"),
    require_fused=False,
)

# Contract 4: Fused-only, 4-6 bit, any family
FUSED_ANY_FAMILY = TemporalContract(
    name="fused_any_family",
    allowed_payload_lengths=(4, 5, 6),
    allowed_payload_families=("adjacent_pair", "containment", "three_regions"),
    allowed_transport_modes=("fused",),
    require_fused=True,
)

# Contract 5: RS-only, 5-8 bit, three_regions only
RS_LARGE_THREE_REGIONS = TemporalContract(
    name="rs_large_three_regions",
    allowed_payload_lengths=(5, 6, 7, 8),
    allowed_payload_families=("three_regions",),
    allowed_transport_modes=("rolling_shutter",),
    require_fused=False,
)

# All frozen contracts
FROZEN_CONTRACTS: Tuple[TemporalContract, ...] = (
    RS_4BIT_ADJACENT,
    CC_ANY_FAMILY,
    EITHER_CONTAINMENT,
    FUSED_ANY_FAMILY,
    RS_LARGE_THREE_REGIONS,
)

CONTRACT_MAP: Dict[str, TemporalContract] = {
    c.name: c for c in FROZEN_CONTRACTS
}


# ════════════════════════════════════════════════════════════
# FROZEN CONTRACT PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TemporalContractProfile:
    """
    Frozen profile defining the bounded temporal contract family.

    supported_contracts: the frozen set of contract names.
    dispatch_profile: the dispatch profile for decode operations.
    fusion_profile: the fusion profile for fused decode.
    version: profile version string.
    """
    supported_contracts: Tuple[str, ...] = tuple(CONTRACT_MAP.keys())
    dispatch_profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE
    fusion_profile: FusionProfile = V1_FUSION_PROFILE
    version: str = CONTRACT_VERSION


V1_CONTRACT_PROFILE = TemporalContractProfile()


# ════════════════════════════════════════════════════════════
# CONTRACT RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalContractResult:
    """Complete result of a temporal payload contract validation."""
    verdict: ContractVerdict = ContractVerdict.ERROR
    contract_name: str = ""
    payload: Tuple[int, ...] = ()
    payload_length: int = 0
    payload_family: str = ""
    transport_mode: str = ""
    is_fused: bool = False
    contract_signature: str = ""
    version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "contract_name": self.contract_name,
            "payload": list(self.payload),
            "payload_length": self.payload_length,
            "payload_family": self.payload_family,
            "transport_mode": self.transport_mode,
            "is_fused": self.is_fused,
            "contract_signature": self.contract_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# CONTRACT SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_contract_signature(
    verdict: str,
    contract_name: str,
    payload: Tuple[int, ...],
    family: str,
    mode: str,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a contract result.

    Canonical form:
        contract_verdict=<verdict>
        contract_name=<name>
        payload=<bits>
        family=<family>
        mode=<mode>
        version=<version>
    """
    bits_str = ",".join(str(b) for b in payload)
    canonical = (
        f"contract_verdict={verdict}\n"
        f"contract_name={contract_name}\n"
        f"payload={bits_str}\n"
        f"family={family}\n"
        f"mode={mode}\n"
        f"version={CONTRACT_VERSION}"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# DISPATCH HELPERS — GENERATE + DECODE VIA EXISTING PATHS
# ════════════════════════════════════════════════════════════

def _dispatch_single_channel(
    payload: Tuple[int, ...],
    mode: str,
    profile: TemporalContractProfile,
) -> Optional[TemporalDispatchResult]:
    """
    Generate a signal for the given payload/mode and dispatch it.
    Returns the dispatch result, or None if signal generation fails.
    """
    if mode == "rolling_shutter":
        signal = generate_rs_signal(payload, profile.dispatch_profile)
        if signal is None:
            return None
        sync_len = len(profile.dispatch_profile.rs_profile.sync_header)
        slot_count = sync_len + len(payload)
        return dispatch_temporal_signal(
            signal,
            expected_rs_slot_count=slot_count,
            profile=profile.dispatch_profile,
        )
    elif mode == "complementary_color":
        signal = generate_cc_signal(payload, profile.dispatch_profile)
        if signal is None:
            return None
        return dispatch_temporal_signal(
            signal,
            profile=profile.dispatch_profile,
        )
    return None


# ════════════════════════════════════════════════════════════
# CONTRACT VALIDATION — THE CORE LOGIC
# ════════════════════════════════════════════════════════════

def validate_temporal_contract(
    payload: Tuple[int, ...],
    contract_name: str,
    transport_mode: str = "rolling_shutter",
    profile: TemporalContractProfile = V1_CONTRACT_PROFILE,
) -> TemporalContractResult:
    """
    Full end-to-end temporal payload contract validation.

    Steps:
    1. Look up the contract by name.
    2. Check for empty payload.
    3. Generate and dispatch the payload through the appropriate
       transport path (single-channel or fused).
    4. Extract recovered structural properties: payload, length,
       family (route), mode.
    5. Validate against the contract constraints in order:
       a. Transport mode allowed?
       b. Fused required?
       c. Payload length allowed?
       d. Payload family allowed?
    6. Return deterministic contract verdict + signature.

    transport_mode: "rolling_shutter", "complementary_color", or "fused".
    For "fused", both RS and CC channels are used via the fusion bridge.

    Deterministic: same inputs → identical result.
    """
    result = TemporalContractResult(contract_name=contract_name)

    try:
        # Step 1: Look up contract
        contract = CONTRACT_MAP.get(contract_name)
        if contract is None:
            result.verdict = ContractVerdict.UNSUPPORTED_CONTRACT
            return result

        # Step 2: Empty payload check
        if len(payload) == 0:
            result.verdict = ContractVerdict.EMPTY_PAYLOAD
            return result

        # Step 3: Dispatch
        recovered_payload: Tuple[int, ...] = ()
        recovered_family: str = ""
        actual_mode: str = transport_mode
        is_fused: bool = False

        if transport_mode == "fused":
            # Fused path
            fusion_result = fused_decode(payload, profile.fusion_profile)
            if fusion_result.verdict != FusionVerdict.BOTH_AGREE:
                result.verdict = ContractVerdict.DECODE_FAILED
                result.transport_mode = "fused"
                return result
            recovered_payload = fusion_result.fused_payload
            recovered_family = fusion_result.fused_route
            actual_mode = "fused"
            is_fused = True
        else:
            # Single-channel path
            dispatch_result = _dispatch_single_channel(
                payload, transport_mode, profile
            )
            if dispatch_result is None:
                result.verdict = ContractVerdict.DECODE_FAILED
                result.transport_mode = transport_mode
                return result
            if dispatch_result.verdict != DispatchVerdict.DISPATCHED:
                result.verdict = ContractVerdict.DECODE_FAILED
                result.transport_mode = transport_mode
                return result
            recovered_payload = dispatch_result.decoded_payload
            recovered_family = dispatch_result.route_name
            actual_mode = dispatch_result.identified_mode

        # Populate result fields
        result.payload = recovered_payload
        result.payload_length = len(recovered_payload)
        result.payload_family = recovered_family
        result.transport_mode = actual_mode
        result.is_fused = is_fused

        # Step 5: Validate against contract
        # 5a: Transport mode
        if actual_mode not in contract.allowed_transport_modes:
            result.verdict = ContractVerdict.WRONG_TRANSPORT_MODE
            result.contract_signature = compute_contract_signature(
                result.verdict.value, contract_name,
                recovered_payload, recovered_family, actual_mode,
            )
            return result

        # 5b: Fused requirement
        if contract.require_fused and not is_fused:
            result.verdict = ContractVerdict.FUSED_REQUIRED
            result.contract_signature = compute_contract_signature(
                result.verdict.value, contract_name,
                recovered_payload, recovered_family, actual_mode,
            )
            return result

        # 5c: Payload length
        if len(recovered_payload) not in contract.allowed_payload_lengths:
            result.verdict = ContractVerdict.WRONG_PAYLOAD_LENGTH
            result.contract_signature = compute_contract_signature(
                result.verdict.value, contract_name,
                recovered_payload, recovered_family, actual_mode,
            )
            return result

        # 5d: Payload family
        if recovered_family not in contract.allowed_payload_families:
            result.verdict = ContractVerdict.WRONG_PAYLOAD_FAMILY
            result.contract_signature = compute_contract_signature(
                result.verdict.value, contract_name,
                recovered_payload, recovered_family, actual_mode,
            )
            return result

        # All checks passed
        result.verdict = ContractVerdict.CONTRACT_SATISFIED
        result.contract_signature = compute_contract_signature(
            result.verdict.value, contract_name,
            recovered_payload, recovered_family, actual_mode,
        )
        return result

    except Exception:
        result.verdict = ContractVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# Cases that should satisfy their contract
SATISFY_CASES = (
    {
        "label": "rs_4bit_adj_pass",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "cc_3bit_adj_pass",
        "payload": (0, 0, 1),
        "contract": "cc_any_family",
        "mode": "complementary_color",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "cc_6bit_cont_pass",
        "payload": (0, 1, 0, 1, 1, 0),
        "contract": "cc_any_family",
        "mode": "complementary_color",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "rs_containment_pass",
        "payload": (0, 1, 1, 0),
        "contract": "either_containment",
        "mode": "rolling_shutter",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "cc_containment_pass",
        "payload": (0, 1, 1, 0),
        "contract": "either_containment",
        "mode": "complementary_color",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "fused_adj_pass",
        "payload": (0, 0, 1, 0),
        "contract": "fused_any_family",
        "mode": "fused",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "rs_5bit_three_pass",
        "payload": (1, 0, 1, 0, 1),
        "contract": "rs_large_three_regions",
        "mode": "rolling_shutter",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
    {
        "label": "fused_containment_pass",
        "payload": (0, 1, 1, 0),
        "contract": "either_containment",
        "mode": "fused",
        "expected_verdict": "CONTRACT_SATISFIED",
    },
)

# Cases that should fail — wrong payload length
WRONG_LENGTH_CASES = (
    {
        "label": "rs_5bit_to_4bit_contract",
        "payload": (1, 0, 1, 0, 1),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_PAYLOAD_LENGTH",
    },
    {
        "label": "rs_4bit_to_large_contract",
        "payload": (0, 0, 1, 0),
        "contract": "rs_large_three_regions",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_PAYLOAD_LENGTH",
    },
)

# Cases that should fail — wrong payload family
WRONG_FAMILY_CASES = (
    {
        "label": "rs_containment_to_adj_contract",
        "payload": (0, 1, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_PAYLOAD_FAMILY",
    },
    {
        "label": "rs_adj_to_containment_contract",
        "payload": (0, 0, 1, 0),
        "contract": "either_containment",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_PAYLOAD_FAMILY",
    },
)

# Cases that should fail — wrong transport mode
WRONG_MODE_CASES = (
    {
        "label": "cc_to_rs_only_contract",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "complementary_color",
        "expected_verdict": "WRONG_TRANSPORT_MODE",
    },
    {
        "label": "rs_to_cc_only_contract",
        "payload": (0, 0, 1, 0),
        "contract": "cc_any_family",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_TRANSPORT_MODE",
    },
)

# Cases that should fail — fused required
FUSED_REQUIRED_CASES = (
    {
        "label": "rs_to_fused_contract",
        "payload": (0, 0, 1, 0),
        "contract": "fused_any_family",
        "mode": "rolling_shutter",
        "expected_verdict": "WRONG_TRANSPORT_MODE",
    },
    {
        "label": "cc_to_fused_contract",
        "payload": (0, 0, 1, 0),
        "contract": "fused_any_family",
        "mode": "complementary_color",
        "expected_verdict": "WRONG_TRANSPORT_MODE",
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
        "contract": "nonexistent_contract",
        "mode": "rolling_shutter",
        "expected_verdict": "UNSUPPORTED_CONTRACT",
    },
    {
        "label": "reserved_route_decode_fail",
        "payload": (1, 1, 0, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "DECODE_FAILED",
    },
)
