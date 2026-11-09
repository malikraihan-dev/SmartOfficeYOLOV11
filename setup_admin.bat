@echo off
setlocal
title Smart Office - Siapkan Admin
cd /d "%~dp0"
python manage_admin.py
pause
