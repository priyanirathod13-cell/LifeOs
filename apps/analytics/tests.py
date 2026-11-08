from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import DismissedInsight
from apps.analytics.services.comparison_service import compare_periods, compute_delta
from apps.analytics.services.date_utils import parse_date_range
from apps.analytics.services.finance_service import get_finance_metrics
from apps.analytics.services.habit_service import get_habit_metrics
from apps.analytics.services.insights_engine import generate_behavioral_insights
from apps.analytics.services.productivity_service import get_productivity_metrics
from apps.analytics.services.study_service import get_study_metrics
from apps.analytics.services.time_service import get_time_metrics
from apps.analytics.services.wellbeing_service import (
    calculate_pearson_r,
    get_wellbeing_metrics,
)
from apps.finance.models import Transaction, TransactionType
from apps.personal.models import DailyMetric
from apps.productivity.models import (
    Activity,
    Category,
    CategoryType,
    Habit,
    HabitFrequency,
    HabitLog,
    ScheduleBlock,
    ScheduleStatus,
    Task,
    TaskStatus,
)
from apps.study.models import (
    PlanStatus,
    StudyPlan,
    StudySession,
    Subject,
    SubjectStatus,
    Topic,
    TopicStatus,
)

User = get_user_model()


class AnalyticsServiceUnitTests(TestCase):
    """
    Unit tests for analytical calculation engines, formulas, and statistical metrics.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='analytics_user',
            email='analytics@lifeos.dev',
            password='TestPassword123!',
        )
        self.other_user = User.objects.create_user(
            username='other_user',
            email='other@lifeos.dev',
            password='TestPassword123!',
        )
        self.today = date(2026, 11, 8)
        self.start_date = self.today - timedelta(days=6)
        self.end_date = self.today

    def test_date_utils_presets_and_bounds(self):
        """Test preset parsing: 7d, 30d, 90d, this_week, this_month, and custom."""
        p_7d = parse_date_range(self.user, {'range': '7d'})
        self.assertEqual(p_7d['days_count'], 7)
        self.assertEqual(p_7d['end_date'] - p_7d['start_date'], timedelta(days=6))

        p_30d = parse_date_range(self.user, {'range': '30d'})
        self.assertEqual(p_30d['days_count'], 30)

        p_week = parse_date_range(self.user, {'range': 'this_week'})
        self.assertEqual(p_week['days_count'], 7)

        # Custom bounds
        p_custom = parse_date_range(self.user, {
            'range': 'custom',
            'date_from': '2026-11-01',
            'date_to': '2026-11-05'
        })
        self.assertEqual(p_custom['days_count'], 5)
        self.assertEqual(p_custom['start_date'], date(2026, 11, 1))
        self.assertEqual(p_custom['end_date'], date(2026, 11, 5))

    def test_productivity_task_performance_and_estimation_error(self):
        """
        Verify:
        - Task completion percentage
        - Overdue task counting
        - Estimation Error = Actual - Estimated
        - Missing actual duration exclusion
        """
        # Task 1: Underestimated (took longer: 60 planned, 90 actual -> error = +30)
        Task.objects.create(
            user=self.user,
            title='Task Underestimated',
            status=TaskStatus.COMPLETED,
            estimated_minutes=60,
            actual_minutes=90,
            completed_at=timezone.make_aware(datetime(2026, 11, 7, 14, 0))
        )
        # Task 2: Overestimated (faster: 60 planned, 40 actual -> error = -20)
        Task.objects.create(
            user=self.user,
            title='Task Overestimated',
            status=TaskStatus.COMPLETED,
            estimated_minutes=60,
            actual_minutes=40,
            completed_at=timezone.make_aware(datetime(2026, 11, 7, 16, 0))
        )
        # Task 3: Missing actual duration (actual_minutes = None) -> MUST NOT be treated as zero!
        Task.objects.create(
            user=self.user,
            title='Task No Actual',
            status=TaskStatus.COMPLETED,
            estimated_minutes=45,
            actual_minutes=None,
            completed_at=timezone.make_aware(datetime(2026, 11, 6, 12, 0))
        )
        # Task 4: Pending Overdue task
        Task.objects.create(
            user=self.user,
            title='Task Overdue',
            status=TaskStatus.PENDING,
            due_date=self.today - timedelta(days=2),
        )

        metrics = get_productivity_metrics(self.user, self.start_date, self.end_date, today=self.today)

        # 3 completed, 1 pending
        self.assertEqual(metrics['completed_tasks'], 3)
        self.assertEqual(metrics['pending_tasks'], 1)
        self.assertEqual(metrics['overdue_tasks'], 1)
        self.assertEqual(metrics['completion_rate'], 75.0)

        # Estimation error: only 2 tasks have valid actual duration
        self.assertEqual(metrics['estimation_comparisons_count'], 2)
        # Total error = +30 + (-20) = +10 -> average error = 5.0
        self.assertEqual(metrics['avg_estimation_error'], 5.0)
        self.assertEqual(len(metrics['underestimated_tasks']), 1)
        self.assertEqual(metrics['underestimated_tasks'][0]['error'], 30)
        self.assertEqual(len(metrics['overestimated_tasks']), 1)
        self.assertEqual(metrics['overestimated_tasks'][0]['error'], -20)

    def test_study_duration_and_syllabus_progress(self):
        """
        Verify:
        - Study session duration aggregation
        - Subject-wise duration breakdown
        - Syllabus topic completion %
        - Planned vs actual study duration
        """
        subj = Subject.objects.create(
            user=self.user,
            name='Algorithms',
            code='CS301',
            status=SubjectStatus.ACTIVE
        )
        t1 = Topic.objects.create(subject=subj, title='Graphs', status=TopicStatus.COMPLETED)
        t2 = Topic.objects.create(subject=subj, title='Dynamic Programming', status=TopicStatus.IN_PROGRESS)

        # Study session of 120 mins (2.0 hours)
        StudySession.objects.create(
            user=self.user,
            subject=subj,
            topic=t1,
            session_date=self.today - timedelta(days=1),
            duration_minutes=120,
            focus_rating=9
        )
        # Study plan of 90 mins (1.5 hours)
        StudyPlan.objects.create(
            user=self.user,
            subject=subj,
            planned_date=self.today - timedelta(days=1),
            estimated_minutes=90,
            status=PlanStatus.COMPLETED
        )

        metrics = get_study_metrics(self.user, self.start_date, self.end_date, today=self.today)

        self.assertEqual(metrics['total_study_hours'], 2.0)
        self.assertEqual(metrics['sessions_count'], 1)
        self.assertEqual(metrics['active_study_days'], 1)
        # Syllabus: 1 completed of 2 total = 50.0%
        self.assertEqual(metrics['overall_syllabus_rate'], 50.0)
        # Planned vs actual: 2.0h actual - 1.5h planned = +0.5h
        self.assertEqual(metrics['total_planned_hours'], 1.5)
        self.assertEqual(metrics['planned_difference_hours'], 0.5)

    def test_habit_frequency_aware_completion_and_streaks(self):
        """
        Verify:
        - Weekly habits evaluated against target count (e.g. 3x/week in 7 days = 3 expected, not 7)
        - Daily habits evaluated against days count
        - Streaks reported accurately for daily habits
        """
        # Daily habit
        daily_h = Habit.objects.create(
            user=self.user,
            name='Daily Meditation',
            frequency=HabitFrequency.DAILY,
            target_count=1
        )
        # Log 5 completions across 7 days
        for i in range(5):
            HabitLog.objects.create(
                user=self.user,
                habit=daily_h,
                log_date=self.start_date + timedelta(days=i),
                completed=True
            )

        # Weekly habit: 3x per week
        weekly_h = Habit.objects.create(
            user=self.user,
            name='Workout',
            frequency=HabitFrequency.WEEKLY,
            target_count=3
        )
        # Log 3 completions
        for i in range(3):
            HabitLog.objects.create(
                user=self.user,
                habit=weekly_h,
                log_date=self.start_date + timedelta(days=i),
                completed=True
            )

        metrics = get_habit_metrics(self.user, self.start_date, self.end_date)

        self.assertEqual(metrics['total_active_habits'], 2)
        # Daily habit: 5 completed / 7 expected = 71.4%
        # Weekly habit: 3 completed / 3 expected = 100.0%
        h_dict = {h['name']: h for h in metrics['habits_list']}
        self.assertEqual(h_dict['Daily Meditation']['completed_count'], 5)
        self.assertEqual(h_dict['Daily Meditation']['expected_count'], 7)
        self.assertEqual(h_dict['Daily Meditation']['completion_rate'], 71.4)

        self.assertEqual(h_dict['Workout']['completed_count'], 3)
        self.assertEqual(h_dict['Workout']['expected_count'], 3)
        self.assertEqual(h_dict['Workout']['completion_rate'], 100.0)
        # Weekly habit streak direct validity is None to prevent false daily comparison
        self.assertIsNone(h_dict['Workout']['streak'])

    def test_wellbeing_correlations_and_minimum_data_threshold(self):
        """
        Verify:
        - Pearson correlation r calculation
        - Insufficient paired data (< 14 observations) flagged properly
        - Sufficient paired data (>= 14 observations) unlocks correlation
        """
        # Test math function directly
        x = [6.0, 7.0, 8.0, 9.0, 8.5]
        y = [5.0, 6.0, 8.0, 9.0, 8.0]
        r, n = calculate_pearson_r(x, y)
        self.assertIsNotNone(r)
        self.assertGreater(r, 0.8)  # Strong positive
        self.assertEqual(n, 5)

        # Populate only 10 daily metrics for the user (< 14 threshold)
        for i in range(10):
            d = self.today - timedelta(days=i)
            DailyMetric.objects.create(
                user=self.user,
                metric_date=d,
                mood_score=7,
                energy_score=6,
                stress_score=4,
                sleep_hours=Decimal('7.5')
            )

        wb_under = get_wellbeing_metrics(self.user, self.today - timedelta(days=9), self.today)
        self.assertEqual(wb_under['avg_mood'], 7.0)
        self.assertEqual(wb_under['avg_energy'], 6.0)
        self.assertEqual(wb_under['avg_sleep'], 7.5)

        # Verify correlations show has_min_data = False
        corr_sleep_energy = next(c for c in wb_under['correlations'] if c['pair_id'] == 'sleep_energy')
        self.assertFalse(corr_sleep_energy['has_min_data'])
        self.assertEqual(corr_sleep_energy['n'], 10)

        # Now add 5 more records (total 15 >= 14 threshold)
        for i in range(10, 15):
            d = self.today - timedelta(days=i)
            DailyMetric.objects.create(
                user=self.user,
                metric_date=d,
                mood_score=8,
                energy_score=7,
                stress_score=3,
                sleep_hours=Decimal('8.0')
            )

        wb_over = get_wellbeing_metrics(self.user, self.today - timedelta(days=14), self.today)
        corr_sleep_energy_over = next(c for c in wb_over['correlations'] if c['pair_id'] == 'sleep_energy')
        self.assertTrue(corr_sleep_energy_over['has_min_data'])
        self.assertGreaterEqual(corr_sleep_energy_over['n'], 14)

    def test_finance_metrics_aggregation(self):
        """Verify income, expenses, net balance, and category breakdown."""
        cat_food = Category.objects.create(user=self.user, name='Food', category_type=CategoryType.FINANCE)
        cat_rent = Category.objects.create(user=self.user, name='Housing', category_type=CategoryType.FINANCE)

        Transaction.objects.create(
            user=self.user,
            transaction_type=TransactionType.INCOME,
            amount=Decimal('50000.00'),
            transaction_date=self.today - timedelta(days=2)
        )
        Transaction.objects.create(
            user=self.user,
            category=cat_food,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('5000.00'),
            transaction_date=self.today - timedelta(days=2)
        )
        Transaction.objects.create(
            user=self.user,
            category=cat_rent,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('15000.00'),
            transaction_date=self.today - timedelta(days=1)
        )

        fin = get_finance_metrics(self.user, self.start_date, self.end_date)
        self.assertEqual(fin['total_income'], Decimal('50000.00'))
        self.assertEqual(fin['total_expenses'], Decimal('20000.00'))
        self.assertEqual(fin['net_balance'], Decimal('30000.00'))
        self.assertEqual(fin['savings_rate'], 60.0)
        self.assertEqual(fin['top_expense']['category'], 'Housing')
        self.assertEqual(fin['top_expense']['percentage'], 75.0)

    def test_comparison_delta_and_zero_denominator_safety(self):
        """
        Verify:
        - Absolute difference calculation
        - Percentage change calculation
        - Safe handling of zero baseline without division by zero error
        """
        # Normal case
        delta1 = compute_delta(curr_val=150, prev_val=100)
        self.assertEqual(delta1['diff'], 50.0)
        self.assertEqual(delta1['pct_change'], 50.0)
        self.assertEqual(delta1['pct_display'], '+50.0%')
        self.assertEqual(delta1['status'], 'positive')

        # Zero baseline case (Previous = 0)
        delta_zero = compute_delta(curr_val=20, prev_val=0)
        self.assertEqual(delta_zero['diff'], 20.0)
        self.assertIsNone(delta_zero['pct_change'])
        self.assertEqual(delta_zero['pct_display'], 'N/A (baseline was 0)')

    def test_behavioral_insights_generation_and_dismissal(self):
        """
        Verify:
        - Behavioral insight rule triggers based on real data
        - Dismissed insight is marked and excluded from active feed
        """
        # Create a keystone habit with 100% completion
        habit = Habit.objects.create(
            user=self.user,
            name='Daily Reading',
            frequency=HabitFrequency.DAILY,
            target_count=1
        )
        for i in range(7):
            HabitLog.objects.create(
                user=self.user,
                habit=habit,
                log_date=self.start_date + timedelta(days=i),
                completed=True
            )

        insights = generate_behavioral_insights(
            self.user, self.start_date, self.end_date,
            self.start_date - timedelta(days=7), self.start_date - timedelta(days=1)
        )

        # Should generate Keystone Habit insight
        self.assertTrue(any(i['category'] == 'HABITS' for i in insights))
        keystone_insight = next(i for i in insights if i['category'] == 'HABITS')
        self.assertFalse(keystone_insight['is_dismissed'])

        # Now dismiss it
        DismissedInsight.objects.create(user=self.user, insight_key=keystone_insight['key'])

        # Re-generate
        insights_after = generate_behavioral_insights(
            self.user, self.start_date, self.end_date,
            self.start_date - timedelta(days=7), self.start_date - timedelta(days=1)
        )
        dismissed_item = next(i for i in insights_after if i['key'] == keystone_insight['key'])
        self.assertTrue(dismissed_item['is_dismissed'])


class AnalyticsSecurityAndIntegrationTests(TestCase):
    """
    Tests for authentication enforcement, URL routing, view rendering,
    and strict multi-user data isolation.
    """

    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(
            username='user_alice',
            email='alice@lifeos.dev',
            password='AlicePassword123!',
        )
        self.user_b = User.objects.create_user(
            username='user_bob',
            email='bob@lifeos.dev',
            password='BobPassword123!',
        )

        # Alice creates a private task and habit
        self.alice_task = Task.objects.create(
            user=self.user_a,
            title='Secret Alice Task',
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
            actual_minutes=45,
            completed_at=timezone.make_aware(datetime(2026, 11, 7, 10, 0))
        )
        self.bob_task = Task.objects.create(
            user=self.user_b,
            title='Secret Bob Task',
            status=TaskStatus.COMPLETED,
            estimated_minutes=60,
            actual_minutes=90,
            completed_at=timezone.make_aware(datetime(2026, 11, 7, 10, 0))
        )

    def test_unauthenticated_access_redirects_to_login(self):
        """Verify unauthenticated requests are redirected to login."""
        urls = [
            reverse('analytics:dashboard'),
            reverse('analytics:productivity'),
            reverse('analytics:study'),
            reverse('analytics:habits'),
            reverse('analytics:time'),
            reverse('analytics:wellbeing'),
            reverse('analytics:insights'),
            reverse('analytics:compare'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_authenticated_view_rendering(self):
        """Verify authenticated users receive 200 OK across all analytics views."""
        self.client.login(username='user_alice', password='AlicePassword123!')
        urls = [
            reverse('analytics:dashboard'),
            reverse('analytics:productivity'),
            reverse('analytics:study'),
            reverse('analytics:habits'),
            reverse('analytics:time'),
            reverse('analytics:wellbeing'),
            reverse('analytics:insights'),
            reverse('analytics:compare'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_strict_multi_user_data_isolation(self):
        """
        Verify Alice cannot see Bob's metrics or tasks, and vice versa.
        """
        self.client.login(username='user_alice', password='AlicePassword123!')
        response = self.client.get(reverse('analytics:productivity'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Alice should see her task and estimation, but NOT Bob's
        self.assertIn('Secret Alice Task', content)
        self.assertNotIn('Secret Bob Task', content)

        # Login as Bob
        self.client.login(username='user_bob', password='BobPassword123!')
        response_bob = self.client.get(reverse('analytics:productivity'))
        self.assertEqual(response_bob.status_code, 200)
        content_bob = response_bob.content.decode()

        self.assertIn('Secret Bob Task', content_bob)
        self.assertNotIn('Secret Alice Task', content_bob)

    def test_insight_dismissal_and_restoration_api(self):
        """Verify POST endpoints for dismissing and restoring insights."""
        self.client.login(username='user_alice', password='AlicePassword123!')

        key = 'test_insight_key_123'
        # Dismiss
        dismiss_resp = self.client.post(reverse('analytics:dismiss_insight'), {
            'insight_key': key
        })
        self.assertEqual(dismiss_resp.status_code, 302)
        self.assertTrue(DismissedInsight.objects.filter(user=self.user_a, insight_key=key).exists())

        # Bob cannot see or alter Alice's dismissed insight
        self.assertFalse(DismissedInsight.objects.filter(user=self.user_b, insight_key=key).exists())

        # Restore
        restore_resp = self.client.post(reverse('analytics:restore_insight'), {
            'insight_key': key
        })
        self.assertEqual(restore_resp.status_code, 302)
        self.assertFalse(DismissedInsight.objects.filter(user=self.user_a, insight_key=key).exists())
