@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo Checking / Upgrading PyInstaller...
echo ========================================================
python -m pip install --upgrade pyinstaller

echo.
echo ========================================================
echo Compiling all Python scripts in src\ ...
echo ========================================================

set COUNT=0
for %%F in (src\*.py) do (
    set "FILENAME=%%~nxF"
    :: Ignore private files and __init__.py
    if not "!FILENAME:~0,1!"=="_" (
        echo.
        if /I "%%~nF"=="connector" (
            set "CONSOLE_FLAG=--noconsole"
        ) else (
            set "CONSOLE_FLAG=--console"
        )
        echo [+] Compiling %%~nF.py -^> dist\%%~nF.exe (!CONSOLE_FLAG!)
        pyinstaller --onefile !CONSOLE_FLAG! --name "%%~nF" "%%F"
        set /a COUNT+=1
    )
)

if exist config.example.json (
    copy /Y config.example.json dist\config.example.json >nul
    echo [+] Copied config.example.json to dist\
)

echo.
echo ========================================================
if %COUNT% equ 0 (
    echo [!] No eligible Python files found in src\
) else (
    echo [OK] Build complete! %COUNT% executable(s) generated in dist\
)
echo ========================================================
pause
