from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.personal.models import (
    DailyMetric,
    Decision,
    DecisionOption,
    DecisionOutcome,
    DecisionStatus,
    JournalEntry,
    Mistake,
    MistakeImpact,
    MistakeStatus,
    SleepRecord,
)
from apps.productivity.models import Category, CategoryType

User = get_user_model()


class PersonalModelsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_pers_a',
            email='pers_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_pers_b',
            email='pers_b@example.com',
            password='Password123!'
        )

        self.category_a = Category.objects.create(
            user=self.user_a,
            name='Mindset',
            category_type=CategoryType.DECISION
        )
        self.category_b = Category.objects.create(
            user=self.user_b,
            name='Mindset',
            category_type=CategoryType.DECISION
        )

    def test_journal_entry_creation(self):
        """Journal entries store reflections and index by date."""
        entry = JournalEntry.objects.create(
            user=self.user_a,
            entry_date=date.today(),
            title='Morning Clarity',
            content='Deep focus session went well today.',
            mood_tag='Focused'
        )
        self.assertIn('Morning Clarity', str(entry))

    def test_decision_option_and_outcome_integrity(self):
        """Decisions, options, and outcomes validate consistent parentage and scores."""
        decision1 = Decision.objects.create(
            user=self.user_a,
            category=self.category_a,
            title='Adopt MySQL or PostgreSQL for LifeOS',
            decision_date=date.today(),
            status=DecisionStatus.EVALUATING,
            reason_for_choosing='Performance on targeted host'
        )
        option_mysql = DecisionOption.objects.create(
            decision=decision1,
            option_name='MySQL 8.0 via XAMPP',
            pros='Pre-installed, lightweight, familiar',
            cons='Fewer advanced JSON types than Postgres'
        )
        decision2 = Decision.objects.create(
            user=self.user_a,
            title='Another Decision',
            decision_date=date.today()
        )
        option_other = DecisionOption.objects.create(
            decision=decision2,
            option_name='Unrelated Option'
        )

        # Cross-decision option linking in outcome fails validation
        mismatched_outcome = DecisionOutcome(
            decision=decision1,
            option=option_other,  # Belongs to decision2!
            actual_outcome='Ran into conflicts',
            outcome_score=5,
            outcome_date=date.today()
        )
        with self.assertRaises(ValidationError):
            mismatched_outcome.full_clean()

        # Outcome score must be between 1 and 10
        invalid_score_outcome = DecisionOutcome(
            decision=decision1,
            option=option_mysql,
            actual_outcome='Super result',
            outcome_score=15,  # Out of range
            outcome_date=date.today()
        )
        with self.assertRaises(ValidationError):
            invalid_score_outcome.full_clean()

        # Valid outcome
        valid_outcome = DecisionOutcome.objects.create(
            decision=decision1,
            option=option_mysql,
            actual_outcome='Flawless setup with zero friction',
            outcome_score=9,
            reflection_notes='Mental models proven true',
            outcome_date=date.today()
        )
        self.assertIn('Outcome for', str(valid_outcome))

    def test_mistake_creation_and_isolation(self):
        """Mistakes log lessons learned and enforce user category isolation."""
        mistake = Mistake.objects.create(
            user=self.user_a,
            category=self.category_a,
            title='Skipping unit tests in early phases',
            mistake_date=date.today(),
            impact_level=MistakeImpact.MODERATE,
            status=MistakeStatus.OPEN,
            cause_or_reason='Rushing to finish features',
            lesson_learned='Always write tests alongside models.',
            corrective_action='Enforce pre-commit test runs.'
        )
        self.assertEqual(str(mistake), 'Skipping unit tests in early phases')

        cross_mistake = Mistake(
            user=self.user_a,
            category=self.category_b,  # Belongs to user_b
            title='Cross User Mistake',
            mistake_date=date.today(),
            lesson_learned='Validation error expected'
        )
        with self.assertRaises(ValidationError):
            cross_mistake.full_clean()

    def test_daily_metric_uniqueness_and_ranges(self):
        """Daily metric enforces single entry per user per day, and valid score ranges."""
        today = date.today()
        dm = DailyMetric.objects.create(
            user=self.user_a,
            metric_date=today,
            mood_score=8,
            energy_score=9,
            stress_score=3,
            sleep_hours=Decimal('7.50')
        )
        self.assertIn('user_pers_a', str(dm))

        # Duplicate entry for same user and date violates unique constraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                DailyMetric.objects.create(
                    user=self.user_a,
                    metric_date=today,
                    mood_score=5
                )

        # Different user on same date succeeds
        dm_b = DailyMetric.objects.create(
            user=self.user_b,
            metric_date=today,
            mood_score=7
        )
        self.assertIsNotNone(dm_b.id)

        # Invalid sleep hours (> 24)
        invalid_sleep = DailyMetric(
            user=self.user_a,
            metric_date=date(2026, 1, 1),
            sleep_hours=Decimal('25.50')
        )
        with self.assertRaises(ValidationError):
            invalid_sleep.full_clean()

    def test_sleep_record_calculations_and_daily_metric_sync(self):
        """Sleep records handle overnight sleep, duration derivation, and DailyMetric synchronization."""
        # Overnight sleep session: 23:30 yesterday to 07:15 today (7.75 hours)
        wake_dt = timezone.now().replace(hour=7, minute=15, second=0, microsecond=0)
        sleep_dt = wake_dt - timedelta(hours=7, minutes=45)
        wake_date = wake_dt.date()

        record = SleepRecord(
            user=self.user_a,
            sleep_date=wake_date,
            sleep_start=sleep_dt,
            wake_time=wake_dt,
            quality_rating=4,
            notes='Woke up refreshed'
        )
        record.full_clean()
        record.save()

        self.assertEqual(record.duration_hours, Decimal('7.75'))

        # Check that DailyMetric was automatically updated/created
        dm = DailyMetric.objects.get(user=self.user_a, metric_date=wake_date)
        self.assertEqual(dm.sleep_hours, Decimal('7.75'))

        # Invalid: wake before start
        invalid_sleep = SleepRecord(
            user=self.user_a,
            sleep_date=wake_date,
            sleep_start=wake_dt,
            wake_time=sleep_dt,
            duration_hours=Decimal('1.0')
        )
        with self.assertRaises(ValidationError):
            invalid_sleep.full_clean()


class PersonalViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(
            username='user_view_a',
            email='view_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_view_b',
            email='view_b@example.com',
            password='Password123!'
        )
        self.client.login(username='user_view_a', password='Password123!')

    def test_views_require_login(self):
        """Unauthenticated requests redirect to login page."""
        self.client.logout()
        protected_urls = [
            reverse('personal:dashboard'),
            reverse('personal:journal_list'),
            reverse('personal:journal_create'),
            reverse('personal:checkin'),
            reverse('personal:mood_energy'),
            reverse('personal:sleep_list'),
            reverse('personal:decision_list'),
            reverse('personal:mistake_list'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    def test_personal_dashboard_authenticated(self):
        """Dashboard renders correctly with aggregate metrics."""
        response = self.client.get(reverse('personal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'personal/dashboard.html')
        self.assertIn('journal_month_count', response.context)
        self.assertIn('month_balance', response.context)

    def test_journal_crud_and_search_filter(self):
        """Journal creation, view, search, edit, and deletion workflows."""
        # Create
        create_url = reverse('personal:journal_create')
        post_data = {
            'title': 'Test Journal Title',
            'entry_date': '2026-11-08',
            'mood_tag': 'Clarity',
            'content': 'Comprehensive test content for private journal entry.',
        }
        res = self.client.post(create_url, post_data)
        self.assertEqual(res.status_code, 302)
        entry = JournalEntry.objects.get(user=self.user_a, title='Test Journal Title')
        self.assertEqual(entry.mood_tag, 'Clarity')

        # List with search
        list_url = reverse('personal:journal_list')
        res = self.client.get(list_url, {'q': 'Comprehensive'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Test Journal Title')

        # Edit
        edit_url = reverse('personal:journal_edit', kwargs={'pk': entry.pk})
        res = self.client.post(edit_url, {
            'title': 'Updated Journal Title',
            'entry_date': '2026-11-08',
            'mood_tag': 'Deep Focus',
            'content': 'Updated content text.',
        })
        self.assertEqual(res.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.title, 'Updated Journal Title')

        # Delete
        delete_url = reverse('personal:journal_delete', kwargs={'pk': entry.pk})
        res = self.client.post(delete_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(JournalEntry.objects.filter(pk=entry.pk).exists())

    def test_daily_checkin_flow(self):
        """Daily checkin view creates or updates entry on the specified date without duplicates."""
        checkin_url = reverse('personal:checkin')
        today_str = date.today().isoformat()

        # Submit initial check-in
        post_data = {
            'metric_date': today_str,
            'mood_score': 4,
            'energy_score': 5,
            'stress_score': 2,
            'sleep_hours': '7.5',
            'notes': 'High productivity day',
        }
        res = self.client.post(f"{checkin_url}?date={today_str}", post_data)
        self.assertEqual(res.status_code, 302)

        dm = DailyMetric.objects.get(user=self.user_a, metric_date=date.today())
        self.assertEqual(dm.mood_score, 4)
        self.assertEqual(dm.energy_score, 5)

        # Update the same date
        post_data['mood_score'] = 5
        res = self.client.post(f"{checkin_url}?date={today_str}", post_data)
        self.assertEqual(res.status_code, 302)

        dm.refresh_from_db()
        self.assertEqual(dm.mood_score, 5)
        self.assertEqual(DailyMetric.objects.filter(user=self.user_a, metric_date=date.today()).count(), 1)

    def test_sleep_tracking_crud(self):
        """Sleep session create, list, and delete."""
        create_url = reverse('personal:sleep_create')
        wake_dt = timezone.now()
        sleep_dt = wake_dt - timedelta(hours=8)
        res = self.client.post(create_url, {
            'sleep_date': wake_dt.date().isoformat(),
            'sleep_start': sleep_dt.strftime('%Y-%m-%dT%H:%M'),
            'wake_time': wake_dt.strftime('%Y-%m-%dT%H:%M'),
            'quality_rating': 5,
            'notes': 'Unbroken 8 hours',
        })
        self.assertEqual(res.status_code, 302)

        record = SleepRecord.objects.get(user=self.user_a, notes='Unbroken 8 hours')
        self.assertEqual(record.duration_hours, Decimal('8.00'))

        # List view
        res = self.client.get(reverse('personal:sleep_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '8.00 hrs')

    def test_decision_and_outcome_flow(self):
        """Decision creation, option addition, option selection, and outcome evaluation."""
        # 1. Create Decision
        res = self.client.post(reverse('personal:decision_create'), {
            'title': 'Launch LifeOS Publicly',
            'decision_date': '2026-11-08',
            'status': DecisionStatus.DRAFT,
            'description': 'Determine deployment strategy',
            'reason_for_choosing': '',
        })
        self.assertEqual(res.status_code, 302)
        dec = Decision.objects.get(user=self.user_a, title='Launch LifeOS Publicly')

        # 2. Add Candidate Option
        res = self.client.post(reverse('personal:decision_option_add', kwargs={'pk': dec.pk}), {
            'option_name': 'Deploy on Managed VPS',
            'description': 'Host with Nginx and Gunicorn',
            'pros': 'Full control, low cost',
            'cons': 'Requires maintenance',
            'expected_outcome': '99.9% uptime with stable database',
        })
        self.assertEqual(res.status_code, 302)
        opt = DecisionOption.objects.get(decision=dec, option_name='Deploy on Managed VPS')

        # 3. Select as Chosen
        res = self.client.post(reverse('personal:decision_select_option', kwargs={'pk': dec.pk, 'option_pk': opt.pk}))
        self.assertEqual(res.status_code, 302)
        dec.refresh_from_db()
        self.assertEqual(dec.chosen_option_id, opt.id)
        self.assertEqual(dec.status, DecisionStatus.DECIDED)

        # 4. Record Outcome
        res = self.client.post(reverse('personal:decision_outcome', kwargs={'pk': dec.pk}), {
            'option': opt.pk,
            'outcome_date': '2026-11-08',
            'outcome_score': 9,
            'actual_outcome': 'VPS setup went smoothly with SSL',
            'lessons_learned': 'Simplicity beats over-engineering',
            'reflection_notes': 'Maintain monthly backup scripts',
        })
        self.assertEqual(res.status_code, 302)
        dec.refresh_from_db()
        self.assertEqual(dec.status, DecisionStatus.REVIEWED)
        self.assertTrue(dec.outcomes.exists())

    def test_mistake_crud_flow(self):
        """Mistake creation, detail view, edit, and deletion."""
        create_url = reverse('personal:mistake_create')
        res = self.client.post(create_url, {
            'title': 'Hardcoded environment credentials in prototype',
            'mistake_date': '2026-11-08',
            'impact_level': MistakeImpact.SEVERE,
            'status': MistakeStatus.RESOLVED,
            'cause_or_reason': 'Rapid prototyping haste',
            'description': 'Pushed sensitive tokens to Git history.',
            'lesson_learned': 'Always configure .env and python-dotenv first.',
            'corrective_action': 'Install pre-commit secret scanner.',
            'follow_up_notes': 'Scanner verified clean.',
        })
        self.assertEqual(res.status_code, 302)
        m = Mistake.objects.get(user=self.user_a, title__icontains='Hardcoded')

        # Detail view
        res = self.client.get(reverse('personal:mistake_detail', kwargs={'pk': m.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Key Lesson Learned')

    def test_cross_user_data_isolation(self):
        """User B cannot access or modify User A's private personal records (IDOR protection)."""
        entry_a = JournalEntry.objects.create(
            user=self.user_a,
            entry_date=date.today(),
            title="User A's Secret Diary",
            content="Private personal thoughts"
        )
        dec_a = Decision.objects.create(
            user=self.user_a,
            title="User A's Private Decision",
            decision_date=date.today()
        )
        mistake_a = Mistake.objects.create(
            user=self.user_a,
            title="User A's Private Mistake",
            mistake_date=date.today(),
            lesson_learned="Private lesson"
        )
        sleep_a = SleepRecord.objects.create(
            user=self.user_a,
            sleep_date=date.today(),
            sleep_start=timezone.now() - timedelta(hours=8),
            wake_time=timezone.now(),
            duration_hours=Decimal('8.00')
        )

        # Switch to User B
        self.client.login(username='user_view_b', password='Password123!')

        # Attempts by User B to view or edit User A's records return 404
        self.assertEqual(self.client.get(reverse('personal:journal_detail', kwargs={'pk': entry_a.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('personal:journal_edit', kwargs={'pk': entry_a.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('personal:journal_delete', kwargs={'pk': entry_a.pk})).status_code, 404)

        self.assertEqual(self.client.get(reverse('personal:decision_detail', kwargs={'pk': dec_a.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('personal:decision_edit', kwargs={'pk': dec_a.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('personal:decision_delete', kwargs={'pk': dec_a.pk})).status_code, 404)

        self.assertEqual(self.client.get(reverse('personal:mistake_detail', kwargs={'pk': mistake_a.pk})).status_code, 404)
        self.assertEqual(self.client.get(reverse('personal:mistake_edit', kwargs={'pk': mistake_a.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('personal:mistake_delete', kwargs={'pk': mistake_a.pk})).status_code, 404)

        self.assertEqual(self.client.get(reverse('personal:sleep_edit', kwargs={'pk': sleep_a.pk})).status_code, 404)
        self.assertEqual(self.client.post(reverse('personal:sleep_delete', kwargs={'pk': sleep_a.pk})).status_code, 404)
