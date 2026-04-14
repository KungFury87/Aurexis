"""
Aurexis Core — Evidence Delta Analysis Bridge V1

Compares observed capture outputs against expected/known bounded
substrate outputs and produces explicit delta surfaces.

What this proves:
  Given an expected substrate output (a set of primitives with
  confidence bands, contract verdicts, and signature outcomes) and
  an observed capture output (the same structure extracted from a
  real capture), the delta analysis produces a deterministic,
  bounded comparison showing exactly what changed.

What this does NOT prove:
  - Why a delta occurred (root-cause analysis)
  - Automatic correction of deltas
  - Full real-world robustness
  - Full Aurexis Core completion

Design:
  - ExpectedOutput: frozen record of expected substrate outputs.
  - ObservedOutput: frozen record of observed capture outputs.
  - PrimitiveDelta: one primitive-level difference.
  - ConfidenceBandDelta: confidence band shift.
  - ContractDelta: contract verdict change.
  - SignatureDelta: signature outcome change.
  - DeltaSurface: full delta analysis result.
  - analyze_deltas(): compares expected vs observed.
  - DeltaVerdict: IDENTICAL / WITHIN_TOLERANCE / DEGRADED /
    MISSING_PRIMITIVES / EXTRA_PRIMITIVES / MIXED.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
import hashlib
import json


# ════════════════════════════════════════════════════════════
# MODULE VERSION
# ════════════════════════════════════════════════════════════

DELTA_ANALYSIS_VERSION = "V1.0"
DELTA_ANALYSIS_FROZEN = True


# ════════════════════════════════════════════════════════════
# DELTA VERDICT
# ════════════════════════════════════════════════════════════

class DeltaVerdict(str, Enum):
    """Overall verdict for a delta analysis."""
    IDENTICAL = "IDENTICAL"
    WITHIN_TOLERANCE = "WITHIN_TOLERANCE"
    DEGRADED = "DEGRADED"
    MISSING_PRIMITIVES = "MISSING_PRIMITIVES"
    EXTRA_PRIMITIVES = "EXTRA_PRIMITIVES"
    MIXED = "MIXED"
    ERROR = "ERROR"


# ════════════════════════════════════════════════════════════
# PRIMITIVE RECORD (shared shape for expected & observed)
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PrimitiveRecord:
    """
    One primitive extracted from substrate output or capture.

    name: primitive identifier (e.g. "POINT_A", "LINE_1")
    kind: primitive type (e.g. "POINT", "LINE", "REGION")
    confidence: extraction confidence [0.0, 1.0]
    x: position x (optional)
    y: position y (optional)
    attributes: additional frozen attributes
    """
    name: str
    kind: str = "UNKNOWN"
    confidence: float = 0.0
    x: float = 0.0
    y: float = 0.0
    attributes: Tuple[Tuple[str, str], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "confidence": round(self.confidence, 6),
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "attributes": dict(self.attributes),
        }


# ════════════════════════════════════════════════════════════
# CONTRACT OUTCOME RECORD
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ContractOutcome:
    """
    Outcome of a contract check (expected or observed).

    contract_name: which contract was checked
    passed: whether it passed
    detail: optional explanation
    """
    contract_name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "passed": self.passed,
            "detail": self.detail,
        }


# ════════════════════════════════════════════════════════════
# SIGNATURE OUTCOME RECORD
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SignatureOutcome:
    """
    Outcome of a signature match (expected or observed).

    signature_name: which signature was checked
    matched: whether it matched
    similarity: similarity score [0.0, 1.0]
    """
    signature_name: str
    matched: bool
    similarity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature_name": self.signature_name,
            "matched": self.matched,
            "similarity": round(self.similarity, 6),
        }


# ════════════════════════════════════════════════════════════
# EXPECTED / OBSERVED OUTPUT
# ════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SubstrateOutput:
    """
    A set of substrate outputs — either expected or observed.

    label: "expected" or "observed"
    primitives: tuple of PrimitiveRecord
    contracts: tuple of ContractOutcome
    signatures: tuple of SignatureOutcome
    """
    label: str
    primitives: Tuple[PrimitiveRecord, ...] = ()
    contracts: Tuple[ContractOutcome, ...] = ()
    signatures: Tuple[SignatureOutcome, ...] = ()

    def primitive_names(self) -> Set[str]:
        return {p.name for p in self.primitives}

    def primitive_by_name(self, name: str) -> Optional[PrimitiveRecord]:
        for p in self.primitives:
            if p.name == name:
                return p
        return None

    def contract_by_name(self, name: str) -> Optional[ContractOutcome]:
        for c in self.contracts:
            if c.contract_name == name:
                return c
        return None

    def signature_by_name(self, name: str) -> Optional[SignatureOutcome]:
        for s in self.signatures:
            if s.signature_name == name:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "primitive_count": len(self.primitives),
            "contract_count": len(self.contracts),
            "signature_count": len(self.signatures),
            "primitives": [p.to_dict() for p in self.primitives],
            "contracts": [c.to_dict() for c in self.contracts],
            "signatures": [s.to_dict() for s in self.signatures],
        }


# ════════════════════════════════════════════════════════════
# INDIVIDUAL DELTA RECORDS
# ════════════════════════════════════════════════════════════

@dataclass
class PrimitiveDelta:
    """Delta for one primitive between expected and observed."""
    name: str
    status: str = ""  # "matched", "missing", "extra", "changed"
    confidence_expected: float = 0.0
    confidence_observed: float = 0.0
    confidence_delta: float = 0.0
    position_delta: float = 0.0  # Euclidean distance
    kind_changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "confidence_expected": round(self.confidence_expected, 6),
            "confidence_observed": round(self.confidence_observed, 6),
            "confidence_delta": round(self.confidence_delta, 6),
            "position_delta": round(self.position_delta, 6),
            "kind_changed": self.kind_changed,
        }


@dataclass
class ContractDelta:
    """Delta for one contract between expected and observed."""
    contract_name: str
    expected_passed: bool = False
    observed_passed: bool = False
    changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "expected_passed": self.expected_passed,
            "observed_passed": self.observed_passed,
            "changed": self.changed,
        }


@dataclass
class SignatureDelta:
    """Delta for one signature between expected and observed."""
    signature_name: str
    expected_matched: bool = False
    observed_matched: bool = False
    similarity_expected: float = 0.0
    similarity_observed: float = 0.0
    similarity_delta: float = 0.0
    changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature_name": self.signature_name,
            "expected_matched": self.expected_matched,
            "observed_matched": self.observed_matched,
            "similarity_expected": round(self.similarity_expected, 6),
            "similarity_observed": round(self.similarity_observed, 6),
            "similarity_delta": round(self.similarity_delta, 6),
            "changed": self.changed,
        }


# ════════════════════════════════════════════════════════════
# DELTA SURFACE — full analysis result
# ════════════════════════════════════════════════════════════

@dataclass
class DeltaSurface:
    """Full result of comparing expected vs observed outputs."""
    verdict: DeltaVerdict = DeltaVerdict.ERROR
    confidence_tolerance: float = 0.0
    position_tolerance: float = 0.0
    primitive_deltas: List[PrimitiveDelta] = field(default_factory=list)
    contract_deltas: List[ContractDelta] = field(default_factory=list)
    signature_deltas: List[SignatureDelta] = field(default_factory=list)
    missing_primitive_count: int = 0
    extra_primitive_count: int = 0
    matched_primitive_count: int = 0
    changed_contract_count: int = 0
    changed_signature_count: int = 0
    max_confidence_delta: float = 0.0
    max_position_delta: float = 0.0
    analysis_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "confidence_tolerance": round(self.confidence_tolerance, 6),
            "position_tolerance": round(self.position_tolerance, 6),
            "missing_primitive_count": self.missing_primitive_count,
            "extra_primitive_count": self.extra_primitive_count,
            "matched_primitive_count": self.matched_primitive_count,
            "changed_contract_count": self.changed_contract_count,
            "changed_signature_count": self.changed_signature_count,
            "max_confidence_delta": round(self.max_confidence_delta, 6),
            "max_position_delta": round(self.max_position_delta, 6),
            "analysis_hash": self.analysis_hash,
            "primitive_deltas": [d.to_dict() for d in self.primitive_deltas],
            "contract_deltas": [d.to_dict() for d in self.contract_deltas],
            "signature_deltas": [d.to_dict() for d in self.signature_deltas],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ════════════════════════════════════════════════════════════
# ANALYZE DELTAS
# ════════════════════════════════════════════════════════════

def analyze_deltas(
    expected: SubstrateOutput,
    observed: SubstrateOutput,
    confidence_tolerance: float = 0.05,
    position_tolerance: float = 5.0,
) -> DeltaSurface:
    """
    Compare expected vs observed substrate outputs and produce
    a deterministic DeltaSurface.

    Parameters:
        expected: the known/baseline substrate output
        observed: the capture-derived output
        confidence_tolerance: max acceptable confidence shift (absolute)
        position_tolerance: max acceptable position shift (pixels)

    Returns a DeltaSurface with all deltas and a verdict.
    """
    import math

    surface = DeltaSurface(
        confidence_tolerance=confidence_tolerance,
        position_tolerance=position_tolerance,
    )

    expected_names = expected.primitive_names()
    observed_names = observed.primitive_names()

    # Missing and extra primitives
    missing_names = expected_names - observed_names
    extra_names = observed_names - expected_names
    common_names = expected_names & observed_names

    surface.missing_primitive_count = len(missing_names)
    surface.extra_primitive_count = len(extra_names)
    surface.matched_primitive_count = len(common_names)

    # Primitive deltas
    for name in sorted(missing_names):
        ep = expected.primitive_by_name(name)
        surface.primitive_deltas.append(PrimitiveDelta(
            name=name,
            status="missing",
            confidence_expected=ep.confidence if ep else 0.0,
        ))

    for name in sorted(extra_names):
        op = observed.primitive_by_name(name)
        surface.primitive_deltas.append(PrimitiveDelta(
            name=name,
            status="extra",
            confidence_observed=op.confidence if op else 0.0,
        ))

    max_conf_delta = 0.0
    max_pos_delta = 0.0
    any_out_of_tolerance = False

    for name in sorted(common_names):
        ep = expected.primitive_by_name(name)
        op = observed.primitive_by_name(name)
        if ep is None or op is None:
            continue

        conf_delta = op.confidence - ep.confidence
        pos_delta = math.sqrt((op.x - ep.x) ** 2 + (op.y - ep.y) ** 2)
        kind_changed = op.kind != ep.kind

        pd = PrimitiveDelta(
            name=name,
            status="changed" if (abs(conf_delta) > confidence_tolerance or
                                 pos_delta > position_tolerance or
                                 kind_changed) else "matched",
            confidence_expected=ep.confidence,
            confidence_observed=op.confidence,
            confidence_delta=conf_delta,
            position_delta=pos_delta,
            kind_changed=kind_changed,
        )
        surface.primitive_deltas.append(pd)

        if abs(conf_delta) > max_conf_delta:
            max_conf_delta = abs(conf_delta)
        if pos_delta > max_pos_delta:
            max_pos_delta = pos_delta
        if pd.status == "changed":
            any_out_of_tolerance = True

    surface.max_confidence_delta = max_conf_delta
    surface.max_position_delta = max_pos_delta

    # Contract deltas
    all_contract_names = set()
    for c in expected.contracts:
        all_contract_names.add(c.contract_name)
    for c in observed.contracts:
        all_contract_names.add(c.contract_name)

    for cn in sorted(all_contract_names):
        ec = expected.contract_by_name(cn)
        oc = observed.contract_by_name(cn)
        ep_passed = ec.passed if ec else False
        op_passed = oc.passed if oc else False
        changed = ep_passed != op_passed
        surface.contract_deltas.append(ContractDelta(
            contract_name=cn,
            expected_passed=ep_passed,
            observed_passed=op_passed,
            changed=changed,
        ))
        if changed:
            surface.changed_contract_count += 1

    # Signature deltas
    all_sig_names = set()
    for s in expected.signatures:
        all_sig_names.add(s.signature_name)
    for s in observed.signatures:
        all_sig_names.add(s.signature_name)

    for sn in sorted(all_sig_names):
        es = expected.signature_by_name(sn)
        os_sig = observed.signature_by_name(sn)
        em = es.matched if es else False
        om = os_sig.matched if os_sig else False
        e_sim = es.similarity if es else 0.0
        o_sim = os_sig.similarity if os_sig else 0.0
        changed = em != om
        surface.signature_deltas.append(SignatureDelta(
            signature_name=sn,
            expected_matched=em,
            observed_matched=om,
            similarity_expected=e_sim,
            similarity_observed=o_sim,
            similarity_delta=o_sim - e_sim,
            changed=changed,
        ))
        if changed:
            surface.changed_signature_count += 1

    # Compute deterministic hash
    hash_data = json.dumps(surface.to_dict(), sort_keys=True, separators=(",", ":"))
    surface.analysis_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    # Determine verdict
    if (surface.missing_primitive_count == 0 and
        surface.extra_primitive_count == 0 and
        not any_out_of_tolerance and
        surface.changed_contract_count == 0 and
        surface.changed_signature_count == 0):
        if max_conf_delta == 0.0 and max_pos_delta == 0.0:
            surface.verdict = DeltaVerdict.IDENTICAL
        else:
            surface.verdict = DeltaVerdict.WITHIN_TOLERANCE
    elif surface.missing_primitive_count > 0 and surface.extra_primitive_count == 0:
        surface.verdict = DeltaVerdict.MISSING_PRIMITIVES
    elif surface.extra_primitive_count > 0 and surface.missing_primitive_count == 0:
        surface.verdict = DeltaVerdict.EXTRA_PRIMITIVES
    elif (surface.missing_primitive_count > 0 or surface.extra_primitive_count > 0 or
          any_out_of_tolerance or surface.changed_contract_count > 0):
        surface.verdict = DeltaVerdict.MIXED
    else:
        surface.verdict = DeltaVerdict.DEGRADED

    # Recompute hash now that verdict is set
    hash_data = json.dumps(surface.to_dict(), sort_keys=True, separators=(",", ":"))
    surface.analysis_hash = hashlib.sha256(hash_data.encode()).hexdigest()

    return surface


def make_error_surface(reason: str) -> DeltaSurface:
    """Create an error delta surface for testing/error paths."""
    return DeltaSurface(verdict=DeltaVerdict.ERROR)


# ════════════════════════════════════════════════════════════
# FROZEN COUNTS FOR TESTING
# ════════════════════════════════════════════════════════════

EXPECTED_VERDICT_COUNT = 7  # IDENTICAL, WITHIN_TOLERANCE, DEGRADED, MISSING, EXTRA, MIXED, ERROR
EXPECTED_DELTA_FIELDS = 13  # fields in DeltaSurface
DEFAULT_CONFIDENCE_TOLERANCE = 0.05
DEFAULT_POSITION_TOLERANCE = 5.0
