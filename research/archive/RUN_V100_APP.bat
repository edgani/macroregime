@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set WARROOM_REFRESH_ON_LOAD=0
python -m streamlit run app.py
