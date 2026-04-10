@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist ".venv\Scripts\python.exe" (
    echo [.venv not found]
    echo Create the virtual environment and install dependencies first.
    echo Example:
    echo   py -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e .[dev]
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m youtube_translator_desktop

if errorlevel 1 (
    echo.
    echo The app exited with an error.
    pause
)

endlocal
