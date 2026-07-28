@echo off
setlocal
cd /d "%~dp0"
python -c "import streamlit,pyarrow,pandas" >nul 2>&1
if errorlevel 1 (echo Dependency belum lengkap. Jalankan SETUP_V99.bat dulu.& pause & exit /b 1)
python -m streamlit run app.py
