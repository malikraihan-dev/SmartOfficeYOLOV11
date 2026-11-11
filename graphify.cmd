@echo off
setlocal
if not exist "%~dp0.venv-graphify\Scripts\python.exe" (
    echo Graphify belum terpasang. Ikuti docs\GRAPHIFY.md.
    exit /b 1
)
"%~dp0.venv-graphify\Scripts\python.exe" -m graphify %*
exit /b %errorlevel%
