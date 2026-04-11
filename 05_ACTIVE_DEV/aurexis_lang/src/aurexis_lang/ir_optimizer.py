"""
ir_optimizer.py — Evidence-aware IR optimization for Aurexis V86+

This is the real optimization layer that was missing from the pipeline.
Previously ir.py produced dead generic IRNode trees; this module transforms
those trees using phoxel context to produce annotated, pruned, promotion-
eligible IR ready for execution planning.

Optimization passes (in order):
  1. Evidence annotation     — stamp every node with phoxel provenance
  2. Confidence propagation  — bubble up min/mean confidence through subtrees
  3. Execution status ladder — classify each node as DESCRIPTIVE/ESTIMATED/
                               VALIDATED/EXECUTABLE based on evidence state
  4. Dead branch elimination — prune nodes with zero evidence support
  5. Supersession folding    — mark overwritten assignments as superseded
  6. Promotion pre-screening — fast O(1) check before expensive checklist

The optimizer is non-destructive: it adds metadata to IRNodes and returns
both the annotated tree and an optimization report. It never mutates the
original AST.

Evidence tier requirements (from Core Law, Section 4 — Executable Promotion):
  - Confidence ≥ 0.7             → eligible for EXECUTABLE status
  - REAL_CAPTURE tier or higher  → required for promotion eligibility
  - synthetic=False              → always required
  - traceable=True               → always required
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .ir import IRNode
from .evidence_tiers import EvidenceTier, normalize_evidence_tier


# ────────────────────────────────────────────────────────────
# Execution status ladder (mirrors Core Law Section 4)
# ────────────────────────────────────────────────────────────

DESCRIPTIVE  = 'descriptive'   # No real evidence — can only describe
ESTIMATED    = 'estimated'     # Some evidence but world anchor unresolved
VALIDATED    = 'validated'     # Evidence validated, multi-frame consistent
EXECUTABLE   = 'executable'    # Passes all promotion checks

# Minimum evidence tier required for any promotion attempt
_PROMOTION_MIN_TIER = EvidenceTier.REAL_CAPTURE

# Confidence threshold from Core Law Section 4 (frozen)
CONFIDENCE_PROMOTION_THRESHOLD = 0.7


# ────────────────────────────────────────────────────────────
# Optimization result types
# ────────────────────────────────────────────────────────────

@dataclass
class NodeOptimizationState:
    """
    Attached to each IRNode as node.metadata['opt'].
    Carries all optimization decisions for that node.
    """
    execution_status: str = DESCRIPTIVE

    # Evidence provenance
    evidence_tier: str = EvidenceTier.LAB.value
    confidence_mean: float = 0.0
    confidence_min: float = 0.0
    traceable: bool = False
    synthetic: bool = True
    phoxel_source: Optional[str] = None
    phoxel_frame_index: Optional[int] = None
    pixel_coordinates: Optional[Tuple[int, int]] = None
    world_anchor_status: str = 'unknown'

    # Optimization flags
    pruned: bool = False
    prune_reason: Optional[str] = None
    superseded: bool = False
    superseded_by: Optional[int] = None   # sibling index that supersedes this

    # Promotion pre-screening result
    promotion_screened: bool = False
    promotion_eligible: bool = False
    promotion_blocked_reasons: List[str] = field(default_factory=list)


@dataclass
class IROptimizationReport:
    """
    Summary of all optimization decisions made over one IR tree.
    Attached to the root node and returned by optimize().
    """
    original_node_count: int = 0
    pruned_node_count: int = 0
    superseded_node_count: int = 0
    active_node_count: int = 0

    # Execution status distribution
    descriptive_count: int = 0
    estimated_count: int = 0
    validated_count: int = 0
    executable_count: int = 0

    # Evidence stats
    confidence_mean: float = 0.0
    confidence_min: float = 1.0
    evidence_tier: str = EvidenceTier.LAB.value
    promotion_eligible_count: int = 0
    has_real_capture_evidence: bool = False

    # Pass completion flags
    evidence_annotation_complete: bool = False
    confidence_propagation_complete: bool = False
    status_ladder_complete: bool = False
    dead_branch_elimination_complete: bool = False
    supersession_folding_complete: bool = False
    promotion_screening_complete: bool = False


# ────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────

def _tier_rank(tier_value: str) -> int:
    """Higher rank = stronger evidence. Used for fast tier comparisons."""
    _ranks = {
        EvidenceTier.LAB.value:          0,
        EvidenceTier.AUTHORED.value:     1,
        EvidenceTier.REAL_CAPTURE.value: 2,
        EvidenceTier.EARNED.value:       3,
    }
    return _ranks.get(str(tier_value).lower(), 0)


def _normalize_tier_str(raw: Any) -> str:
    try:
        return normalize_evidence_tier(raw).value
    except Exception:
        return EvidenceTier.LAB.value


def _get_opt(node: IRNode) -> NodeOptimizationState:
    """Return existing opt state or create a new one for this node."""
    if 'opt' not in node.metadata:
        node.metadata['opt'] = NodeOptimizationState()
    return node.metadata['opt']


def _all_nodes(root: IRNode) -> List[IRNode]:
    """Depth-first traversal of the full IR tree."""
    result: List[IRNode] = []
    stack = [root]
    while stack:
        node = stack.pop()
        result.append(node)
        stack.extend(reversed(node.children))
    return result


def _active_children(node: IRNode) -> List[IRNode]:
    """Return non-pruned children only."""
    return [c for c in node.children if not _get_opt(c).pruned]


# ────────────────────────────────────────────────────────────
# Pass 1 — Evidence annotation
# ────────────────────────────────────────────────────────────

def _pass_evidence_annotation(
    root: IRNode,
    phoxel_context: Optional[Dict[str, Any]],
) -> None:
    """
    Stamp every node in the tree with phoxel provenance from the
    camera context. This is the foundation all later passes build on.
    """
    if phoxel_context is None:
        phoxel_context = {}

    # Extract from phoxel_record if present (from build_phoxel_record output)
    record = phoxel_context.get('record', {})
    integrity = record.get('integrity_state', {})
    image_anchor = record.get('image_anchor', {})
    world_anchor = record.get('world_anchor_state', {})
    time_slice = record.get('time_slice', {})

    evidence_tier = _normalize_tier_str(
        phoxel_context.get('evidence_tier')
        or record.get('photonic_signature', {}).get('measurement_origin')
        or EvidenceTier.LAB.value
    )
    traceable     = bool(integrity.get('traceable', False) or integrity.get('evidence_chain'))
    synthetic     = bool(integrity.get('synthetic', True))
    phoxel_source = phoxel_context.get('source_id') or record.get('source', 'unknown')
    frame_idx     = phoxel_context.get('frame_index')
    pixel_coords  = image_anchor.get('pixel_coordinates')
    world_status  = world_anchor.get('status', 'unknown')

    for node in _all_nodes(root):
        opt = _get_opt(node)
        opt.evidence_tier    = evidence_tier
        opt.traceable        = traceable
        opt.synthetic        = synthetic
        opt.phoxel_source    = str(phoxel_source)
        opt.phoxel_frame_index = frame_idx
        opt.pixel_coordinates  = pixel_coords
        opt.world_anchor_status = world_status

        # Inherit confidence from the node's own args if present
        node_confidence = float(node.args.get('confidence', 0.0) or 0.0)
        # Will be properly propagated in Pass 2 — store raw for now
        opt.confidence_mean = node_confidence
        opt.confidence_min  = node_confidence


# ────────────────────────────────────────────────────────────
# Pass 2 — Confidence propagation (bottom-up)
# ────────────────────────────────────────────────────────────

def _pass_confidence_propagation(root: IRNode) -> None:
    """
    Bubble confidence scores up through the tree.
    A parent's confidence is the mean of its children's confidences,
    floored at its own stated confidence.
    """
    def _propagate(node: IRNode) -> Tuple[float, float]:
        """Returns (mean, min) confidence for the subtree rooted at node."""
        opt = _get_opt(node)
        own_conf = float(node.args.get('confidence', 0.0) or 0.0)

        if not node.children:
            opt.confidence_mean = own_conf
            opt.confidence_min  = own_conf
            return own_conf, own_conf

        child_values: List[Tuple[float, float]] = []
        for child in node.children:
            child_values.append(_propagate(child))

        child_means = [v[0] for v in child_values]
        child_mins  = [v[1] for v in child_values]

        subtree_mean = sum(child_means) / len(child_means) if child_means else own_conf
        subtree_min  = min(child_mins)  if child_mins  else own_conf

        # Node's own confidence is a floor, not an override
        final_mean = max(own_conf, subtree_mean) if own_conf > 0 else subtree_mean
        final_min  = min(own_conf, subtree_min)  if own_conf > 0 else subtree_min

        opt.confidence_mean = final_mean
        opt.confidence_min  = final_min
        return final_mean, final_min

    _propagate(root)


# ────────────────────────────────────────────────────────────
# Pass 3 — Execution status ladder
# ────────────────────────────────────────────────────────────

def _pass_execution_status_ladder(root: IRNode) -> None:
    """
    Classify each node on the ladder: DESCRIPTIVE → ESTIMATED →
    VALIDATED → EXECUTABLE.

    Rules (strict, frozen in Core Law):
      EXECUTABLE: evidence_tier ≥ REAL_CAPTURE AND confidence ≥ 0.7
                  AND traceable AND NOT synthetic
      VALIDATED:  evidence_tier ≥ REAL_CAPTURE AND traceable AND NOT synthetic
                  (but confidence < 0.7 — not yet promotable)
      ESTIMATED:  evidence_tier ≥ AUTHORED AND world_anchor != 'unknown'
      DESCRIPTIVE: everything else
    """
    for node in _all_nodes(root):
        opt = _get_opt(node)
        tier_rank = _tier_rank(opt.evidence_tier)

        if (tier_rank >= _tier_rank(EvidenceTier.REAL_CAPTURE.value)
                and opt.confidence_mean >= CONFIDENCE_PROMOTION_THRESHOLD
                and opt.traceable
                and not opt.synthetic):
            opt.execution_status = EXECUTABLE

        elif (tier_rank >= _tier_rank(EvidenceTier.REAL_CAPTURE.value)
                and opt.traceable
                and not opt.synthetic):
            opt.execution_status = VALIDATED

        elif (tier_rank >= _tier_rank(EvidenceTier.AUTHORED.value)
                and opt.world_anchor_status != 'unknown'):
            opt.execution_status = ESTIMATED

        else:
            opt.execution_status = DESCRIPTIVE


# ────────────────────────────────────────────────────────────
# Pass 4 — Dead branch elimination
# ────────────────────────────────────────────────────────────

def _pass_dead_branch_elimination(root: IRNode) -> int:
    """
    Mark nodes as pruned if they have zero evidence support.
    Returns the count of pruned nodes.

    A node is dead if:
      (a) It is DESCRIPTIVE AND has zero children AND confidence=0.0
          AND no phoxel source (completely empty node)
      (b) It is a synthetic node (integrity_state.synthetic=True) that
          claims to be executable — illegal under Core Law Section 3

    We never delete nodes — we set opt.pruned=True so the execution
    plan skips them but they remain traceable in the IR.
    """
    pruned = 0
    for node in _all_nodes(root):
        if node.op == 'program':
            continue  # Never prune root

        opt = _get_opt(node)

        # Rule (a): completely empty descriptive leaf
        is_empty_leaf = (
            opt.execution_status == DESCRIPTIVE
            and not node.children
            and opt.confidence_mean == 0.0
            and node.args.get('confidence', 0.0) == 0.0
        )
        if is_empty_leaf:
            opt.pruned = True
            opt.prune_reason = 'empty_descriptive_leaf'
            pruned += 1
            continue

        # Rule (b): synthetic node claiming execution capability
        if opt.synthetic and opt.execution_status in (VALIDATED, EXECUTABLE):
            opt.pruned = True
            opt.prune_reason = 'synthetic_promotion_violation'
            pruned += 1

    return pruned


# ────────────────────────────────────────────────────────────
# Pass 5 — Supersession folding
# ────────────────────────────────────────────────────────────

def _pass_supersession_folding(root: IRNode) -> int:
    """
    Within each level of the tree, if two consecutive assignment nodes
    write to the same target with no evidence dependency between them,
    the earlier one is superseded by the later one.

    This is safe to do only for assignments with equal or lower confidence —
    we never suppress higher-confidence evidence.

    Returns the count of superseded nodes.
    """
    superseded = 0

    def _fold_level(nodes: List[IRNode]) -> None:
        nonlocal superseded
        last_assign_for_target: Dict[str, int] = {}  # target → index in nodes

        for idx, node in enumerate(nodes):
            if node.op != 'assign':
                continue
            opt = _get_opt(node)
            if opt.pruned:
                continue

            target = node.args.get('target') or node.args.get('name')
            if target is None:
                continue

            if target in last_assign_for_target:
                prev_idx = last_assign_for_target[target]
                prev_node = nodes[prev_idx]
                prev_opt = _get_opt(prev_node)

                # Only supersede if the previous node has equal or lower confidence
                if prev_opt.confidence_mean <= opt.confidence_mean:
                    prev_opt.superseded = True
                    prev_opt.superseded_by = idx
                    superseded += 1

            last_assign_for_target[target] = idx

        # Recurse into children of each non-pruned node
        for node in nodes:
            if not _get_opt(node).pruned:
                _fold_level(node.children)

    _fold_level(root.children)
    return superseded


# ────────────────────────────────────────────────────────────
# Pass 6 — Promotion pre-screening
# ────────────────────────────────────────────────────────────

def _pass_promotion_prescreening(root: IRNode) -> int:
    """
    Fast O(1)-per-node check before the expensive 8-condition
    validate_executable_promotion_checklist() is run.

    Saves calling the full checklist on nodes that obviously can't promote.
    Sets opt.promotion_eligible and opt.promotion_blocked_reasons.

    Returns count of promotion-eligible nodes.
    """
    eligible = 0

    for node in _all_nodes(root):
        opt = _get_opt(node)
        if opt.pruned or opt.superseded:
            opt.promotion_screened = True
            opt.promotion_eligible = False
            opt.promotion_blocked_reasons.append('pruned_or_superseded')
            continue

        blocked: List[str] = []

        # Check 1: evidence tier
        if _tier_rank(opt.evidence_tier) < _tier_rank(_PROMOTION_MIN_TIER.value):
            blocked.append(f'evidence_tier_too_low:{opt.evidence_tier}')

        # Check 2: confidence threshold (Core Law Section 4, frozen at 0.7)
        if opt.confidence_mean < CONFIDENCE_PROMOTION_THRESHOLD:
            blocked.append(f'confidence_below_threshold:{opt.confidence_mean:.3f}')

        # Check 3: synthetic flag (Core Law Section 3)
        if opt.synthetic:
            blocked.append('synthetic_observation_blocked')

        # Check 4: traceability
        if not opt.traceable:
            blocked.append('not_traceable')

        opt.promotion_screened = True
        opt.promotion_eligible = len(blocked) == 0
        opt.promotion_blocked_reasons = blocked

        if opt.promotion_eligible:
            eligible += 1

    return eligible


# ────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────

def optimize(
    ir: IRNode,
    phoxel_context: Optional[Dict[str, Any]] = None,
) -> Tuple[IRNode, IROptimizationReport]:
    """
    Run all optimization passes over the IR tree.

    Parameters
    ----------
    ir:
        The IRNode tree produced by ast_to_ir().
    phoxel_context:
        The phoxel record dict returned by build_phoxel_record().
        Contains evidence_tier, frame_index, source_id, and the
        canonical phoxel record fields. Pass None for lab/authored contexts.

    Returns
    -------
    (ir, report):
        ir     — the same IRNode tree, now annotated with opt metadata
                 on every node. The tree is modified in-place (metadata
                 dict is mutable) but structure is unchanged.
        report — IROptimizationReport summarizing all optimization decisions.
    """
    report = IROptimizationReport()

    all_nodes = _all_nodes(ir)
    report.original_node_count = len(all_nodes)

    # Ensure all IRNodes have metadata dicts (they should, but be defensive)
    for node in all_nodes:
        if not hasattr(node, 'metadata'):
            object.__setattr__(node, 'metadata', {})

    # Pass 1 — Evidence annotation
    _pass_evidence_annotation(ir, phoxel_context)
    report.evidence_annotation_complete = True

    # Pass 2 — Confidence propagation
    _pass_confidence_propagation(ir)
    report.confidence_propagation_complete = True

    # Pass 3 — Execution status ladder
    _pass_execution_status_ladder(ir)
    report.status_ladder_complete = True

    # Pass 4 — Dead branch elimination
    pruned = _pass_dead_branch_elimination(ir)
    report.pruned_node_count = pruned
    report.dead_branch_elimination_complete = True

    # Pass 5 — Supersession folding
    superseded = _pass_supersession_folding(ir)
    report.superseded_node_count = superseded
    report.supersession_folding_complete = True

    # Pass 6 — Promotion pre-screening
    eligible = _pass_promotion_prescreening(ir)
    report.promotion_eligible_count = eligible
    report.promotion_screening_complete = True

    # Build report summary
    all_nodes_post = _all_nodes(ir)
    confidence_values: List[float] = []
    for node in all_nodes_post:
        opt = _get_opt(node)
        if opt.pruned or opt.superseded:
            continue
        confidence_values.append(opt.confidence_mean)
        if opt.execution_status == DESCRIPTIVE:
            report.descriptive_count += 1
        elif opt.execution_status == ESTIMATED:
            report.estimated_count += 1
        elif opt.execution_status == VALIDATED:
            report.validated_count += 1
        elif opt.execution_status == EXECUTABLE:
            report.executable_count += 1

    report.active_node_count = (
        report.original_node_count
        - report.pruned_node_count
        - report.superseded_node_count
    )

    if confidence_values:
        report.confidence_mean = sum(confidence_values) / len(confidence_values)
        report.confidence_min  = min(confidence_values)

    # Evidence tier for whole tree = root node's tier after annotation
    root_opt = _get_opt(ir)
    report.evidence_tier = root_opt.evidence_tier
    report.has_real_capture_evidence = (
        _tier_rank(root_opt.evidence_tier) >= _tier_rank(EvidenceTier.REAL_CAPTURE.value)
    )

    # Attach the full report to the root node for downstream consumers
    ir.metadata['optimization_report'] = report

    return ir, report


def optimization_report_to_dict(report: IROptimizationReport) -> Dict[str, Any]:
    """Serialize the optimization report to a plain dict for JSON output."""
    return {
        'original_node_count':      report.original_node_count,
        'active_node_count':        report.active_node_count,
        'pruned_node_count':        report.pruned_node_count,
        'superseded_node_count':    report.superseded_node_count,
        'execution_status': {
            'descriptive':   report.descriptive_count,
            'estimated':     report.estimated_count,
            'validated':     report.validated_count,
            'executable':    report.executable_count,
        },
        'confidence': {
            'mean': round(report.confidence_mean, 4),
            'min':  round(report.confidence_min, 4),
        },
        'evidence': {
            'tier':                    report.evidence_tier,
            'has_real_capture':        report.has_real_capture_evidence,
            'promotion_eligible_count': report.promotion_eligible_count,
        },
        'passes_complete': {
            'evidence_annotation':      report.evidence_annotation_complete,
            'confidence_propagation':   report.confidence_propagation_complete,
            'status_ladder':            report.status_ladder_complete,
            'dead_branch_elimination':  report.dead_branch_elimination_complete,
            'supersession_folding':     report.supersession_folding_complete,
            'promotion_screening':      report.promotion_screening_complete,
        },
    }


def get_active_nodes(ir: IRNode) -> List[IRNode]:
    """Return all non-pruned, non-superseded nodes."""
    return [
        n for n in _all_nodes(ir)
        if not _get_opt(n).pruned and not _get_opt(n).superseded
    ]


def get_executable_nodes(ir: IRNode) -> List[IRNode]:
    """Return nodes that passed promotion pre-screening."""
    return [
        n for n in _all_nodes(ir)
        if _get_opt(n).execution_status == EXECUTABLE
        and not _get_opt(n).pruned
    ]
