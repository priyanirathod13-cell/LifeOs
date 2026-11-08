from datetime import date, datetime, time, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.planning.models import Project
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

User = get_user_model()


class ProductivityModelsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera',
            email='usera@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='userb',
            email='userb@example.com',
            password='Password123!'
        )

        self.category_a = Category.objects.create(
            user=self.user_a,
            name='Engineering',
            category_type=CategoryType.TASK,
            color='#3498db'
        )
        self.category_b = Category.objects.create(
            user=self.user_b,
            name='Engineering',  # Same name, different user
            category_type=CategoryType.TASK,
            color='#e74c3c'
        )

    def test_category_user_isolation_and_uniqueness(self):
        """Users can have identical category names, but same user cannot duplicate."""
        self.assertEqual(self.category_a.name, self.category_b.name)
        self.assertNotEqual(self.category_a.user, self.category_b.user)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Category.objects.create(
                    user=self.user_a,
                    name='Engineering',
                    category_type=CategoryType.GENERAL
                )

    def test_task_creation_and_cross_user_isolation(self):
        """Tasks cannot link to categories or projects of another user."""
        task = Task.objects.create(
            user=self.user_a,
            category=self.category_a,
            title='Test Task A',
            priority=Priority.HIGH,
            status=TaskStatus.PENDING,
            estimated_minutes=60,
            actual_minutes=45
        )
        self.assertEqual(str(task), 'Test Task A')

        # Attempt to link user_a task to user_b's category
        invalid_task = Task(
            user=self.user_a,
            category=self.category_b,
            title='Malicious Cross Link'
        )
        with self.assertRaises(ValidationError):
            invalid_task.full_clean()

    def test_task_cross_user_project_isolation(self):
        """Task cannot link to a project belonging to a different user."""
        project_b = Project.objects.create(
            user=self.user_b,
            title='Project B'
        )
        task = Task(
            user=self.user_a,
            project=project_b,
            title='Task linking Project B'
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_habit_and_habit_log_constraints(self):
        """Habit logs enforce uniqueness per day and user isolation."""
        habit = Habit.objects.create(
            user=self.user_a,
            category=self.category_a,
            name='Morning Run',
            frequency=HabitFrequency.DAILY,
            target_count=1
        )
        self.assertEqual(str(habit), 'Morning Run')

        # Cross-user category protection on habit
        invalid_habit = Habit(
            user=self.user_a,
            category=self.category_b,
            name='Invalid Run'
        )
        with self.assertRaises(ValidationError):
            invalid_habit.full_clean()

        today = date.today()
        log1 = HabitLog.objects.create(
            habit=habit,
            user=self.user_a,
            log_date=today,
            completed=True,
            notes='5k run'
        )
        self.assertIn('Morning Run', str(log1))

        # Duplicate log on same date violates unique constraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                HabitLog.objects.create(
                    habit=habit,
                    user=self.user_a,
                    log_date=today,
                    completed=True
                )

        # Cross-user habit log validation
        cross_log = HabitLog(
            habit=habit,
            user=self.user_b,
            log_date=today + timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            cross_log.full_clean()

    def test_activity_duration_and_time_validation(self):
        """Activity duration is computed dynamically and end time cannot precede start time."""
        now = timezone.now()
        start = now - timedelta(minutes=90)

        # Active session (end_time is None)
        active_activity = Activity.objects.create(
            user=self.user_a,
            activity_name='Coding Session',
            start_time=start,
            end_time=None
        )
        self.assertIsNone(active_activity.duration_minutes)

        # Completed session
        active_activity.end_time = now
        active_activity.save()
        self.assertEqual(active_activity.duration_minutes, 90)

        # End time before start time
        invalid_activity = Activity(
            user=self.user_a,
            activity_name='Time Travel',
            start_time=now,
            end_time=now - timedelta(minutes=10)
        )
        with self.assertRaises(ValidationError):
            invalid_activity.full_clean()

    def test_schedule_block_and_routine_isolation(self):
        """Schedule blocks cannot reference tasks or routines belonging to another user."""
        routine_b = Routine.objects.create(
            user=self.user_b,
            title='User B Evening Routine',
            start_time=time(22, 0),
            end_time=time(22, 30)
        )
        task_b = Task.objects.create(
            user=self.user_b,
            title='User B Task'
        )

        invalid_block = ScheduleBlock(
            user=self.user_a,
            title='User A Attempting Cross Access',
            block_date=date.today(),
            start_time=time(14, 0),
            end_time=time(15, 0),
            related_routine=routine_b
        )
        with self.assertRaises(ValidationError):
            invalid_block.full_clean()

        invalid_block.related_routine = None
        invalid_block.related_task = task_b
        with self.assertRaises(ValidationError):
            invalid_block.full_clean()
