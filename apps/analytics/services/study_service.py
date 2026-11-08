from datetime import date, timedelta
from django.db.models import Avg, Count, F, Q, Sum
from apps.study.models import (
    Exam,
    PlanStatus,
    Revision,
    StudyPlan,
    StudySession,
    Subject,
    SubjectStatus,
    Topic,
    TopicStatus,
)


def get_study_metrics(user, start_date: date, end_date: date, today: date = None) -> dict:
    """
    Computes comprehensive academic and self-directed study analytics for the user.
    All data queries strictly filter by `user`.
    """
    if today is None:
        today = date.today()

    days_count = max(1, (end_date - start_date).days + 1)

    # 1. Study Sessions in Period
    sessions = StudySession.objects.filter(
        user=user,
        session_date__range=(start_date, end_date),
        duration_minutes__isnull=False,
        duration_minutes__gt=0
    ).select_related('subject', 'topic')

    total_study_minutes = sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0
    total_study_hours = round(total_study_minutes / 60.0, 1)
    avg_study_hours_per_day = round(total_study_hours / days_count, 2)
    sessions_count = sessions.count()

    # Active study days count
    active_study_days_set = set(sessions.values_list('session_date', flat=True))
    active_days_count = len(active_study_days_set)
    study_consistency_rate = round(active_days_count / days_count * 100.0, 1)

    # Longest Study Streak in Period
    curr_date = start_date
    current_streak = 0
    max_streak = 0
    while curr_date <= end_date:
        if curr_date in active_study_days_set:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
        curr_date += timedelta(days=1)

    # Daily Series for Charts
    daily_dates = []
    daily_hours = []
    curr_date = start_date
    while curr_date <= end_date:
        daily_dates.append(curr_date.strftime('%d %b'))
        d_mins = sum(s.duration_minutes for s in sessions if s.session_date == curr_date)
        daily_hours.append(round(d_mins / 60.0, 1))
        curr_date += timedelta(days=1)

    # 2. Subject-wise Time Allocation
    user_subjects = Subject.objects.filter(user=user)
    subject_durations = []
    subject_names = []
    subject_hours_list = []
    subject_colors = []

    for subj in user_subjects:
        subj_mins = sum(s.duration_minutes for s in sessions if s.subject_id == subj.id)
        subj_hrs = round(subj_mins / 60.0, 1)
        pct = round(subj_mins / total_study_minutes * 100.0, 1) if total_study_minutes > 0 else 0.0

        if subj_hrs > 0 or subj.status == SubjectStatus.ACTIVE:
            subject_durations.append({
                'id': subj.id,
                'name': subj.name,
                'code': subj.code,
                'color': subj.color,
                'hours': subj_hrs,
                'percentage': pct,
            })
            if subj_hrs > 0:
                subject_names.append(subj.name)
                subject_hours_list.append(subj_hrs)
                subject_colors.append(subj.color)

    subject_durations.sort(key=lambda x: x['hours'], reverse=True)

    # 3. Overall & Subject-wise Syllabus Completion
    all_topics = Topic.objects.filter(subject__user=user)
    total_topics_count = all_topics.count()
    completed_topics_count = all_topics.filter(
        status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]
    ).count()
    remaining_topics_count = total_topics_count - completed_topics_count
    overall_syllabus_rate = round(
        (completed_topics_count / total_topics_count * 100.0) if total_topics_count > 0 else 0.0,
        1
    )

    # Subject-wise Syllabus Progress
    subject_syllabus_list = []
    slow_progress_subjects = []

    for subj in user_subjects.filter(status=SubjectStatus.ACTIVE):
        s_topics = all_topics.filter(subject=subj)
        t_total = s_topics.count()
        t_done = s_topics.filter(status__in=[TopicStatus.COMPLETED, TopicStatus.MASTERED]).count()
        t_rate = round((t_done / t_total * 100.0) if t_total > 0 else 0.0, 1)

        info = {
            'id': subj.id,
            'name': subj.name,
            'color': subj.color,
            'total_topics': t_total,
            'completed_topics': t_done,
            'remaining_topics': t_total - t_done,
            'rate': t_rate,
            'target_date': subj.target_date,
        }
        subject_syllabus_list.append(info)

        # Flag slow progress if target is within 30 days and rate < 50%
        if subj.target_date and (subj.target_date - today).days <= 30 and t_rate < 50.0:
            slow_progress_subjects.append(info)

    # 4. Planned vs Actual Study Analysis (StudyPlan vs StudySession)
    plans = StudyPlan.objects.filter(
        user=user,
        planned_date__range=(start_date, end_date)
    ).select_related('subject')

    total_planned_minutes = plans.aggregate(p=Sum('estimated_minutes'))['p'] or 0
    total_planned_hours = round(total_planned_minutes / 60.0, 1)
    planned_difference_hours = round(total_study_hours - total_planned_hours, 1)

    plans_completed = plans.filter(status=PlanStatus.COMPLETED).count()
    plans_skipped = plans.filter(status=PlanStatus.SKIPPED).count()
    plans_rescheduled = plans.filter(status=PlanStatus.RESCHEDULED).count()
    plans_planned = plans.filter(status=PlanStatus.PLANNED).count()
    total_plans_count = plans.count()

    plan_adherence_rate = round(
        (plans_completed / total_plans_count * 100.0) if total_plans_count > 0 else 0.0,
        1
    )

    # Day of Week Study Rhythm
    day_rhythm = {'MON': 0, 'TUE': 0, 'WED': 0, 'THU': 0, 'FRI': 0, 'SAT': 0, 'SUN': 0}
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_keys = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    for s in sessions:
        weekday_idx = s.session_date.weekday()  # 0=Mon, 6=Sun
        day_rhythm[day_keys[weekday_idx]] += s.duration_minutes

    rhythm_hours = [round(day_rhythm[k] / 60.0, 1) for k in day_keys]

    return {
        'total_study_hours': total_study_hours,
        'total_study_minutes': total_study_minutes,
        'sessions_count': sessions_count,
        'avg_study_hours_per_day': avg_study_hours_per_day,
        'active_study_days': active_days_count,
        'inactive_study_days': days_count - active_days_count,
        'study_consistency_rate': study_consistency_rate,
        'longest_study_streak': max_streak,
        'daily_dates': daily_dates,
        'daily_hours': daily_hours,
        'subject_durations': subject_durations,
        'subject_names': subject_names,
        'subject_hours_list': subject_hours_list,
        'subject_colors': subject_colors,
        'total_topics': total_topics_count,
        'completed_topics': completed_topics_count,
        'remaining_topics': remaining_topics_count,
        'overall_syllabus_rate': overall_syllabus_rate,
        'subject_syllabus_list': subject_syllabus_list,
        'slow_progress_subjects': slow_progress_subjects,
        'total_planned_hours': total_planned_hours,
        'planned_difference_hours': planned_difference_hours,
        'total_plans_count': total_plans_count,
        'plans_completed': plans_completed,
        'plans_skipped': plans_skipped,
        'plans_rescheduled': plans_rescheduled,
        'plans_planned': plans_planned,
        'plan_adherence_rate': plan_adherence_rate,
        'rhythm_labels': day_labels,
        'rhythm_hours': rhythm_hours,
    }
