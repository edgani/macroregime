@echo off
setlocal
cd /d %~dp0
if "%~3"=="" (
  echo Usage: NORMALIZE_FILLS_V93.bat input.csv mapping.json output.csv
  exit /b 2
)
python fill_normalizer_v93.py --input "%~1" --mapping "%~2" --output "%~3"
endlocal
