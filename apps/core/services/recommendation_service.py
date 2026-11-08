from datetime import date, datetime, timedelta
from decimal import Decimal
import zoneinfo
from django.conf import settings
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

from apps.core.models import DismissedRecommendation
from apps.personal.models import DailyMetric
from apps.productivity.models import Habit, HabitLog, Priority, ScheduleBlock, ScheduleStatus, Task, TaskStatus
from apps.study.models import Exam, Revision, RevisionStatus, StudyPlan, Subject, Topic, TopicStatus


class RecommendationService:
    """
    Deterministic rule-based behavioral intelligence recommendation engine for LifeOS.
    Analyzes historical patterns across tasks, study, habits, schedules, and biometrics
    to output contextual, prioritized, actionable suggestions.
    """

    @classmethod
    def get_recommendations(cls, user, category_filter=None):
        if not user or not user.is_authenticated:
            return []

        # Retrieve all dismissed recommendation keys for this user
        dismissed_keys = set(
            DismissedRecommendation.objects.filter(user=user).values_list('recommendation_key', flat=True)
        )

        user_tz_name = getattr(user, 'timezone_pref', None) or settings.TIME_ZONE
        try:
            user_tz = zoneinfo.ZoneInfo(user_tz_name)
        except Exception:
            user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

        now = timezone.now().astimezone(user_tz)
        today = now.date()

        recs = []

        # ----------------------------------------------------------------------
        # 1. PRODUCTIVITY: Time Estimation Accuracy Calibration
        # ----------------------------------------------------------------------
        rec_key = 'productivity_estimation_error'
        if rec_key not in dismissed_keys:
            # Check completed tasks with both estimated and actual minutes in last 14 days
            completed_tasks = Task.objects.filter(
                user=user,
                status=TaskStatus.COMPLETED,
                completed_at__gte=now - timedelta(days=14),
                estimated_minutes__gt=0,
                actual_minutes__gt=0
            )
            count_est = completed_tasks.count()
            if count_est >= 3:
                underestimated = [t for t in completed_tasks if t.actual_minutes > t.estimated_minutes]
                underest_ratio = len(underestimated) / count_est
                if underest_ratio >= 0.5:
                    avg_error = sum(t.actual_minutes - t.estimated_minutes for t in underestimated) / len(underestimated)
                    recs.append({
                        'key': rec_key,
                        'category': 'Productivity',
                        'priority': 'high' if avg_error >= 30 else 'medium',
                        'title': 'Calibrate Task Duration Estimates',
                        'description': f"In {round(underest_ratio * 100)}% of recent tasks, actual execution exceeded planned duration by an average of {round(avg_error)} minutes.",
                        'rationale': "Systematic underestimation creates schedule compression and spillover stress. Add a 20-30% buffer to future task estimates.",
                        'action_url': '/tasks/',
                        'action_label': 'Review Task Backlog',
                    })

        # ----------------------------------------------------------------------
        # 2. PRODUCTIVITY: Overdue Task Backlog
        # ----------------------------------------------------------------------
        rec_key = 'productivity_overdue_backlog'
        if rec_key not in dismissed_keys:
            overdue_count = Task.objects.filter(
                user=user,
                due_date__lt=today,
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
            ).count()
            if overdue_count >= 3:
                recs.append({
                    'key': rec_key,
                    'category': 'Productivity',
                    'priority': 'high' if overdue_count >= 5 else 'medium',
                    'title': f"Triage {overdue_count} Overdue Tasks",
                    'description': f"You currently have {overdue_count} tasks past their target completion deadline.",
                    'rationale': "Old overdue items drain cognitive focus. Reschedule feasible tasks for specific upcoming days and prune or archive obsolete ones.",
                    'action_url': '/tasks/?status=PENDING',
                    'action_label': 'Triage Tasks',
                })

        # ----------------------------------------------------------------------
        # 3. SCHEDULE: Unscheduled High-Priority Tasks
        # ----------------------------------------------------------------------
        rec_key = 'schedule_unscheduled_urgent_tasks'
        if rec_key not in dismissed_keys:
            urgent_pending = Task.objects.filter(
                user=user,
                priority=Priority.HIGH,
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
                due_date__lte=today + timedelta(days=2)
            ).exclude(
                id__in=ScheduleBlock.objects.filter(
                    user=user,
                    block_date=today,
                    related_task__isnull=False
                ).values_list('related_task_id', flat=True)
            )
            urgent_count = urgent_pending.count()
            if urgent_count > 0:
                recs.append({
                    'key': rec_key,
                    'category': 'Schedule',
                    'priority': 'high',
                    'title': f"Allocate Timetable Slots for {urgent_count} Urgent Task{'s' if urgent_count > 1 else ''}",
                    'description': f"You have {urgent_count} high-priority task{'s' if urgent_count > 1 else ''} due soon that are not scheduled on today's timetable.",
                    'rationale': "High priority tasks without dedicated calendar blocks often get postponed by reactive interruptions.",
                    'action_url': '/timetable/generator/',
                    'action_label': 'Auto-Generate Schedule',
                })

        # ----------------------------------------------------------------------
        # 4. STUDY: Approaching Exam with Incomplete Syllabus
        # ----------------------------------------------------------------------
        rec_key = 'study_exam_preparation_pace'
        if rec_key not in dismissed_keys:
            upcoming_exams = Exam.objects.filter(
                user=user,
                exam_date__gte=today,
                exam_date__lte=today + timedelta(days=14)
            ).select_related('subject')

            for exam in upcoming_exams:
                subj = exam.subject
                topics = Topic.objects.filter(subject=subj)
                total_t = topics.count()
                comp_t = topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
                progress = round((comp_t / total_t) * 100) if total_t > 0 else 0
                days_left = (exam.exam_date - today).days

                if progress < 60:
                    recs.append({
                        'key': f"study_exam_{exam.id}",
                        'category': 'Study',
                        'priority': 'high',
                        'title': f"Accelerate Syllabus Coverage for {subj.name}",
                        'description': f"Exam '{exam.exam_name}' is in {days_left} day{'s' if days_left != 1 else ''}, but only {progress}% of syllabus topics are completed ({comp_t}/{total_t}).",
                        'rationale': f"To complete the remaining {total_t - comp_t} topics and allow 3 days of revision, increase daily study time for {subj.name}.",
                        'action_url': f'/study/subjects/{subj.id}/',
                        'action_label': 'Inspect Syllabus',
                    })
                    break

        # ----------------------------------------------------------------------
        # 5. STUDY: Overdue Spaced Repetition Revisions
        # ----------------------------------------------------------------------
        rec_key = 'study_revision_spaced_repetition'
        if rec_key not in dismissed_keys:
            overdue_revisions = Revision.objects.filter(
                user=user,
                revision_date__lt=today,
                status=RevisionStatus.PENDING
            ).count()
            if overdue_revisions >= 2:
                recs.append({
                    'key': rec_key,
                    'category': 'Study',
                    'priority': 'medium',
                    'title': f"Conduct {overdue_revisions} Pending Spaced Revisions",
                    'description': f"You have {overdue_revisions} study topics past their scheduled revision date.",
                    'rationale': "Spaced repetition relies on timely active recall before memory decay sets in. Quick 20-minute recall sessions restore long-term retention.",
                    'action_url': '/study/revisions/',
                    'action_label': 'Review Spaced Revisions',
                })

        # ----------------------------------------------------------------------
        # 6. HABITS: Daily Habit Consistency Slip
        # ----------------------------------------------------------------------
        rec_key = 'habits_daily_slip'
        if rec_key not in dismissed_keys:
            daily_habits = Habit.objects.filter(user=user, is_active=True, frequency='DAILY')
            for h in daily_habits:
                recent_logs = HabitLog.objects.filter(
                    habit=h,
                    user=user,
                    log_date__gte=today - timedelta(days=7),
                    completed=True
                ).count()
                consistency_pct = round((recent_logs / 7.0) * 100)
                if consistency_pct < 50:
                    recs.append({
                        'key': f"habits_daily_{h.id}",
                        'category': 'Habits',
                        'priority': 'high',
                        'title': f"Re-anchor Daily Habit: {h.name}",
                        'description': f"Your daily habit '{h.name}' achieved only {recent_logs}/7 completions ({consistency_pct}%) this past week.",
                        'rationale': "Consistent daily routines reduce decision fatigue and build compound momentum. Prioritize completing it early tomorrow.",
                        'action_url': '/habits/',
                        'action_label': 'View Habit Tracker',
                    })
                    break

        # ----------------------------------------------------------------------
        # 7. SCHEDULE: Daily Schedule Overload
        # ----------------------------------------------------------------------
        rec_key = 'schedule_daily_overload'
        if rec_key not in dismissed_keys:
            todays_blocks = ScheduleBlock.objects.filter(user=user, block_date=today)
            total_minutes = sum(b.duration_minutes for b in todays_blocks if b.duration_minutes)
            if total_minutes >= 600:  # 10 hours
                recs.append({
                    'key': rec_key,
                    'category': 'Schedule',
                    'priority': 'high',
                    'title': 'High Workload Overload Risk',
                    'description': f"Today's scheduled timetable contains {round(total_minutes / 60, 1)} hours of planned commitments.",
                    'rationale': "Cognitive endurance degrades significantly past 8-9 hours of structured blocks. Insert 30-minute unscheduled recharge intervals.",
                    'action_url': '/timetable/',
                    'action_label': 'Adjust Timetable',
                })

        # ----------------------------------------------------------------------
        # 8. WELL-BEING: Sleep Deficit Pattern
        # ----------------------------------------------------------------------
        rec_key = 'wellbeing_sleep_deficit'
        if rec_key not in dismissed_keys:
            recent_metrics = DailyMetric.objects.filter(
                user=user,
                metric_date__gte=today - timedelta(days=5),
                sleep_hours__isnull=False
            )
            if recent_metrics.count() >= 3:
                avg_sleep = recent_metrics.aggregate(Avg('sleep_hours'))['sleep_hours__avg']
                if avg_sleep and avg_sleep < Decimal('6.0'):
                    recs.append({
                        'key': rec_key,
                        'category': 'Well-being',
                        'priority': 'high',
                        'title': 'Sleep Debt Accumulation Detected',
                        'description': f"Your average recorded sleep over the last {recent_metrics.count()} days was {round(float(avg_sleep), 1)} hours.",
                        'rationale': "Sustained sleep deprivation directly depresses executive function, memory consolidation, and subjective energy levels.",
                        'action_url': '/checkin/',
                        'action_label': 'Log Sleep & Check-in',
                    })

        # ----------------------------------------------------------------------
        # 9. WELL-BEING: Missing Daily Reflections
        # ----------------------------------------------------------------------
        rec_key = 'wellbeing_missing_checkins'
        if rec_key not in dismissed_keys:
            logged_days = DailyMetric.objects.filter(
                user=user,
                metric_date__gte=today - timedelta(days=7)
            ).count()
            if logged_days <= 3:
                recs.append({
                    'key': rec_key,
                    'category': 'Well-being',
                    'priority': 'medium',
                    'title': 'Establish Daily Check-in Cadence',
                    'description': f"You logged daily reflections on only {logged_days} of the past 7 days.",
                    'rationale': "Consistent reflection feeds the LifeOS behavioral intelligence engine, revealing hidden correlations between rest and high productivity.",
                    'action_url': '/checkin/',
                    'action_label': 'Log Reflection',
                })

        # Filter by category if requested
        if category_filter and category_filter.lower() != 'all':
            recs = [r for r in recs if r['category'].lower() == category_filter.lower()]

        # Sort priority: high -> medium -> low
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recs.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return recs

    @classmethod
    def dismiss_recommendation(cls, user, key):
        if not user or not user.is_authenticated:
            return False
        DismissedRecommendation.objects.get_or_create(user=user, recommendation_key=key)
        return True

    @classmethod
    def reset_dismissed(cls, user):
        if not user or not user.is_authenticated:
            return 0
        deleted, _ = DismissedRecommendation.objects.filter(user=user).delete()
        return deleted
