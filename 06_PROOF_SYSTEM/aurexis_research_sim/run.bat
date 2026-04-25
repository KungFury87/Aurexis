@echo off
REM Aurexis Research Sim v0.1 — Windows launcher.
REM Entry lives at the project root (app.py) so Streamlit's script-dir
REM sys.path behavior resolves the aurexis_sim package cleanly.
pushd "%~dp0"
python -m streamlit run app.py
popd
