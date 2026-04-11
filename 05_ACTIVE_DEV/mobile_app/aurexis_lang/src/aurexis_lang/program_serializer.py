"""
program_serializer.py — Save and load Aurexis programs as JSON.

An Aurexis "program" is the full pipeline output for one source file or
batch: IR structure, phoxel provenance, optimization report, evidence
chain, and execution plan — everything needed to reconstruct, audit, or
promote a program across sessions.

Format version: AUREXIS_PROGRAM_V1

Design goals:
  1. Human-readable JSON — evidence chains are legal documents, not blobs
  2. Integrity hash — SHA-256 over the canonical evidence content so
     tampered programs are detected on load
  3. Evidence-tier locking — a saved program cannot be loaded with a
     higher tier than the one it was saved with (no upward fake-claiming)
  4. Provenance completeness — every saved program embeds enough context
     to re-run Gate evaluations without the original source files
  5. Version migration — schema_version field so V87+ can upgrade V1 programs

Saved file structure:
  {
    "schema_version": "AUREXIS_PROGRAM_V1",
    "saved_at": "2026-04-07T14:30:00",
    "integrity_hash": "sha256:...",
    "program": {
      "source_file": "IMG_001.jpg",
      "frame_index": 0,
      "evidence_tier": "real-capture",
      "camera_metadata": { ... },
      "phoxel_record": { ... },
      "ir": {
        "root_op": "program",
        "nodes": [ { "op": ..., "args": ..., "opt": ... }, ... ],
        "optimization_report": { ... }
      },
      "tokens": [ ... ],
      "execution_plan": { ... },       # from ast_to_execution_plan (optional)
      "schema_valid": true,
      "schema_errors": [],
      "processing_timestamp": "..."
    }
  }
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ir import IRNode
from .evidence_tiers import EvidenceTier, normalize_evidence_tier
from .ir_optimizer import (
    NodeOptimizationState,
    IROptimizationReport,
    optimization_report_to_dict,
    _get_opt,
    _all_nodes,
    DESCRIPTIVE, ESTIMATED, VALIDATED, EXECUTABLE,
)


SCHEMA_VERSION = 'AUREXIS_PROGRAM_V1'
_HASH_PREFIX = 'sha256:'


# ────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────

def _canonical_evidence_content(program_dict: Dict[str, Any]) -> bytes:
    """
    Build the canonical byte string used for integrity hashing.
    Covers: source_file, frame_index, evidence_tier, evidence_chain,
    phoxel pixel_coordinates, and processing_timestamp.

    These are the fields that, if tampered, would constitute evidence fraud.
    """
    phoxel = program_dict.get('phoxel_record', {}) or {}
    record = phoxel.get('record', {}) or {}
    integrity = record.get('integrity_state', {}) or {}
    evidence_chain = integrity.get('evidence_chain', []) or []
    image_anchor = record.get('image_anchor', {}) or {}

    canonical = {
        'source_file':     program_dict.get('source_file', ''),
        'frame_index':     program_dict.get('frame_index', 0),
        'evidence_tier':   program_dict.get('evidence_tier', ''),
        'evidence_chain':  sorted(str(e) for e in evidence_chain),
        'pixel_coordinates': str(image_anchor.get('pixel_coordinates', '')),
        'processing_timestamp': program_dict.get('processing_timestamp', ''),
    }
    return json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _compute_integrity_hash(program_dict: Dict[str, Any]) -> str:
    content = _canonical_evidence_content(program_dict)
    return _HASH_PREFIX + hashlib.sha256(content).hexdigest()


def _verify_integrity_hash(program_dict: Dict[str, Any], stored_hash: str) -> bool:
    if not stored_hash.startswith(_HASH_PREFIX):
        return False
    computed = _compute_integrity_hash(program_dict)
    return computed == stored_hash


def _opt_state_to_dict(opt: NodeOptimizationState) -> Dict[str, Any]:
    """Serialize NodeOptimizationState to a plain dict."""
    return {
        'execution_status':          opt.execution_status,
        'evidence_tier':             opt.evidence_tier,
        'confidence_mean':           round(opt.confidence_mean, 4),
        'confidence_min':            round(opt.confidence_min, 4),
        'traceable':                 opt.traceable,
        'synthetic':                 opt.synthetic,
        'phoxel_source':             opt.phoxel_source,
        'phoxel_frame_index':        opt.phoxel_frame_index,
        'pixel_coordinates':         list(opt.pixel_coordinates) if opt.pixel_coordinates else None,
        'world_anchor_status':       opt.world_anchor_status,
        'pruned':                    opt.pruned,
        'prune_reason':              opt.prune_reason,
        'superseded':                opt.superseded,
        'superseded_by':             opt.superseded_by,
        'promotion_screened':        opt.promotion_screened,
        'promotion_eligible':        opt.promotion_eligible,
        'promotion_blocked_reasons': opt.promotion_blocked_reasons,
    }


def _opt_state_from_dict(d: Dict[str, Any]) -> NodeOptimizationState:
    """Deserialize NodeOptimizationState from a plain dict."""
    pixel_coords = d.get('pixel_coordinates')
    if pixel_coords is not None:
        pixel_coords = tuple(pixel_coords)
    return NodeOptimizationState(
        execution_status=          d.get('execution_status', DESCRIPTIVE),
        evidence_tier=             d.get('evidence_tier', EvidenceTier.LAB.value),
        confidence_mean=           float(d.get('confidence_mean', 0.0)),
        confidence_min=            float(d.get('confidence_min', 0.0)),
        traceable=                 bool(d.get('traceable', False)),
        synthetic=                 bool(d.get('synthetic', True)),
        phoxel_source=             d.get('phoxel_source'),
        phoxel_frame_index=        d.get('phoxel_frame_index'),
        pixel_coordinates=         pixel_coords,
        world_anchor_status=       d.get('world_anchor_status', 'unknown'),
        pruned=                    bool(d.get('pruned', False)),
        prune_reason=              d.get('prune_reason'),
        superseded=                bool(d.get('superseded', False)),
        superseded_by=             d.get('superseded_by'),
        promotion_screened=        bool(d.get('promotion_screened', False)),
        promotion_eligible=        bool(d.get('promotion_eligible', False)),
        promotion_blocked_reasons= list(d.get('promotion_blocked_reasons', [])),
    )


def _ir_node_to_dict(node: IRNode) -> Dict[str, Any]:
    """Serialize an IRNode (including opt metadata) to a plain dict."""
    opt = _get_opt(node)
    return {
        'op':       node.op,
        'args':     {k: _json_safe(v) for k, v in node.args.items()},
        'children': [_ir_node_to_dict(c) for c in node.children],
        'opt':      _opt_state_to_dict(opt),
    }


def _ir_node_from_dict(d: Dict[str, Any]) -> IRNode:
    """Deserialize an IRNode from a plain dict."""
    children = [_ir_node_from_dict(c) for c in d.get('children', [])]
    node = IRNode(
        op=       d.get('op', 'unknown'),
        args=     dict(d.get('args', {})),
        children= children,
        metadata= {},
    )
    if 'opt' in d:
        node.metadata['opt'] = _opt_state_from_dict(d['opt'])
    return node


def _json_safe(v: Any) -> Any:
    """Make a value safe for JSON serialization."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_json_safe(i) for i in v]
    if isinstance(v, dict):
        return {str(k): _json_safe(val) for k, val in v.items()}
    return str(v)


def _make_phoxel_serializable(phoxel: Any) -> Any:
    """Recursively make a phoxel record JSON-safe (handles tuples, enums, etc.)."""
    if isinstance(phoxel, dict):
        return {k: _make_phoxel_serializable(v) for k, v in phoxel.items()}
    if isinstance(phoxel, (list, tuple)):
        return [_make_phoxel_serializable(i) for i in phoxel]
    if hasattr(phoxel, 'value'):  # enum
        return phoxel.value
    return _json_safe(phoxel)


# ────────────────────────────────────────────────────────────
# Public API — Save
# ────────────────────────────────────────────────────────────

def save_program(
    file_to_ir_result: Dict[str, Any],
    output_path: Path,
    *,
    execution_plan: Optional[Dict[str, Any]] = None,
    ir_node: Optional[IRNode] = None,
    opt_report: Optional[IROptimizationReport] = None,
    indent: int = 2,
) -> Dict[str, Any]:
    """
    Save an Aurexis program to a JSON file.

    Parameters
    ----------
    file_to_ir_result:
        The dict returned by camera_bridge.file_to_ir(). Must contain
        source_file, frame_index, phoxel_record, evidence_tier,
        camera_metadata, tokens, schema_valid.
    output_path:
        Where to write the .json file. Parent directory must exist.
    execution_plan:
        Optional output from ast_to_execution_plan(). Embedded verbatim.
    ir_node:
        Optional optimized IRNode tree. If provided, serialized with full
        opt metadata. If omitted, only the optimization_report dict is saved.
    opt_report:
        Optional IROptimizationReport. Auto-extracted from ir_node if
        ir_node is provided.
    indent:
        JSON indentation (default 2).

    Returns
    -------
    The saved document dict (same as written to disk).
    """
    program = {
        'source_file':          file_to_ir_result.get('source_file'),
        'frame_index':          file_to_ir_result.get('frame_index', 0),
        'evidence_tier':        file_to_ir_result.get('evidence_tier', EvidenceTier.LAB.value),
        'camera_metadata':      _make_phoxel_serializable(file_to_ir_result.get('camera_metadata', {})),
        'phoxel_record':        _make_phoxel_serializable(file_to_ir_result.get('phoxel_record', {})),
        'schema_valid':         file_to_ir_result.get('schema_valid', False),
        'schema_errors':        file_to_ir_result.get('schema_errors', []),
        'tokens':               _json_safe(file_to_ir_result.get('tokens', [])),
        'processing_timestamp': file_to_ir_result.get('processing_timestamp', datetime.now().isoformat()),
    }

    # IR section
    ir_section: Dict[str, Any] = {
        'root_op':           file_to_ir_result.get('ir_root', 'program'),
        'optimization_report': _json_safe(file_to_ir_result.get('ir_optimization', {})),
    }

    # Serialize full IR tree if provided
    if ir_node is not None:
        ir_section['nodes'] = _ir_node_to_dict(ir_node)
        # Extract opt report from tree root if not passed explicitly
        if opt_report is None:
            opt_report = ir_node.metadata.get('optimization_report')
        if opt_report is not None:
            ir_section['optimization_report'] = optimization_report_to_dict(opt_report)

    if opt_report is not None and 'optimization_report' not in ir_section:
        ir_section['optimization_report'] = optimization_report_to_dict(opt_report)

    program['ir'] = ir_section

    # Optional execution plan
    if execution_plan is not None:
        program['execution_plan'] = _make_phoxel_serializable(execution_plan)

    # Compute integrity hash over canonical evidence fields
    integrity_hash = _compute_integrity_hash(program)

    document = {
        'schema_version': SCHEMA_VERSION,
        'saved_at':       datetime.now().isoformat(),
        'integrity_hash': integrity_hash,
        'program':        program,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, indent=indent, default=str),
        encoding='utf-8',
    )

    return document


# ────────────────────────────────────────────────────────────
# Public API — Load
# ────────────────────────────────────────────────────────────

class ProgramIntegrityError(Exception):
    """Raised when a loaded program fails its integrity check."""


class ProgramVersionError(Exception):
    """Raised when a loaded program has an unsupported schema version."""


class EvidenceTierViolation(Exception):
    """Raised when a program is loaded with a higher tier than it was saved with."""


def load_program(
    path: Path,
    *,
    expected_min_tier: Optional[str] = None,
    skip_integrity_check: bool = False,
) -> Tuple[Dict[str, Any], Optional[IRNode]]:
    """
    Load an Aurexis program from a JSON file.

    Parameters
    ----------
    path:
        Path to the .json program file.
    expected_min_tier:
        If provided, raises EvidenceTierViolation if the loaded program's
        evidence tier is below this level. Use 'real-capture' to enforce
        that only real camera evidence is loaded.
    skip_integrity_check:
        If True, skip the SHA-256 integrity check (use only for debugging).

    Returns
    -------
    (program_dict, ir_node):
        program_dict — the 'program' section of the saved document
        ir_node      — reconstructed IRNode tree (None if not serialized)

    Raises
    ------
    ProgramVersionError:      Unknown or unsupported schema version
    ProgramIntegrityError:    Integrity hash mismatch
    EvidenceTierViolation:    Evidence tier below required minimum
    FileNotFoundError:        File not found
    json.JSONDecodeError:     Invalid JSON
    """
    document = json.loads(path.read_text(encoding='utf-8'))

    # Version check
    schema_version = document.get('schema_version', '')
    if schema_version != SCHEMA_VERSION:
        raise ProgramVersionError(
            f'Unsupported schema version: {schema_version!r}. '
            f'Expected {SCHEMA_VERSION!r}.'
        )

    program = document.get('program', {})
    integrity_hash = document.get('integrity_hash', '')

    # Integrity check
    if not skip_integrity_check:
        if not _verify_integrity_hash(program, integrity_hash):
            raise ProgramIntegrityError(
                f'Integrity check failed for {path}. '
                f'The program evidence chain may have been tampered with.'
            )

    # Evidence tier check (Core Law: no upward fake-claiming on load)
    saved_tier = program.get('evidence_tier', EvidenceTier.LAB.value)
    if expected_min_tier is not None:
        try:
            saved_rank = _tier_rank(saved_tier)
            min_rank   = _tier_rank(expected_min_tier)
            if saved_rank < min_rank:
                raise EvidenceTierViolation(
                    f'Program evidence tier {saved_tier!r} is below required '
                    f'minimum {expected_min_tier!r}. Cannot load.'
                )
        except EvidenceTierViolation:
            raise
        except Exception:
            pass  # Tier comparison errors are non-fatal

    # Reconstruct IRNode tree if serialized
    ir_node: Optional[IRNode] = None
    ir_section = program.get('ir', {})
    if 'nodes' in ir_section:
        try:
            ir_node = _ir_node_from_dict(ir_section['nodes'])
        except Exception as exc:
            # Corrupt IR is non-fatal — return program dict without IR
            program['_ir_load_warning'] = f'IR reconstruction failed: {exc}'

    return program, ir_node


def _tier_rank(tier_value: str) -> int:
    """Same tier rank table as ir_optimizer — local copy to avoid circular import."""
    _ranks = {
        EvidenceTier.LAB.value:          0,
        EvidenceTier.AUTHORED.value:     1,
        EvidenceTier.REAL_CAPTURE.value: 2,
        EvidenceTier.EARNED.value:       3,
    }
    return _ranks.get(str(tier_value).lower(), 0)


# ────────────────────────────────────────────────────────────
# Batch save helper
# ────────────────────────────────────────────────────────────

def save_batch_programs(
    file_results: List[Dict[str, Any]],
    output_dir: Path,
    *,
    suffix: str = '.aurexis.json',
) -> List[Path]:
    """
    Save a list of file_to_ir results as individual program files.

    Returns the list of paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    for result in file_results:
        source = result.get('source_file') or f"frame_{result.get('frame_index', 0)}"
        stem = Path(str(source)).stem
        out_path = output_dir / f'{stem}{suffix}'

        try:
            save_program(result, out_path)
            written.append(out_path)
        except Exception:
            pass  # Non-fatal — log but continue batch

    return written


# ────────────────────────────────────────────────────────────
# Program summary (for reports and Gate evaluations)
# ────────────────────────────────────────────────────────────

def summarize_program(program_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a compact summary dict suitable for inclusion in batch reports
    and Gate evaluation inputs.
    """
    ir = program_dict.get('ir', {})
    opt = ir.get('optimization_report', {}) or {}
    phoxel = program_dict.get('phoxel_record', {}) or {}
    record  = phoxel.get('record', {}) or {}
    integrity = record.get('integrity_state', {}) or {}
    camera = program_dict.get('camera_metadata', {}) or {}

    return {
        'source_file':           program_dict.get('source_file'),
        'frame_index':           program_dict.get('frame_index', 0),
        'evidence_tier':         program_dict.get('evidence_tier'),
        'schema_valid':          program_dict.get('schema_valid', False),
        'evidence_chain_length': len(integrity.get('evidence_chain', []) or []),
        'traceable':             bool(integrity.get('traceable', False) or integrity.get('evidence_chain')),
        'synthetic':             bool(integrity.get('synthetic', True)),
        'camera_make':           camera.get('make', 'unknown'),
        'camera_model':          camera.get('model', 'unknown'),
        'lens_id':               camera.get('lens_id', 'main'),
        'is_samsung':            bool(camera.get('is_samsung', False)),
        'ir_nodes':              opt.get('original_node_count', 0),
        'ir_active':             opt.get('active_node_count', 0),
        'ir_executable':         (opt.get('execution_status') or {}).get('executable', 0),
        'promotion_eligible':    (opt.get('evidence') or {}).get('promotion_eligible_count', 0),
        'confidence_mean':       (opt.get('confidence') or {}).get('mean', 0.0),
        'processing_timestamp':  program_dict.get('processing_timestamp'),
    }
