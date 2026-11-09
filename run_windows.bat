@echo off
title Backend API Smart Office YOLOv11
echo ===================================================
echo [1/2] Memeriksa dan menginstal library Python...
echo ===================================================
pip install -r requirements.txt
echo.
echo ===================================================
echo [2/2] Menjalankan Server Smart Office YOLOv11...
echo Backend API: http://127.0.0.1:5000
echo Jalankan run_frontend.bat pada terminal lain.
echo Dashboard dan login: http://127.0.0.1:3000/login
echo ===================================================
python app.py
pause
