@echo off
title Stop LifeOS Server
cd /d "%~dp0"

echo ======================================================================
echo                      Stopping LifeOS Server
echo ======================================================================

REM 1. Stop Supervisor via PID file if present
if exist "supervisor.pid" (
    set /p SPID=<"supervisor.pid"
    if defined SPID (
        echo [INFO] Stopping LifeOS Supervisor (PID %SPID%)...
        taskkill /PID %SPID% /F >nul 2>&1
        del /f /q "supervisor.pid" >nul 2>&1
    )
)

REM 2. Stop any remaining python process running supervisor.py or serve.py
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*supervisor.py*' -or $_.CommandLine -like '*serve.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM 3. Terminate any process listening on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":8000 .*LISTENING"') do (
    echo [INFO] Stopping server process on port 8000 (PID %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

echo [OK] LifeOS server and supervisor stopped.
ping -n 3 127.0.0.1 >nul
