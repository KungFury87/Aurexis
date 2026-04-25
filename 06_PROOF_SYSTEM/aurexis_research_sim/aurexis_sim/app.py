"""Deprecated in-package Streamlit entry. Canonical entry is root app.py."""
from __future__ import annotations
import sys
_MSG = ("\nAurexis Research Sim v0.6:\n"
        "  aurexis_sim/app.py is not the Streamlit entry.\n"
        "  Use 'python -m streamlit run app.py' from the project root.\n")
def main(): sys.stderr.write(_MSG); return 2
if __name__ == "__main__":
    raise SystemExit(main())
