@echo off
title LifeOS Public Cloudflare Tunnel
cd /d "%~dp0"

echo ======================================================================
echo                  LifeOS Free Public Access Tunnel
echo                   Powered by Cloudflare Quick Tunnel
echo ======================================================================
echo.
echo  This tool creates a secure, encrypted public HTTPS URL for your
echo  local LifeOS server.
echo.
echo  - Cost: $0 (Free)
echo  - Domain needed: None (*.trycloudflare.com assigned automatically)
echo  - Router port forwarding needed: None
echo  - MySQL port 3306 exposure: Zero (completely protected)
echo.

REM Check if cloudflared exists
if not exist ".venv\Scripts\cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found in .venv\Scripts\
    pause
    exit /b 1
)

REM Verify local server is reachable
netstat -ano | findstr /R /C:":8000 " >nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] LifeOS server does not appear to be running on port 8000.
    echo Please make sure you have started LifeOS using 'start_lifeos.bat' first!
    echo.
)

:run_tunnel
echo ======================================================================
echo [INFO] Starting Cloudflare Tunnel...
echo [INFO] Look for the URL ending with '.trycloudflare.com' below.
echo [INFO] Share that HTTPS link with your friends to give them access!
echo ======================================================================
echo.

.\.venv\Scripts\cloudflared.exe tunnel --url http://127.0.0.1:8000

echo.
echo [WARNING] Cloudflare Tunnel disconnected or connection was reset.
echo [INFO] Re-establishing tunnel in 5 seconds... (Press Ctrl+C to stop)
timeout /t 5 /nobreak >nul
goto run_tunnel
