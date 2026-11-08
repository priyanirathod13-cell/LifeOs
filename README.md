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
- **Frontend Architecture**: Server-rendered HTML5, CSS3 with CSS Variables, Modern Vanilla JavaScript
- **Typography**: Inter (Weights 400, 500, 600, 700)
- **Design Concept**: Minimal Modern Dark + Soft Indigo Accents
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
├── PROJECT_CONTEXT.md          # Architectural context and philosophy
├── DEVELOPMENT_PROGRESS.md     # Step-by-step milestone tracking
├── DATABASE_SCHEMA.md          # Database tables and schema roadmap
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
│   ├── core/                   # System core, health check, landing page, UI system
│   ├── accounts/               # Custom user model, authentication, profile & sessions
│   ├── productivity/           # Category, Task, Habit, HabitLog, Activity, Routine, ScheduleBlock
│   ├── planning/               # Project, Goal, GoalTask
│   ├── personal/               # JournalEntry, Decision, DecisionOption, DecisionOutcome, Mistake, DailyMetric
│   ├── finance/                # Transaction
│   └── study/                  # Subject, Topic, StudySession, Exam
│
├── templates/                  # Django Template Architecture
│   ├── base.html               # Foundational HTML5 shell and asset links
│   ├── layouts/
│   │   └── app_layout.html     # Authenticated three-tier layout
│   ├── components/
│   │   ├── sidebar.html        # Left navigation grouped by domain
│   │   ├── header.html         # Top header with profile, search, breadcrumbs
│   │   └── messages.html       # Flash messages integration
│   └── pages/
│       ├── dashboard.html      # Executive behavioral overview
│       ├── ui_system.html      # 16-component design system catalog
│       ├── placeholder.html    # Reusable module under-construction view
│       ├── tasks.html          # Tasks module page
│       ├── habits.html         # Habits module page
│       ├── study.html          # Study management page
│       ├── projects.html       # Projects page
│       ├── journal.html        # Journal entries page
│       └── settings.html       # System settings page
│
├── static/                     # Design System Static Assets
│   ├── css/
│   │   ├── variables.css       # Central color system & design tokens
│   │   ├── base.css            # Reset, typography, utility classes
│   │   ├── layout.css          # Sidebar, sticky header, content area
│   │   ├── components.css      # All 16 reusable UI components
│   │   └── responsive.css      # Tablet and mobile breakpoint queries
│   ├── js/
│   │   ├── main.js             # Dropdown, modal, alert interactions
│   │   └── navigation.js       # Sidebar toggle, drawer, active links
│   └── images/
│       ├── logo.svg            # Custom LifeOS SVG mark
│       └── avatar-placeholder.svg
│
└── media/                      # User-uploaded files (avatars, attachments)
    └── .gitkeep
```

---

## 4. Design System & Visual Identity

### Direction: Minimal Modern Dark + Soft Indigo Accents
LifeOS adheres to a disciplined visual system prioritizing readability, cognitive calm, and clear visual hierarchy.

### Central CSS Color Palette
All colors are configured centrally in `static/css/variables.css`:
```css
:root {
    --bg-primary: #0F1117;          /* Main application canvas */
    --bg-sidebar: #151821;          /* Left sidebar background */
    --bg-card: #1B1F2A;             /* Cards, dialogs, dropdowns */
    --accent-primary: #818CF8;      /* Primary soft indigo accent */
    --accent-secondary: #A78BFA;    /* Secondary violet accent */
    --text-primary: #F3F4F6;        /* High-contrast body text */
    --text-secondary: #9CA3AF;      /* Secondary descriptive text */
    --text-muted: #6B7280;          /* Captions, labels, timestamps */
    --success: #34D399;             /* Positive streaks, completed states */
    --warning: #FBBF24;             /* In-progress states, deadlines */
    --danger: #F87171;              /* High-friction alerts, overdue items */
    --border: #2A2F3A;              /* Subtle card and divider borders */
}
```

### 16 Foundational UI Components
1. **Primary Button** (`.btn.btn-primary`)
2. **Secondary Button** (`.btn.btn-secondary`)
3. **Outline Button** (`.btn.btn-outline`)
4. **Input Field** (`.form-control`)
5. **Textarea** (`textarea.form-control`)
6. **Select Dropdown** (`.form-select`)
7. **Custom Checkbox** (`.custom-checkbox`)
8. **Toggle Switch** (`.toggle-switch`)
9. **Card & Metric Card** (`.card`, `.metric-card`)
10. **Modal Dialog** (`.modal-backdrop`, `.modal-dialog`)
11. **Status Badges** (`.badge`, `.badge-accent`, `.badge-success`, `.badge-warning`, `.badge-danger`, `.badge-neutral`)
12. **Progress Bars** (`.progress-bar-wrap`, `.progress-fill`)
13. **Responsive Data Tables** (`.table-container`, `.table`)
14. **Empty State** (`.empty-state`)
15. **Alerts & Notifications** (`.alert`, `.alert-info`, `.alert-success`, `.alert-warning`, `.alert-danger`)
16. **Loading Indicators** (`.spinner`, `.skeleton-box`)

---

## 5. Getting Started: Step-by-Step Guide for Beginners

### Prerequisites
1. **Python** (version 3.10 to 3.13)
2. **MySQL Server** or **MariaDB** (port 3306)
3. **Git**

---

### Step 1: Create and Activate the Virtual Environment

**On Windows (PowerShell):**
```powershell
cd c:\LifeOs
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

---

### Step 3: Configure Environment Variables

```powershell
Copy-Item .env.example .env
```

Ensure `.env` matches your MySQL settings:
```ini
SECRET_KEY=django-insecure-lifeos-local-development-key-change-in-prod
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=lifeos_db
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
TIME_ZONE=Asia/Kolkata
LANGUAGE_CODE=en-us
```

---

### Step 4: Run Migrations and Tests

```powershell
# Run database migrations
python manage.py migrate

# (Optional) Import legacy data from legacy 'lifeos' database
python manage.py import_legacy_data

# Run Django system checks
python manage.py check

# Run automated test suite across all 7 applications
python manage.py test
```

Expected output:
```
System check identified no issues (0 silenced).
Ran 59 tests in ~50s

OK
```

---

### Step 5: Start the Development Server

```powershell
python manage.py runserver
```

---

### Step 6: Explore the Interfaces

- **Public Landing Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (Introduces LifeOS, redirects authenticated users to their dashboard)
- **User Registration**: [http://127.0.0.1:8000/accounts/register/](http://127.0.0.1:8000/accounts/register/) (Create a new private user account)
- **User Login**: [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/) (Sign in with email, password, and Remember Me toggle)
- **Password Reset**: [http://127.0.0.1:8000/accounts/password-reset/](http://127.0.0.1:8000/accounts/password-reset/) (Console email delivery in development)
- **Executive Dashboard**: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/) (Central control panel with live tasks, habits, study duration, goals, schedule blocks, recent activity, and quick actions)
- **User Profile & Settings**: [http://127.0.0.1:8000/accounts/profile/](http://127.0.0.1:8000/accounts/profile/) (Update full name, bio, timezone, and change password)
- **UI Design System Showcase**: [http://127.0.0.1:8000/ui-system/](http://127.0.0.1:8000/ui-system/) (Interactive 16-component catalog)
- **Health-Check API Endpoint**: [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/) (Preserved from Step 01)
- **User Profile & Settings**: [http://127.0.0.1:8000/accounts/profile/](http://127.0.0.1:8000/accounts/profile/) (Update full name, bio, timezone, and change password)
- **UI Design System Showcase**: [http://127.0.0.1:8000/ui-system/](http://127.0.0.1:8000/ui-system/) (Interactive 16-component catalog)
- **Health-Check API Endpoint**: [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/) (Preserved from Step 01)
