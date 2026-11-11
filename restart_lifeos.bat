@echo off
title Restart LifeOS Server
cd /d "%~dp0"

echo ======================================================================
echo                     Restarting LifeOS Server
echo ======================================================================

call stop_lifeos.bat
ping -n 3 127.0.0.1 >nul
call start_lifeos.bat
