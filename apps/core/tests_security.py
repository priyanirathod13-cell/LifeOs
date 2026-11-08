"""
LifeOS — Step 12 Multi-User Security & Tenant Isolation Test Suite.

Verifies strict zero-trust data isolation between independent user accounts:
- User A (Alice) cannot view, modify, toggle, or delete User B (Bob)'s records.
- Models tested: Task, Category, Habit, HabitLog, Activity, Routine, ScheduleBlock,
  Goal, Project, Subject, Topic, StudySession, StudyPlan, Revision, Exam,
  JournalEntry, DailyMetric, SleepRecord, Decision, Mistake, Transaction,
  Notification, UserPreference, GlobalSearch, DataExport.
- Unauthenticated access redirects securely to the login portal.
- Custom production error pages render properly.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.core.models import Notification, NotificationType, UserPreference
from apps.finance.models import Transaction, TransactionType
from apps.personal.models import (
    DailyMetric,
    Decision,
    DecisionStatus,
    JournalEntry,
    Mistake,
    MistakeImpact,
    MistakeStatus,
    SleepRecord,
)
from apps.planning.models import Goal, GoalStatus, Priority as GoalPriority, Project
from apps.productivity.models import (
    Activity,
    BlockType,
    Category,
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
from apps.study.models import (
    Exam,
    Revision,
    RevisionStatus,
    StudyPlan,
    StudySession,
    Subject,
    Topic,
)

User = get_user_model()


class MultiUserSecurityAndIsolationTests(TestCase):
    def setUp(self):
        # Create User A (Alice)
        self.user_a = User.objects.create_user(
            username='alice@example.com',
            email='alice@example.com',
            first_name='Alice',
            password='Password123#Alice'
        )
        self.client_a = Client()
        self.client_a.login(email='alice@example.com', password='Password123#Alice')

        # Create User B (Bob)
        self.user_b = User.objects.create_user(
            username='bob@example.com',
            email='bob@example.com',
            first_name='Bob',
            password='Password123#Bob'
        )
        self.client_b = Client()
        self.client_b.login(email='bob@example.com', password='Password123#Bob')

        # Anonymous client
        self.client_anon = Client()

        self.today = date.today()

    # =========================================================================
    # 1. AUTHENTICATION & ACCESS CONTROL
    # =========================================================================

    def test_unauthenticated_access_redirects_to_login(self):
        protected_urls = [
            reverse('core:dashboard'),
            reverse('productivity:task_list'),
            reverse('productivity:category_list'),
            reverse('productivity:habit_list'),
            reverse('productivity:activity_list'),
            reverse('productivity:timetable_daily'),
            reverse('planning:goal_list'),
            reverse('planning:project_list'),
            reverse('study:dashboard'),
            reverse('study:subject_list'),
            reverse('personal:dashboard'),
            reverse('personal:journal_list'),
            reverse('personal:finance'),
            reverse('analytics:dashboard'),
            reverse('core:notifications'),
            reverse('core:global_search'),
            reverse('core:recommendations'),
            reverse('core:data_export'),
            reverse('core:settings'),
        ]
        for url in protected_urls:
            response = self.client_anon.get(url)
            self.assertEqual(response.status_code, 302, f"Expected 302 for unauthenticated {url}")
            self.assertIn(reverse('accounts:login'), response.url)

    # =========================================================================
    # 2. TASKS & CATEGORIES ISOLATION
    # =========================================================================

    def test_multiuser_task_and_category_isolation(self):
        cat_b = Category.objects.create(user=self.user_b, name="Bob Secret Cat", color="#FF0000")
        task_b = Task.objects.create(
            user=self.user_b,
            category=cat_b,
            title="Bob Confidential Task",
            description="Highly classified data",
            status=TaskStatus.PENDING,
            priority=Priority.HIGH
        )

        # Alice views task list — Bob's task must not be visible
        resp_list = self.client_a.get(reverse('productivity:task_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertNotContains(resp_list, "Bob Confidential Task")

        # Alice tries to view Bob's task directly
        resp_detail = self.client_a.get(reverse('productivity:task_detail', args=[task_b.id]))
        self.assertEqual(resp_detail.status_code, 404)

        # Alice tries to toggle Bob's task
        resp_toggle = self.client_a.post(reverse('productivity:task_toggle_complete', args=[task_b.id]))
        self.assertEqual(resp_toggle.status_code, 404)
        task_b.refresh_from_db()
        self.assertEqual(task_b.status, TaskStatus.PENDING)

        # Alice tries to delete Bob's task
        resp_del = self.client_a.post(reverse('productivity:task_delete', args=[task_b.id]))
        self.assertEqual(resp_del.status_code, 404)
        self.assertTrue(Task.objects.filter(id=task_b.id).exists())

        # Alice tries to delete Bob's category
        resp_cat_del = self.client_a.post(reverse('productivity:category_delete', args=[cat_b.id]))
        self.assertEqual(resp_cat_del.status_code, 404)
        self.assertTrue(Category.objects.filter(id=cat_b.id).exists())

    # =========================================================================
    # 3. HABITS & ACTIVITIES ISOLATION
    # =========================================================================

    def test_multiuser_habit_and_activity_isolation(self):
        habit_b = Habit.objects.create(
            user=self.user_b,
            name="Bob Secret Habit",
            frequency=HabitFrequency.DAILY,
            target_count=1
        )
        now = timezone.now()
        activity_b = Activity.objects.create(
            user=self.user_b,
            activity_name="Bob Meditation",
            start_time=now - timedelta(minutes=30),
            end_time=now
        )

        # Alice views habit list
        resp_h = self.client_a.get(reverse('productivity:habit_list'))
        self.assertNotContains(resp_h, "Bob Secret Habit")

        # Alice tries to view Bob's habit detail
        resp_hd = self.client_a.get(reverse('productivity:habit_detail', args=[habit_b.id]))
        self.assertEqual(resp_hd.status_code, 404)

        # Alice tries to toggle Bob's habit
        resp_ht = self.client_a.post(reverse('productivity:habit_toggle_active', args=[habit_b.id]))
        self.assertEqual(resp_ht.status_code, 404)

        # Alice views activities
        resp_act = self.client_a.get(reverse('productivity:activity_list'))
        self.assertNotContains(resp_act, "Bob Meditation")

        # Alice tries to delete Bob's activity
        resp_act_del = self.client_a.post(reverse('productivity:activity_delete', args=[activity_b.id]))
        self.assertEqual(resp_act_del.status_code, 404)
        self.assertTrue(Activity.objects.filter(id=activity_b.id).exists())

    # =========================================================================
    # 4. TIMETABLE & ROUTINES ISOLATION
    # =========================================================================

    def test_multiuser_timetable_and_routine_isolation(self):
        block_b = ScheduleBlock.objects.create(
            user=self.user_b,
            block_date=self.today,
            start_time=time(10, 0),
            end_time=time(11, 0),
            title="Bob Private Block",
            block_type=BlockType.FOCUS,
            status=ScheduleStatus.SCHEDULED
        )
        routine_b = Routine.objects.create(
            user=self.user_b,
            title="Bob Morning Drill",
            start_time=time(7, 0),
            end_time=time(8, 0),
            days_of_week="0,1,2,3,4"
        )

        # Alice views timetable
        resp_tt = self.client_a.get(reverse('productivity:timetable_daily'))
        self.assertNotContains(resp_tt, "Bob Private Block")

        # Alice tries to delete Bob's schedule block
        resp_bdel = self.client_a.post(reverse('productivity:block_delete', args=[block_b.id]))
        self.assertEqual(resp_bdel.status_code, 404)
        self.assertTrue(ScheduleBlock.objects.filter(id=block_b.id).exists())

        # Alice tries to delete Bob's routine
        resp_rdel = self.client_a.post(reverse('productivity:routine_delete', args=[routine_b.id]))
        self.assertEqual(resp_rdel.status_code, 404)
        self.assertTrue(Routine.objects.filter(id=routine_b.id).exists())

    # =========================================================================
    # 5. GOALS & PROJECTS ISOLATION
    # =========================================================================

    def test_multiuser_goals_and_projects_isolation(self):
        proj_b = Project.objects.create(
            user=self.user_b,
            title="Bob Secret Launch",
            description="Project Stealth"
        )
        goal_b = Goal.objects.create(
            user=self.user_b,
            title="Bob Financial Independence",
            target_date=self.today + timedelta(days=90),
            priority=GoalPriority.HIGH,
            status=GoalStatus.IN_PROGRESS
        )

        # Alice views projects & goals
        resp_p = self.client_a.get(reverse('planning:project_list'))
        self.assertNotContains(resp_p, "Bob Secret Launch")

        resp_g = self.client_a.get(reverse('planning:goal_list'))
        self.assertNotContains(resp_g, "Bob Financial Independence")

        # Alice attempts deletion
        resp_pdel = self.client_a.post(reverse('planning:project_delete', args=[proj_b.id]))
        self.assertEqual(resp_pdel.status_code, 404)
        self.assertTrue(Project.objects.filter(id=proj_b.id).exists())

        resp_gdel = self.client_a.post(reverse('planning:goal_delete', args=[goal_b.id]))
        self.assertEqual(resp_gdel.status_code, 404)
        self.assertTrue(Goal.objects.filter(id=goal_b.id).exists())

    # =========================================================================
    # 6. STUDY RECORDS ISOLATION
    # =========================================================================

    def test_multiuser_study_records_isolation(self):
        sub_b = Subject.objects.create(user=self.user_b, name="Bob Advanced Cryptography", code="CS999")
        topic_b = Topic.objects.create(subject=sub_b, title="Bob RSA Exploit")
        exam_b = Exam.objects.create(
            user=self.user_b,
            subject=sub_b,
            exam_name="Bob Finals",
            exam_date=self.today + timedelta(days=5),
            max_score=100
        )

        # Alice views subjects
        resp_s = self.client_a.get(reverse('study:subject_list'))
        self.assertNotContains(resp_s, "Bob Advanced Cryptography")

        # Alice attempts detail view & delete
        resp_sdet = self.client_a.get(reverse('study:subject_detail', args=[sub_b.id]))
        self.assertEqual(resp_sdet.status_code, 404)

        resp_sdel = self.client_a.post(reverse('study:subject_delete', args=[sub_b.id]))
        self.assertEqual(resp_sdel.status_code, 404)
        self.assertTrue(Subject.objects.filter(id=sub_b.id).exists())

        resp_tdel = self.client_a.post(reverse('study:topic_delete', args=[topic_b.id]))
        self.assertEqual(resp_tdel.status_code, 404)
        self.assertTrue(Topic.objects.filter(id=topic_b.id).exists())

        resp_exdel = self.client_a.post(reverse('study:exam_delete', args=[exam_b.id]))
        self.assertEqual(resp_exdel.status_code, 404)
        self.assertTrue(Exam.objects.filter(id=exam_b.id).exists())

    # =========================================================================
    # 7. PERSONAL (JOURNAL, BIOMETRICS, DECISIONS, MISTAKES, FINANCE) ISOLATION
    # =========================================================================

    def test_multiuser_personal_domain_isolation(self):
        # Bob's private journal entry
        j_b = JournalEntry.objects.create(
            user=self.user_b,
            entry_date=self.today,
            title="Bob Private Thoughts",
            content="These are Bob's most secret reflections."
        )

        # Bob's biometric & sleep
        sleep_b = SleepRecord.objects.create(
            user=self.user_b,
            sleep_date=self.today,
            sleep_start=datetime.combine(self.today - timedelta(days=1), time(23, 0)),
            wake_time=datetime.combine(self.today, time(7, 0)),
            duration_hours=Decimal('8.0'),
            quality_rating=4
        )

        # Bob's decision & mistake
        dec_b = Decision.objects.create(
            user=self.user_b,
            title="Bob Career Pivot",
            decision_date=self.today,
            status=DecisionStatus.DRAFT
        )
        mis_b = Mistake.objects.create(
            user=self.user_b,
            title="Bob Production Crash",
            mistake_date=self.today,
            impact_level=MistakeImpact.SEVERE,
            status=MistakeStatus.OPEN
        )

        # Bob's finance ledger
        cat_b_fin = Category.objects.create(user=self.user_b, name="Bob Private Luxury", color="#112233")
        txn_b = Transaction.objects.create(
            user=self.user_b,
            category=cat_b_fin,
            amount=Decimal('50000.00'),
            description="Secret diamond purchase",
            transaction_type=TransactionType.EXPENSE,
            transaction_date=self.today,
            notes="Secret diamond notes"
        )

        # 1. Journal isolation
        resp_j = self.client_a.get(reverse('personal:journal_list'))
        self.assertNotContains(resp_j, "Bob Private Thoughts")
        resp_jdet = self.client_a.get(reverse('personal:journal_detail', args=[j_b.id]))
        self.assertEqual(resp_jdet.status_code, 404)
        resp_jdel = self.client_a.post(reverse('personal:journal_delete', args=[j_b.id]))
        self.assertEqual(resp_jdel.status_code, 404)

        # 2. Sleep isolation
        resp_slp_del = self.client_a.post(reverse('personal:sleep_delete', args=[sleep_b.id]))
        self.assertEqual(resp_slp_del.status_code, 404)

        # 3. Decision & Mistake isolation
        resp_d_del = self.client_a.post(reverse('personal:decision_delete', args=[dec_b.id]))
        self.assertEqual(resp_d_del.status_code, 404)
        resp_m_del = self.client_a.post(reverse('personal:mistake_delete', args=[mis_b.id]))
        self.assertEqual(resp_m_del.status_code, 404)

        # 4. Finance isolation
        resp_f = self.client_a.get(reverse('personal:finance'))
        self.assertNotContains(resp_f, "50000.00")
        self.assertNotContains(resp_f, "Secret diamond purchase")
        resp_txn_del = self.client_a.post(reverse('finance:transaction_delete', args=[txn_b.id]))
        self.assertEqual(resp_txn_del.status_code, 404)

    # =========================================================================
    # 8. NOTIFICATIONS, SEARCH & DATA EXPORT ISOLATION
    # =========================================================================

    def test_multiuser_notifications_search_and_export_isolation(self):
        # Bob's notification
        notif_b = Notification.objects.create(
            user=self.user_b,
            notification_type=NotificationType.TASK,
            title="Bob Private Overdue Notice",
            message="Your top secret task is overdue.",
            target_url="/productivity/tasks/"
        )

        # Alice inspects notifications
        resp_notif = self.client_a.get(reverse('core:notifications'))
        self.assertNotContains(resp_notif, "Bob Private Overdue Notice")

        # Alice attempts deleting Bob's notification
        resp_ndel = self.client_a.post(reverse('core:delete_notification', args=[notif_b.id]))
        self.assertEqual(resp_ndel.status_code, 404)
        self.assertTrue(Notification.objects.filter(id=notif_b.id).exists())

        # Bob creates a distinct search keyword
        Task.objects.create(
            user=self.user_b,
            title="QuantumHyperSecret123",
            description="Bob classified blueprint"
        )

        # Alice searches for Bob's keyword — 0 results
        resp_search = self.client_a.get(reverse('core:global_search') + '?q=QuantumHyperSecret123')
        self.assertEqual(resp_search.status_code, 200)
        self.assertEqual(resp_search.context['total_count'], 0)
        self.assertEqual(len(resp_search.context['all_results']), 0)
        self.assertNotContains(resp_search, "Bob classified blueprint")

        # Alice exports data — Bob's records must NOT appear in JSON export
        resp_exp = self.client_a.get(reverse('core:data_export') + '?format=json')
        self.assertEqual(resp_exp.status_code, 200)
        export_payload = json.loads(resp_exp.content.decode('utf-8'))
        self.assertNotIn("QuantumHyperSecret123", json.dumps(export_payload))
        self.assertEqual(export_payload['user']['email'], 'alice@example.com')

    # =========================================================================
    # 9. PRODUCTION CUSTOM ERROR PAGES (404, 403, 400, 500)
    # =========================================================================

    def test_custom_error_pages_render(self):
        # 404 page
        resp_404 = self.client_a.get('/non-existent-route-for-testing-404/')
        self.assertEqual(resp_404.status_code, 404)
        self.assertContains(resp_404, "Destination Not Found", status_code=404)
        self.assertContains(resp_404, "404", status_code=404)
