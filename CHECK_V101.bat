@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python validate_v101_carry.py
pause
