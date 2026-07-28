@echo off
cd /d %~dp0
python validate_v96_release.py
if errorlevel 1 pause
