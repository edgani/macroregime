@echo off
setlocal
cd /d %~dp0
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% autonomous_public_data_plane_v96.py --output runtime/v96_public_acquisition --max-cftc-rows 5000
if errorlevel 1 pause
