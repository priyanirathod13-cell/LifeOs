from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.planning.models import Goal, GoalStatus, GoalTask, Priority, Project, ProjectStatus
from apps.productivity.models import Category, CategoryType, Task

User = get_user_model()


class PlanningModelsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='user_planner_a',
            email='planner_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_planner_b',
            email='planner_b@example.com',
            password='Password123!'
        )

        self.category_a = Category.objects.create(
            user=self.user_a,
            name='Career Growth',
            category_type=CategoryType.GENERAL
        )
        self.category_b = Category.objects.create(
            user=self.user_b,
            name='Career Growth',
            category_type=CategoryType.GENERAL
        )

    def test_project_creation_and_validation(self):
        """Projects validate dates and category ownership."""
        start = date.today()
        target = start + timedelta(days=30)
        project = Project.objects.create(
            user=self.user_a,
            category=self.category_a,
            title='Launch Portfolio',
            priority=Priority.HIGH,
            status=ProjectStatus.IN_PROGRESS,
            start_date=start,
            target_date=target
        )
        self.assertEqual(str(project), 'Launch Portfolio')

        # Invalid target date before start date
        invalid_proj = Project(
            user=self.user_a,
            title='Time Reversal Project',
            start_date=target,
            target_date=start
        )
        with self.assertRaises(ValidationError):
            invalid_proj.full_clean()

        # Cross-user category violation
        cross_proj = Project(
            user=self.user_a,
            category=self.category_b,
            title='Cross User Category Project'
        )
        with self.assertRaises(ValidationError):
            cross_proj.full_clean()

    def test_goal_creation_and_validation(self):
        """Goals validate dates and category ownership."""
        start = date.today()
        target = start + timedelta(days=90)
        goal = Goal.objects.create(
            user=self.user_a,
            category=self.category_a,
            title='Master Cloud Architecture',
            priority=Priority.URGENT,
            status=GoalStatus.IN_PROGRESS,
            start_date=start,
            target_date=target
        )
        self.assertEqual(str(goal), 'Master Cloud Architecture')

        # Target date before start date
        invalid_goal = Goal(
            user=self.user_a,
            title='Invalid Goal',
            start_date=target,
            target_date=start
        )
        with self.assertRaises(ValidationError):
            invalid_goal.full_clean()

    def test_goal_task_cross_user_isolation_and_uniqueness(self):
        """GoalTask strictly enforces that Goal and Task belong to the exact same user."""
        goal_a = Goal.objects.create(
            user=self.user_a,
            title='Goal A'
        )
        task_a = Task.objects.create(
            user=self.user_a,
            title='Task A'
        )
        task_b = Task.objects.create(
            user=self.user_b,
            title='Task B'
        )

        # Legitimate link
        gt = GoalTask.objects.create(goal=goal_a, task=task_a)
        self.assertIn('Goal A', str(gt))

        # Duplicate link raises IntegrityError
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                GoalTask.objects.create(goal=goal_a, task=task_a)

        # Cross-user link fails clean() validation
        cross_gt = GoalTask(goal=goal_a, task=task_b)
        with self.assertRaises(ValidationError):
            cross_gt.full_clean()
