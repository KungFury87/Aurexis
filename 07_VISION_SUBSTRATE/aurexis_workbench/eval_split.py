"""Hash-deterministic train/test split.

Modeled after the assign_split utility in Donald Pilger's
`bigbugnowadaze/scry`. Re-ingesting the same image always lands in the
same split bucket, so evaluation results are reproducible across
re-ingestion runs.

Usage:
    from aurexis_workbench.eval_split import assign_split
    bucket = assign_split(image_alias, test_fraction=0.1)
    if bucket == "test":
        ...
"""
from __future__ import annotations

import hashlib


def assign_split(alias: str, test_fraction: float = 0.10,
                   seed: str = "phoxelis-v1") -> str:
    """Return 'train' or 'test' deterministically based on the alias.

    Same alias + same seed + same test_fraction always produces the
    same answer. Changing the seed reshuffles the entire split.
    """
    h = hashlib.md5(f"{seed}:{alias}".encode("utf-8")).hexdigest()
    bucket = int(h[:8], 16) / float(0xFFFFFFFF)
    return "test" if bucket < test_fraction else "train"
