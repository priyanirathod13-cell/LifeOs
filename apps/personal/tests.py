from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.personal.models import (
    DailyMetric,
    Decision,
    DecisionOption,
    DecisionOutcome,
    DecisionStatus,
    JournalEntry,
    Mistake,
    MistakeImpact,
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
            status=DecisionStatus.EVALUATING
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
            lesson_learned='Always write tests alongside models.'
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

        # Invalid mood score (> 10)
        invalid_mood = DailyMetric(
            user=self.user_a,
            metric_date=date(2026, 1, 2),
            mood_score=11
        )
        with self.assertRaises(ValidationError):
            invalid_mood.full_clean()
