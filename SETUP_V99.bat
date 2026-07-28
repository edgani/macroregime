@echo off
setlocal
cd /d "%~dp0"
python --version || (echo Python tidak ditemukan. Install Python 3.11+ lalu ulangi.& pause & exit /b 1)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (echo Setup gagal. Lihat error di atas.& pause & exit /b 1)
echo.
echo V9.9 setup selesai.
pause
