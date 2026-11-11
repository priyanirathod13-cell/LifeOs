@echo off
title Stop LifeOS Server
cd /d "%~dp0"

echo ======================================================================
echo                      Stopping LifeOS Server
echo ======================================================================

REM Find process listening on port 8000 and terminate safely
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":8000 .*LISTENING"') do (
    echo [INFO] Stopping LifeOS server process (PID %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

echo [OK] LifeOS server on port 8000 stopped.
timeout /t 2 >nul
