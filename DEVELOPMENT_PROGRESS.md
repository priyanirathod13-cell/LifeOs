# LifeOS — Development Progress Tracker

## Status Overview

| Step | Milestone | Status | Key Deliverables |
|:---:|---|:---:|---|
| **01** | **Project Foundation & Initial Setup** | **Completed** | Django project structure, `.env` config, MySQL database (`lifeos_db`), custom `User` model, health check (`GET /health/`), Git repository, initial migration. |
| **02** | **UI/UX & Design System** | **Completed** | Minimal modern dark design system, 16 reusable UI components, CSS variables, Inter typography, application layout (sidebar, header, content), responsive drawer, zero broken links, showcase demo at `/ui-system/`. |
| **03** | **Authentication System** | **Completed** | Public landing page, user registration with full name & email, case-insensitive unique email check, email authentication backend, login with Remember Me, secure logout, password reset flow via console email, user profile management with password change, strict `@login_required` access control, 25 automated tests. |
| **04** | **Database Architecture & Data Models** | **Completed** | Normalized 3NF models across 5 apps (`productivity`, `planning`, `personal`, `finance`, `study`), 21 models total, check constraints, composite unique keys, multi-user isolation validation, admin registrations, legacy data preservation migration, 45 automated tests (100% passing). |
| **05** | **Main Dashboard Implementation** | **Completed** | Dynamic authenticated dashboard at `/dashboard/`, live data aggregation across 6 domain apps, 4 summary metric cards, interactive task toggle, habit completion toggle, quick add task modal, quick biometric check-in modal, upcoming exams, schedule blocks, recent activity feed, 59 automated tests (100% passing). |
| **06** | **Productivity Management** | **Completed** | Full Productivity Management system across 6 sub-modules: Tasks (CRUD, multi-filter, sort, search, pagination, duration tracking), Categories (color-coded, duplicate prevention, safe unlinking), Habits (CRUD, pause/active toggle, 30-day matrix, daily/weekly streak engine), Activities (manual logging, live start/stop timer, duration aggregation), Goals (CRUD, target countdowns, task linkage, progress calculation), Projects (CRUD, child tasks, completion progress), 79 automated tests (100% passing). |
| **07** | **Study Management & Syllabi** | **Completed** | Full multi-user Study Management module across 9 functional domains: Subjects (CRUD, chapter grouping, cascade warnings), Topics (chapter units, priority, completion toggle), Syllabus Tracker (dynamic progress bars, behind-schedule alerts), Study Planner (commitments, temporal tabs, status transitions), Study Sessions (live stopwatch timer, auto-closing dangling sessions, manual logs), Revision Planner (spaced revision iterations, quick reschedule), Exams & Assessments (deadlines, countdowns, score tracking), Study Analytics (14-day rhythm chart, subject time share, syllabus velocity, plan adherence), 19 study tests, 94 total system tests (100% passing). |
| **08** | **Timetable & Daily Scheduling** | **Completed** | Smart Routine & Timetable Generator across 7 core functional areas: Daily Timetable (chronological timeline, date navigation, status actions, reschedule, KPI cards), Weekly Timetable (7-day calendar overview, backlog sidebar), Routine Management (recurring commitments, weekday filtering, overlap prevention), Availability Management (productive windows per weekday), Smart Generator Engine (deterministic rule-based scheduling, study + task prioritization, break insertion, workload cap, unscheduled item diagnostics), Generation History (audit logs with metrics and unscheduled reasons), Scheduling Preferences (customizable work bounds, break lengths, buffers, fatigue limit), 31 productivity tests, 108 total system tests (100% passing). |
| **09** | **Personal Management Module** | **Completed** | Full Personal Management module across 8 functional areas: Personal Dashboard (8 summary KPI cards, recent journal/decisions/mistakes streams, 14-day mood trend, spending share), Journal (CRUD, date filters, search, newest/oldest sorting), Daily Check-in (standardized 1-5 scales, duplicate date prevention, 14-day history strip), Mood & Energy Tracking (7d/14d/30d/90d ranges, mood bar chart, energy vs stress comparison), Sleep Tracking (bedtime and wake-up timestamps, overnight duration calculation, 7.0–8.5h benchmark band, DailyMetric sync), Decision Journal (DRAFT/EVALUATING/DECIDED/REVIEWED lifecycle, options analysis, post-mortem outcome scoring), Mistake Tracker (anti-pattern logs, root causes, severity impacts, corrective protocols), Finance Manager (positive decimal transactions in ₹ INR, lifetime & monthly net balance/savings, category breakdowns, ledger search/filters), 22 tests in personal & finance, 123 total system tests (100% passing). |

---

## Detailed Step 03 Deliverables

### Public Landing Page
- **Route**: `GET /` (`core:landing`)
- **Headline**: "Your Personal Behavioral Intelligence System."
- **Components**: Brand mark, hero presentation, dashboard preview card mockup, 6 core feature pillars (Tasks & Timetable, Habits & Routines, Study Management, Mood/Sleep/Energy, Decisions/Mistakes, Behavioral Correlations), call-to-action banner, and footer.
- **Dynamic Routing**: Authenticated users visiting `/` are automatically redirected to their private `/dashboard/`.

### Registration Architecture
- **Route**: `GET/POST /accounts/register/` (`accounts:register`)
- **Required Fields**: Full name, email address, password, confirm password.
- **Validation**:
  - Required fields and email format validation.
  - Case-insensitive duplicate email prevention at both database (`UNIQUE`) and form levels.
  - Django password strength validator integration (`validate_password`).
  - Password mismatch verification.
- **Storage**: Passwords hashed securely using PBKDF2/SHA256. Creates user in MySQL and redirects to login with success flash message.

### Login & Session Security
- **Route**: `GET/POST /accounts/login/` (`accounts:login`)
- **Backend**: `EmailAuthBackend` (`apps.accounts.backends.EmailAuthBackend`) supporting case-insensitive email lookup with timing-attack mitigation.
- **Security Features**:
  - Generic error messages for bad credentials ("Invalid email address or password") preventing email enumeration.
  - "Remember Me" toggle: 14-day persistent cookie (`session.set_expiry(1209600)`) vs. session-only cookie (`session.set_expiry(0)` expiring on browser close).
  - Open-redirect protection via `url_has_allowed_host_and_scheme` when handling `?next=`.

### Logout System
- **Route**: `POST /accounts/logout/` (`accounts:logout`)
- **Behavior**: Ends authenticated session, flushes session state, and redirects to landing page with confirmation flash message.

### Password Reset Workflow
- **Views & Routes**:
  - `accounts:password_reset` (`/accounts/password-reset/`): Enter registered email.
  - `accounts:password_reset_done` (`/accounts/password-reset/done/`): Confirmation notice.
  - `accounts:password_reset_confirm` (`/accounts/password-reset-confirm/<uidb64>/<token>/`): Set and confirm new password with one-time cryptographic token.
  - `accounts:password_reset_complete` (`/accounts/password-reset-complete/`): Success page with sign-in link.
- **Development Delivery**: Console email backend (`django.core.mail.backends.console.EmailBackend`).

### User Profile Management
- **Route**: `GET/POST /accounts/profile/` (`accounts:profile`)
- **Display**: Full name, email, creation date, role badge, timezone, and personal philosophy.
- **Actions**:
  - Update full name, personal philosophy/bio, and primary timezone.
  - Change master password with current password verification and `update_session_auth_hash` session preservation.
  - Strict user isolation: operates strictly on `request.user`.

### Access Control Verification
- All internal application routes (`/dashboard/`, `/timetable/`, `/tasks/`, `/habits/`, `/study/`, `/projects/`, `/journal/`, etc.) enforce `@login_required`.
- Unauthenticated requests are redirected to `/accounts/login/?next=<path>`.


---

## Detailed Step 04 Deliverables

### Data Models & Domain Architecture
- **6 Domain Applications**:
  - `apps.accounts`: Custom `User` model (`accounts_user`).
  - `apps.productivity`: `Category`, `Task`, `Habit`, `HabitLog`, `Activity`, `Routine`, `ScheduleBlock`.
  - `apps.planning`: `Project`, `Goal`, `GoalTask`.
  - `apps.personal`: `JournalEntry`, `Decision`, `DecisionOption`, `DecisionOutcome`, `Mistake`, `DailyMetric`.
  - `apps.finance`: `Transaction`.
  - `apps.study`: `Subject`, `Topic`, `StudySession`, `Exam`.
- **Database Normalization (3NF)**:
  - Atomic attribute storage, elimination of partial and transitive dependencies.
  - Calculated duration values (`Activity.duration_minutes`) computed on-the-fly rather than duplicating derived data in columns.
  - Check constraints for scores (`1 <= score <= 10`), sleep hours (`0 <= sleep <= 24`), and strictly positive monetary transactions (`amount > 0`).

### Multi-User Data Isolation
- Direct user ownership foreign keys (`on_delete=models.CASCADE`).
- Composite unique constraints scoped to tenant (`['user', 'name']`, `['user', 'metric_date']`, `['user', 'subject_name']`).
- Application-level verification in model `clean()` preventing cross-user foreign key leakage (e.g. assigning another user's Category or Project).
- High-cardinality composite indexes prefixed with `user_id` for efficient multi-tenant query execution.

### Admin Interface
- Registered all 21 models across all domain apps with customized `ModelAdmin` implementations including `list_display`, `list_filter`, `search_fields`, and computed display properties.

### Legacy Data Migration & Preservation
- Custom management command `python manage.py import_legacy_data` safely imported legacy data from legacy database `lifeos` into active database `lifeos_db` without data loss:
  - 3 Users (`aarav_student`, `sharma_teacher`, `rathod_parent`)
  - 5 Categories (`Engineering & Code`, `Health & Fitness`, `Studies & DBMS`, `Food & Living`, `Freelance & Salary`)
  - 5 Tasks (including priorities, estimates, due dates)
  - 3 Habits & 2 Habit Logs
  - 1 Goal & 3 Goal-Task junction links
  - 1 Daily Metric record (mood 9, energy 8, stress 3, sleep 7.50h)
- 100% idempotent verification: zero duplicate records on repeated runs.

### Automated Test Suite
- Comprehensive unit test suite across all 7 applications (`apps.accounts`, `apps.core`, `apps.productivity`, `apps.planning`, `apps.personal`, `apps.finance`, `apps.study`):
  - 45 automated tests verifying data isolation, unique constraints, check constraints, date validations, and authentication security.
  - 100% pass rate (`Ran 45 tests in 35.984s — OK`).


---

## Detailed Step 05 Deliverables

### Live Authenticated Dashboard (`/dashboard/`)
- **Central Control Panel**:
  - Personalized time-adaptive greeting ("Good morning", "Good afternoon", "Good evening") with user's display name and current date formatted.
  - Contextual motivation line: "Here's your behavioral overview and execution priorities for today."
- **4 Key Performance Summary Cards**:
  - **Today's Tasks**: Total tasks due today (or overdue/pending), completed today, pending tasks, completion percentage with dynamic progress bar.
  - **Daily Habits**: Active habits count, today's completed habit logs count, remaining habits, completion percentage with success progress bar.
  - **Study Duration**: Total study time today (`Xh Ym` / `X mins`), completed study sessions count, distinct subjects studied.
  - **Active Goals**: Active goals count, approaching target dates within 30 days, progress status tracking.
- **Today's Tasks Section**:
  - Real user-scoped tasks prioritizing urgent/high priority and overdue items.
  - Category color pills, estimated minutes, due dates.
  - Overdue status badge (`badge-danger`) for past due items.
  - Quick action checkbox/toggle button with secure CSRF-protected POST handler.
  - Empty state with "+ Add Task" call-to-action.
- **Daily Habit Consistency Section**:
  - Active habits scheduled for the day.
  - Dynamic completion indicator showing whether a habit has been logged today.
  - Quick action toggle to mark habit completed/incomplete directly from the dashboard.
  - Empty state with "Configure Habits" call-to-action.
- **Academic & Study Overview Section**:
  - Today's study time card with "+ Log Study Session" button.
  - Upcoming milestone exams within the next 30 days with days remaining calculation.
  - Friendly empty state: "Your study journey starts here."
- **Daily State & Biometrics Section**:
  - Displays today's recorded `DailyMetric`: Mood (1-10), Energy (1-10), Stress (1-10), Sleep hours (0-24), and cognitive reflections.
  - "Record Daily Check-in" quick action modal.
- **Schedule Blocks Section**:
  - Today's scheduled commitments in chronological order.
  - Temporal state badges: "Active Now", "Upcoming", "Done", "Past".
- **Strategic Goals Section**:
  - Active goals with target dates, days remaining, and progress bar derived from completed linked `GoalTask` records.
- **Recent Activity Feed**:
  - Unified chronological stream of recent completed tasks, logged habits, study sessions, and journal reflections strictly for the authenticated user.
- **Quick Actions & Modals**:
  - `POST /dashboard/toggle-task/<id>/`: Toggles task between `COMPLETED` and `PENDING`, updates `completed_at`, enforces user ownership (IDOR protected).
  - `POST /dashboard/toggle-habit/<id>/`: Toggles `HabitLog` for today, enforces user ownership.
  - `POST /dashboard/quick-add-task/`: Creates a new task with title, priority, due date, category, and estimated minutes.
  - `POST /dashboard/quick-checkin/`: Creates or updates today's `DailyMetric` with score clamping.
- **Automated Test Suite**:
  - 59 automated tests across all 7 applications (`apps.accounts`, `apps.core`, `apps.productivity`, `apps.planning`, `apps.personal`, `apps.finance`, `apps.study`).
  - 100% pass rate (`Ran 59 tests in 53.717s — OK`).


---

## Detailed Step 06 Deliverables: Productivity Management

### 1. Task Management (`apps/productivity/`)
- **Views & Endpoints**:
  - `productivity:task_list` (`GET /productivity/tasks/` or `/tasks/`): Search by title/description, filter by status (`pending`, `in_progress`, `completed`, `cancelled`), priority (`low`, `medium`, `high`, `urgent`), category, due date presets (`today`, `week`, `overdue`), sort by due date / priority / creation date, paginated with 15 tasks per page.
  - `productivity:task_create` (`GET/POST /productivity/tasks/create/`): Validates user-scoped categories and projects; auto-sets `completed_at` if created directly in completed state.
  - `productivity:task_detail` (`GET /productivity/tasks/<id>/`): Shows full description, priority badges, category color chips, estimated vs. actual minutes, project association, and aligned goals.
  - `productivity:task_update` (`GET/POST /productivity/tasks/<id>/edit/`): Update all task attributes with IDOR protection.
  - `productivity:task_delete` (`GET/POST /productivity/tasks/<id>/delete/`): Confirmation dialog with safe deletion.
  - `productivity:task_toggle_complete` (`POST /productivity/tasks/<id>/toggle/`): Quick toggle between pending and completed; automatically stamps `completed_at` timestamps.

### 2. Category Management (`apps/productivity/`)
- **Views & Endpoints**:
  - `productivity:category_list` (`GET /productivity/categories/`): Lists user categories with assigned color preview chips, classification badges, and live counts of associated records.
  - `productivity:category_create` (`GET/POST /productivity/categories/create/`): Enforces case-insensitive duplicate prevention per user.
  - `productivity:category_update` (`GET/POST /productivity/categories/<id>/edit/`): Edit category name, color, and description.
  - `productivity:category_delete` (`GET/POST /productivity/categories/<id>/delete/`): Safe deletion pattern — informs user of associated record counts and sets foreign keys to `NULL` (`on_delete=models.SET_NULL`), ensuring zero cascade destruction of user tasks, habits, or activities.

### 3. Habit Management (`apps/productivity/`)
- **Views & Endpoints**:
  - `productivity:habit_list` (`GET /productivity/habits/` or `/habits/`): Grid of active and paused habits with current streak counters, frequency tags, target counts, and today's execution toggles.
  - `productivity:habit_create` (`GET/POST /productivity/habits/create/`): Configure title, routine cue notes, frequency (Daily or Weekly), and target completions.
  - `productivity:habit_detail` (`GET /productivity/habits/<id>/`): 30-day historical execution matrix showing daily completed/missed cells, total completions, and current consecutive streak.
  - `productivity:habit_log` (`POST /productivity/habits/<id>/log/`): Logs completion for any specified date (defaulting to today), preventing duplicate logs on the same day through `update_or_create`.
  - `productivity:habit_toggle_active` (`POST /productivity/habits/<id>/toggle-active/`): Pause or resume habit routines without deleting history.

### 4. Activity & Time Tracking (`apps/productivity/`)
- **Views & Endpoints**:
  - `productivity:activity_list` (`GET /productivity/activities/` or `/activities/`): Real-time timer interface displaying active session counter, today's aggregated time, past 7 days duration, category breakdown, and chronological logs.
  - `productivity:activity_start` (`POST /productivity/activities/start/`): Starts a live timer session, automatically closing and finalizing any previously dangling active session.
  - `productivity:activity_stop` (`POST /productivity/activities/<id>/stop/`): Finalizes the live timer, calculating and persisting exact `duration_minutes`.
  - `productivity:activity_create` (`GET/POST /productivity/activities/create/`): Manual backfill for past sessions with datetime-local validation preventing `end_time < start_time`.
  - `productivity:activity_delete` (`GET/POST /productivity/activities/<id>/delete/`): Deletes activity session with confirmation.

### 5. Goal Management (`apps/planning/`)
- **Views & Endpoints**:
  - `planning:goal_list` (`GET /planning/goals/` or `/goals/`): Strategic milestone list with countdown badges ("X days left" or "Overdue by Y days"), priority badges, category chips, and live task-progress indicators.
  - `planning:goal_create` (`GET/POST /planning/goals/create/`): Define outcome statements, target deadlines, priority, and categories.
  - `planning:goal_detail` (`GET /planning/goals/<id>/`): Displays outcome scope, countdown, execution progress bar (`completed/total*100`), form to link existing user tasks (`GoalTaskLinkForm`), and table of currently linked tasks with unlinking actions.
  - `planning:goal_link_task` (`POST /planning/goals/<id>/link-task/`): Links an existing user task to the goal; strictly prevents cross-user task linking.
  - `planning:goal_unlink_task` (`POST /planning/goals/<id>/unlink-task/<task_id>/`): Unlinks task from goal without deleting the underlying task.
  - `planning:goal_delete` (`GET/POST /planning/goals/<id>/delete/`): Deletes goal while explicitly keeping all linked tasks intact.

### 6. Project Management (`apps/planning/`)
- **Views & Endpoints**:
  - `planning:project_list` (`GET /planning/projects/` or `/projects/`): High-level project portfolio cards with status tags (`Planning`, `In Progress`, `On Hold`, `Completed`, `Cancelled`), target dates, priority levels, and child task progress bars.
  - `planning:project_create` (`GET/POST /planning/projects/create/`): Create new project initiatives.
  - `planning:project_detail` (`GET /planning/projects/<id>/`): View project deliverables, milestone deadlines, completion rate, and full child task list with links to view details.
  - `planning:project_update` (`GET/POST /planning/projects/<id>/edit/`): Update project scope, status, dates; auto-sets `completed_at` on completion.
  - `planning:project_delete` (`GET/POST /planning/projects/<id>/delete/`): Deletes project safely unlinking child tasks (`Task.project = None`) without deleting tasks.

### Automated Test Suite
- **79 Automated Tests** across the entire application:
  - 29 tests in `apps.productivity` and `apps.planning` covering CRUD, filtering, pagination, search, validation, timer mechanics, streak computation, and strict multi-user cross-boundary IDOR protection.
  - 100% pass rate (`Ran 79 tests in 53.175s — OK`).

---

## Detailed Step 07 Deliverables (Study Management Module)

### 1. Study Dashboard (`apps/study/`)
- **Routes**: `GET /study/`, `GET /study/dashboard/`, alias `GET /core/study/`
- **Deliverables**:
  - 7 summary KPI metric cards: Total Study Time, Today's Study Time, Active Subjects, Total Topics, Completed Topics, Overall Syllabus %, Upcoming Exams.
  - Active Timer Banner: Displays live study timer countdown and quick stop/discard actions when a session is in progress.
  - Quick-start study session launch form.
  - Today's planned study tasks with instant status updates.
  - Upcoming exams cards with deadline countdown badges.
  - Incomplete syllabus subject progress bars.
  - Recent study sessions log.
  - 7-day study rhythm mini bar chart.

### 2. Subjects & Courses Management
- **Routes**:
  - `study:subject_list` (`GET /study/subjects/`): Filterable by status (`ACTIVE`, `COMPLETED`, `ARCHIVED`), subject type, color coding, search, and sorting.
  - `study:subject_create` (`GET/POST /study/subjects/create/`): Create new subjects with unique constraint enforcement per user.
  - `study:subject_detail` (`GET /study/subjects/<pk>/`): Deep inspection view displaying chapter-grouped topics, scheduled exams, logged study sessions, and progress metrics.
  - `study:subject_update` (`GET/POST /study/subjects/<pk>/edit/`): Update subject metadata and target dates.
  - `study:subject_delete` (`GET/POST /study/subjects/<pk>/delete/`): Safe deletion dialog displaying cascade deletion warnings for child topics and study sessions.

### 3. Topics & Chapters Management
- **Routes**:
  - `study:topic_list` (`GET /study/topics/`): Full curriculum topics filterable by subject, chapter, completion status, and priority.
  - `study:topic_create` (`GET/POST /study/topics/create/`): Add new topics under a subject with chapter grouping.
  - `study:topic_update` (`GET/POST /study/topics/<pk>/edit/`): Edit title, description, chapter, duration estimates, and notes.
  - `study:topic_delete` (`GET/POST /study/topics/<pk>/delete/`): Delete topic with confirmation.
  - `study:topic_toggle` (`POST /study/topics/<pk>/toggle/`): Quick toggle between completed and pending with auto-date stamping.

### 4. Syllabus Tracker
- **Route**: `GET /study/syllabus/`
- **Deliverables**:
  - Subject-by-subject curriculum completion cards (`completed / total * 100`).
  - Behind-schedule alerts highlighting active subjects with `target_date < today and completion < 100%`.
  - Chapter and topic breakdown with priority indicators and direct toggle actions.

### 5. Study Planner
- **Routes**:
  - `study:planner` (`GET /study/planner/`): Temporal views (`Today`, `Upcoming`, `This Week`, `Past`, `All`) with planned date filtering.
  - `study:planner_create` (`GET/POST /study/planner/create/`): Schedule future study commitments (subject, optional topic, date, time slot, estimated minutes, priority).
  - `study:planner_update` (`GET/POST /study/planner/<pk>/edit/`): Update planned session parameters.
  - `study:planner_delete` (`GET/POST /study/planner/<pk>/delete/`): Remove plan with confirmation.
  - `study:planner_status` (`POST /study/planner/<pk>/status/`): Action endpoint transitioning plan status between `PLANNED`, `COMPLETED`, `SKIPPED`, and `RESCHEDULED`.

### 6. Study Sessions & Time Tracking
- **Routes**:
  - `study:sessions` (`GET /study/sessions/`): Central study tracker featuring real-time stopwatch, active session indicator, duration statistics, and historical logs.
  - `study:session_start` (`POST /study/sessions/start/`): Start live stopwatch timer; auto-closes any previously running active session to prevent dangling open timers.
  - `study:session_stop` (`POST /study/sessions/<pk>/stop/`): Stop timer, calculate elapsed duration in minutes, and optionally record focus rating (1–10) and notes.
  - `study:session_create` (`GET/POST /study/sessions/create/`): Manual historical session logging with start/end time duration calculation.
  - `study:session_update` (`GET/POST /study/sessions/<pk>/edit/`): Edit recorded session details.
  - `study:session_delete` (`GET/POST /study/sessions/<pk>/delete/`): Delete session entry with confirmation.

### 7. Revision Planner
- **Routes**:
  - `study:revisions` (`GET /study/revisions/`): Spaced revision tracking organized into four temporal sections: Overdue, Today, Upcoming, and Completed.
  - `study:revision_create` (`GET/POST /study/revisions/create/`): Schedule revision with auto-incrementing iteration numbers (`Revision #1`, `#2`, etc.).
  - `study:revision_toggle` (`POST /study/revisions/<pk>/toggle/`): Toggle completion status with timestamping.
  - `study:revision_reschedule` (`POST /study/revisions/<pk>/reschedule/`): Quick date reschedule via POST.
  - `study:revision_delete` (`GET/POST /study/revisions/<pk>/delete/`): Delete scheduled revision.

### 8. Exams & Assessments
- **Routes**:
  - `study:exams` (`GET /study/exams/`): Examination management with countdown badges ("X days left", "Due Today!", "Y days overdue") and historical score outcomes.
  - `study:exam_create` (`GET/POST /study/exams/create/`): Schedule exam with date, type, weightage, and max score.
  - `study:exam_update` (`GET/POST /study/exams/<pk>/edit/`): Update exam details or record achieved score with validation ensuring `score <= max_score`.
  - `study:exam_delete` (`GET/POST /study/exams/<pk>/delete/`): Delete exam with confirmation dialog.

### 9. Study Analytics
- **Routes**: `GET /study/analytics/`, alias `GET /core/study-analytics/`
- **Deliverables**:
  - 4 KPI summary cards: 14-Day Study Volume, Daily Average, 14-Day Consistency Score, 30-Day Plan Adherence.
  - 14-Day Study Rhythm: Daily CSS bar chart with duration tags and day labels.
  - Time Invested by Subject: Proportional stacked bar and breakdown table with percentage shares and color identifiers.
  - Syllabus Completion Velocity: Progress comparisons across all enrolled subjects.
  - Plan vs. Actual Adherence: Execution rate comparison between scheduled study commitments and logged actual sessions.

### Automated Test Suite
- **94 Automated Tests** across the entire application:
  - 19 dedicated tests in `apps.study` verifying models, calculations, views, timer workflows, validation rules, and multi-user IDOR isolation.
  - 100% pass rate (`Ran 94 tests in 93.364s — OK`).

---

## Detailed Step 08 Deliverables

### 1. Daily Timetable
- **Routes**:
  - `productivity:daily_timetable` (`GET /timetable/`): Chronological day schedule, date navigation (`?date=YYYY-MM-DD`), 4 KPI summary cards (Total Scheduled, Completed Tasks, Free Gaps, Work Volume), timeline visualizer with distinct styling for routines, tasks, study sessions, and breaks.
  - `productivity:schedule_block_create` (`GET/POST /timetable/blocks/create/`): Manual creation of schedule blocks with user-scoped foreign keys.
  - `productivity:schedule_block_update` (`GET/POST /timetable/blocks/<pk>/edit/`): Edit existing block details and time intervals.
  - `productivity:schedule_block_delete` (`GET/POST /timetable/blocks/<pk>/delete/`): Safe block deletion with confirmation dialog.
  - `productivity:schedule_block_status` (`POST /timetable/blocks/<pk>/status/`): Inline status transition (`SCHEDULED`, `COMPLETED`, `SKIPPED`).
  - `productivity:schedule_block_reschedule` (`GET/POST /timetable/blocks/<pk>/reschedule/`): Move block to a new date with optional auto-fit slot calculation.

### 2. Weekly Timetable
- **Route**: `productivity:weekly_timetable` (`GET /timetable/weekly/`)
- **Features**:
  - 7-day Monday through Sunday responsive visual schedule grid.
  - Date navigation (`?week_start=YYYY-MM-DD`), Jump to Today action.
  - Current day visual highlight and start/end time markers.
  - Clear visual distinction between fixed routines/commitments and flexible work blocks.
  - Pending backlog sidebar displaying unscheduled high-priority tasks with quick links.

### 3. Daily Routine Management
- **Routes**:
  - `productivity:routines` (`GET /routines/`): Regular commitments management (e.g. Morning Routine, College Lectures, Office Work, Meals, Sleep) with weekday filter pills (`ALL`, `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`, `SUN`).
  - `productivity:routine_create` (`GET/POST /routines/create/`): Create recurring routine with multi-weekday selection pills, routine type, and time bounds.
  - `productivity:routine_update` (`GET/POST /routines/<pk>/edit/`): Update routine properties, schedule, and weekday assignments.
  - `productivity:routine_delete` (`GET/POST /routines/<pk>/delete/`): Delete routine with cascade safety.
  - `productivity:routine_toggle_active` (`POST /routines/<pk>/toggle-active/`): One-click enable/disable toggle.
- **Validation**:
  - Start time must precede end time for single-day commitments.
  - Overlapping routine prevention across shared weekdays (`clean()`).
  - Optional date boundary enforcement (`start_date <= end_date`).

### 4. Availability Management
- **Routes**:
  - `productivity:availability` (`GET /availability/`): Weekly productivity availability configuration with daily breakdown cards (Mon–Sun), window counts, and total available work hours.
  - `productivity:availability_create` (`POST /availability/create/`): Add new availability window for a specified weekday.
  - `productivity:availability_delete` (`POST /availability/<pk>/delete/`): Delete availability window.
- **Validation**:
  - Non-overlapping time window validation on same weekday.
  - Single-day start/end time consistency.

### 5. Smart Timetable Generator
- **Routes**:
  - `productivity:schedule_generator` (`GET /timetable/generator/`): Date selection, rule explanation chips, preview generation simulation, 4 preview KPI cards (Work Time, Tasks Scheduled, Study Plans, Free Buffer), detailed proposed schedule timeline, unscheduled items banner with structured reasons, and conflict warnings.
  - `productivity:schedule_generator_apply` (`POST /timetable/generator/apply/`): Atomic persistence of generated blocks into `ScheduleBlock`, with option to replace existing flexible blocks while strictly preserving completed blocks and fixed commitments. Records audit log in `ScheduleGenerationHistory`.
- **Engine Rules (`apps.productivity.services.generator.TimetableGenerator`)**:
  - Multi-tier candidate priority: Study commitments (`StudyPlan`) prioritized by high/urgent priority, followed by pending tasks (`Task`) sorted by deadline urgency, priority score, and duration.
  - Free slot discovery: Available windows minus fixed routines and existing non-replaceable blocks.
  - Automatic rest break insertion after continuous work exceeding `max_continuous_work_minutes`.
  - Spacing buffer insertion between adjacent work blocks.
  - Daily workload ceiling enforcement (`max_daily_work_minutes`).
  - Granular unscheduled diagnostics with explicit reasons (e.g., slot deficiency, daily cap).

### 6. Schedule Generation History
- **Route**: `productivity:schedule_history` (`GET /timetable/history/`)
- **Features**: Audit log table of previous generation runs, execution metrics (generation date, timestamp, total work minutes, tasks scheduled, study blocks, routines), and expandable unscheduled diagnostics.

### 7. Scheduling Preferences
- **Route**: `productivity:scheduling_preferences` (`GET/POST /timetable/preferences/`)
- **Features**: User-specific scheduling settings form: Day start time, Day end time, Default break minutes (5–60 min), Continuous work limit (30–240 min), Spacing buffer (0–30 min), Automatic break insertion toggle, Maximum daily work minutes (60–960 min).

### Automated Test Suite
- **108 Automated Tests** across the entire application:
  - 31 dedicated tests in `apps.productivity` verifying models, validation rules, availability services, collision detection, timetable generator engine, rescheduling, views, and multi-user IDOR isolation.
  - 100% pass rate (`Ran 108 tests in 106.975s — OK`).

---

## Detailed Step 09 Deliverables

### 1. Personal Dashboard
- **Route**: `personal:dashboard` (`GET /personal/`)
- **Features**:
  - 8 Summary KPI Cards: Journal This Month, Avg Mood (Month), Avg Energy (Month), Avg Sleep Duration (Month), Decisions Recorded (Total & Pending), Monthly Income, Monthly Expenses, Monthly Net Balance / Savings.
  - Recent Streams: Last 3 journal entries with snippets, last 3 decisions with status badges, last 3 mistakes with lessons learned, and latest daily check-in snapshot.
  - Visual Rhythm: 14-day daily mood bar chart (1 to 5 scale with color indicators).
  - Monthly Spending Distribution: Category share progress bars and amounts.

### 2. Journal Management
- **Routes**:
  - `personal:journal_list` (`GET /personal/journal/`): Searchable, date-filterable, sortable (newest/oldest) journal catalog.
  - `personal:journal_create` (`GET/POST /personal/journal/create/`): Form for new reflections with title, date, mood tag, and comfortable textarea.
  - `personal:journal_detail` (`GET /personal/journal/<pk>/`): Full reading interface with formatted paragraphs.
  - `personal:journal_edit` (`GET/POST /personal/journal/<pk>/edit/`): Edit existing entry.
  - `personal:journal_delete` (`GET/POST /personal/journal/<pk>/delete/`): Safe delete with confirmation dialog.

### 3. Daily Check-in
- **Route**: `personal:checkin` (`GET/POST /personal/checkin/`)
- **Features**:
  - Standardized 5-point rating scales with explicit explanations:
    - Mood: 1 (Very Bad) to 5 (Excellent).
    - Energy: 1 (Very Low / Depleted) to 5 (Very High / Vibrant).
    - Stress: 1 (Very Low / Relaxed) to 5 (Very High / Overwhelmed).
  - Sleep duration input (hours, step 0.25).
  - Freeform somatic and daily notes.
  - Duplicate date prevention: automatically updates existing entry for the user and target date without duplicate key collisions.
  - Interactive date selector and 14-day history strip.

### 4. Mood & Energy Tracking
- **Route**: `personal:mood_energy` (`GET /personal/mood-energy/`)
- **Features**:
  - Date range filters: 7 Days, 14 Days, 30 Days, 90 Days.
  - Averages: 7-day vs 30-day mood and energy comparison, stress index.
  - Visualizations: Daily Mood History bar chart (1–5) and dual-bar Energy (Indigo) vs Stress (Rose) daily comparison.
  - Dense history data table with quick edit links.
  - Non-diagnostic behavioral self-awareness disclaimer notice.

### 5. Sleep Tracking
- **Routes**:
  - `personal:sleep_list` (`GET /personal/sleep/`): Log history, 7-day and 30-day sleep duration averages, average sleep quality rating, and total nights recorded.
  - `personal:sleep_create` (`GET/POST /personal/sleep/create/`): Record bedtime and wake time with automatic duration calculation (supporting overnight sessions crossing midnight), quality rating (1–5), notes, and automatic synchronization with `DailyMetric.sleep_hours`.
  - `personal:sleep_edit` (`GET/POST /personal/sleep/<pk>/edit/`): Edit sleep record and re-sync `DailyMetric`.
  - `personal:sleep_delete` (`GET/POST /personal/sleep/<pk>/delete/`): Safe delete with confirmation.
  - Visualization: 14-day sleep duration bar chart with an optimal sleep target band (7.0h to 8.5h).

### 6. Decision Journal
- **Routes**:
  - `personal:decision_list` (`GET /personal/decisions/`): Decision catalog with status filters (`ALL`, `DRAFT`, `EVALUATING`, `DECIDED`, `REVIEWED`), search, and 4 KPI counters.
  - `personal:decision_create` (`GET/POST /personal/decisions/create/`): Record decision title, context, date, status, category, and rationale.
  - `personal:decision_detail` (`GET /personal/decisions/<pk>/`): Comprehensive view of decision context, candidate options, chosen option, and post-mortem outcome.
  - `personal:decision_edit` (`GET/POST /personal/decisions/<pk>/edit/`): Update decision context.
  - `personal:decision_delete` (`GET/POST /personal/decisions/<pk>/delete/`): Delete decision and cascade child options/outcomes.
  - `personal:decision_option_add` (`GET/POST /personal/decisions/<pk>/options/add/`): Add candidate pathways with pros, cons, and expected outcomes.
  - `personal:decision_option_edit` (`GET/POST /personal/decisions/<pk>/options/<opt_pk>/edit/`): Edit option details.
  - `personal:decision_option_delete` (`GET/POST /personal/decisions/<pk>/options/<opt_pk>/delete/`): Delete option.
  - `personal:decision_select_option` (`POST /personal/decisions/<pk>/options/<opt_pk>/select/`): Select chosen pathway, advancing status to `DECIDED`.
  - `personal:decision_outcome` (`GET/POST /personal/decisions/<pk>/outcome/`): Record post-mortem evaluation with outcome score (1–10), actual outcome, lessons learned, and reflection notes, advancing status to `REVIEWED`.

### 7. Mistake Tracker
- **Routes**:
  - `personal:mistake_list` (`GET /personal/mistakes/`): Learning log catalog with impact filters (`MINOR`, `MODERATE`, `SEVERE`), status filters (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `RECURRING`), category filter, and search.
  - `personal:mistake_create` (`GET/POST /personal/mistakes/create/`): Log error, factual description, root cause triggers, lesson learned, and corrective action protocol.
  - `personal:mistake_detail` (`GET /personal/mistakes/<pk>/`): Full view of mistake reflection and preventive guardrails.
  - `personal:mistake_edit` (`GET/POST /personal/mistakes/<pk>/edit/`): Update mistake record.
  - `personal:mistake_delete` (`GET/POST /personal/mistakes/<pk>/delete/`): Safe delete with confirmation.

### 8. Finance Manager
- **Routes**:
  - `personal:finance` / `finance:dashboard` (`GET /personal/finance/` or `GET /finance/`):
    - Lifetime & Monthly Financial KPIs: Total Income, Total Expenses, Net Balance (Income − Expenses), Month Income, Month Expenses, Monthly Savings.
    - Cash flow ratio comparison bar.
    - Category-wise spending breakdown with percentages and ₹ amounts.
    - Searchable, type-filterable (`INCOME`, `EXPENSE`), category-filterable, date-filterable, sortable (by date or amount) transaction ledger.
  - `finance:transaction_create` (`GET/POST /finance/transactions/create/`): Add transaction with positive decimal amount, type, user category, date, payment method, and notes.
  - `finance:transaction_edit` (`GET/POST /finance/transactions/<pk>/edit/`): Update transaction.
  - `finance:transaction_delete` (`GET/POST /finance/transactions/<pk>/delete/`): Safe delete with confirmation.
  - `finance:category_create` (`GET/POST /finance/categories/create/`): Quick creation of dedicated finance categories.

### Automated Test Suite
- **123 Automated Tests** across the entire application:
  - 14 dedicated tests in `apps.personal` verifying models, overnight sleep duration calculations, check-in deduplication, journal search/filters, decision lifecycle, mistake workflows, and IDOR isolation.
  - 8 dedicated tests in `apps.finance` verifying positive decimal validation, lifetime & monthly calculations, category ownership, ledger search/filters, and IDOR isolation.
  - 100% pass rate (`Ran 123 tests in 122.946s — OK`).


