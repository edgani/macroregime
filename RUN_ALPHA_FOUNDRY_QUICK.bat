@echo off
setlocal
cd /d "%~dp0\alpha_foundry"
powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap.ps1 -Mode quick
pause
