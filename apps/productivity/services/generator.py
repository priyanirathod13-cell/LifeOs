from datetime import date, datetime, time, timedelta
import json
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.productivity.models import (
    BlockType,
    Priority,
    Routine,
    ScheduleBlock,
    ScheduleGenerationHistory,
    ScheduleStatus,
    SchedulingPreference,
    Task,
    TaskStatus,
)
from apps.productivity.services.availability import (
    compute_free_intervals,
    get_day_fixed_commitments,
    get_user_availability_windows,
)
from apps.study.models import PlanStatus, StudyPlan


class TimetableGenerator:
    """
    Deterministic rule-based scheduling engine that allocates pending tasks,
    planned study sessions, and fixed routines into available daily time windows.
    """

    def __init__(self, user, target_date: date, preferences: Optional[SchedulingPreference] = None):
        self.user = user
        self.target_date = target_date
        self.preferences = preferences or SchedulingPreference.get_for_user(user)

    def generate(self) -> Dict[str, Any]:
        """
        Executes deterministic scheduling and returns a preview report containing:
        - candidate_blocks: list of proposed schedule block dictionaries
        - fixed_blocks: list of fixed routine commitments
        - unscheduled_items: list of items that could not fit with reasons
        - statistics: metrics including work minutes, break minutes, free minutes
        """
        user = self.user
        target_date = self.target_date
        pref = self.preferences

        # 1. Retrieve Available Working Windows & Fixed Commitments
        available_windows = get_user_availability_windows(user, target_date)
        fixed_commitments = get_day_fixed_commitments(user, target_date)

        # 2. Compute Available Free Intervals
        free_intervals = compute_free_intervals(available_windows, fixed_commitments, target_date)

        # 3. Collect & Prioritize Eligible Pending Flexible Work
        candidate_items = self._collect_and_prioritize_candidates()

        # 4. Sequential Allocation into Free Intervals
        scheduled_blocks: List[Dict[str, Any]] = []
        unscheduled_items: List[Dict[str, Any]] = []

        total_work_minutes = 0
        total_break_minutes = 0
        continuous_work_counter = 0

        # Create mutable list of intervals: [(start_dt, end_dt)]
        intervals_dt = [
            (datetime.combine(target_date, s), datetime.combine(target_date, e))
            for s, e, _ in free_intervals
        ]

        for item in candidate_items:
            duration = item['duration_minutes']

            # Check if adding this item would exceed user's daily maximum work cap
            if total_work_minutes + duration > pref.max_daily_work_minutes:
                unscheduled_items.append({
                    **item,
                    'reason': f"Exceeds max daily work limit ({pref.max_daily_work_minutes // 60}h {pref.max_daily_work_minutes % 60}m)",
                })
                continue

            # Check if we should insert a break before this item
            needs_break = bool(
                pref.auto_insert_breaks and
                continuous_work_counter >= pref.max_continuous_work_minutes
            )
            required_mins = duration + (pref.default_break_minutes if needs_break else 0)

            # Find first interval that can fit the item
            allocated = False
            for idx, (int_start, int_end) in enumerate(intervals_dt):
                interval_capacity = int((int_end - int_start).total_seconds() / 60)

                if interval_capacity >= required_mins:
                    current_cursor = int_start

                    # 1. Insert Rest Break if continuous work threshold was reached
                    if needs_break and interval_capacity >= (duration + pref.default_break_minutes):
                        break_end = current_cursor + timedelta(minutes=pref.default_break_minutes)
                        scheduled_blocks.append({
                            'title': 'Rest & Break',
                            'description': 'Scheduled recharge break to prevent fatigue.',
                            'block_date': target_date,
                            'start_time': current_cursor.time(),
                            'end_time': break_end.time(),
                            'block_type': BlockType.BREAK,
                            'status': ScheduleStatus.SCHEDULED,
                            'priority': Priority.LOW,
                            'is_fixed': False,
                            'duration_minutes': pref.default_break_minutes,
                            'related_task_id': None,
                            'related_routine_id': None,
                            'related_study_plan_id': None,
                        })
                        total_break_minutes += pref.default_break_minutes
                        continuous_work_counter = 0
                        current_cursor = break_end + timedelta(minutes=pref.buffer_minutes)

                    # 2. Allocate the Flexible Item
                    item_end = current_cursor + timedelta(minutes=duration)
                    scheduled_blocks.append({
                        'title': item['title'],
                        'description': item.get('description', ''),
                        'block_date': target_date,
                        'start_time': current_cursor.time(),
                        'end_time': item_end.time(),
                        'block_type': item['block_type'],
                        'status': ScheduleStatus.SCHEDULED,
                        'priority': item.get('priority', Priority.MEDIUM),
                        'is_fixed': False,
                        'duration_minutes': duration,
                        'related_task_id': item.get('related_task_id'),
                        'related_routine_id': None,
                        'related_study_plan_id': item.get('related_study_plan_id'),
                    })

                    total_work_minutes += duration
                    continuous_work_counter += duration

                    # 3. Update the remaining capacity of this interval
                    next_cursor = item_end + timedelta(minutes=pref.buffer_minutes)
                    if next_cursor < int_end:
                        intervals_dt[idx] = (next_cursor, int_end)
                    else:
                        intervals_dt.pop(idx)

                    allocated = True
                    break

            if not allocated:
                unscheduled_items.append({
                    **item,
                    'reason': f"No available time slot large enough ({duration} mins required)",
                })

        # Format Fixed Commitment Blocks for the preview
        fixed_blocks_formatted = []
        for c in fixed_commitments:
            fixed_blocks_formatted.append({
                'title': c['title'],
                'description': getattr(c['obj'], 'description', '') if c['obj'] else '',
                'block_date': target_date,
                'start_time': c['start_time'],
                'end_time': c['end_time'],
                'block_type': BlockType.ROUTINE if c['source'] == 'routine' else BlockType.FOCUS,
                'status': ScheduleStatus.SCHEDULED if c['source'] != 'completed_block' else ScheduleStatus.COMPLETED,
                'priority': Priority.HIGH,
                'is_fixed': True,
                'duration_minutes': c['duration_minutes'],
                'related_task_id': getattr(c['obj'], 'related_task_id', None) if c['source'] != 'routine' else None,
                'related_routine_id': c['obj'].pk if c['source'] == 'routine' else None,
                'related_study_plan_id': None,
            })

        # Calculate remaining free minutes in available windows
        total_free_minutes = sum(
            int((e - s).total_seconds() / 60) for s, e in intervals_dt if e > s
        )

        return {
            'target_date': target_date,
            'scheduled_blocks': scheduled_blocks,
            'fixed_blocks': fixed_blocks_formatted,
            'unscheduled_items': unscheduled_items,
            'statistics': {
                'total_scheduled_blocks': len(scheduled_blocks) + len(fixed_blocks_formatted),
                'tasks_scheduled': sum(1 for b in scheduled_blocks if b['related_task_id']),
                'study_scheduled': sum(1 for b in scheduled_blocks if b['related_study_plan_id']),
                'routines_scheduled': len(fixed_blocks_formatted),
                'breaks_scheduled': sum(1 for b in scheduled_blocks if b['block_type'] == BlockType.BREAK),
                'total_work_minutes': total_work_minutes,
                'total_break_minutes': total_break_minutes,
                'total_free_minutes': max(0, total_free_minutes),
            }
        }

    def _collect_and_prioritize_candidates(self) -> List[Dict[str, Any]]:
        """
        Fetches pending tasks and scheduled study plans for target_date and sorts
        them deterministically by deadline urgency, priority weight, and duration.
        """
        user = self.user
        target_date = self.target_date
        items: List[Dict[str, Any]] = []

        # 1. Pending Tasks
        pending_tasks = Task.objects.filter(
            user=user,
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ).select_related('category')

        priority_weight = {
            Priority.URGENT: 400,
            Priority.HIGH: 300,
            Priority.MEDIUM: 200,
            Priority.LOW: 100,
        }

        for t in pending_tasks:
            duration = t.estimated_minutes if (t.estimated_minutes and t.estimated_minutes > 0) else 45
            
            # Deadline score calculation
            deadline_score = 0
            if t.due_date:
                days_diff = (t.due_date - target_date).days
                if days_diff < 0:
                    deadline_score = 500  # Overdue is utmost priority
                elif days_diff == 0:
                    deadline_score = 450  # Due today
                elif days_diff <= 2:
                    deadline_score = 250  # Approaching deadline
                else:
                    deadline_score = 50

            total_rank = deadline_score + priority_weight.get(t.priority, 200)

            items.append({
                'title': t.title,
                'description': t.description,
                'duration_minutes': duration,
                'priority': t.priority,
                'block_type': BlockType.FOCUS,
                'related_task_id': t.pk,
                'related_study_plan_id': None,
                'item_type': 'task',
                'rank': total_rank,
                'due_date': t.due_date,
            })

        # 2. Planned Study Activities for target_date
        study_plans = StudyPlan.objects.filter(
            user=user,
            planned_date=target_date,
            status=PlanStatus.PLANNED
        ).select_related('subject', 'topic')

        for sp in study_plans:
            duration = sp.estimated_minutes if (sp.estimated_minutes and sp.estimated_minutes > 0) else 60
            title = f"Study: {sp.subject.name}"
            if sp.topic:
                title += f" — {sp.topic.title}"

            total_rank = 350 + priority_weight.get(sp.priority, 200)  # Planned for today gets high ranking

            items.append({
                'title': title,
                'description': sp.notes,
                'duration_minutes': duration,
                'priority': sp.priority,
                'block_type': BlockType.STUDY,
                'related_task_id': None,
                'related_study_plan_id': sp.pk,
                'item_type': 'study',
                'rank': total_rank,
                'due_date': target_date,
            })

        # Sort descending by rank (highest priority first), then by shorter duration to maximize throughput
        items.sort(key=lambda x: (-x['rank'], x['duration_minutes']))
        return items

    @transaction.atomic
    def apply(self, plan_preview: Dict[str, Any], replace_existing: bool = False) -> ScheduleGenerationHistory:
        """
        Saves the generated preview blocks into the database as active ScheduleBlocks.
        
        If replace_existing is True, non-completed flexible blocks for that date are removed
        first. Completed blocks and manual fixed blocks are always strictly preserved.
        """
        user = self.user
        target_date = self.target_date

        if replace_existing:
            # Delete only flexible, non-completed blocks
            ScheduleBlock.objects.filter(
                user=user,
                block_date=target_date,
                is_fixed=False
            ).exclude(status=ScheduleStatus.COMPLETED).delete()

        # Create schedule blocks from fixed routines if not already existing
        for fb in plan_preview.get('fixed_blocks', []):
            if fb.get('related_routine_id'):
                exists = ScheduleBlock.objects.filter(
                    user=user,
                    block_date=target_date,
                    related_routine_id=fb['related_routine_id']
                ).exists()
                if not exists:
                    ScheduleBlock.objects.create(
                        user=user,
                        title=fb['title'],
                        description=fb.get('description', ''),
                        block_date=target_date,
                        start_time=fb['start_time'],
                        end_time=fb['end_time'],
                        block_type=BlockType.ROUTINE,
                        status=ScheduleStatus.SCHEDULED,
                        priority=fb.get('priority', Priority.HIGH),
                        is_fixed=True,
                        related_routine_id=fb['related_routine_id'],
                    )

        # Create flexible scheduled blocks
        created_count = 0
        for sb in plan_preview.get('scheduled_blocks', []):
            ScheduleBlock.objects.create(
                user=user,
                title=sb['title'],
                description=sb.get('description', ''),
                block_date=target_date,
                start_time=sb['start_time'],
                end_time=sb['end_time'],
                block_type=sb['block_type'],
                status=ScheduleStatus.SCHEDULED,
                priority=sb.get('priority', Priority.MEDIUM),
                is_fixed=False,
                related_task_id=sb.get('related_task_id'),
                related_study_plan_id=sb.get('related_study_plan_id'),
            )
            created_count += 1

        stats = plan_preview.get('statistics', {})
        unscheduled = plan_preview.get('unscheduled_items', [])

        # Create Audit History Record
        history = ScheduleGenerationHistory.objects.create(
            user=user,
            generation_date=target_date,
            total_tasks_scheduled=stats.get('tasks_scheduled', 0),
            total_study_scheduled=stats.get('study_scheduled', 0),
            total_routines_scheduled=stats.get('routines_scheduled', 0),
            total_breaks_scheduled=stats.get('breaks_scheduled', 0),
            total_work_minutes=stats.get('total_work_minutes', 0),
            unscheduled_items_json=json.dumps(unscheduled, default=str),
            status='APPLIED',
        )

        return history
