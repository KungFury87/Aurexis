#!/usr/bin/env python3
"""
Aurexis Core — Gate 4 EXECUTABLE Promotion Pipeline
Standalone script. Run after Gate 3 is confirmed complete.

Takes the Gate 3 batch_report.json and original photo folder,
selects the highest-confidence images, runs them through the full
Aurexis pipeline to IR, attempts EXECUTABLE promotion, and serializes
any promoted programs as AUREXIS_PROGRAM_V1 files.

Usage:
    python run_gate4_pipeline.py <batch_report.json> <photo_folder>

    # With options:
    python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/path/to/photos"
    python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/path/to/photos" --top 30
    python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/path/to/photos" --output gate4_run_1

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run Gate 4 EXECUTABLE promotion pipeline.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/Users/vince/Desktop/s23 photos"
  python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/Users/vince/Desktop/s23 photos" --top 30
  python run_gate4_pipeline.py gate3_run_2/batch_report.json "C:/Users/vince/Desktop/s23 photos" --output gate4_run_1
        """,
    )
    parser.add_argument(
        'batch_report',
        type=str,
        help='Path to gate3_run_X/batch_report.json',
    )
    parser.add_argument(
        'photo_folder',
        type=str,
        help='Path to the original S23 photo folder',
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='gate4_run_1',
        help='Output directory for Gate 4 results (default: gate4_run_1)',
    )
    parser.add_argument(
        '--top', '-n',
        type=int,
        default=25,
        help='How many top-confidence files to process (default: 25)',
    )

    args = parser.parse_args()

    batch_path = Path(args.batch_report).expanduser().resolve()
    photo_path = Path(args.photo_folder).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not batch_path.exists():
        print(f'ERROR: Batch report not found: {batch_path}')
        return 1
    if not photo_path.exists():
        print(f'ERROR: Photo folder not found: {photo_path}')
        return 1

    try:
        from aurexis_lang.gate4_runner import run_gate4_evaluation, print_gate4_summary
    except ImportError as e:
        print(f'ERROR: Could not import Gate 4 runner: {e}')
        return 1

    print(f'Loading batch report: {batch_path}')
    batch_report = json.loads(batch_path.read_text(encoding='utf-8'))
    print(f'Files in report: {batch_report.get("files_processed", "?")}')
    print(f'Processing top {args.top} by confidence...')

    try:
        gate4_result = run_gate4_evaluation(
            batch_report=batch_report,
            photo_folder=photo_path,
            output_dir=output_dir,
            top_n=args.top,
        )
    except Exception as e:
        print(f'Gate 4 evaluation error: {e}')
        import traceback
        traceback.print_exc()
        return 1

    # Save full result
    result_path = output_dir / 'gate4_evaluation.json'
    result_path.write_text(
        json.dumps(gate4_result, indent=2, default=str),
        encoding='utf-8',
    )

    print_gate4_summary(gate4_result)
    print(f'Gate 4 report saved: {result_path}')

    gate4_complete = gate4_result.get('summary', {}).get('gate4_complete', False)
    if gate4_complete:
        prog_count = gate4_result.get('stats', {}).get('programs_saved', 0)
        print(f'Gate 4 PASSED. {prog_count} AUREXIS_PROGRAM_V1 file(s) saved to {output_dir}/programs/')
        print('Review gate4_evaluation.json and serialized programs for project sign-off.')
    else:
        blocking = gate4_result.get('summary', {}).get('blocking_reasons', [])
        print(f'Gate 4 in progress. Blocking: {", ".join(blocking) if blocking else "see gate4_evaluation.json"}')

    return 0 if gate4_complete else 1


if __name__ == '__main__':
    sys.exit(main())
