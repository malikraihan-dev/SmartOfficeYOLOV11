@echo off
setlocal
title Smart Office - Siapkan Admin
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage_admin.py
) else (
    python manage_admin.py
)
pause
