@echo off
setlocal
cd /d "%~dp0"
python validate_v99_actual_data.py
if errorlevel 1 (echo V9.9 validation GAGAL.& pause & exit /b 1)
echo.
echo V9.9 validation PASS.
pause
