from datetime import date, datetime, timedelta
import zoneinfo
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Notification, NotificationType, UserPreference
from apps.personal.models import DailyMetric
from apps.planning.models import Goal, GoalStatus
from apps.productivity.models import Task, TaskStatus
from apps.study.models import Exam, Revision, RevisionStatus, StudyPlan, Topic


class NotificationService:
    """
    Central service for dispatching, querying, deduplicating,
    and automatically generating contextual notifications for LifeOS users.
    """

    @staticmethod
    def get_unread_count(user):
        if not user or not user.is_authenticated:
            return 0
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def get_recent(user, limit=5):
        if not user or not user.is_authenticated:
            return []
        return Notification.objects.filter(user=user)[:limit]

    @staticmethod
    def create_notification(user, notification_type, title, message, target_url='', deduplicate_hours=12):
        """
        Creates an in-app notification for the user.
        If deduplicate_hours > 0, skips creation if an identical notification
        was created within the given timeframe.
        """
        if not user or not user.is_authenticated:
            return None

        if deduplicate_hours > 0:
            cutoff = timezone.now() - timedelta(hours=deduplicate_hours)
            existing = Notification.objects.filter(
                user=user,
                notification_type=notification_type,
                title=title,
                created_at__gte=cutoff
            ).exists()
            if existing:
                return None

        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            target_url=target_url,
            is_read=False
        )

    @classmethod
    def generate_system_notifications(cls, user):
        """
        Scans user modules and triggers proactive notifications based on preferences.
        """
        if not user or not user.is_authenticated:
            return

        prefs = UserPreference.get_for_user(user)

        user_tz_name = getattr(user, 'timezone_pref', None) or settings.TIME_ZONE
        try:
            user_tz = zoneinfo.ZoneInfo(user_tz_name)
        except Exception:
            user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

        now = timezone.now().astimezone(user_tz)
        today = now.date()

        # 1. Tasks: Overdue tasks alert
        if prefs.notify_tasks:
            overdue_count = Task.objects.filter(
                user=user,
                due_date__lt=today,
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
            ).count()
            if overdue_count > 0:
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.TASK,
                    title=f"{overdue_count} Overdue Task{'s' if overdue_count > 1 else ''}",
                    message=f"You have {overdue_count} pending task{'s' if overdue_count > 1 else ''} past deadline. Reschedule or complete them to keep your backlog clean.",
                    target_url='/tasks/?status=PENDING',
                    deduplicate_hours=12
                )

            # Due today tasks
            due_today_count = Task.objects.filter(
                user=user,
                due_date=today,
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
            ).count()
            if due_today_count > 0:
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.TASK,
                    title=f"{due_today_count} Task{'s' if due_today_count > 1 else ''} Due Today",
                    message=f"You have {due_today_count} task{'s' if due_today_count > 1 else ''} scheduled for completion today.",
                    target_url='/tasks/?due_date=today',
                    deduplicate_hours=12
                )

        # 2. Study: Upcoming Exams (< 7 days) and Pending Revisions
        if prefs.notify_study:
            upcoming_exams = Exam.objects.filter(
                user=user,
                exam_date__gte=today,
                exam_date__lte=today + timedelta(days=7)
            ).select_related('subject')
            for exam in upcoming_exams:
                days_left = (exam.exam_date - today).days
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.STUDY,
                    title=f"Exam Alert: {exam.subject.name} - {exam.exam_name}",
                    message=f"Exam scheduled on {exam.exam_date.strftime('%b %d, %Y')} ({days_left} day{'s' if days_left != 1 else ''} remaining). Max score: {exam.max_score or 'N/A'}.",
                    target_url='/study/exams/',
                    deduplicate_hours=24
                )

            # Revisions due today or overdue
            pending_revisions_count = Revision.objects.filter(
                user=user,
                revision_date__lte=today,
                status=RevisionStatus.PENDING
            ).count()
            if pending_revisions_count > 0:
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.STUDY,
                    title=f"{pending_revisions_count} Revision{'s' if pending_revisions_count > 1 else ''} Due",
                    message=f"Spaced repetition alert: {pending_revisions_count} topic revision{'s' if pending_revisions_count > 1 else ''} need review to preserve cognitive retention.",
                    target_url='/study/revisions/',
                    deduplicate_hours=12
                )

        # 3. Personal Check-in: Evening reminder if not logged
        if now.hour >= 18:
            has_checkin = DailyMetric.objects.filter(user=user, metric_date=today).exists()
            if not has_checkin:
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.SYSTEM,
                    title="Daily Reflection Reminder",
                    message="You haven't logged your daily check-in yet. Record your mood, energy, and cognitive reflections before the day ends.",
                    target_url='/checkin/',
                    deduplicate_hours=8
                )

        # 4. Goals: Approaching Milestones (< 3 days)
        if prefs.notify_goals:
            approaching_goals = Goal.objects.filter(
                user=user,
                status=GoalStatus.IN_PROGRESS,
                target_date__gte=today,
                target_date__lte=today + timedelta(days=3)
            )
            for goal in approaching_goals:
                days_left = (goal.target_date - today).days
                cls.create_notification(
                    user=user,
                    notification_type=NotificationType.GOAL,
                    title=f"Goal Milestone: {goal.title}",
                    message=f"Goal target date is in {days_left} day{'s' if days_left != 1 else ''} ({goal.target_date.strftime('%b %d')}). Status: {goal.get_status_display()}.",
                    target_url='/goals/',
                    deduplicate_hours=24
                )
