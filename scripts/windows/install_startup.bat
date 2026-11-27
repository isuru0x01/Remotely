@echo off
setlocal

:: Resolve project root dynamically (two levels up from scripts\windows)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo ========================================================
echo  Remotely - Windows Startup Task Installer
echo ========================================================
echo [*] Project Root: %PROJECT_ROOT%
echo [*] Registering Remotely background listener with Task Scheduler...

schtasks /create /tn "RemotelyListener" ^
    /tr "pythonw.exe \"%PROJECT_ROOT%\src\remotely.py\" -l" ^
    /sc onlogon ^
    /d "%PROJECT_ROOT%" ^
    /rl highest /f

echo.
if %ERRORLEVEL% equ 0 (
    echo [OK] Successfully registered! Remotely will start silently on user logon.
) else (
    echo [!] Failed to register. Please right-click and run this script as Administrator.
)
echo ========================================================
pause
