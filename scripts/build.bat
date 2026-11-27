@echo off
setlocal enabledelayedexpansion

:: Set working directory to project root (one folder up from scripts\)
cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "DIST_DIR=%PROJECT_ROOT%\dist"

echo ========================================================
echo Building Remotely Executables...
echo ========================================================

python scripts\build.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Build failed with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

:: Copy local config.json into dist\ if present
if exist "%PROJECT_ROOT%\config.json" (
    copy /Y "%PROJECT_ROOT%\config.json" "%DIST_DIR%\config.json" >nul
    echo [+] Copied config.json to dist\
)

echo.
echo ========================================================
echo Windows Startup Configuration (shell:startup)
echo ========================================================
echo Target: %DIST_DIR%\remotely.exe -l (Silent Background Task Listener)
echo Mode:   100%% Windowless (No command prompt popup on boot)
echo.

set "INSTALL_STARTUP=Y"
set /p "INSTALL_STARTUP=Add remotely.exe -l to Windows Startup? [Y/n]: "
if "%INSTALL_STARTUP%"=="" set "INSTALL_STARTUP=Y"

if /i "%INSTALL_STARTUP%"=="Y" (
    echo.
    echo [*] Configuring silent startup launcher in shell:startup...

    set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    set "VBS_FILE=!STARTUP_FOLDER!\RemotelyListener.vbs"

    :: Remove any legacy shortcuts from previous versions
    if exist "!STARTUP_FOLDER!\RemotelyConnector.lnk" del /f /q "!STARTUP_FOLDER!\RemotelyConnector.lnk" 2>nul
    if exist "!STARTUP_FOLDER!\RemotelyListener.lnk" del /f /q "!STARTUP_FOLDER!\RemotelyListener.lnk" 2>nul

    :: Generate silent VBScript launcher directly in shell:startup
    :: The '0' window style executes remotely.exe hidden with NO console popup window
    echo Set WshShell = CreateObject("WScript.Shell") > "!VBS_FILE!"
    echo WshShell.CurrentDirectory = "%PROJECT_ROOT%" >> "!VBS_FILE!"
    echo WshShell.Run """%DIST_DIR%\remotely.exe"" -l", 0, False >> "!VBS_FILE!"

    if exist "!VBS_FILE!" (
        echo [OK] Created silent launcher: shell:startup\RemotelyListener.vbs
        echo [✓] remotely.exe -l will run completely in the background on startup (no popups).
    ) else (
        echo [!] Error: Failed to write to startup folder.
    )

    echo.
    set "START_NOW=Y"
    set /p "START_NOW=Start remotely.exe -l in the background right now? [Y/n]: "
    if "%START_NOW%"=="" set "START_NOW=Y"

    if /i "!START_NOW!"=="Y" (
        echo.
        echo [*] Launching remotely.exe -l silently in the background...
        wscript.exe "!VBS_FILE!"
        echo [✓] Remotely listener is now active in the background.
    ) else (
        echo [i] Skipped immediate launch.
    )
) else (
    echo [i] Skipped startup registration.
)

echo.
echo ========================================================
pause
