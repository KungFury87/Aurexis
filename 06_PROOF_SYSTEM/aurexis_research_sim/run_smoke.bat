@echo off
REM Headless smoke run — no Streamlit UI, just prints metrics.
pushd "%~dp0"
python -m aurexis_sim.smoke
popd
