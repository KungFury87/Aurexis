"""
Aurexis Core — Temporal Payload Signature Match Bridge V1

Bounded expected-temporal-signature verification for the narrow V1
temporal transport branch.  Proves that a computed temporal payload
signature can be compared against a frozen expected-signature baseline
and return a deterministic MATCH / MISMATCH / UNSUPPORTED verdict.

What this proves:
  Given a recovered temporal payload that has been decoded, dispatched,
  contract-validated, and signed, the system can look up the correct
  expected signature from a frozen baseline and return an honest match
  verdict.  Supported temporal structures match.  Changed payload bits,
  payload family, transport mode, contract, or fused flag produce
  honest MISMATCH or upstream failure.  Unsupported contracts fail
  with UNSUPPORTED.

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
  - A frozen ExpectedTemporalSignatureBaseline maps
    (label → expected SHA-256 hex signature) for exactly the 6 frozen
    SIGN_CASES from the temporal payload signature bridge.
  - match_temporal_signature() computes the signature from the payload +
    contract + mode, looks up the expected value, and returns
    MATCH / MISMATCH / UNSUPPORTED.
  - match_from_signature_result() accepts a pre-computed
    TemporalSignatureResult and compares directly.
  - If the case label is not in the baseline → UNSUPPORTED.
  - If signing fails (contract not satisfied) → propagates as SIGN_FAILED.
  - All operations are deterministic.

This is a narrow deterministic temporal signature match proof, not
general temporal fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.temporal_payload_signature_bridge_v1 import (
    SIGNATURE_VERSION,
    SIGNATURE_FROZEN,
    V1_SIGNATURE_PROFILE,
    TemporalSignatureProfile,
    SignatureVerdict,
    TemporalSignatureResult,
    sign_temporal_payload,
    sign_from_contract_result,
    compute_temporal_signature,
    SIGN_CASES,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

MATCH_VERSION = "V1.0"
MATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# MATCH VERDICTS
# ════════════════════════════════════════════════════════════

class TemporalMatchVerdict(str, Enum):
    """Outcome of a temporal payload signature match operation."""
    MATCH = "MATCH"                         # Signature matches expected
    MISMATCH = "MISMATCH"                   # Signature doesn't match expected
    UNSUPPORTED = "UNSUPPORTED"             # Case label not in expected baseline
    SIGN_FAILED = "SIGN_FAILED"             # Signature generation failed
    EMPTY_PAYLOAD = "EMPTY_PAYLOAD"         # No payload provided
    ERROR = "ERROR"                         # Unexpected error


# ════════════════════════════════════════════════════════════
# MATCH RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class TemporalMatchResult:
    """Complete result of a temporal payload signature match operation."""
    verdict: TemporalMatchVerdict = TemporalMatchVerdict.ERROR
    computed_signature: str = ""
    expected_signature: str = ""
    case_label: str = ""
    contract_name: str = ""
    payload: Tuple[int, ...] = ()
    payload_length: int = 0
    payload_family: str = ""
    transport_mode: str = ""
    is_fused: bool = False
    sign_verdict: str = ""
    version: str = MATCH_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "computed_signature": self.computed_signature,
            "expected_signature": self.expected_signature,
            "case_label": self.case_label,
            "contract_name": self.contract_name,
            "payload": list(self.payload),
            "payload_length": self.payload_length,
            "payload_family": self.payload_family,
            "transport_mode": self.transport_mode,
            "is_fused": self.is_fused,
            "sign_verdict": self.sign_verdict,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED-TEMPORAL-SIGNATURE BASELINE
# ════════════════════════════════════════════════════════════
# These are the canonical SHA-256 temporal payload signatures for
# the 6 frozen SIGN_CASES.  Generated once at module load time
# from the deterministic pipeline and frozen.
#
# Deterministic: same code + same SIGN_CASES + same contract bridge
# → identical signatures every time.  This is a determinism claim,
# NOT a security claim.

def _build_expected_temporal_signatures() -> Dict[str, str]:
    """
    Generate the frozen expected temporal signatures by running the
    full deterministic pipeline for each SIGN_CASE.

    Returns dict mapping case_label → expected SHA-256 hex signature.
    """
    baseline: Dict[str, str] = {}
    for case in SIGN_CASES:
        sr = sign_temporal_payload(
            payload=case["payload"],
            contract_name=case["contract"],
            transport_mode=case["mode"],
        )
        if sr.verdict == SignatureVerdict.SIGNED:
            baseline[case["label"]] = sr.temporal_signature
    return baseline


# Lazy initialization to avoid slow module import
_EXPECTED_TEMPORAL_SIGNATURES: Optional[Dict[str, str]] = None


def _get_expected_temporal_signatures() -> Dict[str, str]:
    """Get or build the frozen expected-temporal-signature baseline."""
    global _EXPECTED_TEMPORAL_SIGNATURES
    if _EXPECTED_TEMPORAL_SIGNATURES is None:
        _EXPECTED_TEMPORAL_SIGNATURES = _build_expected_temporal_signatures()
    return _EXPECTED_TEMPORAL_SIGNATURES


@dataclass(frozen=True)
class ExpectedTemporalSignatureBaseline:
    """
    Frozen profile defining the expected temporal payload signatures
    for the supported temporal payload family.

    This is a narrow baseline for exactly the 6 frozen SIGN_CASES,
    not a general temporal signature registry.
    """
    version: str = MATCH_VERSION
    supported_cases: Tuple[str, ...] = (
        "rs_4bit_adj_sign",
        "cc_3bit_adj_sign",
        "cc_6bit_cont_sign",
        "rs_containment_sign",
        "fused_adj_sign",
        "rs_5bit_three_sign",
    )

    def get_expected(self, case_label: str) -> Optional[str]:
        """
        Look up the expected signature for a case label.
        Returns None if the case is not in the baseline.
        """
        sigs = _get_expected_temporal_signatures()
        return sigs.get(case_label)

    def is_supported(self, case_label: str) -> bool:
        """Check if a case label is in the frozen baseline."""
        return case_label in self.supported_cases


V1_MATCH_BASELINE = ExpectedTemporalSignatureBaseline()


# ════════════════════════════════════════════════════════════
# MATCH: COMPARE COMPUTED SIGNATURE AGAINST EXPECTED BASELINE
# ════════════════════════════════════════════════════════════

def match_temporal_signature(
    payload: Tuple[int, ...],
    contract_name: str,
    case_label: str,
    transport_mode: str = "rolling_shutter",
    baseline: ExpectedTemporalSignatureBaseline = V1_MATCH_BASELINE,
    profile: TemporalSignatureProfile = V1_SIGNATURE_PROFILE,
) -> TemporalMatchResult:
    """
    Compare a temporal payload's computed signature against the frozen
    expected-temporal-signature baseline.

    Steps:
    1. Check if case_label is in the baseline → UNSUPPORTED if not
    2. Sign the temporal payload via sign_temporal_payload
    3. If signing failed → SIGN_FAILED (or EMPTY_PAYLOAD)
    4. Look up the expected signature by case_label
    5. Compare → MATCH or MISMATCH

    Deterministic: same inputs → identical verdict.
    """
    result = TemporalMatchResult(
        case_label=case_label,
        contract_name=contract_name,
        transport_mode=transport_mode,
    )

    try:
        # Step 1: Check if case is in baseline
        if not baseline.is_supported(case_label):
            result.verdict = TemporalMatchVerdict.UNSUPPORTED
            return result

        # Step 1b: Empty payload check
        if len(payload) == 0:
            result.verdict = TemporalMatchVerdict.EMPTY_PAYLOAD
            return result

        # Step 2: Sign the temporal payload
        sr = sign_temporal_payload(
            payload=payload,
            contract_name=contract_name,
            transport_mode=transport_mode,
            profile=profile,
        )
        result.sign_verdict = sr.verdict.value
        result.computed_signature = sr.temporal_signature
        result.payload = sr.payload
        result.payload_length = sr.payload_length
        result.payload_family = sr.payload_family
        result.is_fused = sr.is_fused

        # Step 3: Check if signing succeeded
        if sr.verdict != SignatureVerdict.SIGNED:
            result.verdict = TemporalMatchVerdict.SIGN_FAILED
            return result

        # Step 4: Look up expected signature
        expected = baseline.get_expected(case_label)
        if expected is None:
            result.verdict = TemporalMatchVerdict.UNSUPPORTED
            return result
        result.expected_signature = expected

        # Step 5: Compare
        if sr.temporal_signature == expected:
            result.verdict = TemporalMatchVerdict.MATCH
        else:
            result.verdict = TemporalMatchVerdict.MISMATCH

        return result

    except Exception:
        result.verdict = TemporalMatchVerdict.ERROR
        return result


def match_from_signature_result(
    sig_result: TemporalSignatureResult,
    case_label: str,
    baseline: ExpectedTemporalSignatureBaseline = V1_MATCH_BASELINE,
) -> TemporalMatchResult:
    """
    Compare an already-computed TemporalSignatureResult against the
    frozen expected-temporal-signature baseline.

    Convenience function for when the caller already has a signed result.
    """
    result = TemporalMatchResult(
        case_label=case_label,
        contract_name=sig_result.contract_name,
        payload=sig_result.payload,
        payload_length=sig_result.payload_length,
        payload_family=sig_result.payload_family,
        transport_mode=sig_result.transport_mode,
        is_fused=sig_result.is_fused,
        sign_verdict=sig_result.verdict.value,
    )

    # Check if case is in baseline
    if not baseline.is_supported(case_label):
        result.verdict = TemporalMatchVerdict.UNSUPPORTED
        return result

    # Check if signing was successful
    if sig_result.verdict != SignatureVerdict.SIGNED:
        result.verdict = TemporalMatchVerdict.SIGN_FAILED
        return result

    result.computed_signature = sig_result.temporal_signature

    # Look up expected
    expected = baseline.get_expected(case_label)
    if expected is None:
        result.verdict = TemporalMatchVerdict.UNSUPPORTED
        return result
    result.expected_signature = expected

    # Compare
    if sig_result.temporal_signature == expected:
        result.verdict = TemporalMatchVerdict.MATCH
    else:
        result.verdict = TemporalMatchVerdict.MISMATCH

    return result


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES
# ════════════════════════════════════════════════════════════

# Cases that should produce MATCH — same payload+contract+mode as SIGN_CASES
MATCH_CASES = tuple(
    {
        "label": c["label"],
        "payload": c["payload"],
        "contract": c["contract"],
        "mode": c["mode"],
        "expected_verdict": "MATCH",
    }
    for c in SIGN_CASES
)

# Cases that should produce MISMATCH — correct case_label but wrong payload
MISMATCH_CASES = (
    {
        "label": "mismatch_wrong_payload",
        "case_label": "rs_4bit_adj_sign",
        "payload": (0, 0, 0, 1),  # different 4-bit adjacent_pair payload (route "00")
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "MISMATCH",
        "description": "Correct case_label but different payload bits → MISMATCH",
    },
    {
        "label": "mismatch_wrong_cc_payload",
        "case_label": "cc_3bit_adj_sign",
        "payload": (0, 0, 0),  # different 3-bit CC payload (route "00" = adjacent_pair)
        "contract": "cc_any_family",
        "mode": "complementary_color",
        "expected_verdict": "MISMATCH",
        "description": "Correct case_label but different CC payload → MISMATCH",
    },
    {
        "label": "mismatch_wrong_three_payload",
        "case_label": "rs_5bit_three_sign",
        "payload": (1, 0, 0, 1, 1),  # different 5-bit three_regions payload
        "contract": "rs_large_three_regions",
        "mode": "rolling_shutter",
        "expected_verdict": "MISMATCH",
        "description": "Correct case_label but different three_regions payload → MISMATCH",
    },
)

# Cases that should produce SIGN_FAILED — case_label exists but payload
# fails contract validation (wrong mode / wrong family / wrong length)
SIGN_FAIL_CASES = (
    {
        "label": "sign_fail_wrong_mode",
        "case_label": "rs_4bit_adj_sign",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "complementary_color",  # RS contract requires rolling_shutter
        "expected_verdict": "SIGN_FAILED",
        "description": "Correct label but wrong transport mode → contract fails → SIGN_FAILED",
    },
    {
        "label": "sign_fail_wrong_family",
        "case_label": "rs_4bit_adj_sign",
        "payload": (0, 1, 1, 0),  # containment family, not adjacent_pair
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "SIGN_FAILED",
        "description": "Correct label but wrong payload family → contract fails → SIGN_FAILED",
    },
)

# Unsupported cases — case_label not in baseline
UNSUPPORTED_CASES = (
    {
        "label": "unsupported_label",
        "case_label": "nonexistent_case",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "UNSUPPORTED",
        "description": "Case label not in frozen baseline → UNSUPPORTED",
    },
    {
        "label": "unsupported_empty_label",
        "case_label": "",
        "payload": (0, 0, 1, 0),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "UNSUPPORTED",
        "description": "Empty case label → UNSUPPORTED",
    },
)

# OOB cases
OOB_CASES = (
    {
        "label": "empty_payload_oob",
        "case_label": "rs_4bit_adj_sign",
        "payload": (),
        "contract": "rs_4bit_adjacent",
        "mode": "rolling_shutter",
        "expected_verdict": "EMPTY_PAYLOAD",
        "description": "Empty payload → EMPTY_PAYLOAD",
    },
)
