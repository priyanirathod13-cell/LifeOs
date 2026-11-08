from datetime import time as datetime_time
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class DayOfWeek(models.TextChoices):
    MON = 'MON', 'Monday'
    TUE = 'TUE', 'Tuesday'
    WED = 'WED', 'Wednesday'
    THU = 'THU', 'Thursday'
    FRI = 'FRI', 'Friday'
    SAT = 'SAT', 'Saturday'
    SUN = 'SUN', 'Sunday'


class Priority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class HabitFrequency(models.TextChoices):
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'


class CategoryType(models.TextChoices):
    GENERAL = 'GENERAL', 'General'
    TASK = 'TASK', 'Task'
    HABIT = 'HABIT', 'Habit'
    ACTIVITY = 'ACTIVITY', 'Activity'
    STUDY = 'STUDY', 'Study'
    FINANCE = 'FINANCE', 'Finance'
    DECISION = 'DECISION', 'Decision'


class RoutineType(models.TextChoices):
    MORNING = 'MORNING', 'Morning Ritual'
    EVENING = 'EVENING', 'Evening Ritual'
    WORK = 'WORK', 'Work / College'
    MEAL = 'MEAL', 'Meal / Nutrition'
    EXERCISE = 'EXERCISE', 'Exercise & Fitness'
    SLEEP = 'SLEEP', 'Sleep & Rest'
    CHORE = 'CHORE', 'Household / Chores'
    OTHER = 'OTHER', 'Other Routine'


class BlockType(models.TextChoices):
    FOCUS = 'FOCUS', 'Focus & Deep Work'
    ROUTINE = 'ROUTINE', 'Personal Routine'
    STUDY = 'STUDY', 'Academic / Study'
    BREAK = 'BREAK', 'Rest & Break'
    MEETING = 'MEETING', 'Meeting'
    LEISURE = 'LEISURE', 'Leisure & Recovery'


class ScheduleStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    MISSED = 'MISSED', 'Missed'
    SKIPPED = 'SKIPPED', 'Skipped'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Category(models.Model):
    """
    User-scoped classification entity for tasks, habits, activities, and finances.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category_type = models.CharField(
        max_length=30,
        choices=CategoryType.choices,
        default=CategoryType.GENERAL
    )
    color = models.CharField(max_length=20, default='#818CF8')
    icon = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_category_name'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['user', 'category_type']),
        ]

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()

    def __str__(self):
        return self.name


class Task(models.Model):
    """
    Actionable task entity belonging to a user, with optional category and project.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks'
    )
    project = models.ForeignKey(
        'planning.Project',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING
    )
    due_date = models.DateField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    actual_minutes = models.PositiveIntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['due_date', '-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['user', 'priority']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(estimated_minutes__gte=0) | Q(estimated_minutes__isnull=True),
                name='task_estimated_minutes_positive'
            ),
            models.CheckConstraint(
                check=Q(actual_minutes__gte=0) | Q(actual_minutes__isnull=True),
                name='task_actual_minutes_positive'
            ),
        ]

    def clean(self):
        super().clean()
        # Enforce multi-user data isolation: category and project must belong to same user
        if self.user_id and self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.user_id and self.project and self.project.user_id != self.user_id:
            raise ValidationError({'project': 'Cannot associate with a project belonging to another user.'})

    def __str__(self):
        return self.title


class Habit(models.Model):
    """
    Recurring habit entity tracked over daily or weekly cadences.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habits'
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='habits'
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=20,
        choices=HabitFrequency.choices,
        default=HabitFrequency.DAILY
    )
    target_count = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Habit'
        verbose_name_plural = 'Habits'
        ordering = ['-is_active', 'name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(target_count__gte=1),
                name='habit_target_count_at_least_one'
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})

    def __str__(self):
        return self.name


class HabitLog(models.Model):
    """
    Historical log record verifying execution of a habit on a specific date.
    """
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='habit_logs'
    )
    log_date = models.DateField()
    completed = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Habit Log'
        verbose_name_plural = 'Habit Logs'
        ordering = ['-log_date']
        constraints = [
            models.UniqueConstraint(
                fields=['habit', 'log_date'],
                name='unique_habit_log_per_date'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'log_date']),
        ]

    def clean(self):
        super().clean()
        if self.habit and self.user_id and self.habit.user_id != self.user_id:
            raise ValidationError({'habit': 'Habit must belong to the same user as the log.'})

    def __str__(self):
        return f"{self.habit.name} - {self.log_date}"


class Activity(models.Model):
    """
    Time-tracked activity with start time and optional end time (null end_time indicates active session).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activities'
    )
    activity_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(end_time__isnull=True) | Q(end_time__gte=F('start_time')),
                name='activity_end_after_start'
            )
        ]

    @property
    def duration_minutes(self):
        """Derives duration reliably without storing redundant columns."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return max(0, int(delta.total_seconds() / 60))
        return None

    def clean(self):
        super().clean()
        if self.user_id and self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.end_time and self.start_time and self.end_time < self.start_time:
            raise ValidationError({'end_time': 'End time cannot be prior to start time.'})

    def __str__(self):
        return self.activity_name


class Routine(models.Model):
    """
    Recurring personal routine or fixed daily commitment (e.g. sleep, morning routine, work block).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routines'
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    routine_type = models.CharField(
        max_length=30,
        choices=RoutineType.choices,
        default=RoutineType.OTHER
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    days_of_week = models.CharField(
        max_length=50,
        default='MON,TUE,WED,THU,FRI,SAT,SUN',
        help_text='Comma-separated weekday codes (MON,TUE,WED,THU,FRI,SAT,SUN)'
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Routine'
        verbose_name_plural = 'Routines'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'Start time must be strictly before end time for single-day routines.'})
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be prior to start date.'})

        # Overlapping routine validation across shared weekdays
        if self.is_active and self.start_time and self.end_time and self.user_id:
            overlap_qs = Routine.objects.filter(
                user_id=self.user_id,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlap_qs = overlap_qs.exclude(pk=self.pk)
            if self.start_date:
                overlap_qs = overlap_qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=self.start_date))
            if self.end_date:
                overlap_qs = overlap_qs.filter(Q(start_date__isnull=True) | Q(start_date__lte=self.end_date))

            my_days = set(d.strip().upper() for d in (self.days_of_week or '').split(',') if d.strip())
            for other in overlap_qs:
                other_days = set(d.strip().upper() for d in (other.days_of_week or '').split(',') if d.strip())
                shared = my_days.intersection(other_days)
                if shared:
                    raise ValidationError(
                        f"Routine '{self.title}' conflicts with existing routine '{other.title}' "
                        f"({other.start_time.strftime('%H:%M')}-{other.end_time.strftime('%H:%M')} on {', '.join(sorted(shared))})."
                    )

    @property
    def days_list(self):
        return [d.strip().upper() for d in (self.days_of_week or '').split(',') if d.strip()]

    @property
    def duration_minutes(self):
        from datetime import datetime, date
        s = datetime.combine(date.today(), self.start_time)
        e = datetime.combine(date.today(), self.end_time)
        return max(0, int((e - s).total_seconds() / 60))

    def applies_on_date(self, target_date):
        if not self.is_active:
            return False
        if self.start_date and target_date < self.start_date:
            return False
        if self.end_date and target_date > self.end_date:
            return False
        day_code = target_date.strftime('%a').upper()
        return day_code in self.days_list

    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class AvailabilityWindow(models.Model):
    """
    Permitted or preferred productive working windows per weekday.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_windows'
    )
    day_of_week = models.CharField(max_length=3, choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Availability Window'
        verbose_name_plural = 'Availability Windows'
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['user', 'day_of_week', 'is_active']),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        if self.is_active and self.start_time and self.end_time and self.user_id:
            overlap_qs = AvailabilityWindow.objects.filter(
                user_id=self.user_id,
                day_of_week=self.day_of_week,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlap_qs = overlap_qs.exclude(pk=self.pk)
            if overlap_qs.exists():
                other = overlap_qs.first()
                raise ValidationError(
                    f"Overlaps with another availability window on {self.get_day_of_week_display()} "
                    f"({other.start_time.strftime('%H:%M')}-{other.end_time.strftime('%H:%M')})."
                )

    @property
    def duration_minutes(self):
        from datetime import datetime, date
        s = datetime.combine(date.today(), self.start_time)
        e = datetime.combine(date.today(), self.end_time)
        return max(0, int((e - s).total_seconds() / 60))

    def __str__(self):
        return f"{self.day_of_week}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


class ScheduleBlock(models.Model):
    """
    Individual planned or scheduled time block for a specific calendar date.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_blocks'
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    block_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    block_type = models.CharField(
        max_length=20,
        choices=BlockType.choices,
        default=BlockType.FOCUS
    )
    status = models.CharField(
        max_length=20,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.SCHEDULED
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        blank=True
    )
    is_fixed = models.BooleanField(
        default=False,
        help_text="True if fixed commitment from routine or unshiftable calendar block"
    )
    related_task = models.ForeignKey(
        Task,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='schedule_blocks'
    )
    related_routine = models.ForeignKey(
        Routine,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='schedule_blocks'
    )
    related_study_plan = models.ForeignKey(
        'study.StudyPlan',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='schedule_blocks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Schedule Block'
        verbose_name_plural = 'Schedule Blocks'
        ordering = ['block_date', 'start_time']
        indexes = [
            models.Index(fields=['user', 'block_date', 'start_time']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_fixed']),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        if self.user_id and self.related_task and self.related_task.user_id != self.user_id:
            raise ValidationError({'related_task': 'Related task must belong to the same user.'})
        if self.user_id and self.related_routine and self.related_routine.user_id != self.user_id:
            raise ValidationError({'related_routine': 'Related routine must belong to the same user.'})
        if self.user_id and self.related_study_plan and self.related_study_plan.user_id != self.user_id:
            raise ValidationError({'related_study_plan': 'Related study plan must belong to the same user.'})

    @property
    def duration_minutes(self):
        from datetime import datetime
        s = datetime.combine(self.block_date, self.start_time)
        e = datetime.combine(self.block_date, self.end_time)
        return max(0, int((e - s).total_seconds() / 60))

    def __str__(self):
        return f"{self.block_date} [{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}] {self.title}"


class SchedulingPreference(models.Model):
    """
    User settings governing timetable generation, available limits, and break insertion.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scheduling_preference'
    )
    day_start_time = models.TimeField(default=datetime_time(7, 0))
    day_end_time = models.TimeField(default=datetime_time(23, 0))
    default_break_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Standard rest duration inserted between long work sessions"
    )
    max_continuous_work_minutes = models.PositiveIntegerField(
        default=90,
        help_text="Threshold of continuous work before scheduling a mandatory break"
    )
    buffer_minutes = models.PositiveIntegerField(
        default=10,
        help_text="Spacing buffer between distinct schedule activities"
    )
    auto_insert_breaks = models.BooleanField(
        default=True,
        help_text="Automatically allocate breaks during timetable generation"
    )
    max_daily_work_minutes = models.PositiveIntegerField(
        default=480,
        help_text="Cap on total planned focus/study minutes per day (default 8h = 480m)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scheduling Preference'
        verbose_name_plural = 'Scheduling Preferences'

    @classmethod
    def get_for_user(cls, user):
        pref, _ = cls.objects.get_or_create(user=user)
        return pref

    def __str__(self):
        return f"Preferences for {self.user.username}"


class ScheduleGenerationHistory(models.Model):
    """
    Historical audit record of an automated or manual schedule generation run.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_histories'
    )
    generation_date = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    total_tasks_scheduled = models.PositiveIntegerField(default=0)
    total_study_scheduled = models.PositiveIntegerField(default=0)
    total_routines_scheduled = models.PositiveIntegerField(default=0)
    total_breaks_scheduled = models.PositiveIntegerField(default=0)
    total_work_minutes = models.PositiveIntegerField(default=0)
    unscheduled_items_json = models.TextField(blank=True, default='[]')
    status = models.CharField(max_length=20, default='APPLIED')

    class Meta:
        verbose_name = 'Schedule Generation History'
        verbose_name_plural = 'Schedule Generation Histories'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', 'generation_date']),
            models.Index(fields=['user', '-generated_at']),
        ]

    @property
    def unscheduled_items(self):
        import json
        try:
            return json.loads(self.unscheduled_items_json or '[]')
        except Exception:
            return []

    def __str__(self):
        return f"Schedule for {self.generation_date} generated at {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
