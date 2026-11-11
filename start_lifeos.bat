@echo off
title LifeOS Server (Production Supervisor & WSGI)
cd /d "%~dp0"

echo ======================================================================
echo                 Starting LifeOS Production Service
echo ======================================================================

REM Check if Python venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment (.venv) not found.
    echo Please ensure the Python virtual environment is installed.
    pause
    exit /b 1
)

REM Check if MySQL is running (TCP 3306)
netstat -ano | findstr /R /C:":3306 " >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] MySQL is not running on port 3306. Starting XAMPP MySQL...
    if exist "C:\xampp\mysql\bin\mysqld.exe" (
        start "MySQL Server" /D "C:\xampp\mysql" "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --console
        ping -n 4 127.0.0.1 >nul
    ) else (
        echo [WARNING] C:\xampp\mysql\bin\mysqld.exe not found.
        echo Please ensure your MySQL server is running before continuing.
    )
) else (
    echo [OK] MySQL is active on port 3306.
)

REM Run migrations safely
echo [INFO] Checking database migrations...
.\.venv\Scripts\python.exe manage.py migrate --noinput

REM Launch Supervisor (which supervises Waitress, health checks, and Tailscale Funnel)
echo [INFO] Launching LifeOS Supervisor & Health Monitor...
.\.venv\Scripts\python.exe supervisor.py

pause
