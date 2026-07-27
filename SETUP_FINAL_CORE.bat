@echo off
setlocal
cd /d "%~dp0"
python setup_v79.py
if errorlevel 1 (
  echo.
  echo SETUP FAILED. Authorization was not changed.
)
pause
