from datetime import date, datetime, time, timedelta
from decimal import Decimal
import zoneinfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.personal.models import DailyMetric, JournalEntry
from apps.planning.models import Goal, GoalStatus, GoalTask, Priority as GoalPriority
from apps.productivity.models import (
    Activity,
    BlockType,
    Category,
    CategoryType,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    Routine,
    ScheduleBlock,
    ScheduleStatus,
    Task,
    TaskStatus,
)
from apps.study.models import Exam, StudySession, Subject, SubjectType

User = get_user_model()


class CoreAndLandingTests(TestCase):
    """
    Test suite for LifeOS core endpoints, public landing page, and protected views.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@lifeos.internal',
            email='testuser@lifeos.internal',
            password='TestPassword@2026',
            first_name='Test',
            last_name='User'
        )

    def test_health_check_status_code(self):
        """GET /health/ must return HTTP 200 OK (Step 01 preservation)."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_check_response_payload(self):
        """GET /health/ must return the exact expected JSON structure."""
        response = self.client.get('/health/')
        self.assertEqual(response.json(), {
            "status": "ok",
            "application": "LifeOS"
        })

    def test_public_landing_page_unauthenticated(self):
        """Unauthenticated user accessing '/' sees public Landing Page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/landing.html')
        self.assertContains(response, 'Personal')
        self.assertContains(response, 'Behavioral Intelligence')
        self.assertContains(response, 'Create Account')

    def test_root_redirects_to_dashboard_when_authenticated(self):
        """Authenticated user accessing '/' is redirected to their dashboard."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')
        response = self.client.get('/')
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_dashboard_view_unauthenticated_redirects(self):
        """Unauthenticated user accessing '/dashboard/' is redirected to login."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_dashboard_view_authenticated(self):
        """Authenticated user accessing '/dashboard/' renders dashboard with user greeting."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/dashboard.html')
        self.assertTemplateUsed(response, 'layouts/app_layout.html')
        self.assertContains(response, 'Test')

    def test_ui_system_showcase_accessible(self):
        """Design system demonstration page is accessible at /ui-system/."""
        response = self.client.get(reverse('core:ui_system'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/ui_system.html')
        self.assertContains(response, 'LifeOS Design System')

    def test_all_sidebar_navigation_routes_accessible_when_authenticated(self):
        """Verify that every single sidebar navigation link returns HTTP 200 for authenticated users."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')

        nav_routes = [
            'core:dashboard',
            'core:ui_system',
            'core:timetable',
            'core:routines',
            'core:tasks',
            'core:habits',
            'core:activities',
            'core:checkin',
            'core:study',
            'core:goals',
            'core:projects',
            'core:journal',
            'core:decisions',
            'core:mistakes',
            'core:productivity_analytics',
            'core:study_analytics',
            'core:behavioral_insights',
            'core:financial_analytics',
            'core:recommendations',
            'core:settings',
        ]

        for route_name in nav_routes:
            url = reverse(route_name)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"Expected route '{route_name}' ({url}) to return 200 OK, got {response.status_code}"
            )


class DashboardDataAggregationTests(TestCase):
    """
    Test suite verifying dashboard data aggregation, statistics calculations,
    zero-division safeguards, and empty state rendering.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='aarav_student',
            email='aarav.student@gmail.com',
            password='TestPassword@2026',
            first_name='Aarav',
            last_name='Student',
            timezone_pref='Asia/Kolkata'
        )
        self.client.login(email='aarav.student@gmail.com', password='TestPassword@2026')
        self.today = timezone.localtime(timezone.now()).date()

    def test_empty_dashboard_renders_gracefully(self):
        """A user with 0 records sees accurate zero statistics and friendly empty states with no crashes."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Context zero-state checks
        self.assertEqual(response.context['tasks_total_count'], 0)
        self.assertEqual(response.context['tasks_completed_count'], 0)
        self.assertEqual(response.context['tasks_pending_count'], 0)
        self.assertEqual(response.context['tasks_completion_pct'], 0)

        self.assertEqual(response.context['habits_total_count'], 0)
        self.assertEqual(response.context['habits_completed_count'], 0)
        self.assertEqual(response.context['habits_completion_pct'], 0)

        self.assertEqual(response.context['study_sessions_count'], 0)
        self.assertEqual(response.context['total_study_minutes'], 0)
        self.assertEqual(response.context['study_time_display'], '0 mins')

        self.assertEqual(response.context['goals_active_count'], 0)

        # HTML empty states
        self.assertContains(response, 'No tasks due today')
        self.assertContains(response, 'No habits configured yet')
        self.assertContains(response, 'Your study journey starts here')
        self.assertContains(response, 'No active goals defined yet')

    def test_tasks_aggregation_and_overdue_handling(self):
        """Tasks due today and overdue are accurately summarized and tagged."""
        # 1. Overdue pending task
        Task.objects.create(
            user=self.user,
            title='Overdue assignment',
            priority=Priority.URGENT,
            status=TaskStatus.PENDING,
            due_date=self.today - timedelta(days=2)
        )
        # 2. Task due today (pending)
        Task.objects.create(
            user=self.user,
            title='Today pending task',
            priority=Priority.HIGH,
            status=TaskStatus.PENDING,
            due_date=self.today
        )
        # 3. Task completed today
        Task.objects.create(
            user=self.user,
            title='Today completed task',
            priority=Priority.MEDIUM,
            status=TaskStatus.COMPLETED,
            due_date=self.today,
            completed_at=timezone.now()
        )
        # 4. Future task (should not count towards today's overview)
        Task.objects.create(
            user=self.user,
            title='Future task',
            priority=Priority.LOW,
            status=TaskStatus.PENDING,
            due_date=self.today + timedelta(days=5)
        )

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Total today: 3 (overdue + today pending + today completed)
        self.assertEqual(response.context['tasks_total_count'], 3)
        self.assertEqual(response.context['tasks_completed_count'], 1)
        self.assertEqual(response.context['tasks_pending_count'], 2)
        self.assertEqual(response.context['tasks_completion_pct'], 33)

        # Overdue tag verification
        tasks = response.context['todays_tasks']
        overdue_task = next(t for t in tasks if t.title == 'Overdue assignment')
        self.assertTrue(overdue_task.is_overdue)
        self.assertContains(response, 'Overdue')

    def test_habits_and_today_logs_aggregation(self):
        """Active habits and today's execution logs are computed accurately."""
        h1 = Habit.objects.create(user=self.user, name='Morning Workout', frequency=HabitFrequency.DAILY)
        h2 = Habit.objects.create(user=self.user, name='Read System Design', frequency=HabitFrequency.DAILY)
        h3 = Habit.objects.create(user=self.user, name='Inactive Habit', is_active=False)

        # Log h1 completed for today
        HabitLog.objects.create(habit=h1, user=self.user, log_date=self.today, completed=True)

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        # 2 active habits, 1 completed today -> 50%
        self.assertEqual(response.context['habits_total_count'], 2)
        self.assertEqual(response.context['habits_completed_count'], 1)
        self.assertEqual(response.context['habits_remaining_count'], 1)
        self.assertEqual(response.context['habits_completion_pct'], 50)

        habits_display = response.context['habits_display']
        h1_item = next(item for item in habits_display if item['habit'].id == h1.id)
        h2_item = next(item for item in habits_display if item['habit'].id == h2.id)
        self.assertTrue(h1_item['completed'])
        self.assertFalse(h2_item['completed'])

    def test_study_aggregation_and_upcoming_exams(self):
        """Study duration, distinct subjects, and upcoming exams are aggregated accurately."""
        sub1 = Subject.objects.create(user=self.user, name='Computer Architecture', code='CS201')
        sub2 = Subject.objects.create(user=self.user, name='Discrete Math', code='MA101')

        # Study sessions today: 90 mins on sub1, 45 mins on sub2
        StudySession.objects.create(
            user=self.user,
            subject=sub1,
            session_date=self.today,
            duration_minutes=90
        )
        StudySession.objects.create(
            user=self.user,
            subject=sub2,
            session_date=self.today,
            duration_minutes=45
        )

        # Upcoming exam in 10 days
        exam = Exam.objects.create(
            user=self.user,
            subject=sub1,
            exam_name='Midterm Exam',
            exam_date=self.today + timedelta(days=10)
        )

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['study_sessions_count'], 2)
        self.assertEqual(response.context['total_study_minutes'], 135)
        self.assertEqual(response.context['study_time_display'], '2h 15m')
        self.assertEqual(response.context['study_subjects_count'], 2)

        exams = response.context['upcoming_exams']
        self.assertEqual(len(exams), 1)
        self.assertEqual(exams[0].days_remaining, 10)
        self.assertContains(response, 'Midterm Exam')

    def test_goals_progress_and_approaching_window(self):
        """Goals progress computes completed task ratio and flags targets within 30 days."""
        goal = Goal.objects.create(
            user=self.user,
            title='Master Distributed Systems',
            target_date=self.today + timedelta(days=20),
            status=GoalStatus.IN_PROGRESS
        )
        t1 = Task.objects.create(user=self.user, title='Study Raft', status=TaskStatus.COMPLETED)
        t2 = Task.objects.create(user=self.user, title='Implement Paxos', status=TaskStatus.PENDING)

        GoalTask.objects.create(goal=goal, task=t1)
        GoalTask.objects.create(goal=goal, task=t2)

        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['goals_active_count'], 1)
        self.assertEqual(response.context['goals_approaching_count'], 1)

        goal_preview = response.context['goals_preview'][0]
        self.assertEqual(goal_preview['total_tasks'], 2)
        self.assertEqual(goal_preview['completed_tasks'], 1)
        self.assertEqual(goal_preview['progress_pct'], 50)
        self.assertEqual(goal_preview['days_left'], 20)


class DashboardUserIsolationTests(TestCase):
    """
    Test suite verifying strict multi-user data isolation across all dashboard widgets.
    """

    def setUp(self):
        self.client_a = Client()
        self.user_a = User.objects.create_user(
            username='user_alice',
            email='alice@example.com',
            password='TestPassword@2026',
            first_name='Alice'
        )
        self.client_a.login(email='alice@example.com', password='TestPassword@2026')

        self.client_b = Client()
        self.user_b = User.objects.create_user(
            username='user_bob',
            email='bob@example.com',
            password='TestPassword@2026',
            first_name='Bob'
        )
        self.client_b.login(email='bob@example.com', password='TestPassword@2026')

        self.today = timezone.localtime(timezone.now()).date()

        # Alice's data
        self.task_a = Task.objects.create(user=self.user_a, title="Alice Secret Project Task", due_date=self.today)
        self.habit_a = Habit.objects.create(user=self.user_a, name="Alice Private Meditation")
        self.sub_a = Subject.objects.create(user=self.user_a, name="Alice Cryptography Subject")
        self.session_a = StudySession.objects.create(user=self.user_a, subject=self.sub_a, session_date=self.today, duration_minutes=60)
        self.goal_a = Goal.objects.create(user=self.user_a, title="Alice Confidential Goal")

        # Bob's data
        self.task_b = Task.objects.create(user=self.user_b, title="Bob Private Marketing Task", due_date=self.today)
        self.habit_b = Habit.objects.create(user=self.user_b, name="Bob Gym Workout")
        self.sub_b = Subject.objects.create(user=self.user_b, name="Bob Finance Subject")
        self.session_b = StudySession.objects.create(user=self.user_b, subject=self.sub_b, session_date=self.today, duration_minutes=45)
        self.goal_b = Goal.objects.create(user=self.user_b, title="Bob Revenue Target Goal")

    def test_alice_cannot_see_bob_data(self):
        """Alice's dashboard must contain only Alice's data and zero traces of Bob's records."""
        response = self.client_a.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Alice sees her own data
        self.assertContains(response, "Alice Secret Project Task")
        self.assertContains(response, "Alice Private Meditation")
        self.assertContains(response, "Alice Confidential Goal")

        # Alice NEVER sees Bob's data
        self.assertNotContains(response, "Bob Private Marketing Task")
        self.assertNotContains(response, "Bob Gym Workout")
        self.assertNotContains(response, "Bob Finance Subject")
        self.assertNotContains(response, "Bob Revenue Target Goal")

        # Counts must match Alice's exact totals
        self.assertEqual(response.context['tasks_total_count'], 1)
        self.assertEqual(response.context['habits_total_count'], 1)
        self.assertEqual(response.context['total_study_minutes'], 60)
        self.assertEqual(response.context['goals_active_count'], 1)

    def test_bob_cannot_see_alice_data(self):
        """Bob's dashboard must contain only Bob's data and zero traces of Alice's records."""
        response = self.client_b.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Bob sees his own data
        self.assertContains(response, "Bob Private Marketing Task")
        self.assertContains(response, "Bob Gym Workout")
        self.assertContains(response, "Bob Revenue Target Goal")

        # Bob NEVER sees Alice's data
        self.assertNotContains(response, "Alice Secret Project Task")
        self.assertNotContains(response, "Alice Private Meditation")
        self.assertNotContains(response, "Alice Cryptography Subject")
        self.assertNotContains(response, "Alice Confidential Goal")

        # Counts must match Bob's exact totals
        self.assertEqual(response.context['tasks_total_count'], 1)
        self.assertEqual(response.context['habits_total_count'], 1)
        self.assertEqual(response.context['total_study_minutes'], 45)
        self.assertEqual(response.context['goals_active_count'], 1)


class DashboardQuickActionsSecurityTests(TestCase):
    """
    Test suite verifying security, CSRF, input validation, and IDOR prevention
    for dashboard quick actions (toggle task, toggle habit, quick add task, quick check-in).
    """

    def setUp(self):
        self.client_a = Client()
        self.user_a = User.objects.create_user(
            username='user_alice_qa',
            email='alice_qa@example.com',
            password='TestPassword@2026'
        )
        self.client_a.login(email='alice_qa@example.com', password='TestPassword@2026')

        self.client_b = Client()
        self.user_b = User.objects.create_user(
            username='user_bob_qa',
            email='bob_qa@example.com',
            password='TestPassword@2026'
        )
        self.client_b.login(email='bob_qa@example.com', password='TestPassword@2026')

        self.today = timezone.localtime(timezone.now()).date()

        self.task_a = Task.objects.create(user=self.user_a, title="Alice Task", status=TaskStatus.PENDING)
        self.task_b = Task.objects.create(user=self.user_b, title="Bob Task", status=TaskStatus.PENDING)

        self.habit_a = Habit.objects.create(user=self.user_a, name="Alice Habit")
        self.habit_b = Habit.objects.create(user=self.user_b, name="Bob Habit")

    def test_toggle_own_task_succeeds(self):
        """User can toggle their own task completion state."""
        url = reverse('core:toggle_task', args=[self.task_a.id])
        response = self.client_a.post(url)
        self.assertRedirects(response, reverse('core:dashboard'))

        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(self.task_a.completed_at)

        # Toggle back to pending
        self.client_a.post(url)
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.status, TaskStatus.PENDING)
        self.assertIsNone(self.task_a.completed_at)

    def test_idor_prevented_on_toggle_task(self):
        """User A attempting to toggle User B's task returns 404 and does not modify the record."""
        url = reverse('core:toggle_task', args=[self.task_b.id])
        response = self.client_a.post(url)
        self.assertEqual(response.status_code, 404)

        self.task_b.refresh_from_db()
        self.assertEqual(self.task_b.status, TaskStatus.PENDING)

    def test_toggle_own_habit_succeeds(self):
        """User can toggle today's habit log execution."""
        url = reverse('core:toggle_habit', args=[self.habit_a.id])
        response = self.client_a.post(url)
        self.assertRedirects(response, reverse('core:dashboard'))

        log = HabitLog.objects.get(habit=self.habit_a, user=self.user_a, log_date=self.today)
        self.assertTrue(log.completed)

        # Toggle habit back
        self.client_a.post(url)
        log.refresh_from_db()
        self.assertFalse(log.completed)

    def test_idor_prevented_on_toggle_habit(self):
        """User A attempting to toggle User B's habit returns 404 and does not modify the record."""
        url = reverse('core:toggle_habit', args=[self.habit_b.id])
        response = self.client_a.post(url)
        self.assertEqual(response.status_code, 404)

        self.assertFalse(HabitLog.objects.filter(habit=self.habit_b).exists())

    def test_quick_add_task_validation(self):
        """Quick add task creates a task belonging strictly to the authenticated user."""
        url = reverse('core:quick_add_task')
        payload = {
            'title': 'Build Dashboard Unit Tests',
            'priority': 'HIGH',
            'due_date': str(self.today),
            'estimated_minutes': '45'
        }
        response = self.client_a.post(url, payload)
        self.assertRedirects(response, reverse('core:dashboard'))

        task = Task.objects.get(title='Build Dashboard Unit Tests')
        self.assertEqual(task.user, self.user_a)
        self.assertEqual(task.priority, Priority.HIGH)
        self.assertEqual(task.estimated_minutes, 45)
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_quick_checkin_creates_and_updates_daily_metric(self):
        """Quick check-in updates or creates DailyMetric for today with range clamps."""
        url = reverse('core:quick_checkin')
        payload = {
            'mood_score': '9',
            'energy_score': '8',
            'stress_score': '2',
            'sleep_hours': '8.25',
            'notes': 'High mental clarity today'
        }
        response = self.client_a.post(url, payload)
        self.assertRedirects(response, reverse('core:dashboard'))

        metric = DailyMetric.objects.get(user=self.user_a, metric_date=self.today)
        self.assertEqual(metric.mood_score, 9)
        self.assertEqual(metric.energy_score, 8)
        self.assertEqual(metric.stress_score, 2)
        self.assertEqual(metric.sleep_hours, Decimal('8.25'))
        self.assertEqual(metric.notes, 'High mental clarity today')

        # Updating the checkin on the same day updates existing record
        payload['mood_score'] = '10'
        self.client_a.post(url, payload)
        metric.refresh_from_db()
        self.assertEqual(metric.mood_score, 10)
        self.assertEqual(DailyMetric.objects.filter(user=self.user_a, metric_date=self.today).count(), 1)
