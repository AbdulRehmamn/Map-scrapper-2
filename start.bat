@echo off
setlocal
cd /d "%~dp0"
title Maps Contact Scraper
py -3 --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=py -3"
  goto python_found
)
python --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=python"
  goto python_found
)
echo Python is missing. Install Python 3.10 or later from https://www.python.org/downloads/
echo Enable "Add Python to PATH", then run start.bat again.
pause
exit /b 1
:python_found
%PYTHON% -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if errorlevel 1 goto version_error
if exist ".venv\Scripts\python.exe" goto install
%PYTHON% -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
exit /b 0
:version_error
echo Python 3.10 or later is required.
pause
exit /b 1
:failed
echo Setup or launch failed. Check the error above and your internet connection.
pause
exit /b 1
