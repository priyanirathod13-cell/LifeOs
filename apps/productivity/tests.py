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


# ==============================================================================
# PRODUCTIVITY VIEWS & FUNCTIONALITY TESTS
# ==============================================================================
from django.urls import reverse


class TaskViewsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='task_user_a',
            email='task_a@example.com',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='task_user_b',
            email='task_b@example.com',
            password='Password123!'
        )
        self.cat_a = Category.objects.create(
            user=self.user_a,
            name='Work',
            color='#3b82f6'
        )
        self.task_a1 = Task.objects.create(
            user=self.user_a,
            category=self.cat_a,
            title='Alpha Task',
            priority=Priority.HIGH,
            status=TaskStatus.PENDING,
            due_date=date.today()
        )
        self.task_a2 = Task.objects.create(
            user=self.user_a,
            title='Beta Task Completed',
            priority=Priority.LOW,
            status=TaskStatus.COMPLETED,
            completed_at=timezone.now()
        )
        self.task_b = Task.objects.create(
            user=self.user_b,
            title='User B Task',
            priority=Priority.URGENT,
            status=TaskStatus.PENDING
        )

    def test_task_list_isolation_and_filtering(self):
        self.client.login(username='task_user_a', password='Password123!')
        url = reverse('productivity:task_list')

        # User A sees only their own tasks
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Alpha Task')
        self.assertContains(res, 'Beta Task Completed')
        self.assertNotContains(res, 'User B Task')

        # Filter by status: pending
        res_pending = self.client.get(url, {'status': TaskStatus.PENDING})
        self.assertContains(res_pending, 'Alpha Task')
        self.assertNotContains(res_pending, 'Beta Task Completed')

        # Filter by priority: high
        res_priority = self.client.get(url, {'priority': Priority.HIGH})
        self.assertContains(res_priority, 'Alpha Task')
        self.assertNotContains(res_priority, 'Beta Task Completed')

        # Filter by search
        res_search = self.client.get(url, {'q': 'Alpha'})
        self.assertContains(res_search, 'Alpha Task')
        self.assertNotContains(res_search, 'Beta Task Completed')

    def test_task_create_view(self):
        self.client.login(username='task_user_a', password='Password123!')
        url = reverse('productivity:task_create')

        res = self.client.post(url, {
            'title': 'New Task Test',
            'description': 'Testing creation workflow',
            'category': self.cat_a.pk,
            'priority': Priority.MEDIUM,
            'status': TaskStatus.PENDING,
            'estimated_minutes': 45
        })
        self.assertRedirects(res, reverse('productivity:task_list'))
        created = Task.objects.filter(user=self.user_a, title='New Task Test').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.estimated_minutes, 45)

    def test_task_detail_and_cross_user_protection(self):
        self.client.login(username='task_user_a', password='Password123!')

        # Own task works
        url_own = reverse('productivity:task_detail', args=[self.task_a1.pk])
        res = self.client.get(url_own)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Alpha Task')

        # Another user's task returns 404
        url_cross = reverse('productivity:task_detail', args=[self.task_b.pk])
        res_cross = self.client.get(url_cross)
        self.assertEqual(res_cross.status_code, 404)

    def test_task_update_and_delete(self):
        self.client.login(username='task_user_a', password='Password123!')

        # Update
        url_edit = reverse('productivity:task_update', args=[self.task_a1.pk])
        res = self.client.post(url_edit, {
            'title': 'Alpha Task Renamed',
            'priority': Priority.URGENT,
            'status': TaskStatus.IN_PROGRESS,
            'estimated_minutes': 60
        })
        self.assertRedirects(res, reverse('productivity:task_detail', args=[self.task_a1.pk]))
        self.task_a1.refresh_from_db()
        self.assertEqual(self.task_a1.title, 'Alpha Task Renamed')
        self.assertEqual(self.task_a1.priority, Priority.URGENT)

        # Cross-user edit forbidden
        res_cross_edit = self.client.post(reverse('productivity:task_update', args=[self.task_b.pk]), {
            'title': 'Hacked Task'
        })
        self.assertEqual(res_cross_edit.status_code, 404)

        # Delete
        url_del = reverse('productivity:task_delete', args=[self.task_a1.pk])
        res_del = self.client.post(url_del)
        self.assertRedirects(res_del, reverse('productivity:task_list'))
        self.assertFalse(Task.objects.filter(pk=self.task_a1.pk).exists())

    def test_task_toggle_complete(self):
        self.client.login(username='task_user_a', password='Password123!')
        url = reverse('productivity:task_toggle_complete', args=[self.task_a1.pk])

        # Toggle from pending to completed
        self.client.post(url)
        self.task_a1.refresh_from_db()
        self.assertEqual(self.task_a1.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(self.task_a1.completed_at)

        # Toggle back to pending
        self.client.post(url)
        self.task_a1.refresh_from_db()
        self.assertEqual(self.task_a1.status, TaskStatus.PENDING)
        self.assertIsNone(self.task_a1.completed_at)


class CategoryViewsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='cat_user_a', email='cata@test.com', password='Password123!')
        self.user_b = User.objects.create_user(username='cat_user_b', email='catb@test.com', password='Password123!')
        self.cat_a = Category.objects.create(user=self.user_a, name='Design', color='#10b981')
        self.task_a = Task.objects.create(user=self.user_a, category=self.cat_a, title='Design Spec')

    def test_category_list_and_create(self):
        self.client.login(username='cat_user_a', password='Password123!')
        res = self.client.get(reverse('productivity:category_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Design')

        # Create new category
        res_create = self.client.post(reverse('productivity:category_create'), {
            'name': 'Fitness',
            'color': '#f59e0b',
            'category_type': CategoryType.HABIT
        })
        self.assertRedirects(res_create, reverse('productivity:category_list'))
        self.assertTrue(Category.objects.filter(user=self.user_a, name='Fitness').exists())

        # Duplicate name for same user fails form validation
        res_dup = self.client.post(reverse('productivity:category_create'), {
            'name': 'Design',
            'color': '#000000',
            'category_type': CategoryType.GENERAL
        })
        self.assertEqual(res_dup.status_code, 200)
        self.assertFormError(res_dup, 'form', 'name', 'You already have a category with this name.')

    def test_category_safe_deletion(self):
        self.client.login(username='cat_user_a', password='Password123!')
        url_del = reverse('productivity:category_delete', args=[self.cat_a.pk])

        # GET confirmation page
        res = self.client.get(url_del)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Delete Category')

        # POST delete unlinks task safely
        res_post = self.client.post(url_del)
        self.assertRedirects(res_post, reverse('productivity:category_list'))
        self.assertFalse(Category.objects.filter(pk=self.cat_a.pk).exists())
        self.task_a.refresh_from_db()
        self.assertIsNone(self.task_a.category)  # Unassigned without destroying task


class HabitViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='habit_user', email='habit@test.com', password='Password123!')
        self.habit = Habit.objects.create(
            user=self.user,
            name='Daily Reading',
            frequency=HabitFrequency.DAILY,
            target_count=1
        )

    def test_habit_list_and_create(self):
        self.client.login(username='habit_user', password='Password123!')
        res = self.client.get(reverse('productivity:habit_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Daily Reading')

        # Create
        res_create = self.client.post(reverse('productivity:habit_create'), {
            'name': 'Hydrate 2L',
            'frequency': HabitFrequency.DAILY,
            'target_count': 1,
            'is_active': True
        })
        self.assertRedirects(res_create, reverse('productivity:habit_list'))
        self.assertTrue(Habit.objects.filter(user=self.user, name='Hydrate 2L').exists())

    def test_habit_log_and_streak(self):
        self.client.login(username='habit_user', password='Password123!')
        today = date.today()
        url_log = reverse('productivity:habit_log', args=[self.habit.pk])

        # Log completion today
        res = self.client.post(url_log, {'log_date': today.isoformat(), 'completed': True})
        self.assertRedirects(res, reverse('productivity:habit_list'))
        log = HabitLog.objects.filter(habit=self.habit, log_date=today).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.completed)

        # Log past 2 days to verify streak
        HabitLog.objects.create(habit=self.habit, user=self.user, log_date=today - timedelta(days=1), completed=True)
        HabitLog.objects.create(habit=self.habit, user=self.user, log_date=today - timedelta(days=2), completed=True)

        res_detail = self.client.get(reverse('productivity:habit_detail', args=[self.habit.pk]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, '3 days')  # Streak is 3 days


class ActivityViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='act_user', email='act@test.com', password='Password123!')

    def test_activity_timer_start_and_stop(self):
        self.client.login(username='act_user', password='Password123!')

        # Start timer
        res_start = self.client.post(reverse('productivity:activity_start'), {
            'activity_name': 'Deep Focus Session'
        })
        self.assertRedirects(res_start, reverse('productivity:activity_list'))
        active = Activity.objects.filter(user=self.user, end_time__isnull=True).first()
        self.assertIsNotNone(active)
        self.assertEqual(active.activity_name, 'Deep Focus Session')

        # Stop timer
        res_stop = self.client.post(reverse('productivity:activity_stop', args=[active.pk]))
        self.assertRedirects(res_stop, reverse('productivity:activity_list'))
        active.refresh_from_db()
        self.assertIsNotNone(active.end_time)

    def test_activity_manual_create_and_delete(self):
        self.client.login(username='act_user', password='Password123!')
        now = timezone.now()

        res_create = self.client.post(reverse('productivity:activity_create'), {
            'activity_name': 'Manual Walk',
            'start_time': (now - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
            'end_time': now.strftime('%Y-%m-%dT%H:%M')
        })
        self.assertRedirects(res_create, reverse('productivity:activity_list'))
        act = Activity.objects.filter(user=self.user, activity_name='Manual Walk').first()
        self.assertIsNotNone(act)

        # Delete
        res_del = self.client.post(reverse('productivity:activity_delete', args=[act.pk]))
        self.assertRedirects(res_del, reverse('productivity:activity_list'))
        self.assertFalse(Activity.objects.filter(pk=act.pk).exists())
