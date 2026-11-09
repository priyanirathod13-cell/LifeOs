# LifeOS — Database Backup & Disaster Recovery Guide

Your laptop is the server and source of truth for LifeOS. This guide explains how to back up and restore your local MySQL database (`lifeos_db`) to guarantee zero data loss.

---

## 1. Quick Backup (One-Click)

LifeOS includes an automated backup script at `c:\LifeOs\backup_database.bat`.

### To create an instant timestamped backup:
Double-click `backup_database.bat` or run in terminal:
```cmd
c:\LifeOs\backup_database.bat
```

This generates a timestamped `.sql` dump inside `c:\LifeOs\backups\`, e.g.:
```
c:\LifeOs\backups\lifeos_db_backup_20261109_090444.sql
```
- Includes all tables, indexes, records, routines, and triggers.
- Safe to run while the server is live.

---

## 2. Manual Backup via Command Line

If you prefer to run `mysqldump` directly:

### Standard Backup Command:
```cmd
"C:\xampp\mysql\bin\mysqldump.exe" --user=root --host=127.0.0.1 --port=3306 --databases lifeos_db --routines --triggers --result-file="c:\LifeOs\backups\lifeos_db_manual.sql"
```

### Compressed Backup (PowerShell):
```powershell
& "C:\xampp\mysql\bin\mysqldump.exe" -u root -h 127.0.0.1 lifeos_db | Compress-Archive -DestinationPath "c:\LifeOs\backups\lifeos_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

---

## 3. How to Restore Database (Disaster Recovery)

If you ever need to restore your database from a previous backup:

### Step 1: Ensure MySQL is Running
Confirm MySQL is active on port 3306.

### Step 2: (Optional) Recreate Clean Database
If starting fresh or rolling back:
```cmd
"C:\xampp\mysql\bin\mysql.exe" --user=root --host=127.0.0.1 -e "DROP DATABASE IF EXISTS lifeos_db; CREATE DATABASE lifeos_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Step 3: Import the Backup File
```cmd
"C:\xampp\mysql\bin\mysql.exe" --user=root --host=127.0.0.1 lifeos_db < "c:\LifeOs\backups\lifeos_db_backup_20261109_090444.sql"
```

### Step 4: Verify Restoration
Run migrations check:
```cmd
.\.venv\Scripts\python.exe manage.py showmigrations
```
All migrations should show `[X]`.

---

## 4. Automating Daily Backups (Windows Task Scheduler)

You can set Windows to back up your database automatically every night:

1. Press `Win + R`, type `taskschd.msc`, and press **Enter**.
2. In the right pane, click **Create Basic Task...**.
3. **Name**: `LifeOS Daily Database Backup`.
4. **Trigger**: Select **Daily** (e.g., at 02:00 AM).
5. **Action**: Select **Start a program**.
6. **Program/script**: `c:\LifeOs\backup_database.bat`.
7. **Start in**: `c:\LifeOs`.
8. Click **Finish**.

---

## 5. Offsite Redundancy Recommendation

To guard against laptop hardware failure:
- Sync the `c:\LifeOs\backups\` folder with your cloud storage provider (Google Drive, OneDrive, or Dropbox).
- Or periodically copy the `.sql` files to a USB flash drive.
