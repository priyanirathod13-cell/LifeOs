from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    TASK = 'TASK', 'Task & Deadlines'
    STUDY = 'STUDY', 'Study & Learning'
    ROUTINE = 'ROUTINE', 'Routine & Schedule'
    GOAL = 'GOAL', 'Goals & Milestones'
    SYSTEM = 'SYSTEM', 'System & Intelligence'


class Notification(models.Model):
    """
    User-scoped in-app notifications for LifeOS.
    Tracks notifications across tasks, study plans, schedules, and behavioral milestones.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        help_text='Domain category of the notification'
    )
    title = models.CharField(
        max_length=200,
        help_text='Brief title or subject of notification'
    )
    message = models.TextField(
        help_text='Detailed notification message'
    )
    target_url = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Actionable deep-link URL (e.g., /tasks/ or /study/revisions/)'
    )
    is_read = models.BooleanField(
        default=False,
        help_text='Whether this notification has been marked as read'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{self.notification_type}] {self.title} ({status}) - {self.user.username}"


class UserPreference(models.Model):
    """
    User display, scheduling, and notification configuration preferences.
    """
    DATE_FORMAT_CHOICES = [
        ('YYYY-MM-DD', 'YYYY-MM-DD (2026-11-08)'),
        ('DD/MM/YYYY', 'DD/MM/YYYY (08/11/2026)'),
        ('MM/DD/YYYY', 'MM/DD/YYYY (11/08/2026)'),
    ]

    TIME_FORMAT_CHOICES = [
        ('24h', '24-hour (14:30)'),
        ('12h', '12-hour (2:30 PM)'),
    ]

    WEEK_START_CHOICES = [
        ('monday', 'Monday'),
        ('sunday', 'Sunday'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default='YYYY-MM-DD'
    )
    time_format = models.CharField(
        max_length=10,
        choices=TIME_FORMAT_CHOICES,
        default='24h'
    )
    week_start_day = models.CharField(
        max_length=10,
        choices=WEEK_START_CHOICES,
        default='monday'
    )
    daily_work_goal_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=8.0,
        help_text='Target productive hours per day'
    )
    notify_tasks = models.BooleanField(
        default=True,
        help_text='Receive alerts for upcoming and overdue tasks'
    )
    notify_study = models.BooleanField(
        default=True,
        help_text='Receive alerts for exam deadlines and revisions'
    )
    notify_routines = models.BooleanField(
        default=True,
        help_text='Receive schedule and timetable alerts'
    )
    notify_goals = models.BooleanField(
        default=True,
        help_text='Receive goal target date reminders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"

    @classmethod
    def get_for_user(cls, user):
        """Retrieve or create preferences for the user."""
        prefs, _ = cls.objects.get_or_create(user=user)
        return prefs


class DismissedRecommendation(models.Model):
    """
    Stores keys of recommendations that a user has explicitly dismissed
    so they are not repeatedly shown.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dismissed_recommendations'
    )
    recommendation_key = models.CharField(
        max_length=100,
        help_text='Unique identifier key of the recommendation rule instance'
    )
    dismissed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Dismissed Recommendation'
        verbose_name_plural = 'Dismissed Recommendations'
        unique_together = ('user', 'recommendation_key')
        ordering = ['-dismissed_at']

    def __str__(self):
        return f"{self.user.username} dismissed {self.recommendation_key}"
