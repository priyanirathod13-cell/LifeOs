# LifeOS — Public Access Guide (Tailscale Funnel & Cloudflare)

This guide explains how to host and share LifeOS over the public internet with friends, testers, or evaluators **completely free of cost**, with **zero domain purchases**, **zero router port forwarding**, and **zero cloud hosting fees**.

---

## 1. Primary Method: Tailscale Funnel (Stable & Permanent HTTPS)

Tailscale Funnel exposes your local Waitress server (`http://127.0.0.1:8000`) to the public internet using a **permanent, stable MagicDNS domain** (`*.ts.net`) with automated Let's Encrypt TLS certificates.

### Public Access Endpoints
- **Live Application**: [https://laptop-lkra47mc.tail581455.ts.net/](https://laptop-lkra47mc.tail581455.ts.net/)
- **User Login**: [https://laptop-lkra47mc.tail581455.ts.net/accounts/login/](https://laptop-lkra47mc.tail581455.ts.net/accounts/login/)
- **User Registration**: [https://laptop-lkra47mc.tail581455.ts.net/accounts/register/](https://laptop-lkra47mc.tail581455.ts.net/accounts/register/)
- **Health-Check API**: [https://laptop-lkra47mc.tail581455.ts.net/health/](https://laptop-lkra47mc.tail581455.ts.net/health/)

> **Important Hosting Notice**: This application is edge-hosted directly on the developer's Windows laptop. It is accessible whenever the host laptop, internet connection, Tailscale Windows service, and LifeOS application server are running. It is not hosted on a 24/7 cloud cluster.

---

### Architecture

```
                                [The Public Internet]
                                          |
                                          v
                            [Any Web Browser Worldwide]
                                          |
                                          v (HTTPS / TLS Encrypted)
                             [Tailscale Global Edge Ingress]
                         https://laptop-lkra47mc.tail581455.ts.net
                                          |
                        ======================================
                         Encrypted WireGuard / Funnel Tunnel
                        ======================================
                                          |
                                          v
                           [Your Windows Laptop Server]
                           (Tailscale Windows Service)
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
           [Waitress WSGI: Port 8000]                 [MySQL: Port 3306]
          (Processes Web Requests)                 (STRICTLY PRIVATE / LOCAL)
```

### Why Tailscale Funnel is the Permanent Solution:
- **Stable URL**: Your public URL is **`https://laptop-lkra47mc.tail581455.ts.net/`**. It never rotates or changes randomly.
- **Zero Cost**: 100% free forever for personal use on Tailscale's free tier.
- **Persistent Background Service**: Operates via `Tailscale` Windows Service (`--bg`), automatically recovering across reboots.
- **Complete MySQL Isolation**: Port 3306 is strictly local; only HTTP traffic to port 8000 is proxied.
- **Session Independence**: Runs as a Windows system service, completely unaffected by terminal or editor restarts.

---

### How to Start or Manage Tailscale Funnel:
1. Double-click [`start_tailscale_funnel.bat`](start_tailscale_funnel.bat) or run:
   ```cmd
   tailscale funnel --bg 8000
   ```
2. Check Funnel status anytime:
   ```cmd
   tailscale funnel status
   ```
   **Expected Output**:
   ```text
   # Funnel on:
   #     - https://laptop-lkra47mc.tail581455.ts.net

   https://laptop-lkra47mc.tail581455.ts.net (Funnel on)
   |-- / proxy http://127.0.0.1:8000
   ```
3. To stop public exposure:
   ```cmd
   tailscale funnel --https=443 off
   ```

---

## 2. Troubleshooting Public Access

### Issue 1: `DNS_PROBE_FINISHED_NXDOMAIN`
- **Root Cause**: When the laptop boots or resumes from sleep, the Tailscale Windows Service takes 10 to 20 seconds to establish its connection to the Tailscale coordination network (`BackendState: Running`). If you attempt to open the public URL in your browser before Tailscale finishes initializing, Chrome caches an NXDOMAIN error in its local DNS cache.
- **Resolution**:
  1. Wait ~15 seconds until the Tailscale taskbar icon shows active and connected.
  2. Clear DNS cache in Command Prompt:
     ```cmd
     ipconfig /flushdns
     ```
  3. Perform a hard refresh in Chrome: press **`Ctrl + F5`** (or `Shift + F5`).

### Issue 2: `HTTP ERROR 502 (Bad Gateway)`
- **Root Cause**: Tailscale Funnel is forwarding incoming traffic to `http://127.0.0.1:8000`, but the local Waitress server was stopped or crashed.
- **Resolution**:
  1. LifeOS includes an autonomous supervisor daemon ([`supervisor.py`](supervisor.py)) running in the background. It continuously tests local health every 15 seconds and automatically relaunches Waitress and MySQL if either crashes.
  2. To restart manually, double-click [`restart_lifeos.bat`](restart_lifeos.bat).
  3. Verify local health check returns `HTTP 200`:
     ```powershell
     Invoke-WebRequest -Uri "http://localhost:8000/health/" -UseBasicParsing
     ```

---

## 3. Alternative Method: Cloudflare Quick Tunnel (Ephemeral Demos)

For temporary testing or demonstrations where Tailscale is not desired:

| Feature | LifeOS Laptop + Cloudflare Tunnel | Traditional Cloud / VPS |
|---|---|---|
| **Monthly Cost** | **$0.00 (100% Free)** | $15 – $50 / month |
| **Domain Registration** | **None required** (free `trycloudflare.com`) | $12 – $20 / year |
| **Router Port Forwarding** | **None** (purely outbound connection) | Complex or risky |
| **MySQL Port 3306 Exposure** | **Zero** (completely blocked from internet) | Public or VPN needed |
| **SSL / HTTPS** | **Automatic Free TLS Certificate** | Let's Encrypt / Manual |

### How to Launch Cloudflare Quick Tunnel:
1. Ensure the LifeOS server is running via `start_lifeos.bat`.
2. Double-click [`start_tunnel.bat`](start_tunnel.bat) or run:
   ```powershell
   .\.venv\Scripts\cloudflared.exe tunnel --url http://127.0.0.1:8000
   ```
3. A temporary public HTTPS link (e.g. `https://<random-name>.trycloudflare.com`) is generated.
4. Stop by pressing `Ctrl + C` in the tunnel terminal.
