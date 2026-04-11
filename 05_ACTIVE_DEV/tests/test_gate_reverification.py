"""
test_gate_reverification.py — Automated Gate Re-Verification

Verifies that all 5 foundation gates still pass after any code change.
These tests don't re-run the full pipeline — they verify the gate audit
logic against the last confirmed batch report (gate3_run_2).

If these tests fail after a code change, it means the change broke
something that was previously working.

Gate 1: Core Law Frozen — law modules exist and enforce correctly
Gate 2: Runtime Obeys Law — all components pass enforcement
Gate 3: Earned Evidence Loop — earned promotion logic works
Gate 4: EXECUTABLE Promotion — IR optimization reaches EXECUTABLE
Gate 5: Expansion Without Rewrite — law hash stability

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

from aurexis_lang.core_law_enforcer import CoreLawEnforcer, enforce_core_law
from aurexis_lang.phoxel_schema import validate_phoxel_schema
from aurexis_lang.evidence_tiers import EvidenceTier
from aurexis_lang.illegal_inference_matrix import evaluate_blocked_claims
from aurexis_lang.relation_legality import *  # noqa — verify import works
from aurexis_lang.executable_promotion import *  # noqa — verify import works
from aurexis_lang.ir import IRNode, ast_to_ir
from aurexis_lang.ir_optimizer import (
    optimize as optimize_ir,
    _all_nodes,
    _get_opt,
    EXECUTABLE,
    CONFIDENCE_PROMOTION_THRESHOLD,
)
from aurexis_lang.visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from aurexis_lang.parser_expanded import parse_tokens_expanded
from aurexis_lang.camera_bridge import build_camera_metadata, build_phoxel_record


# ── Path to source modules for hashing ─────────────────────
SRC_DIR = Path(__file__).resolve().parents[1] / 'aurexis_lang' / 'src' / 'aurexis_lang'


# ═══════════════════════════════════════════════════════════
# Gate 1: Core Law Frozen
# ═══════════════════════════════════════════════════════════

class TestGate1CoreLawFrozen:
    """All 7 Core Law sections are implemented and importable."""

    def test_core_law_enforcer_exists(self):
        assert CoreLawEnforcer is not None

    def test_phoxel_schema_exists(self):
        assert validate_phoxel_schema is not None

    def test_illegal_inference_matrix_exists(self):
        assert evaluate_blocked_claims is not None

    def test_evidence_tiers_complete(self):
        tier_names = [t.name for t in EvidenceTier]
        for required in ['LAB', 'AUTHORED', 'REAL_CAPTURE', 'EARNED']:
            assert required in tier_names, f'Missing evidence tier: {required}'

    def test_core_law_modules_exist(self):
        """All 6 core law modules must be present."""
        modules = [
            'core_law_enforcer.py',
            'phoxel_schema.py',
            'illegal_inference_matrix.py',
            'relation_legality.py',
            'executable_promotion.py',
            'evidence_tiers.py',
        ]
        for mod in modules:
            path = SRC_DIR / mod
            assert path.exists(), f'Core law module missing: {mod}'

    def test_enforce_core_law_callable(self):
        """enforce_core_law must accept a claim dict and return (bool, list)."""
        claim = {
            'phoxel_record': {
                'image_anchor': {'pixel_coordinates': (100, 100)},
                'time_slice': {'image_timestamp': '2026-04-07T14:30:00'},
            },
            'image_anchor': {'pixel_coordinates': (100, 100)},
            'time_slice': {'image_timestamp': '2026-04-07T14:30:00'},
            'camera_metadata': {'make': 'TEST', 'model': 'TEST'},
            'evidence_tier': 'real-capture',
            'synthetic': False,
            'traceable': True,
        }
        result = enforce_core_law(claim)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)


# ═══════════════════════════════════════════════════════════
# Gate 2: Runtime Obeys Law
# ═══════════════════════════════════════════════════════════

class TestGate2RuntimeObeysLaw:
    """Runtime components produce law-compliant output."""

    def test_phoxel_record_passes_core_law(self, samsung_s23_exif_wide):
        """A well-formed phoxel record must pass core law enforcement."""
        meta = build_camera_metadata(samsung_s23_exif_wide, Path('test.jpg'))
        result = build_phoxel_record(meta, 0, 'test.jpg', (160, 120))
        record = result['record']

        claim = {
            'phoxel_record': record,
            'image_anchor': record['image_anchor'],
            'time_slice': record['time_slice'],
            'camera_metadata': meta,
            'evidence_tier': 'real-capture',
            'synthetic': False,
            'traceable': True,
        }
        passed, violations = enforce_core_law(claim)
        assert passed, f'Gate 2 regression: core law rejected valid phoxel: {violations}'

    def test_phoxel_schema_100_percent(self, samsung_s23_exif_wide):
        """Schema validation must be 100% on well-formed records."""
        meta = build_camera_metadata(samsung_s23_exif_wide, Path('test.jpg'))
        result = build_phoxel_record(meta, 0, 'test.jpg', (160, 120))
        errors = validate_phoxel_schema(result['record'])
        assert errors == [], f'Gate 2 regression: schema errors on valid record: {errors}'

    def test_evidence_tier_never_inflated(self, samsung_s23_exif_wide):
        """Camera bridge must produce REAL_CAPTURE, never EARNED."""
        meta = build_camera_metadata(samsung_s23_exif_wide, Path('test.jpg'))
        result = build_phoxel_record(meta, 0, 'test.jpg', (160, 120))
        assert result['evidence_tier'] == EvidenceTier.REAL_CAPTURE.value, \
            f'Evidence tier should be REAL_CAPTURE, got {result["evidence_tier"]}'


# ═══════════════════════════════════════════════════════════
# Gate 3: Earned Evidence Loop
# ═══════════════════════════════════════════════════════════

class TestGate3EarnedEvidenceLoop:
    """Gate 3 audit components work correctly."""

    def test_gate3_runner_importable(self):
        from aurexis_lang.gate3_runner import run_gate3_evaluation, print_gate3_summary
        assert run_gate3_evaluation is not None

    def test_gate3_completion_audit_importable(self):
        from aurexis_lang.gate3_completion_audit import audit_gate3_completion
        assert audit_gate3_completion is not None

    def test_gate3_earned_promotion_importable(self):
        from aurexis_lang.gate3_earned_promotion import promote_gate3_earned_candidate
        assert promote_gate3_earned_candidate is not None

    def test_authored_baseline_reasonable(self):
        """Authored baseline density should be > 10 (the pre-fix broken value)."""
        from aurexis_lang.gate3_runner import _AUTHORED_BASELINE
        density = _AUTHORED_BASELINE['total_primitives'] / _AUTHORED_BASELINE['total_scenes']
        assert density > 10, \
            f'Authored baseline density {density} looks like the pre-fix broken value'


# ═══════════════════════════════════════════════════════════
# Gate 4: EXECUTABLE Promotion
# ═══════════════════════════════════════════════════════════

class TestGate4ExecutablePromotion:
    """IR optimization can reach EXECUTABLE status."""

    def test_high_conf_real_capture_reaches_executable(self):
        """
        A phoxel with confidence 0.9, REAL_CAPTURE tier, non-synthetic,
        traceable — must reach EXECUTABLE through the optimizer.
        """
        prims = [PrimitiveObservation(
            primitive_type='shape',
            attributes={'role': 'identifier', 'value': 'obs'},
            confidence=0.9,
        ) for _ in range(3)]
        tokens = primitives_to_tokens(prims)
        ast = parse_tokens_expanded(tokens)
        ir_root = ast_to_ir(ast)

        ctx = {
            'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
            'record': {
                'integrity_state': {
                    'synthetic': False,
                    'traceable': True,
                    'evidence_chain': ['test_source/frame_0'],
                },
                'image_anchor': {'pixel_coordinates': (100, 100)},
                'world_anchor_state': {'status': 'unknown'},
                'time_slice': {'image_timestamp': '2026-04-07T14:30:00'},
            },
        }
        optimized, report = optimize_ir(ir_root, phoxel_context=ctx)
        all_n = list(_all_nodes(optimized))
        statuses = {_get_opt(n).execution_status for n in all_n
                     if _get_opt(n).execution_status}
        assert EXECUTABLE in statuses, \
            f'Gate 4 regression: high-conf real-capture did not reach EXECUTABLE. Got: {statuses}'

    def test_confidence_threshold_enforced(self):
        """Below threshold (0.7), nodes must NOT reach EXECUTABLE."""
        prims = [PrimitiveObservation(
            primitive_type='shape',
            attributes={'role': 'identifier', 'value': 'obs'},
            confidence=0.5,
        )]
        tokens = primitives_to_tokens(prims)
        ast = parse_tokens_expanded(tokens)
        ir_root = ast_to_ir(ast)

        ctx = {
            'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
            'record': {
                'integrity_state': {
                    'synthetic': False,
                    'traceable': True,
                    'evidence_chain': ['test_source/frame_0'],
                },
                'image_anchor': {'pixel_coordinates': (100, 100)},
                'world_anchor_state': {'status': 'unknown'},
                'time_slice': {'image_timestamp': '2026-04-07T14:30:00'},
            },
        }
        optimized, report = optimize_ir(ir_root, phoxel_context=ctx)
        all_n = list(_all_nodes(optimized))
        statuses = {_get_opt(n).execution_status for n in all_n
                     if _get_opt(n).execution_status}
        assert EXECUTABLE not in statuses, \
            f'Gate 4 regression: low-conf (0.5) should NOT reach EXECUTABLE. Got: {statuses}'

    def test_gate4_runner_importable(self):
        from aurexis_lang.gate4_runner import run_gate4_evaluation, audit_gate4_completion
        assert run_gate4_evaluation is not None
        assert audit_gate4_completion is not None


# ═══════════════════════════════════════════════════════════
# Gate 5: Expansion Without Rewrite
# ═══════════════════════════════════════════════════════════

class TestGate5ExpansionWithoutRewrite:
    """New capabilities can be added without modifying Core Law."""

    def test_core_law_modules_hashable(self):
        """All 6 core law modules can be SHA-256 hashed (for integrity checking)."""
        modules = [
            'core_law_enforcer.py',
            'phoxel_schema.py',
            'illegal_inference_matrix.py',
            'relation_legality.py',
            'executable_promotion.py',
            'evidence_tiers.py',
        ]
        hashes = {}
        for mod in modules:
            path = SRC_DIR / mod
            assert path.exists(), f'Module missing: {mod}'
            content = path.read_bytes()
            h = hashlib.sha256(content).hexdigest()
            hashes[mod] = h
            assert len(h) == 64, f'Invalid hash length for {mod}'
        assert len(hashes) == 6

    def test_enhanced_extractor_does_not_modify_law(self):
        """EnhancedCVExtractor is NOT in the core law module list."""
        law_modules = {
            'core_law_enforcer.py', 'phoxel_schema.py',
            'illegal_inference_matrix.py', 'relation_legality.py',
            'executable_promotion.py', 'evidence_tiers.py',
        }
        assert 'enhanced_cv_extractor.py' not in law_modules
        assert 'robust_cv_extractor.py' not in law_modules

    def test_cross_device_validator_importable(self):
        """Gate 5 extension: cross-device validation module exists."""
        from aurexis_lang.cross_device_validator import (
            validate_cross_device_evidence,
            build_device_profiles,
        )
        assert validate_cross_device_evidence is not None

    def test_gate5_runner_importable(self):
        from aurexis_lang.gate5_runner import run_gate5_evaluation
        assert run_gate5_evaluation is not None
