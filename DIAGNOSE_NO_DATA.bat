@echo off
setlocal
cd /d "%~dp0"
python diagnose_no_data.py
pause
endlocal
