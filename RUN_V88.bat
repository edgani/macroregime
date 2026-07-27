@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Run SETUP_V88.bat after installing Python.
  exit /b 1
)
py -m streamlit run app.py
