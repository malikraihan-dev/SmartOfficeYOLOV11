@echo off
setlocal
title Service Backend API Smart Office YOLOv11
cd /d "%~dp0"
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
echo ===================================================
echo [1/2] Memeriksa dan menginstal library Python...
echo ===================================================
"%PYTHON_EXE%" -m pip install -r requirements.txt
echo.
echo ===================================================
echo [2/2] Menjalankan Service Backend Smart Office...
echo Backend API: http://127.0.0.1:5000
echo Health JSON: http://127.0.0.1:5000/api/health
echo ===================================================
"%PYTHON_EXE%" app.py
pause
