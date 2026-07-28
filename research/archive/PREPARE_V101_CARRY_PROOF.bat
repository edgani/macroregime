@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if "%~1"=="" (
  echo Drag a completed point-in-time carry CSV onto this BAT file.
  echo Template: V101_CARRY_HISTORY_TEMPLATE.csv
  pause
  exit /b 1
)
python carry_proof_v101.py "%~1" --out runtime\v101_carry\candidate_returns.csv
if errorlevel 1 pause
