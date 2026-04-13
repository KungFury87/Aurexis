"""
Aurexis Core — Frame-Accurate Transport Bridge V1

Bounded temporal slot-identity preservation proof for the narrow V1 temporal
transport branch.  Proves that a small frozen family of ordered temporal display
sequences can be generated, transported, captured, decoded, and that the
per-slot payload association and slot ordering are deterministically recovered.

What this proves:
  Given a frozen temporal display sequence (an ordered list of per-slot payloads
  under a single transport mode), the system can:
  1. Generate the full multi-slot display sequence.
  2. Transport each slot through the existing temporal transport pipeline.
  3. Capture and decode each slot independently.
  4. Recover the per-slot payload in the correct ordered position.
  5. Compare the recovered ordered slot sequence against the intended sequence
     and produce a deterministic pass/fail verdict.

  Supported bounded sequence shapes (frozen family):
  - 2-slot sequences (two ordered payloads)
  - 3-slot sequences (three ordered payloads)
  - 4-slot sequences (four ordered payloads)

  Each slot carries a bounded payload (3–8 bits depending on mode) and a
  deterministic slot ID derived from its position in the sequence.

  Sequences where slot ordering is ambiguous, a slot fails to decode, or slot
  identity drifts are honestly rejected.

What this does NOT prove:
  - Full synchronization theory
  - Full RS-OFDM timing recovery
  - General video decoding
  - Unconstrained frame-rate robustness
  - Noise-tolerant real-world timing recovery
  - Arbitrary-length temporal sequences
  - Full camera capture robustness
  - Full image-as-program completion
  - Full Aurexis Core completion

Design:
  - A frozen FrameAccurateProfile defines: the supported sequence lengths,
    the underlying dispatch profile reference, and the version.
  - Each slot in a display sequence is represented as a SlotRecord containing
    the slot index, the payload, the transport mode, and the capture signal.
  - Generation: produces an ordered list of slot signals by encoding each
    payload through the appropriate transport mode's encoder.
  - Recovery: dispatches each slot signal through the existing temporal
    dispatch bridge, recording the decoded payload and slot index.
  - Verification: compares the recovered ordered payloads against the
    intended ordered payloads, slot-by-slot.
  - A FrameAccurateResult records: verdict, per-slot details, the intended
    vs recovered sequence, and a deterministic frame-accurate signature.
  - All operations are deterministic and use only stdlib + existing bridges.

This is a narrow deterministic temporal slot-identity proof, not general
synchronization or full temporal fusion.

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

from aurexis_lang.rolling_shutter_temporal_transport_bridge_v1 import (
    V1_TRANSPORT_PROFILE,
)

from aurexis_lang.complementary_color_temporal_transport_bridge_v1 import (
    V1_CC_TRANSPORT_PROFILE,
    ComplementaryColorTransportProfile,
)


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

FRAME_ACCURATE_VERSION = "V1.0"
FRAME_ACCURATE_FROZEN = True


# ════════════════════════════════════════════════════════════
# FRAME-ACCURATE VERDICTS
# ════════════════════════════════════════════════════════════

class FrameAccurateVerdict(str, Enum):
    """Outcome of a frame-accurate transport verification."""
    FRAME_ACCURATE = "FRAME_ACCURATE"                # All slots recovered in correct order
    SLOT_MISMATCH = "SLOT_MISMATCH"                  # Recovered payload differs at one or more slots
    SLOT_DECODE_FAILED = "SLOT_DECODE_FAILED"        # One or more slots failed to decode
    SEQUENCE_TOO_SHORT = "SEQUENCE_TOO_SHORT"        # Fewer than minimum slots
    SEQUENCE_TOO_LONG = "SEQUENCE_TOO_LONG"          # More than maximum slots
    EMPTY_SEQUENCE = "EMPTY_SEQUENCE"                # No slots provided
    GENERATION_FAILED = "GENERATION_FAILED"          # Signal generation failed for a slot
    ERROR = "ERROR"                                  # Unexpected error


# ════════════════════════════════════════════════════════════
# FROZEN SEQUENCE LENGTH FAMILY
# ════════════════════════════════════════════════════════════

SUPPORTED_SEQUENCE_LENGTHS: Tuple[int, ...] = (2, 3, 4)
MIN_SEQUENCE_LENGTH: int = 2
MAX_SEQUENCE_LENGTH: int = 4


# ════════════════════════════════════════════════════════════
# FRAME-ACCURATE PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FrameAccurateProfile:
    """
    Frozen profile defining the bounded temporal sequence family.

    supported_sequence_lengths: the frozen set of supported slot counts.
    min_sequence_length: minimum number of ordered slots.
    max_sequence_length: maximum number of ordered slots.
    supported_modes: the transport modes available for per-slot encoding.
    dispatch_profile: the dispatch profile used for per-slot recovery.
    version: profile version string.
    """
    supported_sequence_lengths: Tuple[int, ...] = SUPPORTED_SEQUENCE_LENGTHS
    min_sequence_length: int = MIN_SEQUENCE_LENGTH
    max_sequence_length: int = MAX_SEQUENCE_LENGTH
    supported_modes: Tuple[str, ...] = ("rolling_shutter", "complementary_color")
    dispatch_profile: TemporalDispatchProfile = V1_DISPATCH_PROFILE
    version: str = FRAME_ACCURATE_VERSION


V1_FRAME_ACCURATE_PROFILE = FrameAccurateProfile()


# ════════════════════════════════════════════════════════════
# SLOT RECORD — PER-SLOT DETAIL
# ════════════════════════════════════════════════════════════

@dataclass
class SlotRecord:
    """Detail record for a single temporal slot in a sequence."""
    slot_index: int = 0
    intended_payload: Tuple[int, ...] = ()
    recovered_payload: Tuple[int, ...] = ()
    transport_mode: str = ""
    dispatch_verdict: str = ""
    route_name: str = ""
    slot_match: bool = False
    succeeded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_index": self.slot_index,
            "intended_payload": list(self.intended_payload),
            "recovered_payload": list(self.recovered_payload),
            "transport_mode": self.transport_mode,
            "dispatch_verdict": self.dispatch_verdict,
            "route_name": self.route_name,
            "slot_match": self.slot_match,
            "succeeded": self.succeeded,
        }


# ════════════════════════════════════════════════════════════
# FRAME-ACCURATE RESULT
# ════════════════════════════════════════════════════════════

@dataclass
class FrameAccurateResult:
    """Complete result of a frame-accurate transport verification."""
    verdict: FrameAccurateVerdict = FrameAccurateVerdict.ERROR
    sequence_length: int = 0
    transport_mode: str = ""
    intended_payloads: Tuple[Tuple[int, ...], ...] = ()
    recovered_payloads: Tuple[Tuple[int, ...], ...] = ()
    slot_records: List[SlotRecord] = field(default_factory=list)
    slots_matched: int = 0
    first_mismatch_index: int = -1
    frame_accurate_signature: str = ""
    version: str = FRAME_ACCURATE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "sequence_length": self.sequence_length,
            "transport_mode": self.transport_mode,
            "intended_payloads": [list(p) for p in self.intended_payloads],
            "recovered_payloads": [list(p) for p in self.recovered_payloads],
            "slot_records": [r.to_dict() for r in self.slot_records],
            "slots_matched": self.slots_matched,
            "first_mismatch_index": self.first_mismatch_index,
            "frame_accurate_signature": self.frame_accurate_signature,
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FRAME-ACCURATE SIGNATURE — DETERMINISTIC FINGERPRINT
# ════════════════════════════════════════════════════════════

def compute_frame_accurate_signature(
    mode: str,
    ordered_payloads: Tuple[Tuple[int, ...], ...],
    sequence_length: int,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of a frame-accurate result.

    Canonical form:
        frame_accurate_mode=<mode>
        sequence_length=<n>
        slot_0=<bits>
        slot_1=<bits>
        ...
        version=<version>

    Deterministic: same mode + same ordered payloads → identical signature.
    """
    parts = [
        f"frame_accurate_mode={mode}",
        f"sequence_length={sequence_length}",
    ]
    for i, payload in enumerate(ordered_payloads):
        bits_str = ",".join(str(b) for b in payload)
        parts.append(f"slot_{i}={bits_str}")
    parts.append(f"version={FRAME_ACCURATE_VERSION}")
    canonical = "\n".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ════════════════════════════════════════════════════════════
# GENERATION: PRODUCE ORDERED SLOT SIGNALS
# ════════════════════════════════════════════════════════════

def generate_sequence_signals(
    ordered_payloads: Tuple[Tuple[int, ...], ...],
    mode: str = "rolling_shutter",
    profile: FrameAccurateProfile = V1_FRAME_ACCURATE_PROFILE,
) -> Optional[List]:
    """
    Generate an ordered list of transport signals, one per slot.

    Each slot's payload is encoded independently using the specified
    transport mode's encoder.  The resulting signals preserve the
    original slot ordering by list position.

    Returns None if any slot fails to generate a signal.
    """
    if mode not in profile.supported_modes:
        return None

    signals = []
    for payload in ordered_payloads:
        if mode == "rolling_shutter":
            signal = generate_rs_signal(payload, profile.dispatch_profile)
        elif mode == "complementary_color":
            signal = generate_cc_signal(payload, profile.dispatch_profile)
        else:
            return None

        if signal is None:
            return None
        signals.append(signal)

    return signals


# ════════════════════════════════════════════════════════════
# RECOVERY: DISPATCH EACH SLOT AND RECOVER ORDERED PAYLOADS
# ════════════════════════════════════════════════════════════

def recover_sequence(
    slot_signals: List,
    mode: str = "rolling_shutter",
    profile: FrameAccurateProfile = V1_FRAME_ACCURATE_PROFILE,
    per_slot_rs_counts: Optional[List[int]] = None,
) -> List[TemporalDispatchResult]:
    """
    Dispatch each slot signal through the existing temporal dispatch bridge
    and return the ordered list of dispatch results.

    Slot ordering is preserved by list position — slot_signals[0] is
    always dispatched first, slot_signals[1] second, etc.

    per_slot_rs_counts: if provided, per_slot_rs_counts[i] is the
    expected RS slot count for slot i (needed because different slots
    may have different payload lengths).

    This is deterministic: same input signals → identical dispatch results.
    """
    results = []
    for i, signal in enumerate(slot_signals):
        rs_count = 0
        if per_slot_rs_counts and i < len(per_slot_rs_counts):
            rs_count = per_slot_rs_counts[i]
        result = dispatch_temporal_signal(
            signal,
            expected_rs_slot_count=rs_count,
            profile=profile.dispatch_profile,
        )
        results.append(result)
    return results


# ════════════════════════════════════════════════════════════
# VERIFICATION: CHECK FRAME-ACCURATE SLOT IDENTITY
# ════════════════════════════════════════════════════════════

def verify_frame_accuracy(
    ordered_payloads: Tuple[Tuple[int, ...], ...],
    mode: str = "rolling_shutter",
    profile: FrameAccurateProfile = V1_FRAME_ACCURATE_PROFILE,
    expected_rs_slot_count: int = 0,
) -> FrameAccurateResult:
    """
    Full end-to-end frame-accurate transport verification.

    Steps:
    1. Validate sequence length against frozen profile.
    2. Generate per-slot transport signals.
    3. Dispatch each slot through the existing temporal dispatch bridge.
    4. Compare recovered payloads against intended payloads, slot-by-slot.
    5. Produce FRAME_ACCURATE if all slots match in order, or an honest
       failure verdict otherwise.

    For RS mode, if expected_rs_slot_count is 0, per-slot counts are
    computed automatically from each slot's payload length + sync header.

    Deterministic: same inputs → identical result.
    """
    result = FrameAccurateResult(
        transport_mode=mode,
        intended_payloads=ordered_payloads,
    )

    try:
        seq_len = len(ordered_payloads)
        result.sequence_length = seq_len

        # Step 1: Validate sequence length
        if seq_len == 0:
            result.verdict = FrameAccurateVerdict.EMPTY_SEQUENCE
            return result

        if seq_len < profile.min_sequence_length:
            result.verdict = FrameAccurateVerdict.SEQUENCE_TOO_SHORT
            return result

        if seq_len > profile.max_sequence_length:
            result.verdict = FrameAccurateVerdict.SEQUENCE_TOO_LONG
            return result

        if seq_len not in profile.supported_sequence_lengths:
            result.verdict = FrameAccurateVerdict.SEQUENCE_TOO_SHORT
            return result

        # Step 2: Generate signals
        signals = generate_sequence_signals(ordered_payloads, mode, profile)
        if signals is None:
            result.verdict = FrameAccurateVerdict.GENERATION_FAILED
            return result

        # Step 3: Compute per-slot RS slot counts
        per_slot_rs_counts = None
        if mode == "rolling_shutter":
            sync_len = len(profile.dispatch_profile.rs_profile.sync_header)
            if expected_rs_slot_count > 0:
                # Use uniform count if explicitly provided
                per_slot_rs_counts = [expected_rs_slot_count] * seq_len
            else:
                # Auto-compute per-slot from payload length
                per_slot_rs_counts = [
                    sync_len + len(p) for p in ordered_payloads
                ]

        # Step 4: Dispatch each slot
        dispatch_results = recover_sequence(
            signals, mode, profile, per_slot_rs_counts
        )

        # Step 4: Build per-slot records and compare
        recovered_list = []
        slot_records = []
        all_matched = True
        first_mismatch = -1

        for i, (intended, dispatch_r) in enumerate(
            zip(ordered_payloads, dispatch_results)
        ):
            rec = SlotRecord(
                slot_index=i,
                intended_payload=intended,
                transport_mode=mode,
            )

            if dispatch_r.verdict == DispatchVerdict.DISPATCHED:
                rec.succeeded = True
                rec.recovered_payload = dispatch_r.decoded_payload
                rec.dispatch_verdict = dispatch_r.verdict.value
                rec.route_name = dispatch_r.route_name
                rec.slot_match = (dispatch_r.decoded_payload == intended)
                recovered_list.append(dispatch_r.decoded_payload)

                if not rec.slot_match and all_matched:
                    all_matched = False
                    first_mismatch = i
            else:
                rec.succeeded = False
                rec.dispatch_verdict = dispatch_r.verdict.value
                rec.recovered_payload = ()
                rec.slot_match = False
                recovered_list.append(())

                if all_matched:
                    all_matched = False
                    first_mismatch = i

            slot_records.append(rec)

        result.slot_records = slot_records
        result.recovered_payloads = tuple(recovered_list)
        result.slots_matched = sum(1 for r in slot_records if r.slot_match)
        result.first_mismatch_index = first_mismatch

        # Step 5: Produce verdict
        if not all(r.succeeded for r in slot_records):
            result.verdict = FrameAccurateVerdict.SLOT_DECODE_FAILED
            return result

        if all_matched:
            result.verdict = FrameAccurateVerdict.FRAME_ACCURATE
            result.frame_accurate_signature = compute_frame_accurate_signature(
                mode, ordered_payloads, seq_len
            )
        else:
            result.verdict = FrameAccurateVerdict.SLOT_MISMATCH

        return result

    except Exception:
        result.verdict = FrameAccurateVerdict.ERROR
        return result


# ════════════════════════════════════════════════════════════
# CONVENIENCE: GENERATE DRIFTED SEQUENCE
# ════════════════════════════════════════════════════════════

def generate_drifted_sequence(
    base_payloads: Tuple[Tuple[int, ...], ...],
    drift_index: int,
    drifted_payload: Tuple[int, ...],
) -> Tuple[Tuple[int, ...], ...]:
    """
    Create a copy of the sequence with one slot's payload replaced,
    simulating temporal drift at a specific position.
    """
    mutated = list(base_payloads)
    mutated[drift_index] = drifted_payload
    return tuple(mutated)


# ════════════════════════════════════════════════════════════
# PREDEFINED TEST CASES — FROZEN IN-BOUNDS FAMILY
# ════════════════════════════════════════════════════════════

# RS in-bounds: sequences that should recover FRAME_ACCURATE
RS_FRAME_CASES = (
    {
        "label": "rs_2slot_adj_cont",
        "payloads": ((0, 0, 1, 0), (0, 1, 1, 0)),
        "mode": "rolling_shutter",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": ("adjacent_pair", "containment"),
        "description": "2-slot RS: adjacent_pair then containment",
    },
    {
        "label": "rs_3slot_adj_cont_three",
        "payloads": ((0, 0, 1, 0), (0, 1, 1, 0), (1, 0, 1, 0, 1)),
        "mode": "rolling_shutter",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": ("adjacent_pair", "containment", "three_regions"),
        "description": "3-slot RS: adj→cont→three",
    },
    {
        "label": "rs_4slot_all_adj",
        "payloads": (
            (0, 0, 1, 0),
            (0, 0, 0, 1),
            (0, 0, 1, 1),
            (0, 0, 0, 0, 1, 0),
        ),
        "mode": "rolling_shutter",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": (
            "adjacent_pair",
            "adjacent_pair",
            "adjacent_pair",
            "adjacent_pair",
        ),
        "description": "4-slot RS: four adjacent_pair payloads",
    },
    {
        "label": "rs_2slot_same_payload",
        "payloads": ((0, 1, 1, 0), (0, 1, 1, 0)),
        "mode": "rolling_shutter",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": ("containment", "containment"),
        "description": "2-slot RS: identical payload at both positions",
    },
)

# CC in-bounds: sequences that should recover FRAME_ACCURATE
CC_FRAME_CASES = (
    {
        "label": "cc_2slot_adj_cont",
        "payloads": ((0, 0, 1), (0, 1, 0)),
        "mode": "complementary_color",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": ("adjacent_pair", "containment"),
        "description": "2-slot CC: adjacent_pair then containment",
    },
    {
        "label": "cc_3slot_mixed_routes",
        "payloads": ((0, 0, 1), (0, 1, 0), (1, 0, 0, 1)),
        "mode": "complementary_color",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": ("adjacent_pair", "containment", "three_regions"),
        "description": "3-slot CC: adj→cont→three",
    },
    {
        "label": "cc_4slot_all_adj",
        "payloads": (
            (0, 0, 1),
            (0, 0, 0, 1),
            (0, 0, 1, 0, 1),
            (0, 0, 1, 0, 1, 0),
        ),
        "mode": "complementary_color",
        "expected_verdict": "FRAME_ACCURATE",
        "expected_routes": (
            "adjacent_pair",
            "adjacent_pair",
            "adjacent_pair",
            "adjacent_pair",
        ),
        "description": "4-slot CC: four adjacent_pair payloads with varying lengths",
    },
)

# Drifted / mismatch cases
DRIFT_CASES = (
    {
        "label": "rs_drift_slot1",
        "base_payloads": ((0, 0, 1, 0), (0, 1, 1, 0)),
        "drift_index": 1,
        "drifted_payload": (1, 0, 1, 0, 1),
        "mode": "rolling_shutter",
        "expected_verdict": "SLOT_MISMATCH",
        "description": "2-slot RS: slot 1 drifted to different payload",
    },
    {
        "label": "cc_drift_slot0",
        "base_payloads": ((0, 0, 1), (0, 1, 0)),
        "drift_index": 0,
        "drifted_payload": (1, 0, 1),
        "mode": "complementary_color",
        "expected_verdict": "SLOT_MISMATCH",
        "description": "2-slot CC: slot 0 drifted to different payload",
    },
)

# OOB cases
OOB_CASES = (
    {
        "label": "empty_sequence",
        "payloads": (),
        "mode": "rolling_shutter",
        "expected_verdict": "EMPTY_SEQUENCE",
    },
    {
        "label": "single_slot",
        "payloads": ((0, 0, 1, 0),),
        "mode": "rolling_shutter",
        "expected_verdict": "SEQUENCE_TOO_SHORT",
    },
    {
        "label": "five_slots",
        "payloads": (
            (0, 0, 1, 0),
            (0, 1, 1, 0),
            (1, 0, 1, 0, 1),
            (0, 0, 0, 1),
            (0, 0, 1, 1),
        ),
        "mode": "rolling_shutter",
        "expected_verdict": "SEQUENCE_TOO_LONG",
    },
)
