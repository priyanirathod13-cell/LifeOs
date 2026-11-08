from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


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
    start_time = models.TimeField()
    end_time = models.TimeField()
    days_of_week = models.CharField(
        max_length=50,
        default='MON,TUE,WED,THU,FRI,SAT,SUN',
        help_text='Comma-separated weekday codes (MON,TUE,WED,THU,FRI,SAT,SUN)'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Routine'
        verbose_name_plural = 'Routines'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Schedule Block'
        verbose_name_plural = 'Schedule Blocks'
        ordering = ['block_date', 'start_time']
        indexes = [
            models.Index(fields=['user', 'block_date', 'start_time']),
            models.Index(fields=['user', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.related_task and self.related_task.user_id != self.user_id:
            raise ValidationError({'related_task': 'Related task must belong to the same user.'})
        if self.related_routine and self.related_routine.user_id != self.user_id:
            raise ValidationError({'related_routine': 'Related routine must belong to the same user.'})

    def __str__(self):
        return f"{self.block_date} [{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}] {self.title}"
