@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python shadow_runner_v100.py
pause
