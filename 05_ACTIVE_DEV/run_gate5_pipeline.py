#!/usr/bin/env python3
"""
Aurexis Core — Gate 5 Expansion Without Rewrite Pipeline
Standalone script. Run after Gate 4 is confirmed complete.

Proves that a new capability (cross-device evidence validation) can be
added to Aurexis Core WITHOUT modifying any frozen Core Law module.
Verification is cryptographic: SHA-256 hashes of all 6 Core Law modules
are computed before and after the extension runs.

Usage:
    python run_gate5_pipeline.py <batch_report.json>

    # With options:
    python run_gate5_pipeline.py gate3_run_2/batch_report.json
    python run_gate5_pipeline.py gate3_run_2/batch_report.json --output gate5_run_1

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
_AUREXIS_PKG = _SRC / 'aurexis_lang'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Run Gate 5 Expansion Without Rewrite evaluation.',
    )
    parser.add_argument(
        'batch_report',
        type=str,
        help='Path to Gate 3 batch_report.json (needs file_results with multiple devices)',
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='gate5_run_1',
        help='Output directory for Gate 5 results (default: gate5_run_1)',
    )

    args = parser.parse_args()

    batch_path = Path(args.batch_report).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not batch_path.exists():
        print(f'ERROR: Batch report not found: {batch_path}')
        return 1

    try:
        from aurexis_lang.gate5_runner import run_gate5_evaluation, print_gate5_summary
    except ImportError as e:
        print(f'ERROR: Could not import Gate 5 runner: {e}')
        import traceback
        traceback.print_exc()
        return 1

    print(f'Loading batch report: {batch_path}')
    batch_report = json.loads(batch_path.read_text(encoding='utf-8'))
    print(f'Files in report: {batch_report.get("files_processed", "?")}')
    print(f'Devices seen: {list(batch_report.get("device_profiles", {}).keys())}')

    print(f'\n{"=" * 60}')
    print(f'AUREXIS GATE 5 — EXPANSION WITHOUT REWRITE')
    print(f'{"=" * 60}')
    print(f'Core Law source dir: {_AUREXIS_PKG}')
    print(f'Output dir:          {output_dir}')
    print(f'{"=" * 60}\n')

    try:
        gate5_result = run_gate5_evaluation(
            batch_report=batch_report,
            src_dir=_AUREXIS_PKG,
        )
    except Exception as e:
        print(f'Gate 5 evaluation error: {e}')
        import traceback
        traceback.print_exc()
        return 1

    # Save full result
    result_path = output_dir / 'gate5_evaluation.json'
    result_path.write_text(
        json.dumps(gate5_result, indent=2, default=str),
        encoding='utf-8',
    )

    print_gate5_summary(gate5_result)
    print(f'Gate 5 report saved: {result_path}')

    gate5_complete = gate5_result.get('summary', {}).get('gate5_complete', False)
    if gate5_complete:
        print('Gate 5 PASSED. Aurexis Core expands without rewriting the law.')
        print('All 5 gates are now COMPLETE.')
    else:
        blocking = gate5_result.get('summary', {}).get('blocking_reasons', [])
        print(f'Gate 5 in progress. Blocking: {", ".join(blocking) if blocking else "see gate5_evaluation.json"}')

    return 0 if gate5_complete else 1


if __name__ == '__main__':
    sys.exit(main())
