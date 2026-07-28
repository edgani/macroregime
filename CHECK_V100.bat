@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python validate_v100_operational.py
pause
