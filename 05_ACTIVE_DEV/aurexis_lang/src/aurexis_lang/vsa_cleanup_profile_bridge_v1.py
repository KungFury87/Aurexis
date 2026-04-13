"""
Aurexis Core — VSA Cleanup Profile Bridge V1

Bounded executable profile defining which deterministic substrate outputs
can be projected into a hyperdimensional (VSA) representation for cleanup
and noise-tolerant retrieval.

What this proves:
  A small frozen family of cleanup targets exists, each mapping a known
  deterministic substrate output (artifact set contract name, sequence
  contract name, or collection contract name) to a VSA-ready symbol
  identifier. The profile is explicit and bounded.

What this does NOT prove:
  - Full hyperdimensional computing generality
  - Noise-robust real-camera cleanup
  - VSA as a replacement for the deterministic substrate
  - Full Aurexis Core completion

Design:
  - CleanupTargetKind: enum of SET_CONTRACT, SEQUENCE_CONTRACT,
    COLLECTION_CONTRACT — the three levels of substrate output.
  - CleanupTarget: frozen record linking a substrate name to a symbol ID.
  - CleanupProfile: frozen profile of all supported cleanup targets.
  - V1_CLEANUP_PROFILE: the frozen instance.
  - All operations are deterministic and read-only.

The VSA cleanup layer is an AUXILIARY helper layer. It does NOT replace
the deterministic substrate. It compresses/cleans substrate outputs and
is always checked against the substrate truth.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from enum import Enum


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

CLEANUP_PROFILE_VERSION = "V1.0"
CLEANUP_PROFILE_FROZEN = True


# ════════════════════════════════════════════════════════════
# CLEANUP TARGET KIND
# ════════════════════════════════════════════════════════════

class CleanupTargetKind(str, Enum):
    """Which level of substrate output this target maps."""
    SET_CONTRACT = "SET_CONTRACT"
    SEQUENCE_CONTRACT = "SEQUENCE_CONTRACT"
    COLLECTION_CONTRACT = "COLLECTION_CONTRACT"


# ════════════════════════════════════════════════════════════
# CLEANUP TARGET
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CleanupTarget:
    """
    A single cleanup target mapping a deterministic substrate output
    to a VSA symbol identifier.

    substrate_name: the name from the frozen substrate contract (e.g.,
                    "two_horizontal_adj_cont").
    kind: which level of substrate hierarchy.
    symbol_id: unique VSA symbol identifier for this target.
    description: human-readable description.
    """
    substrate_name: str = ""
    kind: CleanupTargetKind = CleanupTargetKind.SET_CONTRACT
    symbol_id: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "substrate_name": self.substrate_name,
            "kind": self.kind.value,
            "symbol_id": self.symbol_id,
            "description": self.description,
        }


# ════════════════════════════════════════════════════════════
# CLEANUP PROFILE
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CleanupProfile:
    """Frozen profile of all supported cleanup targets."""
    targets: Tuple[CleanupTarget, ...] = ()
    version: str = CLEANUP_PROFILE_VERSION

    @property
    def target_count(self) -> int:
        return len(self.targets)

    def get_target(self, symbol_id: str) -> Optional[CleanupTarget]:
        for t in self.targets:
            if t.symbol_id == symbol_id:
                return t
        return None

    def get_target_by_substrate_name(self, name: str) -> Optional[CleanupTarget]:
        for t in self.targets:
            if t.substrate_name == name:
                return t
        return None

    def get_targets_by_kind(self, kind: CleanupTargetKind) -> Tuple[CleanupTarget, ...]:
        return tuple(t for t in self.targets if t.kind == kind)

    @property
    def all_symbol_ids(self) -> Tuple[str, ...]:
        return tuple(t.symbol_id for t in self.targets)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_count": self.target_count,
            "targets": [t.to_dict() for t in self.targets],
            "version": self.version,
        }


# ════════════════════════════════════════════════════════════
# FROZEN CLEANUP TARGETS
# ════════════════════════════════════════════════════════════

# --- Set contract targets (from artifact_set_contract_bridge_v1) ---
_SET_TARGETS = (
    CleanupTarget(
        substrate_name="two_horizontal_adj_cont",
        kind=CleanupTargetKind.SET_CONTRACT,
        symbol_id="SET_TWO_H_AC",
        description="Two horizontal artifacts: adjacent_pair + containment",
    ),
    CleanupTarget(
        substrate_name="two_vertical_adj_three",
        kind=CleanupTargetKind.SET_CONTRACT,
        symbol_id="SET_TWO_V_AT",
        description="Two vertical artifacts: adjacent_pair + three_regions",
    ),
    CleanupTarget(
        substrate_name="three_row_all",
        kind=CleanupTargetKind.SET_CONTRACT,
        symbol_id="SET_THREE_ALL",
        description="Three in row: all families",
    ),
    CleanupTarget(
        substrate_name="two_horizontal_cont_three",
        kind=CleanupTargetKind.SET_CONTRACT,
        symbol_id="SET_TWO_H_CT",
        description="Two horizontal: containment + three_regions",
    ),
    CleanupTarget(
        substrate_name="two_vertical_three_adj",
        kind=CleanupTargetKind.SET_CONTRACT,
        symbol_id="SET_TWO_V_TA",
        description="Two vertical: three_regions + adjacent_pair",
    ),
)

# --- Sequence contract targets (from recovered_page_sequence_contract_bridge_v1) ---
_SEQ_TARGETS = (
    CleanupTarget(
        substrate_name="two_page_horizontal_vertical",
        kind=CleanupTargetKind.SEQUENCE_CONTRACT,
        symbol_id="SEQ_TWO_HV",
        description="Two-page sequence: horizontal then vertical",
    ),
    CleanupTarget(
        substrate_name="three_page_all_families",
        kind=CleanupTargetKind.SEQUENCE_CONTRACT,
        symbol_id="SEQ_THREE_ALL",
        description="Three-page sequence: all families",
    ),
    CleanupTarget(
        substrate_name="two_page_mixed_reversed",
        kind=CleanupTargetKind.SEQUENCE_CONTRACT,
        symbol_id="SEQ_TWO_MR",
        description="Two-page sequence: mixed reversed",
    ),
)

# --- Collection contract targets (from recovered_sequence_collection_contract_bridge_v1) ---
_COLL_TARGETS = (
    CleanupTarget(
        substrate_name="two_seq_hv_mixed",
        kind=CleanupTargetKind.COLLECTION_CONTRACT,
        symbol_id="COLL_TWO_HVM",
        description="Two-sequence collection: hv + mixed",
    ),
    CleanupTarget(
        substrate_name="three_seq_all",
        kind=CleanupTargetKind.COLLECTION_CONTRACT,
        symbol_id="COLL_THREE_ALL",
        description="Three-sequence collection: all",
    ),
    CleanupTarget(
        substrate_name="two_seq_all_mixed",
        kind=CleanupTargetKind.COLLECTION_CONTRACT,
        symbol_id="COLL_TWO_AM",
        description="Two-sequence collection: all + mixed",
    ),
)

# ════════════════════════════════════════════════════════════
# FROZEN PROFILE INSTANCE
# ════════════════════════════════════════════════════════════

FROZEN_TARGETS = _SET_TARGETS + _SEQ_TARGETS + _COLL_TARGETS

V1_CLEANUP_PROFILE = CleanupProfile(
    targets=FROZEN_TARGETS,
)

# ════════════════════════════════════════════════════════════
# PREDEFINED COUNTS
# ════════════════════════════════════════════════════════════

EXPECTED_SET_TARGET_COUNT = 5
EXPECTED_SEQ_TARGET_COUNT = 3
EXPECTED_COLL_TARGET_COUNT = 3
EXPECTED_TOTAL_TARGET_COUNT = 11
FROZEN_SYMBOL_IDS = V1_CLEANUP_PROFILE.all_symbol_ids
