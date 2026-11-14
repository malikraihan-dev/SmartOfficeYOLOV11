@echo off
setlocal
title Smart Office - Frontend Next.js
cd /d "%~dp0apps\web"
where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js dan npm belum tersedia. Pasang Node.js lalu coba lagi.
    pause
    exit /b 1
)
if not exist node_modules (
    echo Memasang dependensi frontend...
    call npm ci
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
echo Frontend: http://127.0.0.1:3000
echo Jalankan python app.py pada terminal lain untuk backend.
echo Menggunakan compiler WebAssembly untuk kompatibilitas Windows.
call npm run dev:web:compat
pause
