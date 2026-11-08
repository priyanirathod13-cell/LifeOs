from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple
from django.db import transaction
from django.utils import timezone

from apps.productivity.models import (
    BlockType,
    ScheduleBlock,
    ScheduleStatus,
)
from apps.productivity.services.conflicts import (
    detect_block_collision,
    find_next_free_slot,
)
from apps.study.models import PlanStatus


def reschedule_schedule_block(
    user,
    block: ScheduleBlock,
    new_date: date,
    new_start_time: Optional[time] = None,
    new_end_time: Optional[time] = None
) -> Tuple[bool, str, Optional[ScheduleBlock]]:
    """
    Reschedules an existing ScheduleBlock to a new date and time window.
    
    If `new_start_time` is omitted, automatically finds the earliest available
    free slot on `new_date` that accommodates the block's duration.
    
    Preserves completed blocks and fixed commitments from being arbitrarily moved.
    """
    if block.user_id != user.id:
        return False, "Access denied.", None

    if block.status == ScheduleStatus.COMPLETED:
        return False, "Cannot reschedule a completed schedule block.", None

    if block.is_fixed:
        return False, "Fixed routine commitments cannot be rescheduled.", None

    duration_mins = block.duration_minutes

    if not new_start_time:
        slot = find_next_free_slot(user, new_date, duration_mins)
        if not slot:
            return False, f"No available time slot found on {new_date.strftime('%b %d')} for {duration_mins} minutes.", None
        new_start_time, new_end_time = slot
    elif not new_end_time:
        s_dt = datetime.combine(new_date, new_start_time)
        new_end_time = (s_dt + timedelta(minutes=duration_mins)).time()

    # Validate that proposed slot does not collide with existing commitments
    has_collision, reason = detect_block_collision(
        user=user,
        block_date=new_date,
        start_time=new_start_time,
        end_time=new_end_time,
        exclude_pk=block.pk
    )
    if has_collision:
        return False, f"Reschedule collision: {reason}", None

    with transaction.atomic():
        block.block_date = new_date
        block.start_time = new_start_time
        block.end_time = new_end_time
        block.status = ScheduleStatus.SCHEDULED
        block.save()

        # If linked to a study plan, synchronize study plan date
        if block.related_study_plan:
            sp = block.related_study_plan
            sp.planned_date = new_date
            sp.preferred_time = new_start_time
            if sp.status == PlanStatus.SKIPPED:
                sp.status = PlanStatus.RESCHEDULED
            sp.save()

    return True, f"Block rescheduled to {new_date.strftime('%a, %b %d')} at {new_start_time.strftime('%H:%M')}.", block


def mark_block_skipped(user, block: ScheduleBlock) -> Tuple[bool, str]:
    """
    Marks a scheduled block as skipped, preserving the historical record.
    """
    if block.user_id != user.id:
        return False, "Access denied."

    if block.status == ScheduleStatus.COMPLETED:
        return False, "Completed blocks cannot be marked skipped."

    block.status = ScheduleStatus.SKIPPED
    block.save()

    if block.related_study_plan:
        sp = block.related_study_plan
        sp.status = PlanStatus.SKIPPED
        sp.save()

    return True, f"Marked '{block.title}' as skipped."
