@echo off
rem Launcher for Windows - double-click from Explorer or run from cmd.
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo ERP launcher error: virtualenv Python not found at %CD%\venv
    echo Follow the setup steps in README.md first.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" open_erp.py
if errorlevel 1 (
    echo.
    echo ERP login exited with an error.
    pause
)
endlocal
