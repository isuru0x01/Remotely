@echo off
setlocal

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
echo Target: %DIST_DIR%\remotely.exe -l
echo Mode:   100%% Windowless Background (Zero popups on boot)
echo.

set "INSTALL_STARTUP=Y"
set /p "INSTALL_STARTUP=Add remotely.exe -l to Windows Startup? [Y/n]: "
if "%INSTALL_STARTUP%"=="" set "INSTALL_STARTUP=Y"
if /i not "%INSTALL_STARTUP%"=="Y" goto skip_startup

echo.
echo [*] Configuring silent startup launcher in shell:startup...

:: Verify the target executable exists
if not exist "%DIST_DIR%\remotely.exe" (
    echo [!] Error: %DIST_DIR%\remotely.exe was not found.
    echo     Please make sure remotely.exe compiled successfully.
    goto skip_startup
)

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_VBS=%STARTUP_FOLDER%\RemotelyListener.vbs"

:: Remove any legacy shortcuts from previous versions
if exist "%STARTUP_FOLDER%\RemotelyConnector.lnk" del /f /q "%STARTUP_FOLDER%\RemotelyConnector.lnk" 2>nul
if exist "%STARTUP_FOLDER%\RemotelyListener.lnk" del /f /q "%STARTUP_FOLDER%\RemotelyListener.lnk" 2>nul
if exist "%TARGET_VBS%" del /f /q "%TARGET_VBS%" 2>nul

:: Generate silent VBScript launcher in shell:startup with exact absolute paths and existence guard
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$vbsPath = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'RemotelyListener.vbs'); " ^
    "$exePath = '%DIST_DIR%\remotely.exe'; " ^
    "$workDir = '%PROJECT_ROOT%'; " ^
    "$content = 'Set FSO = CreateObject(\"Scripting.FileSystemObject\")' + [Environment]::NewLine + " ^
    "           'Set WshShell = CreateObject(\"WScript.Shell\")' + [Environment]::NewLine + " ^
    "           'ExePath = \"' + $exePath + '\"' + [Environment]::NewLine + " ^
    "           'If FSO.FileExists(ExePath) Then' + [Environment]::NewLine + " ^
    "           '    WshShell.CurrentDirectory = \"' + $workDir + '\"' + [Environment]::NewLine + " ^
    "           '    WshShell.Run \"\"\"\" & ExePath & \"\"\" -l\", 0, False' + [Environment]::NewLine + " ^
    "           'End If'; " ^
    "[System.IO.File]::WriteAllText($vbsPath, $content)"

if exist "%TARGET_VBS%" (
    echo [OK] Created silent launcher: shell:startup\RemotelyListener.vbs
    echo [OK] Target: %DIST_DIR%\remotely.exe -l
    echo [OK] Working Directory: %PROJECT_ROOT%
    echo [✓] remotely.exe -l is configured to run silently in the background on boot.
) else (
    echo [!] Error: Failed to write launcher to startup folder.
    goto skip_startup
)

echo.
set "START_NOW=Y"
set /p "START_NOW=Start remotely.exe -l in the background right now? [Y/n]: "
if "%START_NOW%"=="" set "START_NOW=Y"
if /i not "%START_NOW%"=="Y" goto skip_startup

echo.
echo [*] Launching remotely.exe -l silently in the background...
start "" wscript.exe "%TARGET_VBS%"
echo [✓] Remotely listener is now active in the background.

:skip_startup
echo.
echo ========================================================
pause
