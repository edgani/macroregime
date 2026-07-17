@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ tidak ditemukan di PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Membuat virtual environment...
  python -m venv .venv
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"

echo Memasang atau memperbarui dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 pause & exit /b 1
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 pause & exit /b 1

echo Membuka War Room US Alpha Foundry...
"%PYTHON%" -m streamlit run app.py
if errorlevel 1 pause & exit /b 1
