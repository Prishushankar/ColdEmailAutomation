@echo off
echo Cold Email Automation Server Launcher
echo =====================================
echo 1) Install dependencies
echo 2) Run with Flask development server
echo 3) Run with Gunicorn (after installing)
echo 4) Start backend server
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    pip install -r requirements.txt
    echo Dependencies installed successfully.
    pause
) else if "%choice%"=="2" (
    python app.py
) else if "%choice%"=="3" (
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
) else if "%choice%"=="4" (
    echo Starting Cold Email Automation Backend...
    pip install -r requirements.txt
    echo.
    echo Backend server running at http://localhost:5000
    echo Press Ctrl+C to stop the server
    echo.
    python app.py
) else (
    echo Invalid choice.
    pause
)
