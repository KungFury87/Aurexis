#!/usr/bin/env python3
"""
Aurexis Core — M8 Live Camera Pipeline Runner

Connects to IP Webcam on your Samsung S23 and processes live camera
frames through the full Aurexis pipeline in real-time.

Setup:
  1. Install IP Webcam on your S23 (free from Play Store)
  2. Open IP Webcam, tap "Start server"
  3. Note the IP address shown (e.g., 192.168.12.251:8080)
  4. Make sure phone and PC are on the same WiFi (VPN off)
  5. Run this script

Usage:
    python run_live_pipeline.py
    python run_live_pipeline.py --url http://192.168.12.251:8080
    python run_live_pipeline.py --duration 30
    python run_live_pipeline.py --fps 1

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run Aurexis live camera pipeline (M8).',
    )
    parser.add_argument(
        '--url', '-u',
        type=str,
        default='http://192.168.12.251:8080',
        help='IP Webcam base URL (default: http://192.168.12.251:8080)',
    )
    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=60.0,
        help='How long to run in seconds (default: 60)',
    )
    parser.add_argument(
        '--fps', '-f',
        type=float,
        default=2.0,
        help='Target frames per second (default: 2.0)',
    )
    parser.add_argument(
        '--mode', '-m',
        type=str,
        default='snapshot',
        choices=['snapshot', 'stream'],
        help='Frame grab mode (default: snapshot)',
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='m8_live_run_1',
        help='Output directory for results',
    )

    args = parser.parse_args()

    try:
        from aurexis_lang.live_camera_feed import LivePipeline
    except ImportError as e:
        print(f'ERROR: Import failed: {e}')
        return 1

    pipeline = LivePipeline(
        base_url=args.url,
        mode=args.mode,
        target_fps=args.fps,
        output_dir=Path(args.output),
    )

    report = pipeline.run(duration_seconds=args.duration)

    m8_complete = report.get('executable_reached', False) and \
                  report.get('law_compliance', 0) >= 1.0 and \
                  report.get('all_within_tech_floor', False)

    return 0 if m8_complete else 1


if __name__ == '__main__':
    sys.exit(main())
