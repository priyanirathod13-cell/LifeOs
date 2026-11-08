# LifeOS — Personal Behavioral Intelligence & Life Management System

LifeOS is a multi-user behavioral intelligence and life management platform designed to help users track, organize, and analyze all aspects of their daily lives. By systematically connecting planning, daily habits, task completion, mood, energy levels, decision-making, and financial activity, LifeOS enables users to discover patterns in their behavior and optimize their personal growth and productivity.

---

## 1. Project Overview

LifeOS brings together multiple life dimensions into a cohesive, private, multi-user system:
- **Tasks & Productivity**: Prioritized task tracking and focus workflows.
- **Habits & Routines**: Streak tracking, consistency metrics, and behavioral feedback.
- **Goals & Projects**: Structured milestones linking high-level objectives to daily tasks.
- **Study Management**: Subject tracking, revision schedules, and academic workflows.
- **Timetables & Schedules**: Dynamic daily and weekly routines.
- **Journal Entries & Reflections**: Qualitative daily logs for retrospectives.
- **Mood, Sleep & Energy**: Biometric and subjective state logging to correlate with productivity.
- **Financial Activities**: Personal expense and cash flow tracking.
- **Decisions & Mistakes**: Documenting decisions, expected outcomes, and lessons learned.
- **Behavioral Analytics**: Insights into the relationships between planning, execution, and outcomes.

---

## 2. Technology Stack

- **Backend**: Python (3.11+) & Django (4.2 LTS)
- **Database**: MySQL / MariaDB via Django ORM and `mysqlclient`
- **Frontend Foundation**: HTML5, CSS3, Modern JavaScript (Vanilla)
- **Environment Management**: Python Virtual Environment (`venv`), `python-dotenv`
- **Version Control**: Git & GitHub

---

## 3. Project Folder Structure

```
LifeOS/
│
├── manage.py                   # Django CLI utility for administrative tasks
├── requirements.txt            # Project dependencies
├── .env                        # Local environment variables (not committed)
├── .env.example                # Example environment configuration template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
│
├── config/                     # Core project configuration
│   ├── __init__.py
│   ├── settings.py             # Django settings (database, apps, middleware, tz)
│   ├── urls.py                 # Top-level URL routing
│   ├── asgi.py                 # ASGI configuration for async support
│   └── wsgi.py                 # WSGI configuration for production servers
│
├── apps/                       # Modular Django applications
│   ├── __init__.py
│   ├── core/                   # Shared foundational views, health check, utilities
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── tests.py            # Core app test suite
│   │   ├── urls.py             # Core routes (/health/)
│   │   └── views.py            # Health check view
│   └── accounts/               # Custom user model & authentication foundation
│       ├── migrations/
│       │   └── 0001_initial.py # Initial custom User migration
│       ├── __init__.py
│       ├── admin.py            # User model admin configuration
│       ├── apps.py
│       ├── models.py           # Custom User model inheriting AbstractUser
│       └── tests.py            # User model test suite
│
├── templates/                  # Global HTML templates directory
│   └── .gitkeep
│
├── static/                     # Global static assets
│   ├── css/                    # Stylesheets
│   ├── js/                     # Client-side JavaScript
│   └── images/                 # Static graphical assets
│
└── media/                      # User-uploaded files (avatars, attachments)
    └── .gitkeep
```

---

## 4. Getting Started: Step-by-Step Guide for Beginners

Follow these instructions to set up and run LifeOS locally on your machine.

### Prerequisites

Ensure you have the following installed:
1. **Python** (version 3.10, 3.11, 3.12, or 3.13)
2. **MySQL Server** or **MariaDB** (standalone or via XAMPP)
3. **Git**

---

### Step 1: Clone or Navigate to the Project

Open your terminal (PowerShell, Command Prompt, or Bash) and navigate to the project directory:

```bash
cd c:\LifeOs
```

---

### Step 2: Create and Activate a Python Virtual Environment

A virtual environment ensures project dependencies do not interfere with your global Python installation.

**On Windows:**
```powershell
# Create the virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# (If using CMD instead of PowerShell: .\.venv\Scripts\activate.bat)
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

When activated, you will see `(.venv)` in your terminal prompt.

---

### Step 3: Install Required Dependencies

Install the verified project packages using `pip`:

```bash
pip install -r requirements.txt
```

This installs:
- `Django`: Web framework.
- `mysqlclient`: High-performance C-based MySQL database driver for Django.
- `python-dotenv`: Loads `.env` environment variables automatically into Django settings.

---

### Step 4: Prepare the MySQL Database

Make sure your MySQL server is running (e.g., start MySQL in the XAMPP Control Panel or start your MySQL Windows service).

Log into the MySQL command line client:

```bash
mysql -u root -p
```
*(If using default local XAMPP without a password, run `mysql -u root`)*

Run the following SQL statement to create the LifeOS database with full UTF-8 support:

```sql
CREATE DATABASE IF NOT EXISTS lifeos_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Type `exit` to return to your terminal.

---

### Step 5: Configure Environment Variables

Create your local `.env` configuration file from the template:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` in your text editor and verify your settings:

```ini
# Django Security and Core Settings
SECRET_KEY=django-insecure-lifeos-local-development-key-change-in-prod
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# MySQL Database Configuration
DB_NAME=lifeos_db
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306

# Timezone and Localization
TIME_ZONE=Asia/Kolkata
LANGUAGE_CODE=en-us
```

> **Note**: If your local MySQL instance has a root password or a custom port, update `DB_PASSWORD` and `DB_PORT` accordingly.

---

### Step 6: Run Database Migrations

Apply the database migrations to create the custom user model and Django system tables:

```bash
python manage.py migrate
```

Expected output:
```
Operations to perform:
  Apply all migrations: accounts, admin, auth, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  ...
  Applying accounts.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying sessions.0001_initial... OK
```

---

### Step 7: Run System Verification and Tests

Verify that all configurations and tests pass:

```bash
# 1. Run Django system checks
python manage.py check

# 2. Run automated test suite
python manage.py test
```

Expected output:
```
Ran 6 tests in 0.943s

OK
```

---

### Step 8: Start the Development Server

Start the local Django development server:

```bash
python manage.py runserver
```

You should see output similar to:
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 4.2.30, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

### Step 9: Test the Health-Check Endpoint

Open your web browser or send an HTTP request using your terminal to test the live health-check endpoint:

**Using Browser:**
Visit: [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/)

**Using PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/"
```

**Using cURL:**
```bash
curl http://127.0.0.1:8000/health/
```

**Expected JSON Response:**
```json
{
    "status": "ok",
    "application": "LifeOS"
}
```

---

## 5. Important Architecture Notes for Future Steps

1. **Custom User Model Configured First**: The custom `User` model (`apps.accounts.models.User`) is registered via `AUTH_USER_MODEL = 'accounts.User'` before any user data has been stored. This ensures clean extensibility for Step 02+ profile features without database migration conflicts.
2. **Modular `apps/` Layout**: All future modules (habits, tasks, journal, finance, analytics) will be created as discrete apps inside `apps/` to maintain clean separation of concerns.
3. **Strict Secrets Separation**: The `.env` file is excluded from Git. Production environments should supply real environment variables with `DEBUG=False` and a secure random `SECRET_KEY`.
