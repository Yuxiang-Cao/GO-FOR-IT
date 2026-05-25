@echo off
echo Starting Job Monitor & CV Tailor...
python run.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Make sure Python 3 is installed and added to PATH.
    pause
)
