@echo off
title LifeOS Tailscale Funnel (Permanent Public HTTPS)
cd /d "%~dp0"

echo ======================================================================
echo                 LifeOS Permanent Public Access
echo                     Powered by Tailscale Funnel
echo ======================================================================
echo.
echo  This tool exposes your local LifeOS server to the public internet
echo  via a stable, permanent HTTPS domain (*.ts.net) with zero cost.
echo.
echo  - Cost: $0 (Free forever)
echo  - Custom domain purchase: None needed (free *.ts.net MagicDNS)
echo  - Random URL rotation: None (stable, permanent hostname)
echo  - Port forwarding: None needed
echo  - MySQL port 3306 exposure: Zero (strictly isolated)
echo.

REM Check if Tailscale CLI is available
where tailscale >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "C:\Program Files\Tailscale\tailscale.exe" (
        set "PATH=%PATH%;C:\Program Files\Tailscale"
    ) else (
        echo [ERROR] Tailscale executable not found in PATH or 'C:\Program Files\Tailscale\'.
        echo Please ensure Tailscale Windows application is installed and running.
        echo Download: https://tailscale.com/download/windows
        pause
        exit /b 1
    )
)

REM Verify local LifeOS server is running on port 8000
netstat -ano | findstr /R /C:":8000 " >nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] LifeOS server does not appear to be running on port 8000.
    echo Please make sure you have started LifeOS using 'start_lifeos.bat' first!
    echo.
)

echo [INFO] Checking Tailscale status...
tailscale status

echo.
echo [INFO] Enabling Tailscale Funnel on port 8000 (Background Persistent Mode)...
echo [INFO] Routing public HTTPS traffic to http://127.0.0.1:8000...
echo.

tailscale funnel --bg 8000

echo.
echo ======================================================================
echo [INFO] Tailscale Funnel Configuration Status:
tailscale funnel status
echo ======================================================================
echo.
echo Your permanent public HTTPS URL is shown above (*.ts.net).
echo This runs as a persistent background service and survives reboots!
echo.
pause
