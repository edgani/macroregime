@echo off
cd /d %~dp0
set PYTHONPATH=.
python run_eros.py
pause
