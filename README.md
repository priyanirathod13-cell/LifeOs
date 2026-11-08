# LifeOS — Personal Behavioral Intelligence & Life Management System

LifeOS is a multi-user behavioral intelligence and life management platform designed to help users track, organize, and analyze all aspects of their daily lives. By systematically connecting planning, daily habits, task completion, mood, energy levels, decision-making, and financial activity, LifeOS enables users to discover patterns in their behavior and optimize their personal growth and productivity.

---

## 1. Project Overview

LifeOS brings together multiple life dimensions into a cohesive, private, multi-user system:
- **Tasks & Productivity**: Prioritized task tracking and focus workflows.
- **Habits & Routines**: Streak tracking, consistency metrics, and behavioral feedback.
- **Goals & Projects**: Structured milestones linking high-level objectives to daily tasks.
- **Study Management**: Subject tracking, revision schedules, and academic workflows.
- **Timetables & Schedules**: Dynamic daily and weekly routines with auto-generation.
- **Journal Entries & Reflections**: Qualitative daily logs for retrospectives.
- **Mood, Sleep & Energy**: Biometric and subjective state logging to correlate with productivity.
- **Financial Activities**: Personal expense and cash flow tracking in INR.
- **Decisions & Mistakes**: Documenting decisions, expected outcomes, and lessons learned.
- **Behavioral Analytics**: Insights into the relationships between planning, execution, and outcomes.
- **In-App Notifications**: Proactive, deduplicated alerts for overdue tasks, exams, revisions, and habits.
- **Global Search**: Instant cross-entity search spanning 10 core LifeOS data models.
- **Personalized Recommendations**: Deterministic heuristic rules across productivity, study, and routines.
- **Data Sovereignty & Export**: Full self-service JSON and multi-table CSV / ZIP downloads.
- **PWA Readiness**: Offline static caching service worker and Web App Manifest.

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
│   ├── core/                   # System core, notifications, search, recommendations, export, preferences
│   │   └── services/           # notification_service, search_service, recommendation_service, export_service
│   ├── accounts/               # Custom user model, authentication, profile & sessions
│   ├── productivity/           # Category, Task, Habit, HabitLog, Activity, Routine, ScheduleBlock
│   ├── planning/               # Project, Goal, GoalTask
│   ├── personal/               # JournalEntry, Decision, DecisionOption, DecisionOutcome, Mistake, DailyMetric, SleepRecord
│   ├── finance/                # Transaction
│   ├── study/                  # Subject, Topic, StudySession, StudyPlan, Revision, Exam
│   └── analytics/              # Multi-domain analytics, correlation engine, charts & insights persistence
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

# Run automated test suite across all 8 applications (160 tests, 100% passing)
python manage.py test

# Or run specific modules
python manage.py test apps.productivity
python manage.py test apps.study
python manage.py test apps.personal
python manage.py test apps.finance
python manage.py test apps.analytics
python manage.py test apps.core.tests_step11
python manage.py test apps.core.tests_security
```

Expected output:
```
System check identified no issues (0 silenced).
Ran 160 tests in ~180s

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
- **Daily Timetable**: [http://127.0.0.1:8000/timetable/](http://127.0.0.1:8000/timetable/) (Chronological day timeline, date navigation, 4 KPI cards, block status actions, reschedule, manual block modal)
- **Weekly Timetable**: [http://127.0.0.1:8000/timetable/weekly/](http://127.0.0.1:8000/timetable/weekly/) (7-day Monday–Sunday visual calendar grid, today indicator, pending backlog sidebar)
- **Daily Routine Management**: [http://127.0.0.1:8000/routines/](http://127.0.0.1:8000/routines/) (Recurring fixed commitments, weekday filter pills, active toggles, overlap prevention)
- **Availability Management**: [http://127.0.0.1:8000/availability/](http://127.0.0.1:8000/availability/) (Productive time windows per weekday, weekly overview cards)
- **Smart Timetable Generator**: [http://127.0.0.1:8000/timetable/generator/](http://127.0.0.1:8000/timetable/generator/) (Deterministic rule-based scheduling simulation, study + task prioritization, rest break insertion, daily workload cap, unscheduled diagnostic reasons, apply confirmation)
- **Schedule History**: [http://127.0.0.1:8000/timetable/history/](http://127.0.0.1:8000/timetable/history/) (Audit log table of generator runs with metrics and unscheduled tags)
- **Scheduling Preferences**: [http://127.0.0.1:8000/timetable/preferences/](http://127.0.0.1:8000/timetable/preferences/) (Day bounds, continuous work threshold, break duration, buffer, daily fatigue cap)
- **Study Dashboard**: [http://127.0.0.1:8000/study/](http://127.0.0.1:8000/study/) (7 summary KPI metrics, active timer banner, today's planned sessions, upcoming exams, weekly study rhythm)
- **Subjects & Courses**: [http://127.0.0.1:8000/study/subjects/](http://127.0.0.1:8000/study/subjects/) (Course catalog, chapter grouping, progress bars, and cascade warnings)
- **Topics & Chapters**: [http://127.0.0.1:8000/study/topics/](http://127.0.0.1:8000/study/topics/) (Curriculum breakdown, duration tracking, priority, instant completion toggle)
- **Syllabus Tracker**: [http://127.0.0.1:8000/study/syllabus/](http://127.0.0.1:8000/study/syllabus/) (Subject mastery progress and behind-schedule alerts)
- **Study Planner**: [http://127.0.0.1:8000/study/planner/](http://127.0.0.1:8000/study/planner/) (Commitment scheduling with temporal tabs: Today, Upcoming, This Week, Past, All)
- **Study Sessions & Stopwatch**: [http://127.0.0.1:8000/study/sessions/](http://127.0.0.1:8000/study/sessions/) (Live stopwatch timer, auto-closing dangling sessions, focus ratings 1-10, manual logging)
- **Revision Planner**: [http://127.0.0.1:8000/study/revisions/](http://127.0.0.1:8000/study/revisions/) (Spaced revision iterations, overdue/today/upcoming groupings, quick reschedule)
- **Exams & Assessments**: [http://127.0.0.1:8000/study/exams/](http://127.0.0.1:8000/study/exams/) (Exam scheduling, deadline countdowns, score tracking)
- **Study Analytics**: [http://127.0.0.1:8000/study/analytics/](http://127.0.0.1:8000/study/analytics/) (14-day study rhythm bar chart, subject time share, syllabus velocity, plan adherence)
- **Task Management**: [http://127.0.0.1:8000/productivity/tasks/](http://127.0.0.1:8000/productivity/tasks/) or `/tasks/` (Full CRUD, filtering, sorting, pagination, search, duration tracking)
- **Category Management**: [http://127.0.0.1:8000/productivity/categories/](http://127.0.0.1:8000/productivity/categories/) (Color-coded categories with safe unlinking)
- **Habit Tracker**: [http://127.0.0.1:8000/productivity/habits/](http://127.0.0.1:8000/productivity/habits/) or `/habits/` (Daily/weekly streaks, 30-day matrix, pause/resume)
- **Activities & Time Tracking**: [http://127.0.0.1:8000/productivity/activities/](http://127.0.0.1:8000/productivity/activities/) or `/activities/` (Live stopwatch timer, duration aggregations, manual logs)
- **Goals & Milestones**: [http://127.0.0.1:8000/planning/goals/](http://127.0.0.1:8000/planning/goals/) or `/goals/` (Outcome tracking, target countdowns, task linkage & progress bars)
- **Projects**: [http://127.0.0.1:8000/planning/projects/](http://127.0.0.1:8000/planning/projects/) or `/projects/` (Initiatives portfolio, deliverable deadlines, child tasks)
- **Personal Dashboard**: [http://127.0.0.1:8000/personal/](http://127.0.0.1:8000/personal/) (8 summary KPI cards, recent journal entries, decisions, mistakes, daily check-in snapshot, 14-day mood chart, monthly spending overview)
- **Journal Management**: [http://127.0.0.1:8000/personal/journal/](http://127.0.0.1:8000/personal/journal/) or `/journal/` (Introspective daily reflections, full-text search, date filtering, detail reading view)
- **Daily Check-in**: [http://127.0.0.1:8000/personal/checkin/](http://127.0.0.1:8000/personal/checkin/) or `/checkin/` (Standardized 5-point scales for mood, energy, and stress, sleep hours, 14-day historical strip, duplicate-date auto-update)
- **Mood & Energy Analytics**: [http://127.0.0.1:8000/personal/mood-energy/](http://127.0.0.1:8000/personal/mood-energy/) (7d/14d/30d/90d filtering, mood bar chart, dual-bar energy vs stress comparison, 7d vs 30d averages, self-awareness disclaimer)
- **Sleep Tracker**: [http://127.0.0.1:8000/personal/sleep/](http://127.0.0.1:8000/personal/sleep/) (Bedtime and wake-up logging, automated midnight-crossing duration calculation, quality ratings 1-5, 14-day duration trend with 7.0-8.5h benchmark band, DailyMetric auto-sync)
- **Decision Journal**: [http://127.0.0.1:8000/personal/decisions/](http://127.0.0.1:8000/personal/decisions/) or `/decisions/` (Decision lifecycle Draft/Evaluating/Decided/Reviewed, candidate option comparison, chosen option selection, delayed outcome evaluations with 1-10 scores and reflections)
- **Mistake Tracker**: [http://127.0.0.1:8000/personal/mistakes/](http://127.0.0.1:8000/personal/mistakes/) or `/mistakes/` (Anti-pattern logging, root cause triggers, severity impact, status Open/In Progress/Resolved/Recurring, lessons learned, preventive action plans)
- **Finance Manager**: [http://127.0.0.1:8000/personal/finance/](http://127.0.0.1:8000/personal/finance/) or `/finance/` (Lifetime and monthly financial KPIs, net balance, cash flow comparison bar, category-wise spending breakdown, ledger transaction search/filter/sort, INR currency formatting)
- **User Profile & Settings**: [http://127.0.0.1:8000/accounts/profile/](http://127.0.0.1:8000/accounts/profile/) (Update full name, bio, timezone, and change password)
- **Main Executive Analytics Dashboard**: [http://127.0.0.1:8000/analytics/](http://127.0.0.1:8000/analytics/) (Central multi-domain overview of productivity, study, habits, well-being, time allocation, finances, and active behavioral insights)
- **Productivity Analytics**: [http://127.0.0.1:8000/analytics/productivity/](http://127.0.0.1:8000/analytics/productivity/) (Task throughput, completion velocity, duration estimation accuracy, under/overestimated task cohorts, and daily trend chart)
- **Study & Learning Analytics**: [http://127.0.0.1:8000/analytics/study/](http://127.0.0.1:8000/analytics/study/) (Study duration charts, subject time allocation, syllabus completion progress per subject, and plan adherence)
- **Habit Analytics**: [http://127.0.0.1:8000/analytics/habits/](http://127.0.0.1:8000/analytics/habits/) (Frequency-aware habit completion rates, consistency tiers, streak reporting, and active habit ledger)
- **Time Management Analytics**: [http://127.0.0.1:8000/analytics/time/](http://127.0.0.1:8000/analytics/time/) (Time distribution donut chart, timetable block execution adherence, and unscheduled task backlog)
- **Well-being & Biological Correlations**: [http://127.0.0.1:8000/analytics/wellbeing/](http://127.0.0.1:8000/analytics/wellbeing/) (Mood/energy/stress/sleep trend charts, Pearson correlations with N >= 14 data threshold, scatter plots, and medical disclaimer)
- **Behavioral Insights Engine**: [http://127.0.0.1:8000/analytics/insights/](http://127.0.0.1:8000/analytics/insights/) (Deterministic rule-based heuristics across all life domains with confidence ratings, supporting metrics, and dismiss/restore persistence)
- **Period Comparison System**: [http://127.0.0.1:8000/analytics/compare/](http://127.0.0.1:8000/analytics/compare/) (Multi-domain comparative delta scorecard comparing current vs. previous periods with zero-denominator safety)
- **Notifications Center**: [http://127.0.0.1:8000/notifications/](http://127.0.0.1:8000/notifications/) (In-app proactive alerts, overdue tasks, exam alerts, revision triggers, mark all read, deletion)
- **Global Search**: [http://127.0.0.1:8000/search/](http://127.0.0.1:8000/search/) (Cross-entity search spanning Tasks, Habits, Goals, Projects, Subjects, Topics, Journal, Decisions, Mistakes, Activities)
- **Personalized Recommendations**: [http://127.0.0.1:8000/recommendations/](http://127.0.0.1:8000/recommendations/) (Heuristic rule-based recommendations with rationales, metrics, actions, and dismissals)
- **Data Export & Privacy**: [http://127.0.0.1:8000/settings/export/](http://127.0.0.1:8000/settings/export/) (Self-service single JSON backup and multi-table CSV/ZIP archive download)
- **System Settings & Preferences**: [http://127.0.0.1:8000/settings/](http://127.0.0.1:8000/settings/) (User localization, 12h/24h time, week start day, daily work goals, notification toggles)
- **UI Design System Showcase**: [http://127.0.0.1:8000/ui-system/](http://127.0.0.1:8000/ui-system/) (Interactive 16-component catalog)
- **Health-Check API Endpoint**: [http://127.0.0.1:8000/health/](http://127.0.0.1:8000/health/) (Preserved from Step 01)

---

## 7. Cloud Deployment & Production Operations

LifeOS is fully production-hardened and pre-configured for instant deployment on cloud platforms:

- **WhiteNoise Static Delivery**: Automatic Gzip/Brotli compression and long-lived caching directly from Gunicorn (`whitenoise.middleware.WhiteNoiseMiddleware`).
- **Gunicorn WSGI Server**: 3 workers with 120-second timeout.
- **Docker & Compose**: Pre-packaged [`Dockerfile`](Dockerfile) and [`docker-compose.yml`](docker-compose.yml) with automatic health checks.
- **PaaS 1-Click Manifests**:
  - **Railway**: Configured via [`railway.toml`](railway.toml) and [`Procfile`](Procfile) with automatic MySQL attachment.
  - **Render**: Blueprint specification via [`render.yaml`](render.yaml).
- **Security Hardening**:
  - `DEBUG=False` production mode.
  - Automatic HTTPS redirect (`SECURE_SSL_REDIRECT = True`).
  - HSTS enabled with 1-year preload (`SECURE_HSTS_SECONDS = 31536000`).
  - Secure and HTTP-only session and CSRF cookies.
  - Frame protection (`X_FRAME_OPTIONS = 'DENY'`).
  - Custom branded error pages for 400, 403, 404, and 500 errors.

For complete, step-by-step production setup instructions across Railway, Render, Docker, and Ubuntu/Nginx, refer to [`DEPLOYMENT.md`](DEPLOYMENT.md).

