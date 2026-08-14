@echo off
setlocal
REM ============================================================
REM SmartITMonitor Agent - Windows launcher
REM Run this on the Windows machine you want to monitor.
REM Requirements: Python 3.9+ installed (python.org, tick "Add to PATH")
REM ============================================================

REM Point at the monitoring server (backend API). Change if needed.
set "SMARTIT_API_URL=http://10.234.69.225:8000"

cd /d "%~dp0"

echo SmartITMonitor Agent for Windows
echo API URL: %SMARTIT_API_URL%
echo.

if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Python not found. Install Python from https://www.python.org/downloads/
        echo and tick "Add Python to PATH" during install.
        pause
        exit /b 1
    )
)

echo Installing dependencies...
"venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting agent... Press Ctrl+C to stop.
"venv\Scripts\python.exe" agent.py
endlocal
