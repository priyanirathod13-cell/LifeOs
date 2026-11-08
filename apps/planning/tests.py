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


# ==============================================================================
# PLANNING VIEWS & FUNCTIONALITY TESTS
# ==============================================================================
from django.urls import reverse
from django.utils import timezone
from apps.productivity.models import TaskStatus


class GoalViewsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='goal_user_a', email='goala@test.com', password='Password123!')
        self.user_b = User.objects.create_user(username='goal_user_b', email='goalb@test.com', password='Password123!')
        self.goal_a = Goal.objects.create(
            user=self.user_a,
            title='Run Marathon',
            priority=Priority.HIGH,
            status=GoalStatus.IN_PROGRESS,
            target_date=date.today() + timedelta(days=60)
        )
        self.goal_b = Goal.objects.create(
            user=self.user_b,
            title='Learn Rust',
            priority=Priority.MEDIUM,
            status=GoalStatus.NOT_STARTED
        )
        self.task_a1 = Task.objects.create(user=self.user_a, title='Buy Running Shoes', status=TaskStatus.COMPLETED)
        self.task_a2 = Task.objects.create(user=self.user_a, title='Run 10km', status=TaskStatus.PENDING)
        self.task_b = Task.objects.create(user=self.user_b, title='Rust Book Ch 1')

    def test_goal_list_isolation_and_metrics(self):
        self.client.login(username='goal_user_a', password='Password123!')
        res = self.client.get(reverse('planning:goal_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Run Marathon')
        self.assertNotContains(res, 'Learn Rust')

    def test_goal_create_and_update(self):
        self.client.login(username='goal_user_a', password='Password123!')

        # Create
        res_create = self.client.post(reverse('planning:goal_create'), {
            'title': 'Read 20 Books',
            'priority': Priority.MEDIUM,
            'status': GoalStatus.IN_PROGRESS
        })
        self.assertRedirects(res_create, reverse('planning:goal_list'))
        self.assertTrue(Goal.objects.filter(user=self.user_a, title='Read 20 Books').exists())

        # Update
        res_edit = self.client.post(reverse('planning:goal_update', args=[self.goal_a.pk]), {
            'title': 'Run Marathon 2026',
            'priority': Priority.URGENT,
            'status': GoalStatus.ACHIEVED
        })
        self.assertRedirects(res_edit, reverse('planning:goal_detail', args=[self.goal_a.pk]))
        self.goal_a.refresh_from_db()
        self.assertEqual(self.goal_a.status, GoalStatus.ACHIEVED)
        self.assertIsNotNone(self.goal_a.achieved_at)

    def test_goal_detail_cross_user_forbidden(self):
        self.client.login(username='goal_user_a', password='Password123!')

        # Own goal
        res_own = self.client.get(reverse('planning:goal_detail', args=[self.goal_a.pk]))
        self.assertEqual(res_own.status_code, 200)

        # Other user's goal
        res_cross = self.client.get(reverse('planning:goal_detail', args=[self.goal_b.pk]))
        self.assertEqual(res_cross.status_code, 404)

    def test_goal_task_linking_and_unlinking(self):
        self.client.login(username='goal_user_a', password='Password123!')

        # Link own task
        url_link = reverse('planning:goal_link_task', args=[self.goal_a.pk])
        res_link = self.client.post(url_link, {'task': self.task_a1.pk})
        self.assertRedirects(res_link, reverse('planning:goal_detail', args=[self.goal_a.pk]))
        self.assertTrue(GoalTask.objects.filter(goal=self.goal_a, task=self.task_a1).exists())

        # Attempt to link cross-user task returns 404
        res_cross_link = self.client.post(url_link, {'task': self.task_b.pk})
        self.assertEqual(res_cross_link.status_code, 404)

        # Unlink task
        url_unlink = reverse('planning:goal_unlink_task', args=[self.goal_a.pk, self.task_a1.pk])
        res_unlink = self.client.post(url_unlink)
        self.assertRedirects(res_unlink, reverse('planning:goal_detail', args=[self.goal_a.pk]))
        self.assertFalse(GoalTask.objects.filter(goal=self.goal_a, task=self.task_a1).exists())
        self.assertTrue(Task.objects.filter(pk=self.task_a1.pk).exists())  # Task preserved

    def test_goal_delete_preserves_tasks(self):
        self.client.login(username='goal_user_a', password='Password123!')
        GoalTask.objects.create(goal=self.goal_a, task=self.task_a1)

        res = self.client.post(reverse('planning:goal_delete', args=[self.goal_a.pk]))
        self.assertRedirects(res, reverse('planning:goal_list'))
        self.assertFalse(Goal.objects.filter(pk=self.goal_a.pk).exists())
        self.assertTrue(Task.objects.filter(pk=self.task_a1.pk).exists())


class ProjectViewsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='proj_user_a', email='proja@test.com', password='Password123!')
        self.user_b = User.objects.create_user(username='proj_user_b', email='projb@test.com', password='Password123!')
        self.project_a = Project.objects.create(
            user=self.user_a,
            title='LifeOS Frontend',
            priority=Priority.HIGH,
            status=ProjectStatus.IN_PROGRESS
        )
        self.project_b = Project.objects.create(
            user=self.user_b,
            title='Secret Project B',
            priority=Priority.LOW,
            status=ProjectStatus.PLANNING
        )
        self.task_a1 = Task.objects.create(
            user=self.user_a,
            project=self.project_a,
            title='Build Navigation Bar',
            status=TaskStatus.COMPLETED
        )
        self.task_a2 = Task.objects.create(
            user=self.user_a,
            project=self.project_a,
            title='Implement Forms',
            status=TaskStatus.PENDING
        )

    def test_project_list_and_progress(self):
        self.client.login(username='proj_user_a', password='Password123!')
        res = self.client.get(reverse('planning:project_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'LifeOS Frontend')
        self.assertNotContains(res, 'Secret Project B')
        # Check progress calculation: 1 completed of 2 tasks = 50%
        self.assertContains(res, '50%')

    def test_project_create_and_update(self):
        self.client.login(username='proj_user_a', password='Password123!')

        # Create
        res_create = self.client.post(reverse('planning:project_create'), {
            'title': 'New Mobile App',
            'priority': Priority.HIGH,
            'status': ProjectStatus.PLANNING
        })
        self.assertRedirects(res_create, reverse('planning:project_list'))
        self.assertTrue(Project.objects.filter(user=self.user_a, title='New Mobile App').exists())

        # Update
        res_edit = self.client.post(reverse('planning:project_update', args=[self.project_a.pk]), {
            'title': 'LifeOS Frontend V2',
            'priority': Priority.URGENT,
            'status': ProjectStatus.COMPLETED
        })
        self.assertRedirects(res_edit, reverse('planning:project_detail', args=[self.project_a.pk]))
        self.project_a.refresh_from_db()
        self.assertEqual(self.project_a.title, 'LifeOS Frontend V2')
        self.assertEqual(self.project_a.status, ProjectStatus.COMPLETED)
        self.assertIsNotNone(self.project_a.completed_at)

    def test_project_detail_and_cross_user_isolation(self):
        self.client.login(username='proj_user_a', password='Password123!')

        # Own project detail
        res_own = self.client.get(reverse('planning:project_detail', args=[self.project_a.pk]))
        self.assertEqual(res_own.status_code, 200)
        self.assertContains(res_own, 'Build Navigation Bar')
        self.assertContains(res_own, 'Implement Forms')

        # Other user's project
        res_cross = self.client.get(reverse('planning:project_detail', args=[self.project_b.pk]))
        self.assertEqual(res_cross.status_code, 404)

    def test_project_delete_unlinks_tasks_safely(self):
        self.client.login(username='proj_user_a', password='Password123!')
        res_del = self.client.post(reverse('planning:project_delete', args=[self.project_a.pk]))
        self.assertRedirects(res_del, reverse('planning:project_list'))
        self.assertFalse(Project.objects.filter(pk=self.project_a.pk).exists())

        # Tasks must remain intact with project set to None
        self.task_a1.refresh_from_db()
        self.task_a2.refresh_from_db()
        self.assertIsNone(self.task_a1.project)
        self.assertIsNone(self.task_a2.project)
