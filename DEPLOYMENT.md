# LifeOS — Deployment & Production Operations Manual

This manual outlines the production deployment architectures, environment configurations, security checklists, and operations procedures for **LifeOS (Personal Behavioral Intelligence — A Debugger for Humans)**.

---

## 1. System Architecture & Deployment Overview

LifeOS is architected to run as a high-performance, edge-hosted production server on a dedicated Windows machine with zero recurring cloud hosting fees, zero domain renewal fees, and complete data sovereignty.

```
                                [The Public Internet]
                                          |
                                          v
                              [Any Browser Worldwide]
                                          |
                                          v (HTTPS / TLS)
                          [Tailscale Global Edge Ingress]
                      https://laptop-lkra47mc.tail581455.ts.net
                                          |
                        ======================================
                         Encrypted WireGuard / Funnel Tunnel
                        ======================================
                                          |
                                          v
                             [Host Development Laptop]
                          (Tailscale Windows Service)
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             [Waitress WSGI: Port 8000]             [MySQL: Port 3306]
             (Django Multi-Threaded Web)          (STRICTLY PRIVATE / LOCAL)
                        ^
                        | (Supervised Every 15s)
             [Autonomous Supervisor Daemon]
             (supervisor.py with Win32 Mutex)
```

### Core Architecture Components:
- **Application Server**: Python 3.13 with Django 4.2 LTS.
- **Production WSGI Server**: Multi-threaded **Waitress WSGI** (`waitress>=3.0.0`) bound to `0.0.0.0:8000`.
- **Autonomous Supervisor**: [`supervisor.py`](supervisor.py) daemon maintaining service uptime, database readiness checks, single-instance Named Mutex locking, and automatic crash recovery.
- **Primary Database**: Local MySQL 8.0 / MariaDB on `127.0.0.1:3306` (`lifeos_db`), strictly blocked from public exposure.
- **Static Assets**: **WhiteNoise** (`whitenoise.middleware.WhiteNoiseMiddleware`) with automated compression and persistent browser caching.
- **Public HTTPS Gateway**: **Tailscale Funnel** providing a permanent, stable MagicDNS URL (`https://laptop-lkra47mc.tail581455.ts.net/`) with automatic Let's Encrypt TLS.
- **Ephemeral Fallback**: Cloudflare Quick Tunnel (`cloudflared`) for temporary, zero-configuration sharing.

---

## 2. Production Environment Configuration (`.env`)

In production environments, ensure environment variables are populated securely through your protected `.env` file (which is strictly excluded from version control):

```ini
# Core Security
DEBUG=False
SECRET_KEY=generate-a-secure-50-plus-character-random-key-here-do-not-use-dev-key
ALLOWED_HOSTS=127.0.0.1,localhost,laptop-lkra47mc.tail581455.ts.net,.ts.net

# CSRF Trusted Origins (Crucial for HTTPS form submissions)
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,https://laptop-lkra47mc.tail581455.ts.net,https://*.ts.net

# Database Configuration (Strictly Private Local Host)
DB_NAME=lifeos_db
DB_USER=root
DB_PASSWORD=your_secure_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Localization & Timezone
TIME_ZONE=Asia/Kolkata
LANGUAGE_CODE=en-us

# Reverse Proxy Security
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## 3. Operational Procedures: Start, Stop & Restart

LifeOS provides deterministic operational scripts for managing the system cleanly on Windows:

### A. How to Start LifeOS
Double-click or run from command line:
```cmd
c:\LifeOs\start_lifeos.bat
```
**Execution Sequence**:
1. Validates Python virtual environment at `.venv\Scripts\python.exe`.
2. Probes port 3306. If MySQL is down, starts XAMPP MySQL daemon (`mysqld.exe`) with its native working directory.
3. Executes any pending database migrations safely (`python manage.py migrate --noinput`).
4. Launches the autonomous supervisor (`supervisor.py`), which acquires the Win32 Named Mutex, verifies database connectivity via `SELECT 1`, spawns Waitress WSGI on port 8000, and enables Tailscale Funnel.

### B. How to Stop LifeOS
Double-click or run:
```cmd
c:\LifeOs\stop_lifeos.bat
```
**Execution Sequence**:
1. Reads `supervisor.pid` and terminates the supervisor process if active.
2. Executes [`stop_lifeos.ps1`](stop_lifeos.ps1) in PowerShell to find and stop any running instances of `supervisor.py` or `serve.py`.
3. Queries `netstat` and gracefully terminates any remaining process holding port 8000.
4. Frees all sockets and releases the single-instance mutex cleanly.

### C. How to Restart LifeOS
Double-click or run:
```cmd
c:\LifeOs\restart_lifeos.bat
```
Executes a clean shutdown via `stop_lifeos.bat`, delays 3 seconds to ensure sockets are fully drained, and then executes `start_lifeos.bat`.

### D. Windows Auto-Start on Logon
LifeOS is registered in Windows Startup to boot headlessly upon user logon:
- **Startup Shortcut**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\LifeOS.lnk`
- **Registry Key**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\LifeOS`
- **Target**: Executes [`launch_lifeos_background.vbs`](launch_lifeos_background.vbs), which starts `pythonw.exe supervisor.py` with zero console popups.

---

## 4. Health Verification & Monitoring

### Local Health Verification
Run in PowerShell or browser:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health/" -UseBasicParsing
```
**Expected Response** (`HTTP 200 OK`):
```json
{"status": "ok", "application": "LifeOS"}
```
*Note: The `/health/` endpoint verifies database connectivity (`SELECT 1`). If MySQL is offline, it returns `HTTP 503 Service Unavailable` with `status: "degraded"`.*

### Public Health Verification
Run from any device on the internet:
```powershell
Invoke-WebRequest -Uri "https://laptop-lkra47mc.tail581455.ts.net/health/" -UseBasicParsing
```
**Expected Response** (`HTTP 200 OK`):
```json
{"status": "ok", "application": "LifeOS"}
```

### Inspecting Live Supervisor Logs
Review recent operational logs and health heartbeats:
```powershell
Get-Content -Path "c:\LifeOs\monitor.log" -Tail 30
```

---

## 5. Multi-Device & Mobile Access

### A. Public Internet Access (Anywhere Worldwide)
1. Ensure the supervisor is active.
2. Share the verified permanent links:
   - **Landing Page**: `https://laptop-lkra47mc.tail581455.ts.net/`
   - **Login**: `https://laptop-lkra47mc.tail581455.ts.net/accounts/login/`
   - **Registration**: `https://laptop-lkra47mc.tail581455.ts.net/accounts/register/`

### B. Local Wi-Fi LAN Access (Phones & Tablets on Same Network)
1. Verify incoming traffic is permitted through the Windows Firewall:
   ```cmd
   netsh advfirewall firewall add rule name="LifeOS Web Server" dir=in action=allow protocol=TCP localport=8000
   ```
2. Check your laptop's current Wi-Fi IP address (displayed in `serve.py` startup logs or via `ipconfig`).
3. On your mobile browser, navigate to:
   ```
   http://<YOUR_LAN_IP>:8000
   ```

---

## 6. Troubleshooting Common Issues

### Issue 1: Browser Displays `DNS_PROBE_FINISHED_NXDOMAIN`
- **Root Cause**: When the host laptop boots or wakes from sleep, the Tailscale Windows service requires 10–20 seconds to establish connection with the coordination network (`BackendState: Running`). Accessing the domain before Tailscale finishes causes Chrome to cache an NXDOMAIN response.
- **Resolution**:
  1. Wait ~15 seconds until the Tailscale taskbar icon shows connected.
  2. Clear DNS cache in Command Prompt:
     ```cmd
     ipconfig /flushdns
     ```
  3. Perform a hard refresh in Chrome: **`Ctrl + F5`** (or `Shift + F5`).

### Issue 2: Browser Displays `HTTP ERROR 502 (Bad Gateway)`
- **Root Cause**: Tailscale Funnel is forwarding traffic to `http://127.0.0.1:8000`, but the Waitress server process was stopped or failed.
- **Resolution**:
  1. The autonomous supervisor (`supervisor.py`) detects unresponsiveness within 15 seconds and automatically restarts Waitress.
  2. To trigger manual recovery immediately, run [`restart_lifeos.bat`](restart_lifeos.bat).
  3. Inspect `monitor.log` and `server.log` for any Python traceback.

### Issue 3: MySQL Connection Refused (`port 3306`)
- **Resolution**:
  1. Verify XAMPP MySQL daemon is running:
     ```powershell
     Get-Process mysqld -ErrorAction SilentlyContinue
     ```
  2. The supervisor automatically attempts to launch `C:\xampp\mysql\bin\mysqld.exe` if port 3306 drops.

---

## 7. Database Backup & Disaster Recovery

### Automated One-Click Backup
Run [`backup_database.bat`](backup_database.bat) to generate an instant timestamped backup in `c:\LifeOs\backups\`:
```cmd
c:\LifeOs\backup_database.bat
```

### Restoring from Backup
```cmd
"C:\xampp\mysql\bin\mysql.exe" --user=root --host=127.0.0.1 lifeos_db < "c:\LifeOs\backups\your_backup_file.sql"
```

For full backup policies and automated schedules, see [`DATABASE_BACKUP_GUIDE.md`](DATABASE_BACKUP_GUIDE.md).

---

## 8. Alternative Hosting Architectures

### Option B: Docker Compose Deployment
```bash
docker compose up -d --build
```
Includes multi-stage Docker build, health checks, volume persistence, and automatic container restarts.

### Option C: Traditional Linux Server (Ubuntu / Nginx / Gunicorn)
Refer to section 3 in legacy deployment docs for Systemd service unit configurations and Nginx reverse proxy blocks.
