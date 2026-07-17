@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap.ps1 -Mode quick
if errorlevel 1 pause & exit /b 1
pause
