@echo off
setlocal
cd /d "%~dp0"
python validate_v92_route.py
if errorlevel 1 exit /b 1
python provider_onboarding_v92.py --env V92_PROVIDER_ONBOARDING.env --out V92_CURRENT_5_OF_5_AUDIT.json
endlocal
