from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Priority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class ProjectStatus(models.TextChoices):
    PLANNING = 'PLANNING', 'Planning'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    ON_HOLD = 'ON_HOLD', 'On Hold'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class GoalStatus(models.TextChoices):
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    ACHIEVED = 'ACHIEVED', 'Achieved'
    ABANDONED = 'ABANDONED', 'Abandoned'


class Project(models.Model):
    """
    High-level project organizing tasks and deliverables towards an overarching objective.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    category = models.ForeignKey(
        'productivity.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='projects'
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
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING
    )
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['target_date', '-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'target_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(target_date__isnull=True) | Q(start_date__isnull=True) | Q(target_date__gte=models.F('start_date')),
                name='project_target_after_start'
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValidationError({'target_date': 'Target date cannot precede start date.'})

    def __str__(self):
        return self.title


class Goal(models.Model):
    """
    Strategic personal or professional ambition tracked with target dates and linked tasks.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals'
    )
    category = models.ForeignKey(
        'productivity.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='goals'
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
        choices=GoalStatus.choices,
        default=GoalStatus.NOT_STARTED
    )
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    achieved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Goal'
        verbose_name_plural = 'Goals'
        ordering = ['target_date', '-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'target_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(target_date__isnull=True) | Q(start_date__isnull=True) | Q(target_date__gte=models.F('start_date')),
                name='goal_target_after_start'
            )
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.category and self.category.user_id != self.user_id:
            raise ValidationError({'category': 'Cannot associate with a category belonging to another user.'})
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValidationError({'target_date': 'Target date cannot precede start date.'})

    def __str__(self):
        return self.title


class GoalTask(models.Model):
    """
    Explicit junction linking actionable tasks directly contributing towards a strategic goal.
    """
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name='goal_tasks'
    )
    task = models.ForeignKey(
        'productivity.Task',
        on_delete=models.CASCADE,
        related_name='goal_links'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Goal Task'
        verbose_name_plural = 'Goal Tasks'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['goal', 'task'],
                name='unique_goal_task'
            )
        ]

    def clean(self):
        super().clean()
        if self.goal and self.task:
            if self.goal.user_id != self.task.user_id:
                raise ValidationError('Goal and Task must belong to the exact same user.')

    def __str__(self):
        return f"{self.goal.title} -> {self.task.title}"
