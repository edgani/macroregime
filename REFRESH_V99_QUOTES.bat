@echo off
setlocal
cd /d "%~dp0"
python execution_quote_collector_v99.py
if errorlevel 1 (echo Quote refresh gagal. Lihat output di atas.& pause & exit /b 1)
echo Quote refresh selesai. Restart app atau tunggu polling berikutnya.
pause
