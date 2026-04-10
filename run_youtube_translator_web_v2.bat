@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Could not find .venv\Scripts\python.exe
  echo Please create the virtual environment and install dependencies first.
  pause
  exit /b 1
)

echo.
echo Starting YouTube Markdown web server...
echo Local browser: http://127.0.0.1:8000
echo Phone on same network: http://192.168.164.53:8000
echo Keep this window open while using the web app.
echo.

".venv\Scripts\python.exe" -c "import webbrowser; webbrowser.open('http://127.0.0.1:8000')" >nul 2>nul
".venv\Scripts\python.exe" -m youtube_translator_desktop.web_main

if errorlevel 1 (
  echo.
  echo The web server exited with an error.
  pause
)
