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
echo Target 1: %DIST_DIR%\connector.exe (Silent Boot Beacon)
echo Target 2: %DIST_DIR%\remotely.exe -l (Incoming Task Listener)
echo.

set "INSTALL_STARTUP=Y"
set /p "INSTALL_STARTUP=Add connector.exe and remotely.exe -l to Windows Startup? [Y/n]: "
if "%INSTALL_STARTUP%"=="" set "INSTALL_STARTUP=Y"

if /i "%INSTALL_STARTUP%"=="Y" (
    echo.
    echo [*] Registering shortcuts in shell:startup...

    :: 1. Register connector.exe shortcut
    if exist "%DIST_DIR%\connector.exe" (
        powershell -NoProfile -Command ^
            "$ws = New-Object -ComObject WScript.Shell; " ^
            "$startup = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup'); " ^
            "$s = $ws.CreateShortcut([System.IO.Path]::Combine($startup, 'RemotelyConnector.lnk')); " ^
            "$s.TargetPath = '%DIST_DIR%\connector.exe'; " ^
            "$s.WorkingDirectory = '%PROJECT_ROOT%'; " ^
            "$s.Description = 'Remotely Silent Boot Beacon'; " ^
            "$s.Save()"
        echo [OK] Created startup shortcut: RemotelyConnector.lnk
    ) else (
        echo [!] Warning: %DIST_DIR%\connector.exe was not found.
    )

    :: 2. Register remotely.exe -l shortcut
    if exist "%DIST_DIR%\remotely.exe" (
        powershell -NoProfile -Command ^
            "$ws = New-Object -ComObject WScript.Shell; " ^
            "$startup = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup'); " ^
            "$s = $ws.CreateShortcut([System.IO.Path]::Combine($startup, 'RemotelyListener.lnk')); " ^
            "$s.TargetPath = '%DIST_DIR%\remotely.exe'; " ^
            "$s.Arguments = '-l'; " ^
            "$s.WorkingDirectory = '%PROJECT_ROOT%'; " ^
            "$s.Description = 'Remotely AI Task Listener'; " ^
            "$s.Save()"
        echo [OK] Created startup shortcut: RemotelyListener.lnk (-l)
    ) else (
        echo [!] Warning: %DIST_DIR%\remotely.exe was not found.
    )

    echo.
    echo [✓] Both executables are now registered to start automatically on Windows boot.

    echo.
    set "START_NOW=Y"
    set /p "START_NOW=Start connector.exe and remotely.exe -l right now? [Y/n]: "
    if "%START_NOW%"=="" set "START_NOW=Y"

    if /i "!START_NOW!"=="Y" (
        echo.
        echo [*] Launching executables...

        if exist "%DIST_DIR%\connector.exe" (
            start "" /d "%PROJECT_ROOT%" "%DIST_DIR%\connector.exe"
            echo [OK] Started connector.exe (silent background boot beacon)
        )

        if exist "%DIST_DIR%\remotely.exe" (
            start "Remotely Listener" /d "%PROJECT_ROOT%" "%DIST_DIR%\remotely.exe" -l
            echo [OK] Started remotely.exe -l (task listener running in separate window)
        )

        echo.
        echo [✓] Both processes are now active and running!
    ) else (
        echo [i] Skipped immediate launch.
    )
) else (
    echo [i] Skipped startup registration.
)

echo.
echo ========================================================
pause
