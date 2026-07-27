@echo off
setlocal
cd /d %~dp0
python validate_v93_public_bootstrap.py
if errorlevel 1 exit /b 1
python validate_v92_route.py
endlocal
