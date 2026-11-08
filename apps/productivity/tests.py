from datetime import date, datetime, time, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.planning.models import Project
from apps.productivity.models import (
    Activity,
    AvailabilityWindow,
    BlockType,
    Category,
    CategoryType,
    DayOfWeek,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    Routine,
    RoutineType,
    ScheduleBlock,
    ScheduleGenerationHistory,
    ScheduleStatus,
    SchedulingPreference,
    Task,
    TaskStatus,
)
from apps.productivity.services import (
    TimetableGenerator,
    compute_free_intervals,
    detect_block_collision,
    detect_routine_overlap,
    find_next_free_slot,
    get_day_fixed_commitments,
    get_user_availability_windows,
    mark_block_skipped,
    reschedule_schedule_block,
)
from apps.study.models import PlanStatus, StudyPlan, Subject, SubjectType, Topic

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


# ==============================================================================
# STEP 08: ROUTINE & AVAILABILITY UNIT TESTS
# ==============================================================================

class RoutineAndAvailabilityTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sched_user', email='sched@example.com', password='Password123!')
        self.user_other = User.objects.create_user(username='other_sched', email='other@example.com', password='Password123!')

    def test_routine_creation_and_properties(self):
        """Routines store weekday codes, calculate duration, and evaluate date applicability."""
        routine = Routine.objects.create(
            user=self.user,
            title='Morning Gym',
            routine_type=RoutineType.EXERCISE,
            start_time=time(6, 30),
            end_time=time(7, 30),
            days_of_week='MON,WED,FRI',
            is_active=True
        )
        self.assertEqual(routine.duration_minutes, 60)
        self.assertEqual(routine.days_list, ['MON', 'WED', 'FRI'])

        # Check date applicability
        # 2026-11-09 is Monday, 2026-11-10 is Tuesday
        monday = date(2026, 11, 9)
        tuesday = date(2026, 11, 10)
        self.assertTrue(routine.applies_on_date(monday))
        self.assertFalse(routine.applies_on_date(tuesday))

    def test_routine_start_end_time_validation(self):
        """End time must be after start time for single-day routines."""
        invalid_routine = Routine(
            user=self.user,
            title='Inverted Routine',
            start_time=time(18, 0),
            end_time=time(17, 0),
            days_of_week='MON,TUE'
        )
        with self.assertRaises(ValidationError):
            invalid_routine.full_clean()

    def test_routine_conflict_detection_on_shared_weekdays(self):
        """Overlapping active routines on shared weekdays must be detected and rejected."""
        Routine.objects.create(
            user=self.user,
            title='College Lectures',
            routine_type=RoutineType.WORK,
            start_time=time(9, 0),
            end_time=time(13, 0),
            days_of_week='MON,TUE,WED,THU,FRI',
            is_active=True
        )

        # Conflicting routine overlapping from 10:00 to 11:30 on Wednesday
        conflict_routine = Routine(
            user=self.user,
            title='Conflicting Meeting',
            start_time=time(10, 0),
            end_time=time(11, 30),
            days_of_week='WED',
            is_active=True
        )
        with self.assertRaises(ValidationError):
            conflict_routine.full_clean()

        # Non-conflicting routine on Sunday
        sunday_routine = Routine(
            user=self.user,
            title='Sunday Study',
            start_time=time(10, 0),
            end_time=time(12, 0),
            days_of_week='SUN',
            is_active=True
        )
        sunday_routine.full_clean()  # Should pass!

    def test_availability_window_validation_and_overlap(self):
        """Availability windows reject invalid bounds and overlapping windows on the same weekday."""
        w1 = AvailabilityWindow.objects.create(
            user=self.user,
            day_of_week=DayOfWeek.MON,
            start_time=time(8, 0),
            end_time=time(12, 0),
            is_active=True
        )
        self.assertEqual(w1.duration_minutes, 240)

        # Inverted timing fails
        w_inv = AvailabilityWindow(
            user=self.user,
            day_of_week=DayOfWeek.MON,
            start_time=time(15, 0),
            end_time=time(14, 0),
        )
        with self.assertRaises(ValidationError):
            w_inv.full_clean()

        # Overlapping window on Monday fails
        w_overlap = AvailabilityWindow(
            user=self.user,
            day_of_week=DayOfWeek.MON,
            start_time=time(10, 0),
            end_time=time(14, 0),
            is_active=True
        )
        with self.assertRaises(ValidationError):
            w_overlap.full_clean()

        # Non-overlapping afternoon window on Monday succeeds
        w_afternoon = AvailabilityWindow(
            user=self.user,
            day_of_week=DayOfWeek.MON,
            start_time=time(14, 0),
            end_time=time(18, 0),
            is_active=True
        )
        w_afternoon.full_clean()


# ==============================================================================
# STEP 08: SCHEDULING GENERATOR ENGINE TESTS
# ==============================================================================

class TimetableGeneratorEngineTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gen_user', email='gen@example.com', password='Password123!')
        self.target_date = date(2026, 11, 9)  # Monday

        # Custom preferences
        self.pref = SchedulingPreference.objects.create(
            user=self.user,
            day_start_time=time(8, 0),
            day_end_time=time(20, 0),
            default_break_minutes=15,
            max_continuous_work_minutes=90,
            buffer_minutes=5,
            auto_insert_breaks=True,
            max_daily_work_minutes=360  # 6 hours max
        )

        # Fixed routine from 12:00 to 13:00 (Lunch)
        self.lunch = Routine.objects.create(
            user=self.user,
            title='Lunch Break',
            routine_type=RoutineType.MEAL,
            start_time=time(12, 0),
            end_time=time(13, 0),
            days_of_week='MON,TUE,WED,THU,FRI',
            is_active=True
        )

    def test_free_intervals_computation(self):
        """Free intervals correctly subtract fixed routines from available working hours."""
        avail_windows = get_user_availability_windows(self.user, self.target_date)
        fixed_commitments = get_day_fixed_commitments(self.user, self.target_date)

        free = compute_free_intervals(avail_windows, fixed_commitments, self.target_date)
        # Expect two intervals: 08:00 to 12:00 (240m) and 13:00 to 20:00 (420m)
        self.assertEqual(len(free), 2)
        self.assertEqual(free[0], (time(8, 0), time(12, 0), 240))
        self.assertEqual(free[1], (time(13, 0), time(20, 0), 420))

    def test_generator_deterministic_prioritization_and_allocation(self):
        """Generator prioritizes urgent deadlines, high priorities, and integrates study plans."""
        # 1. Urgent task due today (target_date)
        t_urgent = Task.objects.create(
            user=self.user,
            title='Urgent Tax Filing',
            priority=Priority.URGENT,
            status=TaskStatus.PENDING,
            due_date=self.target_date,
            estimated_minutes=60
        )

        # 2. Medium task with distant deadline
        t_medium = Task.objects.create(
            user=self.user,
            title='Clean Desk',
            priority=Priority.LOW,
            status=TaskStatus.PENDING,
            due_date=self.target_date + timedelta(days=10),
            estimated_minutes=30
        )

        # 3. Study plan scheduled for today
        subject = Subject.objects.create(
            user=self.user,
            name='Algorithms',
            subject_type=SubjectType.COLLEGE
        )
        study_plan = StudyPlan.objects.create(
            user=self.user,
            subject=subject,
            planned_date=self.target_date,
            estimated_minutes=90,
            priority=Priority.HIGH,
            status=PlanStatus.PLANNED
        )

        generator = TimetableGenerator(self.user, self.target_date, self.pref)
        preview = generator.generate()

        scheduled = preview['scheduled_blocks']
        self.assertGreater(len(scheduled), 0)

        # First scheduled block should be the urgent task or high priority study plan
        first_block = scheduled[0]
        self.assertEqual(first_block['related_task_id'], t_urgent.pk)
        self.assertEqual(first_block['start_time'], time(8, 0))

        # Check applying preview persists to ScheduleBlock
        history = generator.apply(preview)
        self.assertIsNotNone(history)
        self.assertTrue(ScheduleBlock.objects.filter(user=self.user, block_date=self.target_date).exists())

    def test_generator_max_work_cap_and_unscheduled_reporting(self):
        """Tasks exceeding the user's daily maximum work limit are reported as unscheduled."""
        # Create a huge 8-hour task when user cap is 6 hours (360m)
        Task.objects.create(
            user=self.user,
            title='Monumental Project Refactor',
            priority=Priority.HIGH,
            status=TaskStatus.PENDING,
            estimated_minutes=480
        )

        generator = TimetableGenerator(self.user, self.target_date, self.pref)
        preview = generator.generate()

        self.assertIn('unscheduled_items', preview)
        self.assertEqual(len(preview['unscheduled_items']), 1)
        self.assertIn('Exceeds max daily work limit', preview['unscheduled_items'][0]['reason'])


# ==============================================================================
# STEP 08: TIMETABLE & ROUTINE VIEWS END-TO-END TESTS
# ==============================================================================

class TimetableAndRoutineViewsTestCase(TestCase):
    def setUp(self):
        self.client_a = Client(SERVER_NAME='127.0.0.1')
        self.client_b = Client(SERVER_NAME='127.0.0.1')

        self.user_a = User.objects.create_user(username='alice_time', email='alice_t@test.com', password='Password123!')
        self.user_b = User.objects.create_user(username='bob_time', email='bob_t@test.com', password='Password123!')

        self.client_a.force_login(self.user_a)
        self.client_b.force_login(self.user_b)

        self.target_date = date.today()

        # Alice's schedule block
        self.block_a = ScheduleBlock.objects.create(
            user=self.user_a,
            title='Architecture Design',
            block_date=self.target_date,
            start_time=time(9, 0),
            end_time=time(10, 30),
            block_type=BlockType.FOCUS,
            status=ScheduleStatus.SCHEDULED,
            priority=Priority.HIGH,
            is_fixed=False
        )

        # Alice's routine
        self.routine_a = Routine.objects.create(
            user=self.user_a,
            title='Morning Standup',
            routine_type=RoutineType.WORK,
            start_time=time(10, 30),
            end_time=time(11, 0),
            days_of_week='MON,TUE,WED,THU,FRI',
            is_active=True
        )

    def test_daily_and_weekly_timetable_views(self):
        """Daily and weekly views return 200 OK and isolate user data."""
        # Daily
        res_daily = self.client_a.get(reverse('productivity:timetable_daily'))
        self.assertEqual(res_daily.status_code, 200)
        self.assertContains(res_daily, 'Architecture Design')

        # Weekly
        res_weekly = self.client_a.get(reverse('productivity:timetable_weekly'))
        self.assertEqual(res_weekly.status_code, 200)
        self.assertContains(res_weekly, 'Architecture Design')

        # Check core aliases
        res_alias_tt = self.client_a.get(reverse('core:timetable'))
        self.assertEqual(res_alias_tt.status_code, 200)
        res_alias_rt = self.client_a.get(reverse('core:routines'))
        self.assertEqual(res_alias_rt.status_code, 200)

    def test_schedule_block_status_action_and_task_sync(self):
        """Completing a schedule block marks linked Task as completed."""
        task = Task.objects.create(
            user=self.user_a,
            title='Write Unit Tests',
            status=TaskStatus.PENDING,
            estimated_minutes=45
        )
        self.block_a.related_task = task
        self.block_a.save()

        res = self.client_a.post(
            reverse('productivity:block_status', args=[self.block_a.pk]),
            {'status': 'COMPLETED'}
        )
        self.assertEqual(res.status_code, 302)

        self.block_a.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(self.block_a.status, ScheduleStatus.COMPLETED)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.actual_minutes, self.block_a.duration_minutes)

    def test_schedule_block_reschedule_action(self):
        """Rescheduling moves a block to a new date and updates start/end times."""
        tomorrow = self.target_date + timedelta(days=1)
        res = self.client_a.post(
            reverse('productivity:block_reschedule', args=[self.block_a.pk]),
            {'new_date': tomorrow.strftime('%Y-%m-%d')}
        )
        self.assertEqual(res.status_code, 302)
        self.block_a.refresh_from_db()
        self.assertEqual(self.block_a.block_date, tomorrow)

    def test_routine_crud_workflow(self):
        """User can create, edit, toggle active, and delete routines."""
        # Create
        res_create = self.client_a.post(reverse('productivity:routine_create'), {
            'title': 'Evening Walk',
            'routine_type': RoutineType.EXERCISE,
            'start_time': '18:00',
            'end_time': '18:45',
            'days_list': ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'],
            'is_active': True,
        })
        self.assertEqual(res_create.status_code, 302)
        new_routine = Routine.objects.filter(user=self.user_a, title='Evening Walk').first()
        self.assertIsNotNone(new_routine)

        # Toggle Active
        res_toggle = self.client_a.post(reverse('productivity:routine_toggle_active', args=[new_routine.pk]))
        self.assertEqual(res_toggle.status_code, 302)
        new_routine.refresh_from_db()
        self.assertFalse(new_routine.is_active)

        # Delete
        res_del = self.client_a.post(reverse('productivity:routine_delete', args=[new_routine.pk]))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Routine.objects.filter(pk=new_routine.pk).exists())

    def test_availability_crud_workflow(self):
        """User can create and delete custom availability windows."""
        res_create = self.client_a.post(reverse('productivity:availability_create'), {
            'day_of_week': DayOfWeek.WED,
            'start_time': '07:00',
            'end_time': '11:00',
            'is_active': True
        })
        self.assertEqual(res_create.status_code, 302)
        win = AvailabilityWindow.objects.filter(user=self.user_a, day_of_week=DayOfWeek.WED).first()
        self.assertIsNotNone(win)

        # Delete
        res_del = self.client_a.post(reverse('productivity:availability_delete', args=[win.pk]))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(AvailabilityWindow.objects.filter(pk=win.pk).exists())

    def test_schedule_generator_preview_and_apply(self):
        """Generator view produces preview; apply action creates ScheduleBlocks and History."""
        # Add a pending task
        Task.objects.create(
            user=self.user_a,
            title='Prepare Presentation',
            priority=Priority.HIGH,
            status=TaskStatus.PENDING,
            estimated_minutes=60
        )

        gen_date = self.target_date + timedelta(days=2)

        # Preview GET
        res_preview = self.client_a.get(reverse('productivity:generator'), {'date': gen_date.strftime('%Y-%m-%d')})
        self.assertEqual(res_preview.status_code, 200)
        self.assertContains(res_preview, 'Prepare Presentation')

        # Apply POST
        res_apply = self.client_a.post(reverse('productivity:generator_apply'), {
            'target_date': gen_date.strftime('%Y-%m-%d'),
            'replace_existing': '1'
        })
        self.assertEqual(res_apply.status_code, 302)

        # Verify created blocks and history
        self.assertTrue(ScheduleBlock.objects.filter(user=self.user_a, block_date=gen_date).exists())
        self.assertTrue(ScheduleGenerationHistory.objects.filter(user=self.user_a, generation_date=gen_date).exists())

    def test_cross_user_idor_isolation(self):
        """User B cannot view, edit, reschedule, or delete User A's schedule blocks or routines."""
        # Block edit
        res_block_edit = self.client_b.get(reverse('productivity:block_update', args=[self.block_a.pk]))
        self.assertEqual(res_block_edit.status_code, 404)

        # Block delete
        res_block_del = self.client_b.post(reverse('productivity:block_delete', args=[self.block_a.pk]))
        self.assertEqual(res_block_del.status_code, 404)

        # Routine edit
        res_routine_edit = self.client_b.get(reverse('productivity:routine_update', args=[self.routine_a.pk]))
        self.assertEqual(res_routine_edit.status_code, 404)

        # Routine delete
        res_routine_del = self.client_b.post(reverse('productivity:routine_delete', args=[self.routine_a.pk]))
        self.assertEqual(res_routine_del.status_code, 404)

