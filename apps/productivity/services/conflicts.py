from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple
from django.db.models import Q

from apps.productivity.models import (
    Routine,
    ScheduleBlock,
    SchedulingPreference,
)
from apps.productivity.services.availability import (
    compute_free_intervals,
    get_day_fixed_commitments,
    get_user_availability_windows,
)


def detect_routine_overlap(user, routine, exclude_pk: Optional[int] = None) -> Optional[Routine]:
    """
    Checks if `routine` conflicts with another active routine for `user` on any shared weekday.
    Returns the conflicting Routine instance if found, or None.
    """
    if not routine.is_active or not routine.start_time or not routine.end_time:
        return None

    overlap_qs = Routine.objects.filter(
        user=user,
        is_active=True,
        start_time__lt=routine.end_time,
        end_time__gt=routine.start_time,
    )
    if exclude_pk:
        overlap_qs = overlap_qs.exclude(pk=exclude_pk)

    if routine.start_date:
        overlap_qs = overlap_qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=routine.start_date))
    if routine.end_date:
        overlap_qs = overlap_qs.filter(Q(start_date__isnull=True) | Q(start_date__lte=routine.end_date))

    my_days = set(d.strip().upper() for d in (routine.days_of_week or '').split(',') if d.strip())
    for other in overlap_qs:
        other_days = set(d.strip().upper() for d in (other.days_of_week or '').split(',') if d.strip())
        if my_days.intersection(other_days):
            return other

    return None


def detect_block_collision(
    user,
    block_date: date,
    start_time: time,
    end_time: time,
    exclude_pk: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Checks whether a proposed schedule time slot on `block_date` collides with
    an existing active Routine or ScheduleBlock.
    
    Returns (has_collision: bool, reason: str or None).
    """
    if end_time <= start_time:
        return True, "End time must be after start time."

    # 1. Check collisions with active Routines that apply on this date
    routines = Routine.objects.filter(
        user=user,
        is_active=True,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    for r in routines:
        if r.applies_on_date(block_date):
            return True, f"Collides with recurring routine '{r.title}' ({r.start_time.strftime('%H:%M')}-{r.end_time.strftime('%H:%M')})"

    # 2. Check collisions with existing ScheduleBlocks on this date
    blocks_qs = ScheduleBlock.objects.filter(
        user=user,
        block_date=block_date,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_pk:
        blocks_qs = blocks_qs.exclude(pk=exclude_pk)

    # Exclude cancelled or skipped blocks from hard collision
    blocks_qs = blocks_qs.exclude(status__in=['CANCELLED', 'SKIPPED'])

    colliding_block = blocks_qs.first()
    if colliding_block:
        return True, f"Collides with schedule block '{colliding_block.title}' ({colliding_block.start_time.strftime('%H:%M')}-{colliding_block.end_time.strftime('%H:%M')})"

    return False, None


def find_next_free_slot(
    user,
    target_date: date,
    duration_minutes: int,
    after_time: Optional[time] = None
) -> Optional[Tuple[time, time]]:
    """
    Finds the earliest available time window on `target_date` that can fit
    `duration_minutes`, optionally after `after_time`.
    
    Returns (start_time, end_time) or None if no sufficient slot exists.
    """
    avail_windows = get_user_availability_windows(user, target_date)
    fixed_commitments = get_day_fixed_commitments(user, target_date)

    # Also treat all existing active schedule blocks on this day as occupied intervals
    existing_blocks = ScheduleBlock.objects.filter(
        user=user,
        block_date=target_date
    ).exclude(status__in=['CANCELLED', 'SKIPPED'])

    for b in existing_blocks:
        fixed_commitments.append({
            'title': b.title,
            'start_time': b.start_time,
            'end_time': b.end_time,
            'source': 'schedule_block',
            'obj': b,
            'duration_minutes': b.duration_minutes,
        })

    fixed_commitments.sort(key=lambda x: x['start_time'])
    free_intervals = compute_free_intervals(avail_windows, fixed_commitments, target_date)

    pref = SchedulingPreference.get_for_user(user)
    buffer_mins = pref.buffer_minutes

    for s_time, e_time, interval_mins in free_intervals:
        candidate_start = s_time

        if after_time and candidate_start < after_time:
            if e_time <= after_time:
                continue
            candidate_start = after_time

        s_dt = datetime.combine(target_date, candidate_start)
        e_dt = datetime.combine(target_date, e_time)
        available_segment_mins = int((e_dt - s_dt).total_seconds() / 60)

        if available_segment_mins >= duration_minutes:
            proposed_end_dt = s_dt + timedelta(minutes=duration_minutes)
            return candidate_start, proposed_end_dt.time()

    return None
