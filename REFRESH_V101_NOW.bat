@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python warroom_data_worker_v101.py --once --full
if errorlevel 1 pause
