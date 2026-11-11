@echo off
title Stop LifeOS Server
cd /d "%~dp0"

echo ======================================================================
echo                      Stopping LifeOS Server
echo ======================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_lifeos.ps1"

echo [OK] LifeOS server and supervisor stopped.
ping -n 3 127.0.0.1 >nul
