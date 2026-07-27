@echo off
setlocal
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% autonomous_public_data_plane_v95.py --output runtime/v95_public_acquisition --max-cftc-rows 5000
pause
