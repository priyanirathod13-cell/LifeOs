from datetime import date, datetime, time, timedelta
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from apps.productivity.models import (
    Activity,
    BlockType,
    Category,
    ScheduleBlock,
    ScheduleStatus,
    Task,
    TaskStatus,
)
from apps.study.models import StudySession


def get_time_metrics(user, start_date: date, end_date: date) -> dict:
    """
    Computes time allocation, schedule adherence, and time distribution metrics.
    Prevents double-counting across activities, study sessions, and tasks.
    """
    days_count = max(1, (end_date - start_date).days + 1)
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

    # 1. Activities Recorded
    activities = Activity.objects.filter(
        user=user,
        start_time__range=(start_dt, end_dt)
    ).select_related('category')

    activity_minutes_by_cat = {}
    for act in activities:
        cat_name = act.category.name if act.category else 'Personal'
        act_dur = act.duration_minutes or 0
        activity_minutes_by_cat[cat_name] = activity_minutes_by_cat.get(cat_name, 0) + act_dur

    # 2. Study Sessions
    study_sessions = StudySession.objects.filter(
        user=user,
        session_date__range=(start_date, end_date),
        duration_minutes__isnull=False,
        duration_minutes__gt=0
    )
    study_minutes = study_sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0

    # 3. Tasks Completed (with actual duration)
    completed_tasks = Task.objects.filter(
        user=user,
        status=TaskStatus.COMPLETED,
        actual_minutes__gt=0
    ).filter(
        Q(completed_at__range=(start_dt, end_dt)) |
        Q(due_date__range=(start_date, end_date))
    ).select_related('category')
    task_minutes = completed_tasks.aggregate(total=Sum('actual_minutes'))['total'] or 0

    # Categorized Time Distribution (Donut Chart)
    time_distribution = {}
    time_distribution['Study'] = round(study_minutes / 60.0, 1)

    # Distribute task minutes into their categories or 'Tasks'
    for t in completed_tasks:
        cat_name = t.category.name if t.category else 'Tasks'
        if cat_name.lower() != 'study':
            time_distribution[cat_name] = time_distribution.get(cat_name, 0.0) + round(t.actual_minutes / 60.0, 1)

    # Add activity minutes
    for cat_name, mins in activity_minutes_by_cat.items():
        if cat_name.lower() != 'study':
            time_distribution[cat_name] = time_distribution.get(cat_name, 0.0) + round(mins / 60.0, 1)

    # Filter out 0 hours
    dist_labels = [k for k, v in time_distribution.items() if v > 0]
    dist_values = [time_distribution[k] for k in dist_labels]

    total_tracked_hours = sum(dist_values)

    # 4. Schedule Adherence (ScheduleBlock analysis using block_date)
    schedule_blocks = ScheduleBlock.objects.filter(
        user=user,
        block_date__range=(start_date, end_date)
    )

    total_scheduled = schedule_blocks.count()
    completed_blocks = schedule_blocks.filter(status=ScheduleStatus.COMPLETED).count()
    missed_blocks = schedule_blocks.filter(status=ScheduleStatus.MISSED).count()
    skipped_blocks = schedule_blocks.filter(status=ScheduleStatus.SKIPPED).count()
    rescheduled_blocks = schedule_blocks.filter(status=ScheduleStatus.RESCHEDULED).count()

    adherence_rate = round(
        (completed_blocks / total_scheduled * 100.0) if total_scheduled > 0 else 0.0,
        1
    )

    # Unscheduled tasks count (pending tasks with due date in range but no schedule block)
    unscheduled_tasks_count = Task.objects.filter(
        user=user,
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date__range=(start_date, end_date),
        schedule_blocks__isnull=True
    ).distinct().count()

    # Time Estimation Comparison
    # Compare average estimated vs actual minutes across completed tasks with both
    timed_tasks = Task.objects.filter(
        user=user,
        status=TaskStatus.COMPLETED,
        estimated_minutes__gt=0,
        actual_minutes__gt=0
    ).filter(
        Q(completed_at__range=(start_dt, end_dt)) |
        Q(due_date__range=(start_date, end_date))
    )
    est_agg = timed_tasks.aggregate(avg_est=Avg('estimated_minutes'), avg_act=Avg('actual_minutes'))
    avg_planned_mins = round(est_agg['avg_est'] or 0.0, 1)
    avg_actual_mins = round(est_agg['avg_act'] or 0.0, 1)
    avg_error_mins = round(avg_actual_mins - avg_planned_mins, 1)

    return {
        'total_tracked_hours': round(total_tracked_hours, 1),
        'dist_labels': dist_labels,
        'dist_values': dist_values,
        'time_distribution_table': [{'category': k, 'hours': v, 'pct': round(v / total_tracked_hours * 100.0, 1) if total_tracked_hours > 0 else 0.0} for k, v in time_distribution.items() if v > 0],
        'total_scheduled_blocks': total_scheduled,
        'completed_blocks': completed_blocks,
        'missed_blocks': missed_blocks,
        'skipped_blocks': skipped_blocks,
        'rescheduled_blocks': rescheduled_blocks,
        'adherence_rate': adherence_rate,
        'unscheduled_tasks_count': unscheduled_tasks_count,
        'avg_planned_minutes': avg_planned_mins,
        'avg_actual_minutes': avg_actual_mins,
        'avg_estimation_error': avg_error_mins,
    }
