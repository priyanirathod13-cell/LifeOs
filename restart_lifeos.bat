@echo off
title Restart LifeOS Server
cd /d "%~dp0"

echo ======================================================================
echo                     Restarting LifeOS Server
echo ======================================================================

call stop_lifeos.bat
timeout /t 2 /nobreak >nul
call start_lifeos.bat
