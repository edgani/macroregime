@echo off
setlocal
cd /d "%~dp0"
python public_context_collector_v99.py
if errorlevel 1 (echo Public-data refresh gagal. Lihat output di atas.& pause & exit /b 1)
echo Public-data refresh selesai. Restart app atau tunggu polling berikutnya.
pause
