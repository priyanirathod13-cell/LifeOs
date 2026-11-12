# LifeOS — Local Hosting & Wi-Fi Access Guide

This guide explains how to host LifeOS directly on your Windows laptop as a production-grade home server, allowing you and anyone on your local Wi-Fi network (phones, tablets, laptops) to access the application with zero cloud hosting costs and complete data privacy.

---

## 1. Architecture Overview

```
                      +---------------------------------------+
                      |       Windows Laptop Server           |
                      |                                       |
                      |  [MySQL 8.0 / MariaDB on Port 3306]  |
                      |                  ^                    |
                      |                  | (TCP 127.0.0.1)    |
                      |                  v                    |
                      |     [LifeOS Django Application]      |
                      |   + WhiteNoise (Optimized Static)     |
                      |                  ^                    |
                      |                  | (WSGI)             |
                      |                  v                    |
                      |  [Waitress Multi-Threaded Server]     |
                      |            (Port 8000)                |
                      +-------------------+-------------------+
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
       [Local Laptop Browser]                         [Same Wi-Fi Network]
       http://localhost:8000                                     |
       http://127.0.0.1:8000                      +--------------+--------------+
                                                  |                             |
                                                  v                             v
                                         [Android Phone / Tablet]      [iPhone / iPad]
                                         http://<YOUR_LAN_IP>:8000     http://<YOUR_LAN_IP>:8000
```

- **Application Server**: Waitress WSGI server (multi-threaded, production-ready on Windows).
- **Supervisor Daemon**: Autonomous supervisor (`supervisor.py`) running in the background with automatic self-healing.
- **Static Files**: WhiteNoise handles caching, compression, and serving with zero configuration.
- **Database**: Local MySQL (`lifeos_db`) strictly on `127.0.0.1:3306`.
- **Cost**: **$0.00** — completely free forever.

---

## 2. Prerequisites

1. **Python Virtual Environment**: Located at `c:\LifeOs\.venv` with all dependencies installed.
2. **Local MySQL Service**: Running on port `3306` with database `lifeos_db` (via XAMPP MySQL or standalone service).

---

## 3. How to Start, Stop and Restart LifeOS

### Start LifeOS (One-Click)
Double-click or run:
```cmd
c:\LifeOs\start_lifeos.bat
```
This script automatically:
1. Verifies the virtual environment.
2. Checks whether MySQL is running on port 3306 (and launches it if XAMPP is installed).
3. Executes pending database migrations.
4. Launches the supervisor and Waitress WSGI server bound to `0.0.0.0:8000`.

### Stop LifeOS (One-Click)
Double-click or run:
```cmd
c:\LifeOs\stop_lifeos.bat
```
Safely terminates the supervisor, Waitress server, and frees port 8000 without orphan processes.

### Restart LifeOS (One-Click)
Double-click or run:
```cmd
c:\LifeOs\restart_lifeos.bat
```
Stops the server cleanly, waits 3 seconds, and restarts all services.

### Background Auto-Start on Windows Login
LifeOS is registered in your Windows Startup folder. When you log in to Windows, [`launch_lifeos_background.vbs`](launch_lifeos_background.vbs) automatically starts the supervisor silently in the background.

---

## 4. Accessing from Your Laptop Browser

Once the server is running, open any browser on your laptop:
- **Primary URL**: [http://localhost:8000](http://localhost:8000)
- **Loopback URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Health Check**: [http://localhost:8000/health/](http://localhost:8000/health/) (Returns `{"status": "ok", "application": "LifeOS"}`)

---

## 5. Accessing from Mobile Phones & Tablets on Wi-Fi

You can access LifeOS from your smartphone, tablet, or another computer on the same Wi-Fi network:

1. Connect your mobile device to the **exact same Wi-Fi network** as your laptop.
2. Check your laptop's current Wi-Fi IP address:
   - Run `ipconfig` in Command Prompt to find your IPv4 Address (e.g. `10.65.211.34`).
3. Open your mobile browser (Chrome on Android, Safari on iOS) and navigate to:
   ```
   http://<YOUR_LAN_IP>:8000
   ```
   *(e.g. `http://10.65.211.34:8000`)*.

---

## 6. Windows Firewall Setup (One-Time Step)

To allow incoming connections from your local Wi-Fi network to port 8000, add a Windows Firewall inbound rule:

### Add Firewall Inbound Rule:
Run the following command once in **Administrator PowerShell** or **Administrator Command Prompt**:
```cmd
netsh advfirewall firewall add rule name="LifeOS Web Server" dir=in action=allow protocol=TCP localport=8000
```

### To Remove the Rule (if ever needed):
```cmd
netsh advfirewall firewall delete rule name="LifeOS Web Server"
```

---

## 7. Installing LifeOS as a Mobile App (PWA)

LifeOS includes an offline-ready Web App Manifest and Service Worker:
1. Open `http://<YOUR_LAN_IP>:8000` (or the public Tailscale link) on your mobile browser.
2. **On Android (Google Chrome)**:
   - Tap the three-dot menu icon `⋮`.
   - Tap **"Add to Home Screen"** or **"Install app"**.
3. **On iOS (Apple Safari)**:
   - Tap the **Share** button (box with upward arrow).
   - Scroll down and tap **"Add to Home Screen"**.
4. LifeOS launches in full-screen standalone app mode with its own dedicated home screen icon.

---

## 8. Keeping Your Laptop Awake as a Server

To ensure the server remains accessible without sleeping when you step away:
1. Open Windows **Settings** > **System** > **Power & battery**.
2. Expand **Screen and sleep**.
3. Under **"When plugged in, put my device to sleep after"**, select **"Never"**.
4. Set "Turn off my screen after" to 5 or 10 minutes so your display turns off while the laptop and server remain fully operational.

---

## 9. Checking Server Health & Logs

- **Local Health Endpoint**: [http://localhost:8000/health/](http://localhost:8000/health/)
- **Supervisor Health Log**: `c:\LifeOs\monitor.log`
- **Waitress Server Log**: `c:\LifeOs\server.log`
