@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe official_source_radar.py
) else (
  py -3 official_source_radar.py
)
pause
