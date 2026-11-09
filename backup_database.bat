@echo off
title LifeOS Database Backup Utility
cd /d "%~dp0"

echo ======================================================================
echo                     LifeOS Database Backup Utility
echo ======================================================================

REM Ensure backups folder exists
if not exist "backups" mkdir "backups"

REM Find mysqldump executable
set MYSQLDUMP=""
if exist "C:\xampp\mysql\bin\mysqldump.exe" (
    set MYSQLDUMP="C:\xampp\mysql\bin\mysqldump.exe"
) else (
    where mysqldump >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set MYSQLDUMP=mysqldump
    )
)

if %MYSQLDUMP%=="" (
    echo [ERROR] mysqldump executable not found in PATH or C:\xampp\mysql\bin\
    echo Please ensure MySQL / XAMPP is installed.
    pause
    exit /b 1
)

REM Generate date and time stamp (YYYYMMDD_HHMMSS) via PowerShell for reliable formatting
for /f "usebackq tokens=*" %%I in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set TIMESTAMP=%%I

if "%TIMESTAMP%"=="" set TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_FILE=backups\lifeos_db_backup_%TIMESTAMP%.sql

echo [INFO] Starting database backup for 'lifeos_db'...
echo [INFO] Target file: %BACKUP_FILE%

%MYSQLDUMP% --user=root --host=127.0.0.1 --port=3306 --databases lifeos_db --routines --triggers --result-file="%BACKUP_FILE%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo [SUCCESS] Backup completed successfully!
    echo Location: %BACKUP_FILE%
    for %%F in ("%BACKUP_FILE%") do echo File Size: %%~zF bytes
    echo ======================================================================
) else (
    echo.
    echo [ERROR] Backup failed with exit code %ERRORLEVEL%.
    echo Please verify that MySQL is running on port 3306.
)
