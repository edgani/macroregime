@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python order_review_export_v101.py
pause
