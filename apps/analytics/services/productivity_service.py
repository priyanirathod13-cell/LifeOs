from datetime import date, datetime, time, timedelta
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone
from apps.productivity.models import Activity, Task, TaskStatus


def get_productivity_metrics(user, start_date: date, end_date: date, today: date = None) -> dict:
    """
    Computes comprehensive productivity metrics for the specified user and date range.
    All calculations strictly isolate data to `user`.
    Uses timezone-aware datetime bounds for DateTimeField queries to ensure robust compatibility with MySQL.
    """
    if today is None:
        today = date.today()

    days_count = max(1, (end_date - start_date).days + 1)

    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

    # Base task query set within the date range (tasks due or completed or created in period)
    period_tasks = Task.objects.filter(user=user).filter(
        Q(due_date__range=(start_date, end_date)) |
        Q(completed_at__range=(start_dt, end_dt)) |
        Q(created_at__range=(start_dt, end_dt))
    ).distinct()

    total_tasks_created = period_tasks.count()
    completed_tasks_qs = period_tasks.filter(status=TaskStatus.COMPLETED)
    completed_count = completed_tasks_qs.count()
    pending_count = period_tasks.filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]).count()

    overdue_count = Task.objects.filter(
        user=user,
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
        due_date__lt=today
    ).count()

    completion_rate = (completed_count / total_tasks_created * 100.0) if total_tasks_created > 0 else 0.0

    # Average task completion time (only for completed tasks with valid actual_minutes > 0)
    completed_with_actual = completed_tasks_qs.filter(actual_minutes__gt=0)
    avg_actual_agg = completed_with_actual.aggregate(avg_mins=Avg('actual_minutes'))
    avg_completion_minutes = round(avg_actual_agg['avg_mins'] or 0.0, 1)

    tasks_per_day = round(completed_count / days_count, 2)

    # Planned vs Actual Duration Estimation Analysis
    # Strictly only include tasks with BOTH estimated_minutes > 0 AND actual_minutes > 0
    duration_tasks = Task.objects.filter(
        user=user,
        estimated_minutes__gt=0,
        actual_minutes__gt=0
    ).filter(
        Q(completed_at__range=(start_dt, end_dt)) |
        Q(due_date__range=(start_date, end_date)) |
        Q(created_at__range=(start_dt, end_dt))
    ).select_related('category').distinct()

    estimation_data = []
    underestimated_tasks = []
    overestimated_tasks = []
    accurate_tasks = []
    total_error = 0
    total_accuracy_sum = 0.0

    for task in duration_tasks:
        est = task.estimated_minutes
        act = task.actual_minutes
        error = act - est  # Positive = took longer (underestimated), Negative = faster (overestimated)
        total_error += error

        # Accuracy metric: 100% minus relative error capped at 0
        rel_error = abs(error) / est
        acc = max(0.0, round((1.0 - min(1.0, rel_error)) * 100.0, 1))
        total_accuracy_sum += acc

        item = {
            'id': task.id,
            'title': task.title,
            'category': task.category.name if task.category else 'General',
            'category_color': task.category.color if task.category else '#818CF8',
            'estimated': est,
            'actual': act,
            'error': error,
            'accuracy': acc,
        }
        estimation_data.append(item)

        if error > 0:
            underestimated_tasks.append(item)
        elif error < 0:
            overestimated_tasks.append(item)
        else:
            accurate_tasks.append(item)

    comp_count = len(estimation_data)
    avg_estimation_error = round(total_error / comp_count, 1) if comp_count > 0 else None
    avg_estimation_accuracy = round(total_accuracy_sum / comp_count, 1) if comp_count > 0 else None

    # Sort under/overestimated by magnitude of error
    underestimated_tasks.sort(key=lambda x: x['error'], reverse=True)
    overestimated_tasks.sort(key=lambda x: x['error'])

    # Tracked Activities & Time
    activities_qs = Activity.objects.filter(
        user=user,
        start_time__range=(start_dt, end_dt)
    ).select_related('category')
    activities_count = activities_qs.count()

    # Calculate total activity minutes
    total_activity_minutes = 0
    for act in activities_qs:
        total_activity_minutes += (act.duration_minutes or 0)

    # Add completed tasks actual minutes
    task_minutes = completed_tasks_qs.aggregate(total_mins=Sum('actual_minutes'))['total_mins'] or 0

    # Total productive tracked time (minutes)
    total_tracked_minutes = total_activity_minutes + task_minutes
    total_tracked_hours = round(total_tracked_minutes / 60.0, 1)
    avg_daily_productive_hours = round(total_tracked_hours / days_count, 2)

    # Daily Trend Series
    date_series = []
    completed_series = []
    minutes_series = []

    curr_date = start_date
    while curr_date <= end_date:
        d_start_dt = timezone.make_aware(datetime.combine(curr_date, time.min))
        d_end_dt = timezone.make_aware(datetime.combine(curr_date, time.max))
        date_series.append(curr_date.strftime('%d %b'))

        # Count tasks completed on this date
        d_comp = Task.objects.filter(
            user=user,
            status=TaskStatus.COMPLETED,
            completed_at__range=(d_start_dt, d_end_dt)
        ).count()
        completed_series.append(d_comp)

        # Minutes from activities on this date
        d_acts = Activity.objects.filter(user=user, start_time__range=(d_start_dt, d_end_dt))
        d_act_mins = sum((a.duration_minutes or 0) for a in d_acts)

        # Minutes from tasks completed on this date
        d_task_mins = Task.objects.filter(
            user=user,
            status=TaskStatus.COMPLETED,
            completed_at__range=(d_start_dt, d_end_dt),
            actual_minutes__gt=0
        ).aggregate(m=Sum('actual_minutes'))['m'] or 0

        minutes_series.append(d_act_mins + d_task_mins)
        curr_date += timedelta(days=1)

        # Minutes from tasks completed on this date
        d_task_mins = Task.objects.filter(
            user=user,
            status=TaskStatus.COMPLETED,
            completed_at__date=curr_date,
            actual_minutes__gt=0
        ).aggregate(m=Sum('actual_minutes'))['m'] or 0

        minutes_series.append(d_act_mins + d_task_mins)
        curr_date += timedelta(days=1)

    return {
        'total_tasks': total_tasks_created,
        'completed_tasks': completed_count,
        'pending_tasks': pending_count,
        'overdue_tasks': overdue_count,
        'completion_rate': round(completion_rate, 1),
        'avg_completion_minutes': avg_completion_minutes,
        'tasks_per_day': tasks_per_day,
        'activities_count': activities_count,
        'total_tracked_minutes': total_tracked_minutes,
        'total_tracked_hours': total_tracked_hours,
        'avg_daily_productive_hours': avg_daily_productive_hours,
        'estimation_comparisons_count': comp_count,
        'avg_estimation_error': avg_estimation_error,
        'avg_estimation_accuracy': avg_estimation_accuracy,
        'underestimated_tasks': underestimated_tasks[:5],
        'overestimated_tasks': overestimated_tasks[:5],
        'accurate_tasks': accurate_tasks[:5],
        'date_series': date_series,
        'completed_series': completed_series,
        'minutes_series': minutes_series,
    }
