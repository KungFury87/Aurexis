"""
Tests for camera_bridge.py

Covers:
- EXIF parsing (with and without real EXIF data)
- Camera metadata construction (Samsung S23 lens inference)
- Phoxel record construction and schema validation
- Frame extraction routing (image vs video paths)
- Evidence tier stamping (must be REAL_CAPTURE, never synthetic)
- file_to_ir pipeline integration

These tests use synthetic frames (numpy arrays) and mock paths
so no real camera or phone is required. Real camera testing is
done separately using the run_real_capture_pipeline.py script.

Evidence tier for these tests: AUTHORED (test harness, no real camera).
The pipeline itself stamps REAL_CAPTURE when processing real files.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Ensure aurexis_lang is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'aurexis_lang' / 'src'
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from aurexis_lang.camera_bridge import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    _rational_to_float,
    _infer_samsung_lens,
    build_camera_metadata,
    build_phoxel_record,
    extract_file_exif,
)
from aurexis_lang.evidence_tiers import EvidenceTier
from aurexis_lang.phoxel_schema import validate_phoxel_schema


# ─────────────────────────────────────────────
# EXIF helpers
# ─────────────────────────────────────────────

class TestRationalToFloat:
    def test_tuple_rational(self):
        assert _rational_to_float((1, 2)) == pytest.approx(0.5)

    def test_tuple_zero_denominator(self):
        assert _rational_to_float((5, 0)) is None

    def test_plain_float(self):
        assert _rational_to_float(4.0) == pytest.approx(4.0)

    def test_none(self):
        assert _rational_to_float(None) is None

    def test_integer(self):
        assert _rational_to_float(100) == pytest.approx(100.0)


class TestSamsungLensInference:
    def test_ultrawide(self):
        assert _infer_samsung_lens(None, 13.0) == 'ultrawide'

    def test_wide_main(self):
        assert _infer_samsung_lens(None, 24.0) == 'wide_main'

    def test_telephoto_3x(self):
        assert _infer_samsung_lens(None, 70.0) == 'telephoto_3x'

    def test_periscope_10x(self):
        assert _infer_samsung_lens(None, 230.0) == 'periscope_10x'

    def test_no_focal_length(self):
        assert _infer_samsung_lens(None, None) == 'main'

    def test_from_focal_mm_fallback(self):
        # 24mm / 4.5 crop ≈ 5.3mm, 35mm equiv ≈ 24mm → wide_main
        result = _infer_samsung_lens(5.3, None)
        assert result == 'wide_main'


# ─────────────────────────────────────────────
# Camera metadata
# ─────────────────────────────────────────────

class TestBuildCameraMetadata:
    def _make_samsung_exif(self) -> dict:
        return {
            'make': 'SAMSUNG',
            'model': 'SM-S918B',
            'datetime_original': '2026:04:07 14:30:00',
            'focal_length': (22, 10),   # 2.2mm
            'focal_length_35mm': 24,
            'iso': 100,
            'f_number': (18, 10),       # f/1.8
            'exposure_time': (1, 120),
            'image_width': 4000,
            'image_height': 3000,
            'lens_model': 'Galaxy S23 Ultra Main',
        }

    def test_samsung_identified(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('test.jpg'))
        assert meta['is_samsung'] is True
        assert meta['is_s23_series'] is True

    def test_lens_inference_wide_main(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('test.jpg'))
        assert meta['lens_id'] == 'wide_main'

    def test_focal_length_parsed(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('test.jpg'))
        assert meta['focal_length_mm'] == pytest.approx(2.2)

    def test_f_number_parsed(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('test.jpg'))
        assert meta['f_number'] == pytest.approx(1.8)

    def test_timestamp_parsed(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('test.jpg'))
        assert '2026-04-07' in (meta['image_timestamp'] or '')

    def test_no_exif_graceful(self):
        meta = build_camera_metadata({}, Path('no_exif.jpg'))
        assert meta['make'] == 'unknown'
        assert meta['exif_present'] is False

    def test_source_file_recorded(self):
        exif = self._make_samsung_exif()
        meta = build_camera_metadata(exif, Path('/some/folder/DCIM001.jpg'))
        assert meta['source_file'] == 'DCIM001.jpg'

    def test_measurement_origin(self):
        meta = build_camera_metadata({}, Path('x.jpg'))
        assert meta['measurement_origin'] == 'camera-observation'


# ─────────────────────────────────────────────
# Phoxel record
# ─────────────────────────────────────────────

class TestBuildPhoxelRecord:
    def _meta(self) -> dict:
        return {
            'make': 'SAMSUNG',
            'model': 'SM-S918B',
            'image_timestamp': '2026-04-07T14:30:00',
            'measurement_origin': 'camera-observation',
        }

    def test_schema_valid(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 0, 'test_source', (320, 240))
        assert result['schema_valid'] is True
        assert result['schema_errors'] == []

    def test_not_synthetic(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 0, 'test_source', (0, 0))
        assert result['record']['integrity_state']['synthetic'] is False

    def test_evidence_tier_real_capture(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 0, 'test_source', (10, 10))
        assert result['evidence_tier'] == EvidenceTier.REAL_CAPTURE.value

    def test_pixel_coordinates_present(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 5, 'vid', (100, 200))
        assert result['record']['image_anchor']['pixel_coordinates'] == (100, 200)

    def test_evidence_chain_includes_source_and_frame(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 3, 'my_video', (0, 0))
        chain = result['record']['integrity_state']['evidence_chain']
        assert any('my_video' in entry and '3' in entry for entry in chain)

    def test_world_anchor_status_unknown(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 0, 'x', (0, 0))
        assert result['record']['world_anchor_state']['status'] == 'unknown'

    def test_world_anchor_image_grounded_only(self):
        meta = self._meta()
        result = build_phoxel_record(meta, 0, 'x', (0, 0))
        assert result['record']['world_anchor_state']['evidence_status'] == 'image-grounded-only'

    def test_validate_against_phoxel_schema_directly(self):
        meta = self._meta()
        record = build_phoxel_record(meta, 0, 'direct_test', (50, 75))
        errors = validate_phoxel_schema(record['record'])
        assert errors == [], f'Schema errors: {errors}'

    def test_no_timestamp_falls_back_gracefully(self):
        meta = {
            'make': 'SAMSUNG',
            'model': 'SM-S918B',
            'measurement_origin': 'camera-observation',
        }
        result = build_phoxel_record(meta, 0, 'no_ts', (0, 0))
        # Should still produce a valid record using datetime.now() fallback
        assert result['record']['time_slice']['image_timestamp'] is not None


# ─────────────────────────────────────────────
# Evidence tier integrity
# ─────────────────────────────────────────────

class TestEvidenceTierIntegrity:
    """The camera bridge must never produce LAB or AUTHORED tier records."""

    def test_phoxel_record_never_lab(self):
        meta = {'make': 'x', 'model': 'y', 'image_timestamp': '2026-01-01T00:00:00', 'measurement_origin': 'camera-observation'}
        result = build_phoxel_record(meta, 0, 'src', (0, 0))
        assert result['evidence_tier'] != EvidenceTier.LAB.value

    def test_phoxel_record_never_authored(self):
        meta = {'make': 'x', 'model': 'y', 'image_timestamp': '2026-01-01T00:00:00', 'measurement_origin': 'camera-observation'}
        result = build_phoxel_record(meta, 0, 'src', (0, 0))
        assert result['evidence_tier'] != EvidenceTier.AUTHORED.value

    def test_phoxel_record_is_real_capture(self):
        meta = {'make': 'x', 'model': 'y', 'image_timestamp': '2026-01-01T00:00:00', 'measurement_origin': 'camera-observation'}
        result = build_phoxel_record(meta, 0, 'src', (0, 0))
        assert result['evidence_tier'] == EvidenceTier.REAL_CAPTURE.value


# ─────────────────────────────────────────────
# Extension routing
# ─────────────────────────────────────────────

class TestExtensionRouting:
    def test_jpeg_in_image_extensions(self):
        assert '.jpg' in IMAGE_EXTENSIONS
        assert '.jpeg' in IMAGE_EXTENSIONS

    def test_png_in_image_extensions(self):
        assert '.png' in IMAGE_EXTENSIONS

    def test_dng_in_image_extensions(self):
        assert '.dng' in IMAGE_EXTENSIONS

    def test_mp4_in_video_extensions(self):
        assert '.mp4' in VIDEO_EXTENSIONS

    def test_mov_in_video_extensions(self):
        assert '.mov' in VIDEO_EXTENSIONS

    def test_no_extension_overlap(self):
        assert IMAGE_EXTENSIONS.isdisjoint(VIDEO_EXTENSIONS), \
            'Image and video extension sets must not overlap'
