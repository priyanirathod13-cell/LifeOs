# LifeOS — Cloud Deployment & Production Operations Manual

This guide outlines the production deployment architectures, environment configurations, security checklists, and operations procedures for **LifeOS (Personal Behavioral Intelligence & Life Management System)**.

---

## 1. System Architecture & Prerequisites

### Architecture Overview
- **Application Server**: Python 3.12+ with Django 4.2 LTS
- **WSGI Production Server**: Gunicorn (3 worker processes with 120s timeout)
- **Static Assets**: Automated compression and caching via **WhiteNoise** (`whitenoise.middleware.WhiteNoiseMiddleware`)
- **Primary Database**: MySQL 8.0 / MariaDB 10.4+ (or cloud-managed MySQL/PostgreSQL via `DATABASE_URL`)
- **Security**: Strict TLS/HTTPS termination, HSTS (1 year), HTTP-only and secure session/CSRF cookies, isolated tenant scoping

### Prerequisites
- Python 3.12 or newer
- MySQL Server or a cloud-managed database instance
- Git version control
- (Optional) Docker & Docker Compose installed

---

## 2. Production Environment Configuration (`.env`)

In production environments, ensure environment variables are populated securely through your hosting platform's secret manager or a protected `.env` file:

```ini
# Core Security
DEBUG=False
SECRET_KEY=generate-a-secure-50-plus-character-random-key-here-do-not-use-dev-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-app.railway.app,your-app.onrender.com

# CSRF Whitelist (Crucial for HTTPS POST submissions)
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://your-app.railway.app,https://your-app.onrender.com

# Database Configuration (Option 1: Standard Connection Parameters)
DB_NAME=lifeos_db
DB_USER=lifeos_admin
DB_PASSWORD=your_strong_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Database Configuration (Option 2: Cloud Connection URL)
# If provided, DATABASE_URL overrides the individual DB_* settings above:
# DATABASE_URL=mysql://lifeos_admin:password@mysql.host.provider.com:3306/lifeos_db

# Localization & Preferences
TIME_ZONE=Asia/Kolkata
LANGUAGE_CODE=en-us

# Production SSL & Cookie Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Logging Levels
DJANGO_LOG_LEVEL=INFO
LIFEOS_LOG_LEVEL=INFO
```

---

## 3. Cloud Deployment Options

LifeOS is pre-configured with deployment manifests for major cloud PaaS and container hosting providers.

### Option A: Railway (Recommended — 1-Click Zero Config)

LifeOS includes [`railway.toml`](file:///c:/LifeOs/railway.toml) and [`Procfile`](file:///c:/LifeOs/Procfile) for automated deployment on Railway.

1. **Create Project**: Sign in to [Railway.app](https://railway.app) and click **New Project** → **Deploy from GitHub repo**.
2. **Select Repository**: Connect your LifeOS repository.
3. **Add Database**:
   - In the Railway project canvas, click **New** → **Database** → **MySQL**.
   - Railway will provision a dedicated MySQL 8.0 instance and expose `DATABASE_URL`.
4. **Configure Environment Variables**:
   In your Web Service settings, add:
   - `SECRET_KEY`: (Generate a secure 50+ character string)
   - `DEBUG`: `False`
   - `DATABASE_URL`: `${{ MySQL.DATABASE_URL }}`
   - `ALLOWED_HOSTS`: `*.railway.app,yourdomain.com`
   - `CSRF_TRUSTED_ORIGINS`: `https://*.railway.app,https://yourdomain.com`
   - `SECURE_SSL_REDIRECT`: `True`
5. **Deploy**:
   Railway automatically detects `Nixpacks` / `Procfile`, executes static collection (`python manage.py collectstatic --noinput`), runs database migrations (`python manage.py migrate`), and starts Gunicorn.
6. **Verify**: Visit `https://your-service.up.railway.app/health/` — it will return `{"status": "ok", "application": "LifeOS"}`.

---

### Option B: Render (Blueprint Deployment)

LifeOS provides a complete [`render.yaml`](file:///c:/LifeOs/render.yaml) blueprint declaring both the web service and managed database.

1. Push your repository to GitHub or GitLab.
2. Sign in to [Render.com](https://render.com) and navigate to **Blueprints**.
3. Select your LifeOS repository. Render reads `render.yaml` and initializes:
   - A Web Service (`lifeos-app`) running Python 3.12.
   - A managed database (`lifeos-db`).
4. Review the generated configuration and click **Apply**.
5. Render runs the build command:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput
   ```
   And executes the start command:
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
   ```
6. On initial deployment, run migrations from the Render Web Shell:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

---

### Option C: Containerized Deployment (Docker & Docker Compose)

LifeOS includes a production [`Dockerfile`](file:///c:/LifeOs/Dockerfile), [`docker-compose.yml`](file:///c:/LifeOs/docker-compose.yml), and [`.dockerignore`](file:///c:/LifeOs/.dockerignore).

#### Quick Start with Docker Compose:

1. Clone repository to your production server:
   ```bash
   git clone <repo_url> /opt/lifeos
   cd /opt/lifeos
   ```

2. Generate a secure secret key and review `docker-compose.yml`:
   ```bash
   # Replace SECRET_KEY in docker-compose.yml with a production secret
   ```

3. Launch the container stack:
   ```bash
   docker compose up -d --build
   ```

4. Verify service status and database health:
   ```bash
   docker compose ps
   docker compose logs -f web
   ```

5. Create administrative superuser inside the container:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

---

### Option D: Traditional Linux Server (Ubuntu / Nginx / Systemd)

For deployment on AWS EC2, DigitalOcean Droplet, Linode, or Hetzner:

#### 1. Server Prerequisites
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev default-libmysqlclient-dev pkg-config nginx git curl
```

#### 2. Virtual Environment Setup
```bash
sudo git clone <repo_url> /var/www/lifeos
sudo chown -R $USER:$USER /var/www/lifeos
cd /var/www/lifeos
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### 3. Environment & Migrations
```bash
cp .env.example .env
nano .env  # Configure MySQL credentials, SECRET_KEY, ALLOWED_HOSTS
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

#### 4. Systemd Gunicorn Service (`/etc/systemd/system/lifeos.service`)
```ini
[Unit]
Description=LifeOS Gunicorn Application Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/lifeos
ExecStart=/var/www/lifeos/.venv/bin/gunicorn \
          --access-logfile /var/log/lifeos/access.log \
          --error-logfile /var/log/lifeos/error.log \
          --workers 3 \
          --timeout 120 \
          --bind unix:/run/lifeos.sock \
          config.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo mkdir -p /var/log/lifeos
sudo chown -R www-data:www-data /var/log/lifeos
sudo systemctl daemon-reload
sudo systemctl enable --now lifeos.service
```

#### 5. Nginx Reverse Proxy (`/etc/nginx/sites-available/lifeos`)
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 25M;

    location /static/ {
        alias /var/www/lifeos/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }

    location /media/ {
        alias /var/www/lifeos/media/;
        expires 30d;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/lifeos.sock;
    }
}
```

Enable site and configure SSL with Let's Encrypt Certbot:
```bash
sudo ln -s /etc/nginx/sites-available/lifeos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 4. Post-Deployment Verification Checklist

Once deployed, execute these sanity checks:

1. **Health Check Endpoint**:
   ```bash
   curl -i https://yourdomain.com/health/
   # Expected: HTTP/2 200 OK {"status": "ok", "application": "LifeOS"}
   ```

2. **Security Headers Verification**:
   ```bash
   curl -I https://yourdomain.com/
   # Verify:
   # Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
   # X-Content-Type-Options: nosniff
   # X-Frame-Options: DENY
   ```

3. **User Authentication & Isolation**:
   - Register account `user1@example.com`.
   - Register account `user2@example.com`.
   - Verify each user sees their own private dashboard, tasks, habits, and study syllabi.

4. **Static Asset Integrity**:
   - Verify CSS styling, Inter typography, and SVGs load without console 404 errors.
   - WhiteNoise provides automated gzip/brotli compression with cache-busting headers.

5. **PWA Offline Service Worker**:
   - Open browser developer tools → Application → Service Workers.
   - Verify `service-worker.js` is registered and caching static CSS/JS assets.

---

## 5. Maintenance & Disaster Recovery

- **Database Backup**:
  ```bash
  mysqldump -u root -p lifeos_db > lifeos_backup_$(date +%Y%m%d_%H%M%S).sql
  ```
- **Self-Service User Data Export**:
  Users can download their complete account state anytime in JSON or CSV format via [`/settings/export/`](http://127.0.0.1:8000/settings/export/).
- **Log Inspection**:
  ```bash
  # Systemd logs
  sudo journalctl -u lifeos.service -f
  # Docker logs
  docker compose logs -f web
  ```
