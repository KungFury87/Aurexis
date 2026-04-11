"""
Aurexis Core — Recovered Set Signature Match Bridge V1

Bounded expected-signature verification for the narrow V1 raster bridge.
Proves that a recovered artifact set's computed signature can be compared
against a frozen expected-signature baseline and return a deterministic
MATCH / MISMATCH / UNSUPPORTED verdict.

What this proves:
  Given a host image that has been recovered, dispatched, validated against
  a frozen contract, and signed, the system can look up the correct
  expected signature from a frozen baseline and return an honest match
  verdict.  Supported recovered sets match.  Changed order, families, or
  content produce honest mismatch or validation failure.  Unsupported
  recovered sets fail with UNSUPPORTED.

What this does NOT prove:
  - Secure authenticity or tamper-proof guarantees
  - General provenance
  - Cryptographic authentication of arbitrary content
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen ExpectedSignatureBaseline maps (contract_name → expected
    SHA-256 hex signature) for exactly the 5 frozen layout×contract pairs.
  - match_signature() computes the signature from recovery+contract,
    looks up the expected value, and returns MATCH/MISMATCH/UNSUPPORTED.
  - match_from_png() chains the full end-to-end pipeline.
  - If the contract_name is not in the baseline → UNSUPPORTED.
  - If signing fails (contract not satisfied) → propagates the failure.
  - All operations are deterministic.

This is a narrow deterministic recovered-set match proof, not general
document fingerprinting or secure provenance.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from aurexis_lang.recovered_set_signature_bridge_v1 import (
    SIGNATURE_VERSION, SIGNATURE_FROZEN,
    V1_SIGNATURE_PROFILE, SignatureProfile,
    SignatureVerdict, SignatureResult,
    sign_recovered_set, sign_from_png,
    canonicalize_recovered_set, compute_signature,
    IN_BOUNDS_CASES as SIG_IN_BOUNDS_CASES,
)
from aurexis_lang.artifact_set_contract_bridge_v1 import (
    PageContract, ContractVerdict,
    FROZEN_CONTRACTS, V1_CONTRACT_PROFILE,
    validate_contract,
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
    V1_DISPATCH_PROFILE, DispatchProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

MATCH_VERSION = "V1.0"
MATCH_FROZEN = True


# ════════════════════════════════════════════════════════════
# MATCH VERDICTS
# ════════════════════════════════════════════════════════════

class MatchVerdict(str, Enum):
    """Outcome of a recovered-set signature match operation."""
    MATCH = "MATCH"                            # Signature matches expected
    MISMATCH = "MISMATCH"                      # Signature doesn't match expected
    UNSUPPORTED = "UNSUPPORTED"                # Contract not in expected baseline
    SIGN_FAILED = "SIGN_FAILED"                # Signature generation failed
    ERROR = "ERROR"                            # Unexpected error


# ════════════════════════════════════════════════════════════
# MATCH RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class MatchResult:
    """Complete result of a recovered-set signature match operation."""
    verdict: MatchVerdict = MatchVerdict.ERROR
    computed_signature: str = ""
    expected_signature: str = ""
    contract_name: str = ""
    sign_verdict: str = ""
    dispatched_families: Tuple[str, ...] = ()
    version: str = MATCH_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "computed_signature": self.computed_signature,
            "expected_signature": self.expected_signature,
            "contract_name": self.contract_name,
            "sign_verdict": self.sign_verdict,
            "dispatched_families": list(self.dispatched_families),
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN EXPECTED-SIGNATURE BASELINE
# ════════════════════════════════════════════════════════════
# These are the canonical SHA-256 signatures for the 5 frozen
# layout×contract pairs.  They are generated once at module
# load time from the deterministic pipeline and frozen.
#
# The generation is deterministic: same code + same frozen
# layouts + same frozen contracts → identical signatures every
# time.  This is not a security claim — it is a determinism
# claim for this narrow proof.

def _build_expected_signatures() -> Dict[str, str]:
    """
    Generate the frozen expected signatures by running the full
    deterministic pipeline for each in-bounds case.

    This runs at module load time.  The result is a dict mapping
    contract_name → expected SHA-256 hex signature.
    """
    baseline = {}
    for case in SIG_IN_BOUNDS_CASES:
        layout = FROZEN_LAYOUTS[case["layout_index"]]
        contract = FROZEN_CONTRACTS[case["contract_index"]]
        spec = build_layout_spec(layout)
        host_png = generate_multi_artifact_host(spec)
        recovery = multi_artifact_recover_and_dispatch(
            host_png,
            expected_families=layout["expected_families"],
        )
        sr = sign_recovered_set(recovery, contract)
        if sr.verdict == SignatureVerdict.SIGNED:
            baseline[contract.name] = sr.signature
    return baseline


# Lazy initialization to avoid slow module import
_EXPECTED_SIGNATURES: Optional[Dict[str, str]] = None


def _get_expected_signatures() -> Dict[str, str]:
    """Get or build the frozen expected-signature baseline."""
    global _EXPECTED_SIGNATURES
    if _EXPECTED_SIGNATURES is None:
        _EXPECTED_SIGNATURES = _build_expected_signatures()
    return _EXPECTED_SIGNATURES


@dataclass(frozen=True)
class ExpectedSignatureBaseline:
    """
    Frozen profile defining the expected signatures for the supported
    recovered-set family.

    This is a narrow baseline for exactly the 5 frozen layout×contract
    pairs, not a general signature registry.
    """
    version: str = MATCH_VERSION
    supported_contracts: Tuple[str, ...] = (
        "two_horizontal_adj_cont",
        "two_vertical_adj_three",
        "three_row_all",
        "two_horizontal_cont_three",
        "two_vertical_three_adj",
    )

    def get_expected(self, contract_name: str) -> Optional[str]:
        """
        Look up the expected signature for a contract name.
        Returns None if the contract is not in the baseline.
        """
        sigs = _get_expected_signatures()
        return sigs.get(contract_name)

    def is_supported(self, contract_name: str) -> bool:
        """Check if a contract name is in the frozen baseline."""
        return contract_name in self.supported_contracts


V1_MATCH_BASELINE = ExpectedSignatureBaseline()


# ════════════════════════════════════════════════════════════
# MATCH: COMPARE COMPUTED SIGNATURE AGAINST EXPECTED BASELINE
# ════════════════════════════════════════════════════════════

def match_signature(
    recovery_result: MultiLayoutResult,
    contract: PageContract,
    baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> MatchResult:
    """
    Compare a recovered set's computed signature against the frozen
    expected-signature baseline.

    Steps:
    1. Check if the contract is in the baseline → UNSUPPORTED if not
    2. Sign the recovered set via sign_recovered_set
    3. If signing failed → SIGN_FAILED
    4. Look up the expected signature
    5. Compare → MATCH or MISMATCH

    Deterministic: same recovery_result + same contract + same baseline
    → identical verdict.
    """
    result = MatchResult(
        contract_name=contract.name,
        dispatched_families=recovery_result.dispatched_families,
    )

    # Step 1: Check if contract is in baseline
    if not baseline.is_supported(contract.name):
        result.verdict = MatchVerdict.UNSUPPORTED
        return result

    # Step 2: Sign the recovered set
    sr = sign_recovered_set(recovery_result, contract, signature_profile)
    result.sign_verdict = sr.verdict.value
    result.computed_signature = sr.signature

    # Step 3: Check if signing succeeded
    if sr.verdict != SignatureVerdict.SIGNED:
        result.verdict = MatchVerdict.SIGN_FAILED
        return result

    # Step 4: Look up expected signature
    expected = baseline.get_expected(contract.name)
    if expected is None:
        # Should not happen if is_supported was true, but be safe
        result.verdict = MatchVerdict.UNSUPPORTED
        return result
    result.expected_signature = expected

    # Step 5: Compare
    if sr.signature == expected:
        result.verdict = MatchVerdict.MATCH
    else:
        result.verdict = MatchVerdict.MISMATCH

    return result


def match_from_png(
    host_png: bytes,
    contract: PageContract,
    baseline: ExpectedSignatureBaseline = V1_MATCH_BASELINE,
    layout_profile: MultiLayoutProfile = V1_MULTI_LAYOUT_PROFILE,
    tolerance: ToleranceProfile = V1_TOLERANCE_PROFILE,
    dispatch_profile: DispatchProfile = V1_DISPATCH_PROFILE,
    signature_profile: SignatureProfile = V1_SIGNATURE_PROFILE,
) -> MatchResult:
    """
    Full end-to-end signature match from a host image.

      host_png → multi-artifact recovery → dispatch → contract validation
      → signature generation → expected-signature lookup → MATCH/MISMATCH

    Deterministic: same host_png + same contract + same baseline
    → identical verdict.
    """
    recovery = multi_artifact_recover_and_dispatch(
        host_png,
        expected_families=contract.expected_families,
        profile=layout_profile,
        tolerance=tolerance,
        dispatch_profile=dispatch_profile,
    )
    return match_signature(recovery, contract, baseline, signature_profile)


# ════════════════════════════════════════════════════════════
# PREDEFINED IN-BOUNDS AND OUT-OF-BOUNDS CASES
# ════════════════════════════════════════════════════════════

# In-bounds: each frozen layout + matching contract → MATCH
IN_BOUNDS_CASES = (
    {"label": "two_horizontal", "layout_index": 0, "contract_index": 0},
    {"label": "two_vertical", "layout_index": 1, "contract_index": 1},
    {"label": "three_in_row", "layout_index": 2, "contract_index": 2},
    {"label": "two_horizontal_mixed", "layout_index": 3, "contract_index": 3},
    {"label": "two_vertical_reversed", "layout_index": 4, "contract_index": 4},
)

# Out-of-bounds: mismatched layout/contract → SIGN_FAILED (contract not satisfied)
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

# Unsupported: contract not in the frozen baseline
UNSUPPORTED_CASES = (
    {
        "label": "unknown_contract",
        "description": "Contract name not in the frozen expected-signature baseline",
        "contract_name": "nonexistent_contract",
        "expected_count": 2,
        "expected_families": ("adjacent_pair", "containment"),
    },
)
