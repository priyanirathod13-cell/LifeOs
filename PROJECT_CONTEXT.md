# LifeOS — Project Context & Architectural Blueprint

## 1. System Mission & Identity

**LifeOS** is a multi-user Personal Behavioral Intelligence and Life Management System.
Its mission is to empower individuals to capture, manage, understand, and optimize the multi-dimensional relationships between planning, daily behaviors, decisions, habits, states of mind, and tangible life outcomes.

### Core Philosophy
1. **Behavioral Intelligence**: Correlation across different aspects of life (sleep vs. focus, habits vs. energy, planning vs. goal realization).
2. **Minimalist, Modern Experience**: Zero visual clutter. Clear visual hierarchy prioritizing usability and focus.
3. **Privacy & Independence**: Multi-user architecture with complete data isolation per user account.
4. **Resilient Foundation**: Built on Python/Django, MySQL with Django ORM, and modern semantic HTML5/CSS3/JavaScript.

---

## 2. Core Functional Domains

LifeOS is structured into four primary cognitive domains:

### A. My Day (Execution & Rhythm)
- **Dashboard**: High-level real-time overview of current focus, habits, schedules, and active behavioral insights.
- **Daily Timetable**: Structured timeblocks, scheduling, and dynamic calendar allocation.
- **Daily Routines**: Morning, workday, and evening behavioral checklists and sequences.
- **Tasks**: Action item management, priority matrix, time estimates, and backlog.
- **Habits**: Daily streak tracking, habit loops, and consistency analytics.
- **Activities**: Sports, recovery, leisure, and unstructured time logging.
- **Daily Check-in**: Subjective metrics logging (energy, mood, stress, sleep quality).

### B. My Growth (Direction & Strategy)
- **Study Management**: Course syllabi, topics, active recall sessions, and study schedules.
- **Goals & Milestones**: Vision, quarterly objectives, and actionable milestone trees.
- **Projects**: Multi-task initiatives with deadlines, deliverables, and progress tracking.
- **Journal Entries**: Daily reflections, retrospective notes, and qualitative logs.
- **Decisions**: Decision log documenting expected payoffs, rationale, mental models, and post-mortems.
- **Mistakes & Learning**: Anti-pattern analysis, root-cause deductions, and mitigation rules.

### C. My Intelligence (Analytics & Synthesis)
- **Productivity Analytics**: Deep work time, interruption analysis, and task velocity.
- **Study Analytics**: Retention curves, revision schedules, and topic mastery.
- **Behavioral Insights**: Cross-dimensional correlation engine (e.g. sleep duration vs. study focus).
- **Financial Analytics**: Cash flow, expense classification, and impulse spending analysis.
- **Recommendations**: Proactive suggestions to optimize daily timetable and routine execution.

### D. Settings & System Administration
- **Settings**: User profile, authentication credentials, notifications, and application preferences.
- **Design System Showcase**: Live component catalog verifying UI standards and visual tokens.

---

## 3. Technology Stack & Architecture

- **Backend Framework**: Python 3.13, Django 4.2 LTS
- **Database Engine**: MySQL / MariaDB via Django ORM and `mysqlclient`
- **Frontend Architecture**: Server-rendered Django templates, Vanilla CSS3 with CSS Variables, Modular Vanilla JavaScript
- **Typography**: Inter (Google Fonts + system fallback stack)
- **Design Identity**: Minimal Modern Dark + Soft Indigo Accents
- **Security & Configuration**: Environment variables loaded via `python-dotenv`, secrets excluded from version control, custom `AbstractUser` model configured upfront.

---

## 4. Multi-User Authentication & Data Isolation Architecture

Established in Step 03:
- **Authentication**: Email-based authentication backend (`apps.accounts.backends.EmailAuthBackend`) with case-insensitive normalization and timing-attack mitigation.
- **Session Management**: Session cookies configured with `HttpOnly`, CSRF protection, and duration toggled by "Remember Me" (14 days persistent vs. browser session).
- **Access Control Rule**: All private application routes (`/dashboard/`, `/timetable/`, `/tasks/`, `/habits/`, `/study/`, `/profile/`, etc.) strictly enforce `@login_required` access control.
- **Ownership Verification**: All future models must tie private records directly to `user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)`. Never trust user IDs provided in form payloads or URL parameters — always filter and assign through `request.user`.


---

## 5. Data Architecture & Domain Model Registry (Step 04)

Established in Step 04:
- **Application Structure**:
  - `apps.accounts`: Custom `User` model.
  - `apps.productivity`: `Category`, `Task`, `Habit`, `HabitLog`, `Activity`, `Routine`, `ScheduleBlock`.
  - `apps.planning`: `Project`, `Goal`, `GoalTask`.
  - `apps.personal`: `JournalEntry`, `Decision`, `DecisionOption`, `DecisionOutcome`, `Mistake`, `DailyMetric`.
  - `apps.finance`: `Transaction`.
  - `apps.study`: `Subject`, `Topic`, `StudySession`, `Exam`.
- **Integrity & Constraints**:
  - Check constraints for strictly positive amounts (`amount > 0`), valid score ranges (`1 <= score <= 10`), valid sleep hours (`0 <= sleep <= 24`), and target dates (`target_date >= start_date`).
  - Strict multi-user data isolation: Cross-model foreign keys validate identical user ownership in `clean()`.
  - Normalization to 3NF: Computed values (e.g. `Activity.duration_minutes`) are derived dynamically on-the-fly rather than storing redundant columns.
- **Legacy Preservation**:
  - Legacy records from `lifeos` database migrated into `lifeos_db` via `python manage.py import_legacy_data` with zero data loss.


---

## 6. Main Dashboard Architecture & Central Control Panel (Step 05)

Established in Step 05:
- **Central Control Panel**: Live authenticated dashboard at `/dashboard/` integrating real domain models across tasks, habits, studies, schedules, goals, biometrics, and recent activity.
- **Timezone-Aware Temporal Processing**: User greeting and daily boundaries respect `request.user.timezone_pref` with fallback to `settings.TIME_ZONE`.
- **Zero-Division and Empty State Resilience**: All statistics (task completion percentage, habit completion percentage, goal progress) feature defensive zero-division safeguards (`round((completed / total) * 100) if total > 0 else 0`).
- **Interactive Quick Actions & Security**:
  - `toggle_task_view` (`POST /dashboard/toggle-task/<id>/`): Toggles task completion state with IDOR protection (`get_object_or_404(Task, id=id, user=request.user)`).
  - `toggle_habit_view` (`POST /dashboard/toggle-habit/<id>/`): Logs or unlogs habit execution for the current date with IDOR protection.
  - `quick_add_task_view` (`POST /dashboard/quick-add-task/`): Modal-driven task creation with category ownership validation.
  - `quick_checkin_view` (`POST /dashboard/quick-checkin/`): Modal-driven biometric logging updating `DailyMetric` for the current date.


---

## 7. Productivity Management Architecture (Step 06)

Established in Step 06:
- **Modular Division of Labor**:
  - `apps.productivity`: Focused on execution mechanics — individual action items (`Task`), user classifications (`Category`), behavioral loops (`Habit`, `HabitLog`), and continuous time investment (`Activity`).
  - `apps.planning`: Focused on strategic direction — multi-task initiatives (`Project`), outcome horizons (`Goal`), and explicit task contributions (`GoalTask`).
- **Data Isolation & IDOR Protection**:
  - Every view rigorously queries `request.user` (e.g. `get_object_or_404(Task, pk=pk, user=request.user)`).
  - Model forms explicitly scope foreign key querysets (`category`, `project`, `task`) to `self.user`.
  - In `clean()` methods, cross-user associations between `Task`, `Category`, `Project`, and `Goal` raise `ValidationError`.
  - Attempts by User A to access, edit, delete, or link records belonging to User B reliably return HTTP 404.
- **Safe Cascade & Referential Integrity**:
  - Deleting a `Category` sets `category_id = NULL` on linked tasks, habits, and activities; records are never destroyed.
  - Deleting a `Project` sets `project_id = NULL` on child tasks; tasks remain available in the user's backlog.
  - Deleting a `Goal` only destroys the junction records (`GoalTask`); the underlying tasks remain intact.
- **Dynamic Derived Calculations**:
  - Task completion rates and goal progress percentages are computed on-the-fly (`round((completed / total) * 100) if total > 0 else None`).
  - Habit streaks are evaluated dynamically across daily or weekly frequencies by traversing chronological `HabitLog` records.
  - Activity durations are derived from `end_time - start_time` when closed, leaving open sessions marked as live.


---

## 8. Study Management Architecture (Step 07)

Established in Step 07:
- **Module Structure (`apps.study`)**:
  - `Subject`: Coursework or learning area with status (`ACTIVE`, `COMPLETED`, `ARCHIVED`), type (`COLLEGE`, `EXAM_PREP`, `SKILL`, `PROJECT`, `PERSONAL`), color, and target dates.
  - `Topic`: Discrete concept or syllabus unit organized under chapters, tracking mastery status (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `MASTERED`, `NEEDS_REVISION`) and priority.
  - `StudySession`: Logged active recall or study sessions supporting both real-time stopwatch timers (with auto-closing of dangling sessions) and manual historical time recording.
  - `StudyPlan`: Daily/weekly study commitment scheduling independent of actual recorded sessions, supporting temporal views (`Today`, `Upcoming`, `This Week`, `Past`, `All`) and status transitions (`PLANNED`, `COMPLETED`, `SKIPPED`, `RESCHEDULED`).
  - `Revision`: Iterative spaced revision tracking with auto-incrementing iteration numbers (`Revision #1, #2`), completion toggling, and date rescheduling.
  - `Exam`: Assessment scheduling with deadline countdown badges, exam types, scoring, and percentage computation.
- **Data Isolation & IDOR Protection**:
  - All 28 controller views rigorously isolate records to `request.user`.
  - Forms enforce user-scoped foreign keys (`subject`, `topic`) and validate cross-user mismatch prevention in `clean()`.
- **9 Core Functional Sections**:
  1. Study Dashboard (`/study/`): 7 summary KPI cards, active timer banner, today's planned sessions, upcoming exams countdown, incomplete syllabus progress, recent session activity, weekly rhythm chart.
  2. Subjects & Courses (`/study/subjects/`): CRUD, chapter grouping, status filters, search, and safe deletion with cascade impact warnings.
  3. Topics & Chapters (`/study/topics/`): Chapter grouping, CRUD, duration tracking, completion toggle with auto-date stamping, priority rankings.
  4. Syllabus Tracker (`/study/syllabus/`): Dynamic progress bars (`completed / total * 100`), behind-schedule detection (`target_date < today and pct < 100%`).
  5. Study Planner (`/study/planner/`): Commitment scheduling, temporal tabs, and status actions.
  6. Study Sessions & Time Tracking (`/study/sessions/`): Stopwatch timer, quick-start, focus ratings (1–10), and manual logging.
  7. Revision Planner (`/study/revisions/`): Spaced revision iterations, overdue/today/upcoming groupings, quick reschedule.
  8. Exams & Assessments (`/study/exams/`): Exam scheduling, deadline countdowns, score tracking (`score_achieved / max_score`).
  9. Study Analytics (`/study/analytics/`): 14-day daily rhythm bar chart, subject time share, syllabus velocity, and plan adherence.

---

## 9. Smart Routine & Timetable Generator Architecture (Step 08)

Established in Step 08:
- **Module Architecture (`apps.productivity` & `apps.study` Integration)**:
  - `Routine`: Recurring fixed commitments (e.g. Morning Routine, College Lectures, Office Work, Meals, Sleep) with weekday recurring sets (`MON,TUE...`), time validation, and cross-weekday overlap prevention.
  - `AvailabilityWindow`: User-configured productive time windows by weekday (e.g. Mon 09:00–12:00, Mon 14:00–18:00) with duplicate and overlap validation.
  - `ScheduleBlock`: Chronological calendar timeblocks on a specific date, linking to `Task`, `Routine`, or `StudyPlan`, with `status` (`SCHEDULED`, `COMPLETED`, `SKIPPED`, `RESCHEDULED`), `priority`, and `is_fixed` flags.
  - `SchedulingPreference`: Per-user configuration for day bounds (`day_start_time`, `day_end_time`), `default_break_minutes`, `max_continuous_work_minutes`, `buffer_minutes`, `auto_insert_breaks`, and daily fatigue limits (`max_daily_work_minutes`).
  - `ScheduleGenerationHistory`: Audit trail of generator runs, capturing generation timestamp, counts of scheduled tasks/study/routines/breaks, total work minutes, and structured reasons for unscheduled items in JSON format.
- **Rule-Based Scheduling Engine (`apps.productivity.services.generator.TimetableGenerator`)**:
  - Pure Python deterministic heuristic algorithm (100% testable, zero black-box AI dependencies).
  - Multi-tier candidate prioritization:
    1. Study commitments (`StudyPlan` for target date, prioritized by high/urgent priority and subject status).
    2. Pending tasks (`Task`), ordered by deadline proximity (`due_date <= target_date`), priority weight (URGENT > HIGH > MEDIUM > LOW), and estimated duration.
  - Continuous free slot discovery: Subtracts fixed routines and existing protected blocks from user availability windows or day bounds.
  - Fatigue and ergonomics: Automatically inserts rest breaks when continuous work exceeds `max_continuous_work_minutes`, applies spacing buffers between activities, and caps daily workload at `max_daily_work_minutes`.
  - Detailed unscheduled diagnostic reporting: Tags any unscheduled tasks or study plans with actionable reasons (e.g. "No available time slot of required duration", "Daily work limit reached").
- **7 Core Functional Sections**:
  1. Daily Timetable (`/timetable/`): Chronological day timeline, date navigation, 4 KPI cards (scheduled, completed, free time, work minutes), status actions (`COMPLETED`, `SKIPPED`), block reschedule, delete, manual block modal.
  2. Weekly Timetable (`/timetable/weekly/`): 7-day Monday–Sunday responsive calendar view, today highlight, fixed vs flexible visual distinction, pending backlog sidebar.
  3. Routine Management (`/routines/`): Recurring commitments CRUD, weekday filter pills, active status toggle, overlap protection.
  4. Availability Windows (`/availability/`): Weekly productivity availability configuration with daily breakdown cards and add/delete actions.
  5. Smart Timetable Generator (`/timetable/generator/`): Date selection, rule chips, schedule simulation preview, 4 preview KPI cards, unscheduled items callout with explicit reasons, conflict alerts, and atomic apply engine.
  6. Schedule History (`/timetable/history/`): Generation history audit log table, execution metrics, and expandable unscheduled diagnostics.
  7. Scheduling Preferences (`/timetable/preferences/`): User-configurable day bounds, fatigue thresholds, break lengths, buffers, and daily workload caps.
- **Data Isolation & IDOR Protection**:
  - All 17 timetable and routine endpoints strictly isolate data to `request.user`.
  - Service layer functions require `user` argument and query exclusively within `user` scope.
  - Forms validate foreign keys and prevent cross-user item manipulation with HTTP 404 responses.


