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
        echo [+] Compiling %%~nF.py -^> dist\%%~nF.exe
        :: --onefile: packages everything into a single standalone portable .exe
        :: --noconsole: suppresses console window (runs in background)
        pyinstaller --onefile --noconsole --name "%%~nF" "%%F"
        set /a COUNT+=1
    )
)

echo.
echo ========================================================
if %COUNT% equ 0 (
    echo [!] No eligible Python files found in src\
) else (
    echo [✓] Build complete! %COUNT% executable(s) generated in dist\
)
echo ========================================================
pause
