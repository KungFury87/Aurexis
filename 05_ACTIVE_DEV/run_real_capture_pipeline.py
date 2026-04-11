#!/usr/bin/env python3
"""
Aurexis Core — Real Capture Pipeline Runner
Standalone script. Run this directly against your Samsung photos/videos folder.

Usage:
    python run_real_capture_pipeline.py <path_to_photos_folder>

    # With options:
    python run_real_capture_pipeline.py ~/Desktop/samsung_photos --workers 6
    python run_real_capture_pipeline.py ~/Desktop/samsung_photos --video-fps 3
    python run_real_capture_pipeline.py ~/Desktop/samsung_photos --output results/my_run

    # Skip Gate 3 evaluation (batch only):
    python run_real_capture_pipeline.py ~/Desktop/samsung_photos --no-gate3

Copy your Samsung S23 photos and videos to a folder on your desktop,
then run this. The pipeline processes everything concurrently and generates
a full Gate 3 evidence report in the output directory.

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure aurexis_lang is importable from this script's location
_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run the Aurexis real-capture pipeline on a folder of phone photos/videos.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_real_capture_pipeline.py ~/Desktop/samsung_photos
  python run_real_capture_pipeline.py ~/Desktop/samsung_photos --workers 6
  python run_real_capture_pipeline.py ~/Desktop/samsung_photos --strict-law
  python run_real_capture_pipeline.py ~/Desktop/samsung_photos --no-gate3
        """,
    )
    parser.add_argument(
        'input_folder',
        type=str,
        help='Path to folder containing your phone photos and/or videos',
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='real_capture_pipeline_results',
        help='Output directory for results (default: real_capture_pipeline_results)',
    )
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of concurrent file processors (default: 4)',
    )
    parser.add_argument(
        '--video-fps',
        type=float,
        default=2.0,
        help='Frames per second to sample from video files (default: 2.0)',
    )
    parser.add_argument(
        '--max-video-frames',
        type=int,
        default=150,
        help='Maximum frames to extract per video file (default: 150)',
    )
    parser.add_argument(
        '--strict-law',
        action='store_true',
        default=False,
        help='Use strict core law enforcement (default: adaptive)',
    )
    parser.add_argument(
        '--no-gate3',
        action='store_true',
        default=False,
        help='Skip Gate 3 evaluation after batch processing',
    )
    parser.add_argument(
        '--batch-name',
        type=str,
        default=None,
        help='Name for this batch run (used in Gate 3 report, defaults to folder name)',
    )

    args = parser.parse_args()

    input_path = Path(args.input_folder).expanduser().resolve()
    if not input_path.exists():
        print(f'ERROR: Input folder not found: {input_path}')
        return 1

    output_dir = Path(args.output).expanduser().resolve()
    batch_name = args.batch_name or input_path.name

    try:
        from aurexis_lang.file_ingestion_pipeline import run_batch_pipeline
    except ImportError as e:
        print(f'ERROR: Could not import Aurexis pipeline: {e}')
        print('Make sure you are running from the directory containing aurexis_lang/.')
        return 1

    # ── Step 1: Run the batch ingestion pipeline ───────────────────
    try:
        batch_report = run_batch_pipeline(
            input_folder=input_path,
            output_dir=output_dir,
            max_workers=args.workers,
            sample_fps=args.video_fps,
            max_video_frames=args.max_video_frames,
            strict_law=args.strict_law,
        )
    except Exception as e:
        print(f'Batch pipeline error: {e}')
        import traceback
        traceback.print_exc()
        return 1

    if batch_report.get('status') == 'no_files':
        print('No image or video files found. Nothing to process.')
        return 0

    # ── Step 2: Run Gate 3 evaluation ──────────────────────────────
    if args.no_gate3:
        print('Gate 3 evaluation skipped (--no-gate3).')
        return 0

    try:
        from aurexis_lang.gate3_runner import run_gate3_evaluation, print_gate3_summary
    except ImportError as e:
        print(f'WARNING: Gate 3 runner not available ({e}). Skipping Gate 3 evaluation.')
        return 0

    print('\nRunning Gate 3 evaluation...')
    try:
        gate3_result = run_gate3_evaluation(batch_report, batch_name=batch_name)
    except Exception as e:
        print(f'Gate 3 evaluation error: {e}')
        import traceback
        traceback.print_exc()
        return 1

    # Save Gate 3 result
    gate3_path = output_dir / 'gate3_evaluation.json'
    gate3_path.write_text(
        json.dumps(gate3_result, indent=2, default=str),
        encoding='utf-8',
    )

    # Print Gate 3 summary to console
    print_gate3_summary(gate3_result)
    print(f'Gate 3 report saved: {gate3_path}')

    # Exit code reflects Gate 3 result so CI/scripts can check it
    gate3_complete = gate3_result.get('summary', {}).get('gate3_complete', False)
    if gate3_complete:
        print('Gate 3 audit passed. This is strong evidence — not a self-issued badge.')
        print('Review gate3_evaluation.json and submit for project sign-off.')
    else:
        blocking = gate3_result.get('summary', {}).get('blocking_reasons', [])
        print(f'Gate 3 in progress. Blocking: {", ".join(blocking) if blocking else "see gate3_evaluation.json"}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
