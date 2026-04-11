#!/usr/bin/env python3
"""
Aurexis Core — Gate 3 Re-evaluator
Re-runs Gate 3 against an existing batch_report.json without re-processing files.

Usage:
    python rerun_gate3.py gate3_run_2/batch_report.json

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / 'aurexis_lang' / 'src'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python rerun_gate3.py <path_to_batch_report.json>')
        return 1

    report_path = Path(sys.argv[1]).expanduser().resolve()
    if not report_path.exists():
        print(f'ERROR: Report file not found: {report_path}')
        return 1

    try:
        from aurexis_lang.gate3_runner import run_gate3_evaluation, print_gate3_summary
    except ImportError as e:
        print(f'ERROR: Could not import gate3_runner: {e}')
        return 1

    print(f'Loading batch report: {report_path}')
    batch_report = json.loads(report_path.read_text(encoding='utf-8'))

    batch_name = sys.argv[2] if len(sys.argv) > 2 else report_path.parent.name
    print(f'Batch name: {batch_name}')
    print(f'Files in report: {batch_report.get("files_processed", "?")}')
    print(f'Frames in report: {batch_report.get("total_frames", "?")}')
    print()

    print('Running Gate 3 evaluation...')
    try:
        gate3_result = run_gate3_evaluation(batch_report, batch_name=batch_name)
    except Exception as e:
        print(f'Gate 3 evaluation error: {e}')
        import traceback
        traceback.print_exc()
        return 1

    # Save alongside the batch report
    output_path = report_path.parent / 'gate3_evaluation.json'
    output_path.write_text(
        json.dumps(gate3_result, indent=2, default=str),
        encoding='utf-8',
    )

    print_gate3_summary(gate3_result)
    print(f'Gate 3 report saved: {output_path}')

    gate3_complete = gate3_result.get('summary', {}).get('gate3_complete', False)
    if gate3_complete:
        print('Gate 3 audit PASSED.')
    else:
        blocking = gate3_result.get('summary', {}).get('blocking_reasons', [])
        print(f'Gate 3 in progress. Blocking: {", ".join(blocking) if blocking else "see gate3_evaluation.json"}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
