"""
live_camera_feed.py — M8 Real-Time Camera Integration

Connects to a live camera feed (IP Webcam, DroidCam, or any MJPEG/RTSP source)
and processes frames through the full Aurexis pipeline in real-time.

Architecture:
  - Producer thread: grabs frames from the camera feed at ~2-5 FPS
  - Consumer (main thread): processes frames through EnhancedCVExtractor → tokens →
    AST → IR → optimizer. Drops frames if processing can't keep up.
  - Display: prints live phoxel field status to terminal after each frame

Tech floor constraints (Core Law Section 6):
  - Max processing time: 30 seconds per frame batch
  - Graceful degradation: drop frames rather than queue endlessly

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import json
import queue
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .enhanced_cv_extractor import EnhancedCVExtractor
from .camera_bridge import build_camera_metadata, build_phoxel_record
from .visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from .parser_expanded import parse_tokens_expanded
from .ir import ast_to_ir, IRNode
from .ir_optimizer import (
    optimize as optimize_ir,
    _all_nodes,
    _get_opt,
    EXECUTABLE,
    VALIDATED,
    DESCRIPTIVE,
)
from .core_law_enforcer import enforce_core_law
from .phoxel_schema import validate_phoxel_schema
from .evidence_tiers import EvidenceTier
from .program_serializer import save_program


# ────────────────────────────────────────────────────────────
# Frame source — pulls frames from IP Webcam or any MJPEG feed
# ────────────────────────────────────────────────────────────

class LiveFrameSource:
    """
    Grabs frames from an IP Webcam (or any HTTP MJPEG/snapshot source).
    Runs in a background thread, pushes frames to a bounded queue.
    Drops old frames when the queue is full (graceful degradation).
    """

    def __init__(
        self,
        base_url: str = 'http://192.168.12.251:8080',
        mode: str = 'snapshot',       # 'snapshot' or 'stream'
        target_fps: float = 2.0,      # target frames per second
        queue_size: int = 5,          # max frames buffered
    ):
        self.base_url = base_url.rstrip('/')
        self.mode = mode
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps

        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frames_grabbed = 0
        self._frames_dropped = 0
        self._cap: Optional[cv2.VideoCapture] = None

    @property
    def snapshot_url(self) -> str:
        return f'{self.base_url}/shot.jpg'

    @property
    def stream_url(self) -> str:
        return f'{self.base_url}/video'

    def start(self) -> None:
        """Start the frame grabber thread."""
        self._stop_event.clear()
        if self.mode == 'stream':
            self._cap = cv2.VideoCapture(self.stream_url)
        self._thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the frame grabber thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
            self._cap = None

    def get_frame(self, timeout: float = 2.0) -> Optional[Tuple[np.ndarray, float]]:
        """
        Get the next frame from the queue.
        Returns (frame, timestamp) or None if timeout.
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def stats(self) -> Dict[str, int]:
        return {
            'frames_grabbed': self._frames_grabbed,
            'frames_dropped': self._frames_dropped,
            'queue_size': self._queue.qsize(),
        }

    def _grab_loop(self) -> None:
        """Background thread: grab frames at target FPS."""
        while not self._stop_event.is_set():
            t0 = time.time()
            frame = self._grab_one_frame()
            if frame is not None:
                self._frames_grabbed += 1
                try:
                    self._queue.put_nowait((frame, time.time()))
                except queue.Full:
                    # Drop oldest frame, add new one
                    try:
                        self._queue.get_nowait()
                        self._frames_dropped += 1
                    except queue.Empty:
                        pass
                    self._queue.put_nowait((frame, time.time()))

            # Sleep to maintain target FPS
            elapsed = time.time() - t0
            sleep_time = self.frame_interval - elapsed
            if sleep_time > 0:
                self._stop_event.wait(timeout=sleep_time)

    def _grab_one_frame(self) -> Optional[np.ndarray]:
        """Grab a single frame from the source."""
        try:
            if self.mode == 'snapshot':
                resp = urllib.request.urlopen(self.snapshot_url, timeout=3)
                img_array = np.frombuffer(resp.read(), dtype=np.uint8)
                return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                if self._cap and self._cap.isOpened():
                    ret, frame = self._cap.read()
                    return frame if ret else None
                return None
        except Exception:
            return None


# ────────────────────────────────────────────────────────────
# Live frame processor — full Aurexis pipeline per frame
# ────────────────────────────────────────────────────────────

class LiveFrameProcessor:
    """
    Processes a single frame through the full Aurexis pipeline:
    frame → CV extraction → tokens → AST → IR → optimize → (optional) serialize
    """

    def __init__(self):
        self.extractor = EnhancedCVExtractor(adaptive_mode=True)
        self._frame_count = 0

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        source_id: str = 'live_camera',
    ) -> Dict[str, Any]:
        """
        Run one frame through the full pipeline.
        Returns a result dict with all metrics.
        """
        t0 = time.time()
        self._frame_count += 1
        frame_idx = self._frame_count
        h, w = frame.shape[:2]

        # ── Step 1: CV Extraction ──────────────────────────
        extraction = self.extractor.extract_robust_primitives(frame)
        primitives = extraction.get('primitive_observations', [])
        prim_count = len(primitives)

        # Get mean confidence from extraction
        if primitives:
            confs = [p.get('confidence', 0) for p in primitives]
            mean_conf = sum(confs) / len(confs)
            max_conf = max(confs)
        else:
            mean_conf = 0.0
            max_conf = 0.0

        # ── Step 2: Build camera metadata + phoxel record ──
        meta = {
            'make': 'SAMSUNG',
            'model': 'SM-S918B',
            'image_timestamp': datetime.fromtimestamp(timestamp).isoformat(),
            'measurement_origin': 'camera-observation',
            'source_file': f'live_frame_{frame_idx}',
            'image_width': w,
            'image_height': h,
            'is_samsung': True,
            'is_s23_series': True,
            'lens_id': 'wide_main',
            'exif_present': False,
        }
        phoxel = build_phoxel_record(meta, frame_idx, source_id, (w // 2, h // 2))
        schema_valid = phoxel.get('schema_valid', False)

        # ── Step 3: Core Law enforcement ───────────────────
        record = phoxel.get('record', {})
        claim = {
            'phoxel_record': record,
            'image_anchor': record.get('image_anchor', {}),
            'time_slice': record.get('time_slice', {}),
            'camera_metadata': meta,
            'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
            'synthetic': False,
            'traceable': True,
        }
        law_passed, violations = enforce_core_law(claim)

        # ── Step 4: Tokenize → Parse → IR ─────────────────
        prim_obs = []
        for p in primitives:
            prim_obs.append(PrimitiveObservation(
                primitive_type=p.get('primitive_type', 'unknown'),
                attributes=p.get('attributes', {}),
                confidence=p.get('confidence', 0),
            ))

        tokens = primitives_to_tokens(prim_obs) if prim_obs else []
        ast = parse_tokens_expanded(tokens) if tokens else None
        ir_root = ast_to_ir(ast) if ast else None

        # ── Step 5: Optimize IR ────────────────────────────
        executable_count = 0
        validated_count = 0
        best_status = 'none'

        if ir_root is not None:
            phoxel_context = {
                'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
                'record': {
                    'integrity_state': {
                        'synthetic': False,
                        'traceable': True,
                        'evidence_chain': [f'{source_id}/frame_{frame_idx}'],
                    },
                    'image_anchor': record.get('image_anchor', {}),
                    'world_anchor_state': record.get('world_anchor_state', {}),
                    'time_slice': record.get('time_slice', {}),
                },
            }
            optimized, opt_report = optimize_ir(ir_root, phoxel_context=phoxel_context)
            executable_count = opt_report.executable_count
            validated_count = opt_report.validated_count

            if executable_count > 0:
                best_status = 'EXECUTABLE'
            elif validated_count > 0:
                best_status = 'VALIDATED'
            elif opt_report.descriptive_count > 0:
                best_status = 'DESCRIPTIVE'
        else:
            optimized = None
            opt_report = None

        processing_time = time.time() - t0

        return {
            'frame_index': frame_idx,
            'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
            'resolution': f'{w}x{h}',
            'primitives': prim_count,
            'mean_confidence': round(mean_conf, 4),
            'max_confidence': round(max_conf, 4),
            'schema_valid': schema_valid,
            'law_passed': law_passed,
            'law_violations': len(violations),
            'tokens': len(tokens),
            'ir_nodes': len(list(_all_nodes(optimized))) if optimized else 0,
            'executable_count': executable_count,
            'validated_count': validated_count,
            'best_status': best_status,
            'processing_time_seconds': round(processing_time, 3),
            'within_tech_floor': processing_time <= 30.0,
            # Keep references for serialization
            '_ir_root': optimized,
            '_opt_report': opt_report,
            '_phoxel_record': phoxel,
            '_camera_metadata': meta,
            '_tokens': tokens,
        }


# ────────────────────────────────────────────────────────────
# Live pipeline — ties it all together
# ────────────────────────────────────────────────────────────

class LivePipeline:
    """
    Full real-time Aurexis pipeline.
    Grabs frames from a live source, processes them, displays results.
    """

    def __init__(
        self,
        base_url: str = 'http://192.168.12.251:8080',
        mode: str = 'snapshot',
        target_fps: float = 2.0,
        output_dir: Optional[Path] = None,
    ):
        self.source = LiveFrameSource(
            base_url=base_url,
            mode=mode,
            target_fps=target_fps,
        )
        self.processor = LiveFrameProcessor()
        self.output_dir = Path(output_dir) if output_dir else None
        self.results: List[Dict[str, Any]] = []
        self._start_time: float = 0
        self._executable_reached = False

    def run(self, duration_seconds: float = 60.0) -> Dict[str, Any]:
        """
        Run the live pipeline for the specified duration.
        Returns a summary report.
        """
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            programs_dir = self.output_dir / 'programs'
            programs_dir.mkdir(exist_ok=True)

        print('=' * 65)
        print('  AUREXIS CORE — LIVE CAMERA PIPELINE')
        print('=' * 65)
        print(f'  Source:   {self.source.base_url}')
        print(f'  Mode:     {self.source.mode}')
        print(f'  Duration: {duration_seconds}s')
        print(f'  Target:   {self.source.target_fps} FPS')
        print()

        self.source.start()
        self._start_time = time.time()
        programs_saved = 0

        try:
            while (time.time() - self._start_time) < duration_seconds:
                frame_data = self.source.get_frame(timeout=2.0)
                if frame_data is None:
                    print('  [waiting for frame...]')
                    continue

                frame, timestamp = frame_data
                result = self.processor.process_frame(frame, timestamp)
                self.results.append(result)

                # Check if EXECUTABLE reached
                if result['best_status'] == 'EXECUTABLE' and not self._executable_reached:
                    self._executable_reached = True

                # Save program if EXECUTABLE
                if result['best_status'] == 'EXECUTABLE' and self.output_dir:
                    ir_root = result.get('_ir_root')
                    if ir_root is not None:
                        try:
                            fir = {
                                'source_file': f'live_frame_{result["frame_index"]}',
                                'frame_index': result['frame_index'],
                                'camera_metadata': result['_camera_metadata'],
                                'phoxel_record': result['_phoxel_record'],
                                'evidence_tier': EvidenceTier.REAL_CAPTURE.value,
                                'tokens': [],
                                'schema_valid': result['schema_valid'],
                                'schema_errors': [],
                            }
                            out_path = programs_dir / f'live_program_{result["frame_index"]:04d}.json'
                            save_program(fir, out_path, ir_node=ir_root)
                            programs_saved += 1
                        except Exception:
                            pass  # Non-fatal — keep processing

                # Display live status
                self._print_frame_status(result)

                elapsed = time.time() - self._start_time
                remaining = duration_seconds - elapsed
                if remaining < 0:
                    break

        except KeyboardInterrupt:
            print('\n  [Stopped by user]')
        finally:
            self.source.stop()

        total_time = time.time() - self._start_time
        report = self._build_report(total_time, programs_saved)

        if self.output_dir:
            report_path = self.output_dir / 'live_pipeline_report.json'
            # Remove non-serializable fields
            clean_results = []
            for r in self.results:
                clean = {k: v for k, v in r.items() if not k.startswith('_')}
                clean_results.append(clean)
            report['frame_results'] = clean_results
            report_path.write_text(
                json.dumps(report, indent=2, default=str),
                encoding='utf-8',
            )

        self._print_summary(report)
        return report

    def _print_frame_status(self, result: Dict[str, Any]) -> None:
        """Print one line per frame showing live pipeline status."""
        elapsed = time.time() - self._start_time
        status = result['best_status']

        # Color-code status
        if status == 'EXECUTABLE':
            status_str = f'\033[92m{status}\033[0m'   # green
        elif status == 'VALIDATED':
            status_str = f'\033[93m{status}\033[0m'    # yellow
        else:
            status_str = f'\033[90m{status}\033[0m'    # gray

        law_str = '\033[92m✓\033[0m' if result['law_passed'] else '\033[91m✗\033[0m'

        print(
            f'  [{elapsed:6.1f}s] '
            f'frame {result["frame_index"]:4d}  '
            f'prims={result["primitives"]:3d}  '
            f'conf={result["mean_confidence"]:.3f}  '
            f'law={law_str}  '
            f'exec={result["executable_count"]:3d}  '
            f'status={status_str}  '
            f't={result["processing_time_seconds"]:.2f}s'
        )

    def _build_report(self, total_time: float, programs_saved: int) -> Dict[str, Any]:
        """Build the final pipeline report."""
        if not self.results:
            return {'status': 'no_frames', 'total_time': total_time}

        prims = [r['primitives'] for r in self.results]
        confs = [r['mean_confidence'] for r in self.results]
        times = [r['processing_time_seconds'] for r in self.results]
        exec_frames = sum(1 for r in self.results if r['best_status'] == 'EXECUTABLE')
        law_pass = sum(1 for r in self.results if r['law_passed'])

        return {
            'pipeline': 'live_camera',
            'source': self.source.base_url,
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': round(total_time, 1),
            'frames_processed': len(self.results),
            'frames_grabbed': self.source.stats['frames_grabbed'],
            'frames_dropped': self.source.stats['frames_dropped'],
            'primitives': {
                'mean': round(sum(prims) / len(prims), 1),
                'min': min(prims),
                'max': max(prims),
            },
            'confidence': {
                'mean': round(sum(confs) / len(confs), 4),
                'min': round(min(confs), 4),
                'max': round(max(confs), 4),
            },
            'processing_time': {
                'mean': round(sum(times) / len(times), 3),
                'min': round(min(times), 3),
                'max': round(max(times), 3),
            },
            'law_compliance': round(law_pass / len(self.results), 4),
            'executable_frames': exec_frames,
            'executable_reached': self._executable_reached,
            'programs_saved': programs_saved,
            'all_within_tech_floor': all(r['within_tech_floor'] for r in self.results),
            'effective_fps': round(len(self.results) / total_time, 2) if total_time > 0 else 0,
        }

    def _print_summary(self, report: Dict[str, Any]) -> None:
        """Print the final summary."""
        print()
        print('=' * 65)
        print('  LIVE PIPELINE SUMMARY')
        print('=' * 65)
        print(f'  Duration:          {report.get("total_time_seconds", 0):.1f}s')
        print(f'  Frames processed:  {report.get("frames_processed", 0)}')
        print(f'  Frames dropped:    {report.get("frames_dropped", 0)}')
        print(f'  Effective FPS:     {report.get("effective_fps", 0):.2f}')
        print()

        p = report.get('primitives', {})
        c = report.get('confidence', {})
        t = report.get('processing_time', {})
        print(f'  Primitives/frame:  {p.get("mean", 0):.1f} (min={p.get("min", 0)}, max={p.get("max", 0)})')
        print(f'  Mean confidence:   {c.get("mean", 0):.4f}')
        print(f'  Processing time:   {t.get("mean", 0):.3f}s/frame (max={t.get("max", 0):.3f}s)')
        print(f'  Law compliance:    {report.get("law_compliance", 0):.0%}')
        print(f'  Tech floor OK:     {report.get("all_within_tech_floor", False)}')
        print()

        exec_reached = report.get('executable_reached', False)
        exec_frames = report.get('executable_frames', 0)
        programs = report.get('programs_saved', 0)

        if exec_reached:
            print(f'  \033[92m✅ EXECUTABLE reached on {exec_frames} frames\033[0m')
            print(f'  \033[92m   {programs} programs saved\033[0m')
        else:
            print(f'  \033[93m⏳ EXECUTABLE not yet reached\033[0m')

        # M8 completion check
        m8_checks = {
            'frames_processed': report.get('frames_processed', 0) >= 1,
            'executable_reached': exec_reached,
            'law_compliance_100': report.get('law_compliance', 0) >= 1.0,
            'within_tech_floor': report.get('all_within_tech_floor', False),
            'live_source_confirmed': report.get('frames_processed', 0) >= 5,
        }

        print()
        print('  M8 Completion Checks:')
        for check, passed in m8_checks.items():
            icon = '\033[92m✅\033[0m' if passed else '\033[91m❌\033[0m'
            print(f'    {icon}  {check}')

        m8_complete = all(m8_checks.values())
        print()
        if m8_complete:
            print('  ══════════════════════════════════════════════════')
            print('  ║  M8 COMPLETE — Real-Time Camera Integration ✅ ║')
            print('  ══════════════════════════════════════════════════')
        else:
            failed = [k for k, v in m8_checks.items() if not v]
            print(f'  M8 NOT YET COMPLETE. Failed: {", ".join(failed)}')
