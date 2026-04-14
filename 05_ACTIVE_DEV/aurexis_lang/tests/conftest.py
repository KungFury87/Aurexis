"""
Aurexis Core V1 Substrate Candidate — shared pytest fixtures.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.

Usage:
    cd 05_ACTIVE_DEV/aurexis_lang
    PYTHONPATH=src pytest tests/ -q

All test modules in this directory import from aurexis_lang.*
which must be on PYTHONPATH (the src/ directory).
"""
import sys
import os

# Ensure the src directory is on the path so aurexis_lang is importable
_src = os.path.join(os.path.dirname(__file__), "..", "src")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))
