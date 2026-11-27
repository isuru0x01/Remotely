@echo off
setlocal

:: Set working directory to project root (one folder up from scripts\)
cd /d "%~dp0\.."

echo ========================================================
echo Building Remotely Executables...
echo ========================================================

python scripts\build.py %*

echo.
pause
