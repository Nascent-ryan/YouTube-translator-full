@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv\Scripts\python.exe 를 찾을 수 없습니다.
  echo 먼저 가상환경과 의존성을 설치해 주세요.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m youtube_translator_desktop.web_main

if errorlevel 1 (
  echo.
  echo 웹 서버가 오류와 함께 종료되었습니다.
  pause
)
