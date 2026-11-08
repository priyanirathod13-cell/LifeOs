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
