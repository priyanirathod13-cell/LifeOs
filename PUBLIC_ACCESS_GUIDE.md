# LifeOS — Permanent Free Public Access Guide (Tailscale Funnel & Cloudflare)

This guide explains how to host and share LifeOS over the public internet with friends, testers, or family **completely free of cost**, with **zero domain purchases**, **zero router port forwarding**, and **zero cloud hosting fees**.

---

## 1. Primary Method: Tailscale Funnel (Stable & Permanent HTTPS)

Tailscale Funnel exposes your local Waitress server (`http://127.0.0.1:8000`) to the public internet using a **permanent, stable MagicDNS domain** (`*.ts.net`) with automated Let's Encrypt TLS certificates.

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
                           (Tailscale IPN Windows Service)
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
- **Persistent Background Service**: Operates via `Tailscale IPN` Windows Service (`--bg`), automatically recovering across reboots.
- **Complete MySQL Isolation**: Port 3306 is never exposed to the public; only HTTP traffic to port 8000 is proxied.
- **Antigravity Independence**: Runs as a Windows system service, completely unaffected by IDE or editor restarts.

### How to Start or Manage Tailscale Funnel:
1. Double-click [`start_tailscale_funnel.bat`](start_tailscale_funnel.bat) or run:
   ```cmd
   tailscale funnel --bg 8000
   ```
2. Check Funnel status anytime:
   ```cmd
   tailscale funnel status
   ```
3. To stop public exposure:
   ```cmd
   tailscale funnel --https=443 off
   ```

### Troubleshooting: `DNS_PROBE_FINISHED_NXDOMAIN` or `HTTP 502`
- **`DNS_PROBE_FINISHED_NXDOMAIN`**:
  * **Cause**: When your laptop first boots or wakes from sleep, Tailscale requires 10–20 seconds to establish connection to the coordination network (`BackendState: Running`). If you attempt to open the URL in Chrome immediately before Tailscale initializes, Chrome records an NXDOMAIN error in its local DNS cache.
  * **Resolution**: Wait ~15 seconds until Tailscale icon shows connected. Run `ipconfig /flushdns` in Command Prompt or press `Ctrl + F5` (hard refresh) in the browser to clear Chrome's internal cache (`chrome://net-internals/#dns`).
- **`HTTP 502 Bad Gateway`**:
  * **Cause**: Tailscale Funnel is listening, but the local Waitress server on port 8000 was stopped or crashed.
  * **Resolution**: LifeOS includes an autonomous supervisor daemon (`supervisor.py`) running in the background. It continuously tests local health every 15 seconds and automatically relaunches Waitress and MySQL if either crashes. To restart manually, double-click [`restart_lifeos.bat`](restart_lifeos.bat).

---

## 2. Alternative Method: Cloudflare Quick Tunnel (Ephemeral Demos)

| Feature | LifeOS Laptop + Cloudflare Tunnel | Traditional Cloud / VPS |
|---|---|---|
| **Monthly Cost** | **$0.00 (100% Free)** | $15 – $50 / month |
| **Domain Registration** | **None required** (free `trycloudflare.com`) | $12 – $20 / year |
| **Router Port Forwarding** | **None** (purely outbound connection) | Complex or risky |
| **MySQL Port 3306 Exposure** | **Zero** (completely blocked from internet) | Public or VPN needed |
| **SSL / HTTPS** | **Automatic Free TLS Certificate** | Let's Encrypt / Manual |
| **DDoS Protection** | **Included** by Cloudflare Edge | Extra cost / Complex |

---

## 3. Step-by-Step Instructions

### Step 1: Start LifeOS Server
First, start the local server in your primary terminal or by double-clicking:
```cmd
c:\LifeOs\start_lifeos.bat
```
Wait until the console confirms the server is running on `http://localhost:8000`.

### Step 2: Start Cloudflare Tunnel
In a second terminal window (or by double-clicking):
```cmd
c:\LifeOs\start_tunnel.bat
```
Or manually run:
```powershell
.\.venv\Scripts\cloudflared.exe tunnel --url http://127.0.0.1:8000
```

### Step 3: Copy Your Public HTTPS Link
Within 3–5 seconds, the tunnel console will output log lines. Look for lines like:
```text
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://somewhere-example-phrase.trycloudflare.com                                        |
+--------------------------------------------------------------------------------------------+
```

### Step 4: Share with Friends
1. Copy that `https://....trycloudflare.com` link.
2. Send it to your friends or collaborators.
3. They can open it on their phones, laptops, or tablets from anywhere in the world.
4. They can register their own accounts (`/accounts/register/`) and explore LifeOS with full data isolation!

---

## 4. Built-in Django Security Configuration

The LifeOS Django configuration (`config/settings.py`) has been configured out of the box to support this architecture:

1. **`ALLOWED_HOSTS`**:
   Includes `'.trycloudflare.com'`, allowing any generated Cloudflare subdomain to serve traffic without `DisallowedHost` HTTP 400 errors.
2. **`CSRF_TRUSTED_ORIGINS`**:
   Includes `'https://*.trycloudflare.com'`, ensuring login, registration, and form submissions pass Django CSRF checks securely.
3. **`SECURE_PROXY_SSL_HEADER`**:
   Configured as `('HTTP_X_FORWARDED_PROTO', 'https')`. Django knows when traffic arrived over Cloudflare's HTTPS connection, generating correct secure cookies and HTTPS redirects without forcing local Wi-Fi connections onto invalid SSL.

---

## 5. Ephemeral vs Permanent Tunnels

- **Quick Tunnel (Default)**:
  Requires no account, no setup, no login. Whenever you stop and restart `start_tunnel.bat`, a new random URL is generated. This is perfect for testing, demonstrations, and sharing with friends.
- **Named Tunnel (Optional Future Enhancement)**:
  If you ever want a persistent custom domain (e.g. `lifeos.yourdomain.com`), you can create a free Cloudflare Zero Trust account, run `cloudflared tunnel login`, and bind a permanent tunnel. LifeOS requires zero code changes to support this.

---

## 6. How to Stop Public Access

When you are done sharing:
- Press `Ctrl + C` in the `start_tunnel.bat` window.
- The public tunnel is terminated instantly. Your local server (`http://localhost:8000`) and Wi-Fi access (`http://<LAN_IP>:8000`) will continue running normally.
