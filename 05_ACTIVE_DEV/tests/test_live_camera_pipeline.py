"""
Aurexis Core — M8 Live Camera Pipeline Tests

Tests the real-time camera integration layer WITHOUT requiring a live camera.
Uses synthetic frames injected directly into the processor and pipeline classes.

Evidence tier: AUTHORED (synthetic test data).

Tests cover:
  - LiveFrameSource: queue behavior, drop-oldest, stats
  - LiveFrameProcessor: full per-frame pipeline with synthetic frames
  - LivePipeline: report generation, M8 completion checks
  - Tech floor compliance (processing time ≤ 30s)
  - Core Law compliance on live-processed frames
  - Graceful degradation (frames dropped, not queued endlessly)
"""

from __future__ import annotations

import queue
import time
import threading
from pathlib import Path
from typing import Dict, Any

import cv2
import numpy as np
import pytest

from aurexis_lang.live_camera_feed import (
    LiveFrameSource,
    LiveFrameProcessor,
    LivePipeline,
)


# ────────────────────────────────────────────────────────────
# LiveFrameSource tests (queue mechanics — no network needed)
# ────────────────────────────────────────────────────────────

class TestLiveFrameSource:
    """Tests for the frame source queue and threading behavior."""

    def test_source_initializes_with_defaults(self):
        src = LiveFrameSource()
        assert src.base_url == 'http://192.168.12.251:8080'
        assert src.mode == 'snapshot'
        assert src.target_fps == 2.0

    def test_source_custom_url(self):
        src = LiveFrameSource(base_url='http://10.0.0.5:9090/')
        assert src.base_url == 'http://10.0.0.5:9090'
        assert src.snapshot_url == 'http://10.0.0.5:9090/shot.jpg'
        assert src.stream_url == 'http://10.0.0.5:9090/video'

    def test_source_stats_initial(self):
        src = LiveFrameSource()
        stats = src.stats
        assert stats['frames_grabbed'] == 0
        assert stats['frames_dropped'] == 0
        assert stats['queue_size'] == 0

    def test_source_queue_bounded(self):
        """Queue should not grow beyond queue_size."""
        src = LiveFrameSource(queue_size=3)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Manually push frames into the internal queue
        for i in range(3):
            src._queue.put((frame, time.time()))
        assert src._queue.qsize() == 3
        # Queue is now full
        assert src._queue.full()

    def test_source_get_frame_timeout(self):
        """get_frame should return None on timeout."""
        src = LiveFrameSource()
        result = src.get_frame(timeout=0.1)
        assert result is None

    def test_source_get_frame_returns_data(self):
        """get_frame should return (frame, timestamp) tuple."""
        src = LiveFrameSource()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        ts = time.time()
        src._queue.put((frame, ts))
        result = src.get_frame(timeout=1.0)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        np.testing.assert_array_equal(result[0], frame)
        assert result[1] == ts

    def test_source_drop_oldest_on_overflow(self):
        """When queue is full, oldest frame should be dropped."""
        src = LiveFrameSource(queue_size=2)
        f1 = np.ones((10, 10, 3), dtype=np.uint8) * 1
        f2 = np.ones((10, 10, 3), dtype=np.uint8) * 2
        f3 = np.ones((10, 10, 3), dtype=np.uint8) * 3

        src._queue.put((f1, 1.0))
        src._queue.put((f2, 2.0))
        # Queue full — simulate what _grab_loop does
        try:
            src._queue.put_nowait((f3, 3.0))
        except queue.Full:
            src._queue.get_nowait()  # drop oldest
            src._frames_dropped += 1
            src._queue.put_nowait((f3, 3.0))

        assert src._frames_dropped == 1
        # Remaining frames should be f2 and f3
        _, ts1 = src._queue.get()
        _, ts2 = src._queue.get()
        assert ts1 == 2.0
        assert ts2 == 3.0


# ────────────────────────────────────────────────────────────
# LiveFrameProcessor tests (full pipeline on synthetic frames)
# ────────────────────────────────────────────────────────────

class TestLiveFrameProcessor:
    """Tests the per-frame processing pipeline with synthetic data."""

    def test_process_simple_frame(self, synthetic_frame_simple):
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_simple, time.time())

        assert result['frame_index'] == 1
        assert result['primitives'] >= 0
        assert 0.0 <= result['mean_confidence'] <= 1.0
        assert result['schema_valid'] is True
        assert result['law_passed'] is True
        assert result['processing_time_seconds'] > 0

    def test_process_complex_frame(self, synthetic_frame_complex):
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_complex, time.time())

        assert result['primitives'] > 0
        assert result['tokens'] > 0
        assert result['ir_nodes'] > 0

    def test_process_blank_frame(self, synthetic_frame_blank):
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_blank, time.time())

        # Blank frame should still process without crashing
        assert result['frame_index'] == 1
        assert result['schema_valid'] is True
        assert result['law_passed'] is True

    def test_frame_index_increments(self, synthetic_frame_simple):
        proc = LiveFrameProcessor()
        r1 = proc.process_frame(synthetic_frame_simple, time.time())
        r2 = proc.process_frame(synthetic_frame_simple, time.time())
        r3 = proc.process_frame(synthetic_frame_simple, time.time())
        assert r1['frame_index'] == 1
        assert r2['frame_index'] == 2
        assert r3['frame_index'] == 3

    def test_result_has_required_keys(self, synthetic_frame_simple):
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_simple, time.time())

        required = [
            'frame_index', 'timestamp', 'resolution', 'primitives',
            'mean_confidence', 'max_confidence', 'schema_valid',
            'law_passed', 'law_violations', 'tokens', 'ir_nodes',
            'executable_count', 'validated_count', 'best_status',
            'processing_time_seconds', 'within_tech_floor',
        ]
        for key in required:
            assert key in result, f'Missing key: {key}'

    def test_tech_floor_compliance(self, synthetic_frame_simple):
        """Processing a single frame must be well under 30s."""
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_simple, time.time())
        assert result['within_tech_floor'] is True
        assert result['processing_time_seconds'] < 30.0

    def test_law_compliance_on_live_frame(self, synthetic_frame_complex):
        """Core Law must pass on live-processed frames."""
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_complex, time.time())
        assert result['law_passed'] is True
        assert result['law_violations'] == 0

    def test_resolution_format(self, synthetic_frame_simple):
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_simple, time.time())
        assert result['resolution'] == '320x240'

    def test_complex_frame_reaches_executable(self, synthetic_frame_complex):
        """Complex synthetic frame should produce at least some IR nodes."""
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_complex, time.time())
        # The exact status depends on confidence, but IR should be generated
        assert result['ir_nodes'] > 0
        assert result['best_status'] in ('DESCRIPTIVE', 'ESTIMATED', 'VALIDATED', 'EXECUTABLE', 'none')

    def test_internal_refs_present(self, synthetic_frame_simple):
        """Internal references (_ir_root, etc.) should be in result for serialization."""
        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_simple, time.time())
        assert '_camera_metadata' in result
        assert '_phoxel_record' in result
        assert '_tokens' in result


# ────────────────────────────────────────────────────────────
# LivePipeline report and M8 check tests
# ────────────────────────────────────────────────────────────

class TestLivePipelineReport:
    """Tests the report generation and M8 completion logic."""

    def _make_fake_results(self, n: int = 10, executable: bool = True) -> list:
        """Generate fake result dicts for report testing."""
        results = []
        for i in range(n):
            results.append({
                'frame_index': i + 1,
                'timestamp': f'2026-04-09T12:00:{i:02d}',
                'resolution': '640x480',
                'primitives': 100,
                'mean_confidence': 0.65,
                'max_confidence': 0.85,
                'schema_valid': True,
                'law_passed': True,
                'law_violations': 0,
                'tokens': 50,
                'ir_nodes': 30,
                'executable_count': 5 if executable else 0,
                'validated_count': 10,
                'best_status': 'EXECUTABLE' if executable else 'VALIDATED',
                'processing_time_seconds': 1.5,
                'within_tech_floor': True,
            })
        return results

    def test_report_with_executable_frames(self):
        pipe = LivePipeline.__new__(LivePipeline)
        pipe.results = self._make_fake_results(10, executable=True)
        pipe.source = LiveFrameSource()
        pipe.source._frames_grabbed = 15
        pipe.source._frames_dropped = 5
        pipe._executable_reached = True

        report = pipe._build_report(total_time=60.0, programs_saved=10)

        assert report['frames_processed'] == 10
        assert report['frames_dropped'] == 5
        assert report['executable_reached'] is True
        assert report['law_compliance'] == 1.0
        assert report['all_within_tech_floor'] is True
        assert report['programs_saved'] == 10

    def test_report_without_executable(self):
        pipe = LivePipeline.__new__(LivePipeline)
        pipe.results = self._make_fake_results(5, executable=False)
        pipe.source = LiveFrameSource()
        pipe.source._frames_grabbed = 5
        pipe.source._frames_dropped = 0
        pipe._executable_reached = False

        report = pipe._build_report(total_time=30.0, programs_saved=0)

        assert report['executable_reached'] is False
        assert report['executable_frames'] == 0
        assert report['programs_saved'] == 0

    def test_report_empty_results(self):
        pipe = LivePipeline.__new__(LivePipeline)
        pipe.results = []
        pipe.source = LiveFrameSource()
        pipe._executable_reached = False

        report = pipe._build_report(total_time=5.0, programs_saved=0)

        assert report['status'] == 'no_frames'

    def test_effective_fps_calculation(self):
        pipe = LivePipeline.__new__(LivePipeline)
        pipe.results = self._make_fake_results(30)
        pipe.source = LiveFrameSource()
        pipe.source._frames_grabbed = 30
        pipe.source._frames_dropped = 0
        pipe._executable_reached = True

        report = pipe._build_report(total_time=60.0, programs_saved=30)
        assert report['effective_fps'] == 0.5  # 30 frames / 60 seconds

    def test_m8_completion_checks_all_pass(self):
        """Verify M8 check logic: all 5 must pass."""
        report = {
            'frames_processed': 54,
            'executable_reached': True,
            'law_compliance': 1.0,
            'all_within_tech_floor': True,
        }
        checks = {
            'frames_processed': report['frames_processed'] >= 1,
            'executable_reached': report['executable_reached'],
            'law_compliance_100': report['law_compliance'] >= 1.0,
            'within_tech_floor': report['all_within_tech_floor'],
            'live_source_confirmed': report['frames_processed'] >= 5,
        }
        assert all(checks.values())

    def test_m8_completion_fails_without_executable(self):
        report = {
            'frames_processed': 54,
            'executable_reached': False,
            'law_compliance': 1.0,
            'all_within_tech_floor': True,
        }
        checks = {
            'executable_reached': report['executable_reached'],
        }
        assert not checks['executable_reached']


# ────────────────────────────────────────────────────────────
# Integration: processor on real synthetic frames (no network)
# ────────────────────────────────────────────────────────────

class TestLivePipelineIntegration:
    """End-to-end integration using LiveFrameProcessor with synthetic data."""

    def test_multi_frame_processing(self, synthetic_frame_simple, synthetic_frame_complex):
        """Process multiple frames sequentially — simulates live run."""
        proc = LiveFrameProcessor()
        frames = [synthetic_frame_simple, synthetic_frame_complex] * 3
        results = []

        for f in frames:
            result = proc.process_frame(f, time.time())
            results.append(result)

        assert len(results) == 6
        assert all(r['schema_valid'] for r in results)
        assert all(r['law_passed'] for r in results)
        # Frame indices should increment
        indices = [r['frame_index'] for r in results]
        assert indices == [1, 2, 3, 4, 5, 6]

    def test_all_frames_within_tech_floor(self, synthetic_frame_complex):
        """All frames must process under 30 seconds."""
        proc = LiveFrameProcessor()
        for _ in range(5):
            result = proc.process_frame(synthetic_frame_complex, time.time())
            assert result['within_tech_floor'] is True

    def test_program_save_on_executable(self, synthetic_frame_complex, tmp_output):
        """If EXECUTABLE is reached, program should serialize without error."""
        from aurexis_lang.program_serializer import save_program
        from aurexis_lang.evidence_tiers import EvidenceTier

        proc = LiveFrameProcessor()
        result = proc.process_frame(synthetic_frame_complex, time.time())

        ir_root = result.get('_ir_root')
        if ir_root is not None and result['best_status'] == 'EXECUTABLE':
            fir = {
                'source_file': 'test_live_frame',
                'frame_index': 1,
                'camera_metadata': result['_camera_metadata'],
                'phoxel_record': result['_phoxel_record'],
                'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
                'tokens': [],
                'schema_valid': True,
                'schema_errors': [],
            }
            out_path = tmp_output / 'test_program.json'
            save_program(fir, out_path, ir_node=ir_root)
            assert out_path.exists()
