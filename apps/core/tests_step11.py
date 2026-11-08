import json
import zipfile
import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import (
    DismissedRecommendation,
    Notification,
    NotificationType,
    UserPreference,
)
from apps.core.services.export_service import ExportService
from apps.core.services.notification_service import NotificationService
from apps.core.services.recommendation_service import RecommendationService
from apps.core.services.search_service import GlobalSearchService
from apps.personal.models import DailyMetric, Decision, JournalEntry, Mistake
from apps.planning.models import Goal, GoalStatus, Priority as GoalPriority, Project
from apps.productivity.models import (
    Activity,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    ScheduleBlock,
    ScheduleStatus,
    Task,
    TaskStatus,
)
from apps.study.models import Exam, StudyPlan, StudySession, Subject, Topic

User = get_user_model()


class Step11NotificationTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='alice@lifeos.internal',
            email='alice@lifeos.internal',
            password='TestPassword@2026',
            first_name='Alice'
        )
        self.user_b = User.objects.create_user(
            username='bob@lifeos.internal',
            email='bob@lifeos.internal',
            password='TestPassword@2026',
            first_name='Bob'
        )
        self.client_a = Client()
        self.client_a.login(email='alice@lifeos.internal', password='TestPassword@2026')
        self.client_b = Client()
        self.client_b.login(email='bob@lifeos.internal', password='TestPassword@2026')

    def test_notification_creation_and_deduplication(self):
        notif1 = NotificationService.create_notification(
            user=self.user_a,
            notification_type=NotificationType.TASK,
            title='Overdue Task Alert',
            message='You have 2 overdue tasks.',
            target_url='/tasks/',
            deduplicate_hours=12
        )
        self.assertIsNotNone(notif1)
        self.assertEqual(NotificationService.get_unread_count(self.user_a), 1)

        # Deduplication within 12 hours prevents spamming
        notif2 = NotificationService.create_notification(
            user=self.user_a,
            notification_type=NotificationType.TASK,
            title='Overdue Task Alert',
            message='Duplicate call within 12 hours.',
            deduplicate_hours=12
        )
        self.assertIsNone(notif2)
        self.assertEqual(Notification.objects.filter(user=self.user_a).count(), 1)

    def test_notification_list_and_filters(self):
        n1 = Notification.objects.create(
            user=self.user_a,
            notification_type=NotificationType.TASK,
            title='Task Due',
            message='Task A due today',
            is_read=False
        )
        n2 = Notification.objects.create(
            user=self.user_a,
            notification_type=NotificationType.STUDY,
            title='Exam Alert',
            message='Exam in 3 days',
            is_read=True
        )

        # Alice views all notifications
        resp = self.client_a.get(reverse('core:notifications'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(n1, resp.context['notifications'])
        self.assertIn(n2, resp.context['notifications'])

        # Filter by unread
        resp_unread = self.client_a.get(reverse('core:notifications') + '?status=unread')
        self.assertEqual(resp_unread.status_code, 200)
        self.assertIn(n1, resp_unread.context['notifications'])
        self.assertNotIn(n2, resp_unread.context['notifications'])

        # Filter by type
        resp_study = self.client_a.get(reverse('core:notifications') + '?type=STUDY')
        self.assertEqual(resp_study.status_code, 200)
        self.assertIn(n2, resp_study.context['notifications'])
        self.assertNotIn(n1, resp_study.context['notifications'])

    def test_mark_read_and_mark_all_read(self):
        n1 = Notification.objects.create(user=self.user_a, title='N1', message='M1', is_read=False)
        n2 = Notification.objects.create(user=self.user_a, title='N2', message='M2', is_read=False)

        # Mark single notification as read
        resp = self.client_a.get(reverse('core:mark_notification_read', args=[n1.id]))
        self.assertRedirects(resp, reverse('core:notifications'))
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)
        self.assertEqual(NotificationService.get_unread_count(self.user_a), 1)

        # Mark all read
        resp_all = self.client_a.post(reverse('core:mark_all_notifications_read'))
        self.assertRedirects(resp_all, reverse('core:notifications'))
        self.assertEqual(NotificationService.get_unread_count(self.user_a), 0)

    def test_notification_multi_user_isolation(self):
        n_bob = Notification.objects.create(
            user=self.user_b,
            title='Bob Secret Notif',
            message='Classified alert for Bob',
            is_read=False
        )
        # Alice cannot mark Bob's notification as read (returns 404)
        resp = self.client_a.get(reverse('core:mark_notification_read', args=[n_bob.id]))
        self.assertEqual(resp.status_code, 404)

        # Alice cannot delete Bob's notification (returns 404)
        resp_del = self.client_a.get(reverse('core:delete_notification', args=[n_bob.id]))
        self.assertEqual(resp_del.status_code, 404)

        # Alice's notification center does not show Bob's notification
        resp_list = self.client_a.get(reverse('core:notifications'))
        self.assertNotContains(resp_list, 'Bob Secret Notif')


class Step11GlobalSearchTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='alice@lifeos.internal',
            email='alice@lifeos.internal',
            password='TestPassword@2026',
            first_name='Alice'
        )
        self.user_b = User.objects.create_user(
            username='bob@lifeos.internal',
            email='bob@lifeos.internal',
            password='TestPassword@2026',
            first_name='Bob'
        )
        self.client_a = Client()
        self.client_a.login(email='alice@lifeos.internal', password='TestPassword@2026')

        # Alice records
        self.task_a = Task.objects.create(
            user=self.user_a,
            title='Master Quantum Algorithms',
            description='Study Shor algorithm implementation in Qiskit'
        )
        self.habit_a = Habit.objects.create(
            user=self.user_a,
            name='Quantum Meditation',
            description='Daily mindfulness'
        )
        self.goal_a = Goal.objects.create(
            user=self.user_a,
            title='Publish Quantum Research Paper',
            description='Target submission to Quantum Journal'
        )
        self.journal_a = JournalEntry.objects.create(
            user=self.user_a,
            title='Quantum Breakthrough Thoughts',
            content='Discovered novel error correction scheme today',
            entry_date=timezone.now().date()
        )

        # Bob private records
        self.task_b = Task.objects.create(
            user=self.user_b,
            title='Bob Quantum Secret Weapon',
            description='Super confidential Quantum plan'
        )

    def test_global_search_returns_multi_entity_matches_for_user(self):
        res = GlobalSearchService.search(self.user_a, 'Quantum')
        self.assertEqual(res['total_count'], 4)
        types = set(res['results_by_type'].keys())
        self.assertIn('Task', types)
        self.assertIn('Habit', types)
        self.assertIn('Goal', types)
        self.assertIn('Journal', types)

    def test_global_search_strict_user_isolation(self):
        # Alice searches 'Quantum'
        resp = self.client_a.get(reverse('core:global_search') + '?q=Quantum')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Master Quantum Algorithms')
        self.assertContains(resp, 'Quantum Breakthrough Thoughts')
        # Bob's private records must NEVER appear in Alice's search
        self.assertNotContains(resp, 'Bob Quantum Secret Weapon')

    def test_global_search_empty_and_short_queries(self):
        resp_empty = self.client_a.get(reverse('core:global_search'))
        self.assertEqual(resp_empty.status_code, 200)
        self.assertContains(resp_empty, 'Global Search')

        resp_short = self.client_a.get(reverse('core:global_search') + '?q=q')
        self.assertEqual(resp_short.status_code, 200)
        self.assertEqual(resp_short.context['total_count'], 0)


class Step11RecommendationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='carol@lifeos.internal',
            email='carol@lifeos.internal',
            password='TestPassword@2026',
            first_name='Carol'
        )
        self.client = Client()
        self.client.login(email='carol@lifeos.internal', password='TestPassword@2026')
        self.today = timezone.now().date()

    def test_estimation_error_recommendation_triggered(self):
        # Create 3 completed tasks with underestimation >= 50%
        now = timezone.now()
        for i in range(3):
            Task.objects.create(
                user=self.user,
                title=f'Underestimated Task {i}',
                status=TaskStatus.COMPLETED,
                completed_at=now - timedelta(days=2),
                estimated_minutes=30,
                actual_minutes=75
            )

        recs = RecommendationService.get_recommendations(self.user)
        rec_keys = [r['key'] for r in recs]
        self.assertIn('productivity_estimation_error', rec_keys)

    def test_overdue_backlog_recommendation_triggered(self):
        # Create 3 overdue tasks
        for i in range(3):
            Task.objects.create(
                user=self.user,
                title=f'Overdue Task {i}',
                status=TaskStatus.PENDING,
                due_date=self.today - timedelta(days=3)
            )

        recs = RecommendationService.get_recommendations(self.user)
        rec_keys = [r['key'] for r in recs]
        self.assertIn('productivity_overdue_backlog', rec_keys)

    def test_recommendation_dismissal_and_reset(self):
        for i in range(3):
            Task.objects.create(
                user=self.user,
                title=f'Overdue Task {i}',
                status=TaskStatus.PENDING,
                due_date=self.today - timedelta(days=3)
            )

        # Initially present
        recs_before = RecommendationService.get_recommendations(self.user)
        self.assertIn('productivity_overdue_backlog', [r['key'] for r in recs_before])

        # Dismiss recommendation
        resp_dismiss = self.client.post(
            reverse('core:dismiss_recommendation', args=['productivity_overdue_backlog'])
        )
        self.assertRedirects(resp_dismiss, reverse('core:recommendations'))

        # Now omitted from recommendations
        recs_after = RecommendationService.get_recommendations(self.user)
        self.assertNotIn('productivity_overdue_backlog', [r['key'] for r in recs_after])

        # Reset dismissed
        resp_reset = self.client.post(reverse('core:reset_dismissed_recommendations'))
        self.assertRedirects(resp_reset, reverse('core:recommendations'))

        # Now present again
        recs_restored = RecommendationService.get_recommendations(self.user)
        self.assertIn('productivity_overdue_backlog', [r['key'] for r in recs_restored])


class Step11DataExportTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='alice@lifeos.internal',
            email='alice@lifeos.internal',
            password='TestPassword@2026',
            first_name='Alice'
        )
        self.user_b = User.objects.create_user(
            username='bob@lifeos.internal',
            email='bob@lifeos.internal',
            password='TestPassword@2026',
            first_name='Bob'
        )
        self.client_a = Client()
        self.client_a.login(email='alice@lifeos.internal', password='TestPassword@2026')

        Task.objects.create(user=self.user_a, title='Alice Secret Task', estimated_minutes=45)
        Task.objects.create(user=self.user_b, title='Bob Secret Task', estimated_minutes=90)

    def test_json_export_structure_and_security(self):
        resp = self.client_a.get(reverse('core:data_export') + '?format=json&module=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertIn('attachment', resp['Content-Disposition'])

        payload = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(payload['application'], 'LifeOS')
        self.assertEqual(payload['user']['username'], 'alice@lifeos.internal')

        tasks = payload['data']['tasks']
        task_titles = [t['title'] for t in tasks]
        self.assertIn('Alice Secret Task', task_titles)
        self.assertNotIn('Bob Secret Task', task_titles)

        # Passwords, salts, or security hashes must never exist
        content_str = resp.content.decode('utf-8')
        self.assertNotIn('password', content_str)
        self.assertNotIn('pbkdf2', content_str)

    def test_csv_single_module_export(self):
        resp = self.client_a.get(reverse('core:data_export') + '?format=csv&module=tasks')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        csv_text = resp.content.decode('utf-8')
        self.assertIn('Alice Secret Task', csv_text)
        self.assertNotIn('Bob Secret Task', csv_text)

    def test_csv_all_modules_zip_archive(self):
        resp = self.client_a.get(reverse('core:data_export') + '?format=csv&module=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/zip')

        # Read zip buffer
        zip_buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(zip_buf, 'r') as zf:
            namelist = zf.namelist()
            self.assertIn('tasks.csv', namelist)
            tasks_content = zf.read('tasks.csv').decode('utf-8')
            self.assertIn('Alice Secret Task', tasks_content)
            self.assertNotIn('Bob Secret Task', tasks_content)


class Step11SettingsAndPreferencesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dan@lifeos.internal',
            email='dan@lifeos.internal',
            password='TestPassword@2026',
            first_name='Dan'
        )
        self.client = Client()
        self.client.login(email='dan@lifeos.internal', password='TestPassword@2026')

    def test_settings_page_get_and_post_preferences(self):
        resp = self.client.get(reverse('core:settings'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Settings & Preferences')

        payload = {
            'action': 'save_preferences',
            'date_format': 'DD/MM/YYYY',
            'time_format': '12h',
            'week_start_day': 'sunday',
            'daily_work_goal_hours': '6.5',
            'notify_tasks': 'on',
            'notify_study': 'on',
            # notify_routines omitted (unchecked)
            # notify_goals omitted (unchecked)
            'timezone_pref': 'Europe/London'
        }
        resp_post = self.client.post(reverse('core:settings'), payload)
        self.assertRedirects(resp_post, reverse('core:settings'))

        prefs = UserPreference.get_for_user(self.user)
        self.assertEqual(prefs.date_format, 'DD/MM/YYYY')
        self.assertEqual(prefs.time_format, '12h')
        self.assertEqual(prefs.week_start_day, 'sunday')
        self.assertEqual(prefs.daily_work_goal_hours, Decimal('6.5'))
        self.assertTrue(prefs.notify_tasks)
        self.assertTrue(prefs.notify_study)
        self.assertFalse(prefs.notify_routines)
        self.assertFalse(prefs.notify_goals)

        self.user.refresh_from_db()
        self.assertEqual(self.user.timezone_pref, 'Europe/London')


class Step11CrossModuleIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='eve@lifeos.internal',
            email='eve@lifeos.internal',
            password='TestPassword@2026',
            first_name='Eve'
        )
        self.client = Client()
        self.client.login(email='eve@lifeos.internal', password='TestPassword@2026')
        self.today = timezone.now().date()

    def test_task_toggle_syncs_linked_schedule_block(self):
        task = Task.objects.create(
            user=self.user,
            title='Write Physics Report',
            status=TaskStatus.PENDING
        )
        block = ScheduleBlock.objects.create(
            user=self.user,
            title='Physics Report Block',
            block_date=self.today,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=ScheduleStatus.SCHEDULED,
            related_task=task
        )

        # Toggle task to COMPLETED from productivity view
        resp = self.client.post(reverse('productivity:task_toggle_complete', args=[task.id]))
        task.refresh_from_db()
        block.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(block.status, ScheduleStatus.COMPLETED)

        # Toggle back to PENDING from dashboard toggle
        resp_dash = self.client.post(reverse('core:toggle_task', args=[task.id]))
        task.refresh_from_db()
        block.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(block.status, ScheduleStatus.SCHEDULED)

    def test_study_session_syncs_study_plan_and_topic(self):
        subject = Subject.objects.create(
            user=self.user,
            name='Cognitive Science',
            code='COG101'
        )
        topic = Topic.objects.create(
            subject=subject,
            title='Working Memory Capacity'
        )
        plan = StudyPlan.objects.create(
            user=self.user,
            subject=subject,
            topic=topic,
            planned_date=self.today,
            status='PLANNED',
            estimated_minutes=60
        )

        # Log a completed study session
        payload = {
            'subject': subject.id,
            'topic': topic.id,
            'session_date': str(self.today),
            'start_time': '14:00',
            'end_time': '15:15',
            'duration_minutes': '75',
            'session_type': 'THEORY',
            'focus_rating': '8',
            'notes': 'Deep focus on Baddeley model'
        }
        resp = self.client.post(reverse('study:session_create'), payload)
        self.assertRedirects(resp, reverse('study:sessions'))

        plan.refresh_from_db()
        self.assertEqual(plan.status, 'COMPLETED')
        self.assertEqual(topic.actual_minutes, 75)
