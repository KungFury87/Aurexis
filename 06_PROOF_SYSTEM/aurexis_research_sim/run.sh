#!/usr/bin/env bash
# Aurexis Research Sim v0.1 — bash launcher.
# Entry lives at the project root (app.py) so Streamlit's script-dir
# sys.path behavior resolves the aurexis_sim package cleanly.
set -e
cd "$(dirname "$0")"
python -m streamlit run app.py
