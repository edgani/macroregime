@echo off
cd /d %~dp0
python autonomous_research_factory_v96.py init
python autonomous_research_factory_v96.py run-all
if errorlevel 1 pause
