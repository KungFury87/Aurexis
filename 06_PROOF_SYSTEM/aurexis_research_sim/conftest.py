"""Root conftest.

Ensures the project root is on sys.path regardless of pytest version or
invocation style. Redundant with pyproject.toml's [tool.pytest.ini_options]
pythonpath entry, but kept as belt-and-braces so tests work from any CWD.
"""
from __future__ import annotations

import os
import sys


_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
