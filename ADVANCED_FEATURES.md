# LifeOS — Advanced Features & Integration Documentation (Step 11)

## 1. Executive Summary

Step 11 elevates LifeOS from a collection of powerful standalone life-management modules into a deeply synchronized, reactive, and unified **Personal Behavioral Intelligence System**. This milestone establishes:

1. **Cross-Module Reactive Synchronization**: Bidirectional synchronization between Tasks and the Daily Timetable, between Study Sessions and Syllabus Plans/Topics, and between daily biometric check-ins and executive dashboard telemetry.
2. **In-App Proactive Notification System**: User-scoped notifications across Tasks, Study, Schedule, and Goals with automated event-driven triggers, persistent state, unread badge counters, and real-time dropdown inspection.
3. **Global Multi-Entity Search**: Unified, sub-millisecond search engine scanning across 10 distinct domain entities with strict multi-user tenant isolation.
4. **Deterministic Heuristic Recommendation Engine**: Modular, rule-based behavioral diagnostics identifying time-estimation distortions, syllabus backlog, keystone habit decay, schedule overload, and sleep deficits.
5. **Data Sovereignty & Portability (Export Engine)**: Self-service streaming export of private records in sanitized JSON and modular CSV/ZIP formats, guaranteeing zero password hash or credential exposure.
6. **Comprehensive System Settings & Localization**: Complete customization of primary timezone, ISO date formats, 12h/24h time formatting, week start day, daily productive work hour benchmarks, and notification toggles.
7. **Progressive Web App (PWA) Readiness**: Web App Manifest (`manifest.json`) and a privacy-preserving static-only Service Worker (`service-worker.js`) that delivers instant load times without caching sensitive user records.

---

## 2. Architecture & System Design

```
+-----------------------------------------------------------------------------------+
|                                     LifeOS Header                                 |
|  [Logo] [Breadcrumbs]  [Global Search: Ctrl+K]  [Timezone Pill]  [Bell (N)] [User]|
+-----------------------------------------+-----------------------------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
                v                                                   v
    +------------------------+                             +------------------------+
    | Global Search Service  |                             |  Notification Service  |
    |  - Tasks & Backlog     |                             |  - Overdue Deadlines   |
    |  - Habits & Logs       |                             |  - Exam Reminders (<7d)|
    |  - Goals & Projects    |                             |  - Spaced Revisions    |
    |  - Subjects & Topics   |                             |  - Evening Reflections|
    |  - Journal & Notes     |                             |  - Goal Target Dates   |
    |  - Decisions & Mistakes|                             +-----------+------------+
    |  - Activities          |                                         |
    +------------------------+                                         v
                                                           +------------------------+
                                                           | Core Notifications DB  |
                                                           |  - Notification Model  |
                                                           |  - UserPreference Model|
                                                           +------------------------+

                +-------------------------+-------------------------+
                |                                                   |
                v                                                   v
    +------------------------+                             +------------------------+
    | Recommendation Engine  |                             | Personal Data Export   |
    |  - Estimation Calibr.  |                             |  - Complete JSON Backup|
    |  - Overdue Triage      |                             |  - Modular CSV / ZIP   |
    |  - Urgent Block Sched. |                             |  - Zero-credential leak|
    |  - Syllabus Velocity   |                             +------------------------+
    |  - Spaced Recall Queue |
    |  - Daily Habit Slip    |
    |  - Sleep Debt Recovery |
    |  - Dismissal Tracking  |
    +------------------------+
```

---

## 3. Data Models (`apps/core/models.py`)

### 3.1 `Notification`
User-scoped notifications tracking domain alerts, timestamps, read state, and deep-link targets.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Auto-incrementing identifier |
| `user` | ForeignKey | `AUTH_USER_MODEL`, CASCADE | Owner of notification |
| `notification_type` | CharField(20) | Choices: `TASK`, `STUDY`, `ROUTINE`, `GOAL`, `SYSTEM` | Notification domain |
| `title` | CharField(200) | Required | Brief heading of notification |
| `message` | TextField | Required | Detailed explanatory content |
| `target_url` | CharField(255) | Blank, default `''` | Actionable target URL |
| `is_read` | BooleanField | Default `False` | Read receipt toggle |
| `created_at` | DateTimeField | Auto-now-add | Timestamp of notification creation |

*Indexes*: `(user, is_read, -created_at)`, `(user, notification_type)`.

### 3.2 `UserPreference`
User-specific localization, scheduling parameters, and notification preferences.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Auto-incrementing identifier |
| `user` | OneToOneField | `AUTH_USER_MODEL`, CASCADE | Target user |
| `date_format` | CharField(20) | Choices: `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY` | Preferred display date format |
| `time_format` | CharField(10) | Choices: `24h`, `12h` | Preferred display time format |
| `week_start_day` | CharField(10) | Choices: `monday`, `sunday` | First day of weekly timetables |
| `daily_work_goal_hours` | DecimalField(4, 1) | Default `8.0` | Target productive hours per day |
| `notify_tasks` | BooleanField | Default `True` | Deadline reminders enabled |
| `notify_study` | BooleanField | Default `True` | Exam/revision alerts enabled |
| `notify_routines` | BooleanField | Default `True` | Timetable overload alerts enabled |
| `notify_goals` | BooleanField | Default `True` | Goal milestone alerts enabled |
| `created_at` | DateTimeField | Auto-now-add | Creation timestamp |
| `updated_at` | DateTimeField | Auto-now | Last modified timestamp |

### 3.3 `DismissedRecommendation`
Tracks explicitly dismissed rule-based recommendations per user to avoid alert fatigue.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | BigAutoField | Primary Key | Auto-incrementing identifier |
| `user` | ForeignKey | `AUTH_USER_MODEL`, CASCADE | Target user |
| `recommendation_key` | CharField(100) | Required | Unique rule recommendation slug |
| `dismissed_at` | DateTimeField | Auto-now-add | Dismissal timestamp |

*Constraints*: `unique_together = ('user', 'recommendation_key')`.

---

## 4. Cross-Module Integration Details

### 4.1 Task Completion & ScheduleBlock Synchronization
- **Action**: When a user marks a task completed (via the Dashboard toggle or Tasks module), any `ScheduleBlock` where `related_task=task` and `status=SCHEDULED` is automatically updated to `status=COMPLETED`.
- **Reopening**: When a completed task is reverted to `PENDING`, linked `ScheduleBlock` entries revert back to `SCHEDULED`.
- **Location**: `apps.productivity.views.task_toggle_complete_view` and `apps.core.views.toggle_task_view`.

### 4.2 Study Session Completion & StudyPlan Synchronization
- **Action**: When a completed study session is saved (either manually logged or when stopping the active timer), the system searches for an open `StudyPlan` for that subject, topic, and date where `status=PLANNED` and marks it `COMPLETED`.
- **Topic Time Accumulation**: `Topic.actual_minutes` automatically aggregates total duration from linked `StudySession` records via Django ORM aggregation properties.
- **Location**: `apps.study.views.study_session_create_view` and `apps.study.views.study_session_stop_view`.

---

## 5. In-App Notification System

### 5.1 Proactive Trigger Rules (`NotificationService.generate_system_notifications`)
1. **Task Overdue Alert**: Scans for tasks with `due_date < today` and status `[PENDING, IN_PROGRESS]`. Triggers a consolidated summary alert with target `/tasks/?status=PENDING`.
2. **Today's Deadlines**: Scans for pending tasks due on current date.
3. **Exam Countdown Alert**: Scans for upcoming exams within 7 days. Displays days remaining, subject name, and maximum score with target `/study/exams/`.
4. **Spaced Repetition Due Alert**: Scans `Revision` records with `revision_date <= today` and status `PENDING`. Direct link to `/study/revisions/`.
5. **Evening Reflection Reminder**: Evaluates local time; if hour is `>= 18:00` and no `DailyMetric` check-in has been logged for today, prompts the user to record their psychometrics at `/checkin/`.
6. **Goal Target Reminder**: Scans active goals with `target_date` within 3 days.

### 5.2 Deduplication Protocol
- All proactive alerts specify a `deduplicate_hours` window (defaulting to 12 or 24 hours). If an alert with the same `(user, notification_type, title)` was generated within that window, creation is silently skipped.

### 5.3 Global Context Processor
- `lifeos_core_context` runs on every authenticated request, injecting `unread_notifications_count`, `recent_notifications`, and `user_preferences` into all templates for immediate header badge rendering.

---

## 6. Global Multi-Entity Search

### 6.1 Supported Search Entities
| Entity | Queried Fields | Search Output Metadata | Destination URL |
|---|---|---|---|
| **Task** | `title`, `description` | Status, Priority, Due Date | `/tasks/<id>/` |
| **Habit** | `name`, `description` | Frequency, Target Count | `/habits/<id>/edit/` |
| **Goal** | `title`, `description` | Status, Priority, Target Date | `/goals/<id>/` |
| **Project** | `title`, `description` | Status, Priority | `/projects/<id>/` |
| **Subject** | `name`, `code`, `description` | Status, Subject Type | `/study/subjects/<id>/` |
| **Topic** | `title`, `description` | Subject Name, Status | `/study/topics/<id>/edit/` |
| **Journal** | `title`, `content` | Entry Date, Mood Tag | `/personal/journal/<id>/edit/` |
| **Decision** | `title`, `description`, `reason_for_choosing` | Decision Date, Status | `/personal/decisions/<id>/edit/` |
| **Mistake** | `title`, `description`, `lesson_learned` | Impact Level, Status | `/personal/mistakes/<id>/edit/` |
| **Activity** | `activity_name`, `description` | Duration (min), Start Time | `/activities/<id>/edit/` |

### 6.2 Security & Isolation
Every individual query executes with an explicit `user=request.user` (or `subject__user=request.user`) filter. It is structurally impossible for User A to retrieve records belonging to User B.

---

## 7. Deterministic Recommendation Engine

The recommendation engine (`RecommendationService.get_recommendations`) executes clean heuristics without external ML dependencies:

1. **`productivity_estimation_error`**: Triggered when `>= 50%` of recent completed tasks exceeded planned estimates with an average error of `>= 30 minutes`.
2. **`productivity_overdue_backlog`**: Triggered when `>= 3` tasks are overdue.
3. **`schedule_unscheduled_urgent_tasks`**: Triggered when high-priority tasks due within 2 days lack a corresponding timetable block for today.
4. **`study_exam_preparation_pace`**: Triggered when an exam is within 14 days and syllabus topic completion is `< 60%`.
5. **`study_revision_spaced_repetition`**: Triggered when `>= 2` spaced repetition reviews are overdue.
6. **`habits_daily_slip`**: Triggered when an active daily habit has `< 50%` completion over the past 7 days.
7. **`schedule_daily_overload`**: Triggered when today's timetable commitments exceed 10 planned hours (600 minutes).
8. **`wellbeing_sleep_deficit`**: Triggered when average sleep duration across recent entries is `< 6.0 hours`.
9. **`wellbeing_missing_checkins`**: Triggered when daily reflections were logged on `<= 3` of the past 7 days.

Each recommendation provides:
- Category & Priority badge
- Diagnostic summary with real figures
- "Why LifeOS Recommends This" behavioral science rationale
- Actionable deep-link button
- Dismiss button backed by `DismissedRecommendation`

---

## 8. Data Export & Sovereignty Engine

Users can export their complete data ledger via `/settings/export/`:

- **Complete Backup (JSON)**: Single comprehensive JSON archive containing application metadata, user credentials (username, email, timezone preference only), and nested arrays for all 7 modules.
- **Table Archive (CSV / ZIP)**: Generates a compressed `.zip` containing individual CSV files (`tasks.csv`, `habits.csv`, `study_sessions.csv`, `study_plans.csv`, `revisions.csv`, `exams.csv`, `daily_metrics.csv`, `journal_entries.csv`, `decisions.csv`, `mistakes.csv`, `transactions.csv`).
- **Individual Module (CSV)**: Instant direct download of a specific domain table.
- **Privacy Assurance**: Password hashes, salt strings, session keys, and internal authentication tokens are strictly stripped at the serialization boundary.

---

## 9. PWA Readiness

1. **Web App Manifest (`static/manifest.json`)**: Configured with dark theme `#0F1117`, background color `#0F1117`, standalone display mode, and maskable icons.
2. **Service Worker (`static/js/service-worker.js`)**:
   - Cache-first strategy strictly for static stylesheet tokens, layout scripts, and logos.
   - Dynamic bypass on all non-static paths to guarantee private user records and live database states are never cached in shared browser cache storage.
3. **Template Registration (`templates/base.html`)**: Automatic background registration upon window load.

---

## 10. Automated Verification

- **Step 11 Test Suite**: 16 dedicated unit and integration tests in `apps/core/tests_step11.py` covering Notifications, Global Search, Recommendation Heuristics, Data Export, Preferences, Cross-Module Synchronization, and Multi-User Isolation.
- **Total Test Suite**: 151 tests across all 8 applications.
- **Pass Rate**: 100% (151/151 passed in 165.151s).
