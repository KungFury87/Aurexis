"""Render + verify the V2 B1 benchmark artifact set (standalone runner).

Renders all five mandatory B1 artifacts to
``V2_BENCHMARK_SET/assets/`` and rewrites
``V2_BENCHMARK_SET/V2_BENCHMARK_SET_MANIFEST.json`` with fresh SHA-256
values, then re-verifies bytes and manifest. Exits with code 0 on success,
non-zero on any mismatch.

Run from the V2 working folder (the folder containing V2_BENCHMARK_SET/):

    python 05_ACTIVE_DEV/aurexis_lang/run_v2_benchmark_verify.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    here = Path(__file__).resolve().parent
    src = here / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    _ensure_src_on_path()
    from aurexis_lang.v2_benchmark.render import (  # noqa: E402
        build_manifest,
        render_to_disk,
        verify_on_disk,
    )

    # Repo root = the folder that owns V2_BENCHMARK_SET/ (two levels up from
    # this runner: aurexis_lang -> 05_ACTIVE_DEV -> <repo root>).
    repo_root = Path(__file__).resolve().parents[2]

    manifest = build_manifest()
    render_to_disk(repo_root, manifest)
    print(
        f"rendered {len(manifest['artifacts'])} B1 artifacts under "
        f"{repo_root}/V2_BENCHMARK_SET/"
    )

    errors = verify_on_disk(repo_root)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("OK: V2 benchmark set verified (manifest, checksums, bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
