from datetime import date, datetime, time, timedelta
from typing import List, Tuple
from django.db.models import Q

from apps.productivity.models import (
    AvailabilityWindow,
    DayOfWeek,
    Routine,
    ScheduleBlock,
    SchedulingPreference,
)


def get_weekday_code(target_date: date) -> str:
    """
    Returns the DayOfWeek text code (e.g. 'MON', 'TUE') for a given date.
    """
    return target_date.strftime('%a').upper()


def get_user_availability_windows(user, target_date: date) -> List[Tuple[time, time]]:
    """
    Returns a list of (start_time, end_time) tuples representing the user's
    permitted working hours for target_date.
    
    If the user has configured custom AvailabilityWindows for this weekday,
    they are returned. Otherwise, returns a single default window derived from
    the user's SchedulingPreference (e.g. 07:00 to 23:00).
    """
    day_code = get_weekday_code(target_date)
    windows = AvailabilityWindow.objects.filter(
        user=user,
        day_of_week=day_code,
        is_active=True
    ).order_by('start_time')

    if windows.exists():
        return [(w.start_time, w.end_time) for w in windows]

    pref = SchedulingPreference.get_for_user(user)
    return [(pref.day_start_time, pref.day_end_time)]


def get_day_fixed_commitments(user, target_date: date) -> List[dict]:
    """
    Retrieves all fixed, non-movable commitments on target_date:
    1. Active recurring routines that apply to target_date's weekday.
    2. Any existing ScheduleBlock explicitly marked is_fixed=True or COMPLETED.
    
    Returns a list of dicts sorted by start_time:
    [{
        'title': str,
        'start_time': time,
        'end_time': time,
        'source': 'routine' | 'fixed_block' | 'completed_block',
        'obj': model instance,
        'duration_minutes': int
    }]
    """
    day_code = get_weekday_code(target_date)
    commitments = []

    # 1. Recurring routines
    routines = Routine.objects.filter(user=user, is_active=True)
    for r in routines:
        if r.applies_on_date(target_date):
            commitments.append({
                'title': r.title,
                'start_time': r.start_time,
                'end_time': r.end_time,
                'source': 'routine',
                'obj': r,
                'duration_minutes': r.duration_minutes,
            })

    # 2. Existing fixed or completed schedule blocks on this date
    existing_blocks = ScheduleBlock.objects.filter(
        user=user,
        block_date=target_date
    ).filter(
        Q(is_fixed=True) | Q(status='COMPLETED')
    )
    for b in existing_blocks:
        commitments.append({
            'title': b.title,
            'start_time': b.start_time,
            'end_time': b.end_time,
            'source': 'fixed_block' if b.is_fixed else 'completed_block',
            'obj': b,
            'duration_minutes': b.duration_minutes,
        })

    # Sort commitments chronologically by start_time
    commitments.sort(key=lambda x: x['start_time'])
    return commitments


def compute_free_intervals(
    available_windows: List[Tuple[time, time]],
    fixed_commitments: List[dict],
    target_date: date = None
) -> List[Tuple[time, time, int]]:
    """
    Intersects available working windows with fixed commitments to compute
    the available free time intervals.
    
    Returns a list of (start_time, end_time, duration_minutes) tuples where
    flexible activities can be scheduled without collision.
    """
    if not target_date:
        target_date = date.today()

    # Convert everything to datetime for clean interval arithmetic
    def to_dt(t: time) -> datetime:
        return datetime.combine(target_date, t)

    def to_time(dt: datetime) -> time:
        return dt.time()

    # Normalized available intervals
    avail_intervals = [(to_dt(s), to_dt(e)) for s, e in available_windows if to_dt(e) > to_dt(s)]
    fixed_intervals = [(to_dt(c['start_time']), to_dt(c['end_time'])) for c in fixed_commitments if to_dt(c['end_time']) > to_dt(c['start_time'])]

    free_intervals = []

    for a_start, a_end in avail_intervals:
        current_cursor = a_start

        # Filter and sort fixed intervals that overlap with this available window
        overlapping_fixed = [
            (max(f_start, a_start), min(f_end, a_end))
            for f_start, f_end in fixed_intervals
            if f_end > a_start and f_start < a_end
        ]
        overlapping_fixed.sort(key=lambda x: x[0])

        for f_start, f_end in overlapping_fixed:
            if f_start > current_cursor:
                diff_mins = int((f_start - current_cursor).total_seconds() / 60)
                if diff_mins > 0:
                    free_intervals.append((to_time(current_cursor), to_time(f_start), diff_mins))
            current_cursor = max(current_cursor, f_end)

        if current_cursor < a_end:
            diff_mins = int((a_end - current_cursor).total_seconds() / 60)
            if diff_mins > 0:
                free_intervals.append((to_time(current_cursor), to_time(a_end), diff_mins))

    return free_intervals
