from datetime import date, datetime, time, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Case, Count, Q, Sum, When
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ActivityForm,
    AvailabilityWindowForm,
    CategoryForm,
    HabitForm,
    HabitLogForm,
    RescheduleBlockForm,
    RoutineForm,
    ScheduleBlockForm,
    SchedulingPreferenceForm,
    TaskForm,
)
from .models import (
    Activity,
    AvailabilityWindow,
    BlockType,
    Category,
    CategoryType,
    DayOfWeek,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    Routine,
    RoutineType,
    ScheduleBlock,
    ScheduleGenerationHistory,
    ScheduleStatus,
    SchedulingPreference,
    Task,
    TaskStatus,
)
from .services import (
    TimetableGenerator,
    compute_free_intervals,
    detect_block_collision,
    get_day_fixed_commitments,
    get_user_availability_windows,
    mark_block_skipped,
    reschedule_schedule_block,
)
from apps.study.models import PlanStatus, StudyPlan


def calculate_habit_streak(habit, user):
    """
    Computes current streak and best streak for a habit based on actual frequency.
    """
    today = timezone.localtime(timezone.now()).date()
    logs = list(HabitLog.objects.filter(
        habit=habit, user=user, completed=True
    ).order_by('log_date').values_list('log_date', flat=True))

    if not logs:
        return {'current_streak': 0, 'best_streak': 0}

    log_set = set(logs)

    if habit.frequency == HabitFrequency.WEEKLY:
        # Group by (ISO year, ISO week)
        completed_weeks = sorted({d.isocalendar()[:2] for d in logs})
        current_year, current_week, _ = today.isocalendar()

        curr_streak = 0
        check_date = today
        # Check current week, or if not logged yet, start checking from previous week
        if (current_year, current_week) in completed_weeks:
            curr_streak += 1
            check_date -= timedelta(days=7)
        else:
            check_date -= timedelta(days=7)

        while True:
            y, w, _ = check_date.isocalendar()
            if (y, w) in completed_weeks:
                curr_streak += 1
                check_date -= timedelta(days=7)
            else:
                break

        # Calculate longest contiguous weekly streak
        best_streak = max(curr_streak, len(completed_weeks))
        return {'current_streak': curr_streak, 'best_streak': best_streak}

    else:
        # Daily streak calculation
        curr_streak = 0
        check_date = today
        if check_date not in log_set:
            check_date -= timedelta(days=1)

        while check_date in log_set:
            curr_streak += 1
            check_date -= timedelta(days=1)

        # Longest contiguous daily streak
        sorted_dates = sorted(log_set)
        best_streak = 0
        temp_streak = 0
        prev_d = None
        for d in sorted_dates:
            if prev_d and d == prev_d + timedelta(days=1):
                temp_streak += 1
            else:
                temp_streak = 1
            prev_d = d
            best_streak = max(best_streak, temp_streak)

        best_streak = max(best_streak, curr_streak)
        return {'current_streak': curr_streak, 'best_streak': best_streak}


# ==============================================================================
# 1. TASK MANAGEMENT VIEWS
# ==============================================================================

@login_required
def task_list_view(request):
    """
    Task management list with search, status/priority/category/due filtering, sorting,
    and summary metrics.
    """
    today = timezone.localtime(timezone.now()).date()
    qs = Task.objects.filter(user=request.user).select_related('category', 'project')

    # Summary metrics across all user tasks
    total_count = qs.count()
    pending_count = qs.filter(status=TaskStatus.PENDING).count()
    in_progress_count = qs.filter(status=TaskStatus.IN_PROGRESS).count()
    completed_count = qs.filter(status=TaskStatus.COMPLETED).count()
    overdue_count = qs.filter(
        due_date__lt=today,
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ).count()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    # Filters
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in TaskStatus.values:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '').strip()
    if priority_filter and priority_filter in Priority.values:
        qs = qs.filter(priority=priority_filter)

    category_filter = request.GET.get('category', '').strip()
    if category_filter and category_filter.isdigit():
        qs = qs.filter(category_id=int(category_filter))

    due_filter = request.GET.get('due', '').strip()
    if due_filter == 'today':
        qs = qs.filter(due_date=today)
    elif due_filter == 'overdue':
        qs = qs.filter(due_date__lt=today, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
    elif due_filter == 'upcoming':
        qs = qs.filter(due_date__gt=today)
    elif due_filter == 'nodate':
        qs = qs.filter(due_date__isnull=True)

    # Sorting
    sort = request.GET.get('sort', 'default').strip()
    if sort == 'due_asc':
        qs = qs.order_by(models.F('due_date').asc(nulls_last=True), '-created_at')
    elif sort == 'due_desc':
        qs = qs.order_by(models.F('due_date').desc(nulls_last=True), '-created_at')
    elif sort == 'priority':
        qs = qs.order_by(
            Case(
                When(priority=Priority.URGENT, then=0),
                When(priority=Priority.HIGH, then=1),
                When(priority=Priority.MEDIUM, then=2),
                default=3
            ),
            '-created_at'
        )
    elif sort == 'created_desc':
        qs = qs.order_by('-created_at')
    elif sort == 'created_asc':
        qs = qs.order_by('created_at')
    else:
        # Default order: pending/in_progress first, then overdue/priority, completed at end
        qs = qs.order_by(
            Case(When(status=TaskStatus.COMPLETED, then=1), default=0),
            Case(
                When(due_date__lt=today, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS], then=0),
                default=1
            ),
            Case(
                When(priority=Priority.URGENT, then=0),
                When(priority=Priority.HIGH, then=1),
                When(priority=Priority.MEDIUM, then=2),
                default=3
            ),
            models.F('due_date').asc(nulls_last=True),
            '-created_at'
        )

    # Annotate overdue
    tasks_list = list(qs)
    for t in tasks_list:
        t.is_overdue = bool(t.due_date and t.due_date < today and t.status != TaskStatus.COMPLETED)

    # Pagination
    paginator = Paginator(tasks_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(user=request.user).order_by('name')

    context = {
        'page_title': 'Tasks & Productivity',
        'active_nav': 'tasks',
        'page_obj': page_obj,
        'tasks': page_obj.object_list,
        'categories': categories,
        'today': today,

        # Metrics
        'total_count': total_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,

        # Filter states
        'q': q,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'due_filter': due_filter,
        'sort': sort,
        'priorities': Priority.choices,
        'statuses': TaskStatus.choices,
    }
    return render(request, 'productivity/tasks.html', context)


@login_required
def task_create_view(request):
    """
    Create a new task with category, project, priority, estimated duration, and due date.
    """
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            if task.status == TaskStatus.COMPLETED:
                task.completed_at = timezone.now()
            task.save()
            messages.success(request, f"Task '{task.title}' created successfully.")
            return redirect('productivity:task_list')
    else:
        # Prepopulate project or category if passed in GET params
        initial = {}
        if 'project' in request.GET and request.GET['project'].isdigit():
            initial['project'] = int(request.GET['project'])
        if 'category' in request.GET and request.GET['category'].isdigit():
            initial['category'] = int(request.GET['category'])
        form = TaskForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Create Task',
        'active_nav': 'tasks',
        'form': form,
    }
    return render(request, 'productivity/task_form.html', context)


@login_required
def task_detail_view(request, pk):
    """
    Detailed task view displaying time tracking, linked project, and associated goals.
    """
    task = get_object_or_404(Task.objects.select_related('category', 'project'), pk=pk, user=request.user)
    today = timezone.localtime(timezone.now()).date()
    task.is_overdue = bool(task.due_date and task.due_date < today and task.status != TaskStatus.COMPLETED)

    # Linked goals through GoalTask junction
    from apps.planning.models import GoalTask
    goal_links = GoalTask.objects.filter(task=task).select_related('goal')

    context = {
        'page_title': task.title,
        'active_nav': 'tasks',
        'task': task,
        'goal_links': goal_links,
    }
    return render(request, 'productivity/task_detail.html', context)


@login_required
def task_update_view(request, pk):
    """
    Update an existing task, managing status changes and completion timestamps.
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == 'POST':
        prev_status = task.status
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            updated_task = form.save(commit=False)
            if updated_task.status == TaskStatus.COMPLETED and prev_status != TaskStatus.COMPLETED:
                updated_task.completed_at = timezone.now()
            elif updated_task.status != TaskStatus.COMPLETED:
                updated_task.completed_at = None
            updated_task.save()
            messages.success(request, f"Task '{updated_task.title}' updated successfully.")
            return redirect('productivity:task_detail', pk=updated_task.pk)
    else:
        form = TaskForm(instance=task, user=request.user)

    context = {
        'page_title': f"Edit Task — {task.title}",
        'active_nav': 'tasks',
        'form': form,
        'task': task,
    }
    return render(request, 'productivity/task_form.html', context)


@login_required
def task_delete_view(request, pk):
    """
    Delete task with explicit user confirmation.
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == 'POST':
        title = task.title
        task.delete()
        messages.success(request, f"Task '{title}' was deleted.")
        return redirect('productivity:task_list')

    context = {
        'page_title': f"Delete Task — {task.title}",
        'active_nav': 'tasks',
        'task': task,
    }
    return render(request, 'productivity/task_confirm_delete.html', context)


@login_required
@require_POST
def task_toggle_complete_view(request, pk):
    """
    Quick status toggle between COMPLETED and PENDING.
    """
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if task.status == TaskStatus.COMPLETED:
        task.status = TaskStatus.PENDING
        task.completed_at = None
        action = "reopened"
        # Sync linked schedule blocks
        ScheduleBlock.objects.filter(
            user=request.user,
            related_task=task,
            status=ScheduleStatus.COMPLETED
        ).update(status=ScheduleStatus.SCHEDULED)
    else:
        task.status = TaskStatus.COMPLETED
        task.completed_at = timezone.now()
        action = "completed"
        # Sync linked schedule blocks
        ScheduleBlock.objects.filter(
            user=request.user,
            related_task=task,
            status=ScheduleStatus.SCHEDULED
        ).update(status=ScheduleStatus.COMPLETED)
    task.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok',
            'is_completed': task.status == TaskStatus.COMPLETED,
            'message': f"Task {action}."
        })

    messages.success(request, f"Task '{task.title}' marked as {action}.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('productivity:task_list')


# ==============================================================================
# 2. CATEGORY MANAGEMENT VIEWS
# ==============================================================================

@login_required
def category_list_view(request):
    """
    Category management list showing category definitions, color codes,
    and associated record counts.
    """
    categories = Category.objects.filter(user=request.user).annotate(
        task_count=Count('tasks', distinct=True),
        habit_count=Count('habits', distinct=True),
        activity_count=Count('activities', distinct=True),
        project_count=Count('projects', distinct=True),
        goal_count=Count('goals', distinct=True),
    ).order_by('name')

    context = {
        'page_title': 'Categories',
        'active_nav': 'tasks',
        'categories': categories,
        'category_types': CategoryType.choices,
    }
    return render(request, 'productivity/categories.html', context)


@login_required
def category_create_view(request):
    """
    Create a new user-scoped category.
    """
    if request.method == 'POST':
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect('productivity:category_list')
    else:
        form = CategoryForm(user=request.user)

    context = {
        'page_title': 'Create Category',
        'active_nav': 'tasks',
        'form': form,
    }
    return render(request, 'productivity/category_form.html', context)


@login_required
def category_update_view(request, pk):
    """
    Edit category attributes.
    """
    category = get_object_or_404(Category, pk=pk, user=request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' updated.")
            return redirect('productivity:category_list')
    else:
        form = CategoryForm(instance=category, user=request.user)

    context = {
        'page_title': f"Edit Category — {category.name}",
        'active_nav': 'tasks',
        'form': form,
        'category': category,
    }
    return render(request, 'productivity/category_form.html', context)


@login_required
def category_delete_view(request, pk):
    """
    Safely delete a category. Informs user of associated records that will be unassigned.
    """
    category = get_object_or_404(Category, pk=pk, user=request.user)
    associated_count = (
        category.tasks.count() +
        category.habits.count() +
        category.activities.count() +
        category.projects.count() +
        category.goals.count()
    )

    if request.method == 'POST':
        name = category.name
        # on_delete=models.SET_NULL automatically sets references to null
        category.delete()
        messages.success(request, f"Category '{name}' deleted. Associated records have been preserved without category.")
        return redirect('productivity:category_list')

    context = {
        'page_title': f"Delete Category — {category.name}",
        'active_nav': 'tasks',
        'category': category,
        'associated_count': associated_count,
    }
    return render(request, 'productivity/category_confirm_delete.html', context)


# ==============================================================================
# 3. HABIT MANAGEMENT VIEWS
# ==============================================================================

@login_required
def habit_list_view(request):
    """
    Habit tracker list with completion toggling, streak calculations,
    and frequency-aware statistics.
    """
    today = timezone.localtime(timezone.now()).date()
    qs = Habit.objects.filter(user=request.user).select_related('category')

    status_filter = request.GET.get('status', 'active').strip()
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'archived':
        qs = qs.filter(is_active=False)

    habits = list(qs.order_by('-is_active', 'name'))

    today_logs = set(HabitLog.objects.filter(
        user=request.user, log_date=today, completed=True
    ).values_list('habit_id', flat=True))

    habits_data = []
    total_completed_today = 0

    for h in habits:
        is_done = h.id in today_logs
        if is_done and h.is_active:
            total_completed_today += 1

        streaks = calculate_habit_streak(h, request.user)
        habits_data.append({
            'habit': h,
            'completed_today': is_done,
            'current_streak': streaks['current_streak'],
            'best_streak': streaks['best_streak'],
        })

    active_count = Habit.objects.filter(user=request.user, is_active=True).count()
    completion_rate = round((total_completed_today / active_count) * 100) if active_count > 0 else 0

    context = {
        'page_title': 'Habits & Routines',
        'active_nav': 'habits',
        'habits_data': habits_data,
        'today': today,
        'status_filter': status_filter,
        'active_count': active_count,
        'total_completed_today': total_completed_today,
        'completion_rate': completion_rate,
    }
    return render(request, 'productivity/habits.html', context)


@login_required
def habit_create_view(request):
    """
    Create a new habit with frequency and target count.
    """
    if request.method == 'POST':
        form = HabitForm(request.POST, user=request.user)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, f"Habit '{habit.name}' created.")
            return redirect('productivity:habit_list')
    else:
        form = HabitForm(user=request.user)

    context = {
        'page_title': 'Create Habit',
        'active_nav': 'habits',
        'form': form,
    }
    return render(request, 'productivity/habit_form.html', context)


@login_required
def habit_detail_view(request, pk):
    """
    Detailed habit view showing 30-day historical log calendar, streaks, and completion analytics.
    """
    habit = get_object_or_404(Habit.objects.select_related('category'), pk=pk, user=request.user)
    today = timezone.localtime(timezone.now()).date()

    # Recent 30 days log history
    thirty_days_ago = today - timedelta(days=29)
    logs = HabitLog.objects.filter(
        habit=habit, user=request.user, log_date__gte=thirty_days_ago
    ).order_by('-log_date')

    logs_by_date = {log.log_date: log for log in logs}

    # Calendar matrix for last 30 days
    history_days = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        log_entry = logs_by_date.get(day)
        history_days.append({
            'date': day,
            'is_today': day == today,
            'completed': log_entry.completed if log_entry else False,
            'notes': log_entry.notes if log_entry else '',
        })

    streaks = calculate_habit_streak(habit, request.user)

    context = {
        'page_title': habit.name,
        'active_nav': 'habits',
        'habit': habit,
        'history_days': history_days,
        'current_streak': streaks['current_streak'],
        'best_streak': streaks['best_streak'],
        'total_logs_count': HabitLog.objects.filter(habit=habit, user=request.user, completed=True).count(),
        'today': today,
    }
    return render(request, 'productivity/habit_detail.html', context)


@login_required
def habit_update_view(request, pk):
    """
    Update habit properties.
    """
    habit = get_object_or_404(Habit, pk=pk, user=request.user)

    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit, user=request.user)
        if form.is_valid():
            h = form.save()
            messages.success(request, f"Habit '{h.name}' updated.")
            return redirect('productivity:habit_detail', pk=h.pk)
    else:
        form = HabitForm(instance=habit, user=request.user)

    context = {
        'page_title': f"Edit Habit — {habit.name}",
        'active_nav': 'habits',
        'form': form,
        'habit': habit,
    }
    return render(request, 'productivity/habit_form.html', context)


@login_required
def habit_delete_view(request, pk):
    """
    Delete habit and associated logs with confirmation.
    """
    habit = get_object_or_404(Habit, pk=pk, user=request.user)

    if request.method == 'POST':
        name = habit.name
        habit.delete()
        messages.success(request, f"Habit '{name}' and its log history were deleted.")
        return redirect('productivity:habit_list')

    context = {
        'page_title': f"Delete Habit — {habit.name}",
        'active_nav': 'habits',
        'habit': habit,
        'logs_count': habit.logs.count(),
    }
    return render(request, 'productivity/habit_confirm_delete.html', context)


@login_required
@require_POST
def habit_log_view(request, pk):
    """
    Log or toggle habit completion for today or a specific date with optional notes.
    """
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.localtime(timezone.now()).date()

    log_date_str = request.POST.get('log_date', '').strip()
    target_date = today
    if log_date_str:
        try:
            target_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = today

    notes = request.POST.get('notes', '').strip()

    hlog, created = HabitLog.objects.get_or_create(
        habit=habit,
        user=request.user,
        log_date=target_date,
        defaults={'completed': True, 'notes': notes}
    )

    if not created:
        hlog.completed = not hlog.completed
        if notes:
            hlog.notes = notes
        hlog.save()

    status_str = "completed" if hlog.completed else "unmarked"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok',
            'completed': hlog.completed,
            'message': f"Habit '{habit.name}' {status_str} for {target_date}."
        })

    messages.success(request, f"Habit '{habit.name}' {status_str} for {target_date}.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('productivity:habit_list')


@login_required
@require_POST
def habit_toggle_active_view(request, pk):
    """
    Pause or resume a habit without destroying log history.
    """
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit.is_active = not habit.is_active
    habit.save()

    status_desc = "resumed" if habit.is_active else "paused"
    messages.success(request, f"Habit '{habit.name}' has been {status_desc}.")
    return redirect('productivity:habit_list')


# ==============================================================================
# 4. ACTIVITY TRACKING VIEWS
# ==============================================================================

@login_required
def activity_list_view(request):
    """
    Activity tracking view displaying running timers, manual activity logging,
    and history filtering by category and date.
    """
    today = timezone.localtime(timezone.now()).date()
    qs = Activity.objects.filter(user=request.user).select_related('category')

    # Find currently running active session if any
    active_activity = qs.filter(end_time__isnull=True).order_by('-start_time').first()

    # Time calculations
    today_activities = qs.filter(start_time__date=today, end_time__isnull=False)
    today_minutes = sum(a.duration_minutes or 0 for a in today_activities)

    week_start = today - timedelta(days=today.weekday())
    week_activities = qs.filter(start_time__date__gte=week_start, end_time__isnull=False)
    week_minutes = sum(a.duration_minutes or 0 for a in week_activities)

    # Filter by category
    cat_id = request.GET.get('category', '').strip()
    if cat_id and cat_id.isdigit():
        qs = qs.filter(category_id=int(cat_id))

    # Filter by date range
    date_filter = request.GET.get('date', '').strip()
    if date_filter == 'today':
        qs = qs.filter(start_time__date=today)
    elif date_filter == 'week':
        qs = qs.filter(start_time__date__gte=week_start)

    activities = qs.order_by('-start_time')[:30]
    categories = Category.objects.filter(user=request.user).order_by('name')

    def format_mins(mins):
        if mins >= 60:
            return f"{mins // 60}h {mins % 60}m"
        return f"{mins} mins"

    context = {
        'page_title': 'Activities & Time Tracking',
        'active_nav': 'activities',
        'activities': activities,
        'active_activity': active_activity,
        'categories': categories,
        'today_duration': format_mins(today_minutes),
        'week_duration': format_mins(week_minutes),
        'today': today,
        'cat_id': cat_id,
        'date_filter': date_filter,
    }
    return render(request, 'productivity/activities.html', context)


@login_required
def activity_create_view(request):
    """
    Manual entry of an activity that occurred in the past.
    """
    if request.method == 'POST':
        form = ActivityForm(request.POST, user=request.user)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.user = request.user
            activity.save()
            messages.success(request, f"Activity '{activity.activity_name}' recorded.")
            return redirect('productivity:activity_list')
    else:
        now = timezone.localtime(timezone.now())
        initial = {
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now + timedelta(minutes=45)).strftime('%Y-%m-%dT%H:%M'),
        }
        form = ActivityForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Record Activity',
        'active_nav': 'activities',
        'form': form,
    }
    return render(request, 'productivity/activity_form.html', context)


@login_required
@require_POST
def activity_start_view(request):
    """
    Start a live activity timer. If an existing activity is already active,
    automatically stops it first.
    """
    name = request.POST.get('activity_name', '').strip() or 'Focus Session'
    cat_id = request.POST.get('category_id', '').strip()
    category = None
    if cat_id and cat_id.isdigit():
        category = Category.objects.filter(id=int(cat_id), user=request.user).first()

    now = timezone.now()

    # Close any currently active activity cleanly
    active = Activity.objects.filter(user=request.user, end_time__isnull=True).first()
    if active:
        active.end_time = now
        active.save()

    new_activity = Activity.objects.create(
        user=request.user,
        activity_name=name,
        category=category,
        start_time=now,
        end_time=None
    )

    messages.success(request, f"Started timer for '{new_activity.activity_name}'.")
    return redirect('productivity:activity_list')


@login_required
@require_POST
def activity_stop_view(request, pk):
    """
    Stop an active timer and finalize its duration.
    """
    activity = get_object_or_404(Activity, pk=pk, user=request.user)
    if activity.end_time is None:
        activity.end_time = timezone.now()
        activity.save()
        messages.success(request, f"Stopped '{activity.activity_name}'. Logged {activity.duration_minutes} minutes.")
    return redirect('productivity:activity_list')


@login_required
def activity_delete_view(request, pk):
    """
    Delete activity record with confirmation.
    """
    activity = get_object_or_404(Activity, pk=pk, user=request.user)
    if request.method == 'POST':
        name = activity.activity_name
        activity.delete()
        messages.success(request, f"Activity '{name}' was deleted.")
        return redirect('productivity:activity_list')

    context = {
        'page_title': f"Delete Activity — {activity.activity_name}",
        'active_nav': 'activities',
        'activity': activity,
    }
    return render(request, 'productivity/activity_confirm_delete.html', context)


# ==============================================================================
# 5. DAILY TIMETABLE VIEWS
# ==============================================================================

@login_required
def daily_timetable_view(request):
    """
    Chronological daily timetable displaying fixed routines, scheduled tasks,
    study blocks, rest breaks, and available gaps for a specific calendar date.
    """
    user = request.user
    date_str = request.GET.get('date', '').strip()
    today = timezone.localtime(timezone.now()).date()

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = today
    else:
        target_date = today

    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    is_today = (target_date == today)

    # Fetch scheduled blocks for this date
    blocks = list(
        ScheduleBlock.objects.filter(
            user=user,
            block_date=target_date
        ).select_related('related_task', 'related_routine', 'related_study_plan')
        .order_by('start_time')
    )

    # Active routines that apply on this date
    routines = [
        r for r in Routine.objects.filter(user=user, is_active=True).order_by('start_time')
        if r.applies_on_date(target_date)
    ]

    # Metrics
    total_work_minutes = sum(
        b.duration_minutes for b in blocks
        if b.block_type in [BlockType.FOCUS, BlockType.STUDY]
    )
    completed_count = sum(1 for b in blocks if b.status == ScheduleStatus.COMPLETED)
    scheduled_count = sum(1 for b in blocks if b.status == ScheduleStatus.SCHEDULED)
    skipped_count = sum(1 for b in blocks if b.status == ScheduleStatus.SKIPPED)

    # Compute free gaps in working windows
    available_windows = get_user_availability_windows(user, target_date)
    fixed_commitments = get_day_fixed_commitments(user, target_date)
    free_intervals = compute_free_intervals(available_windows, fixed_commitments, target_date)
    total_free_minutes = sum(dur for _, _, dur in free_intervals)

    context = {
        'page_title': f"Daily Timetable — {target_date.strftime('%a, %b %d')}",
        'active_nav': 'timetable',
        'subnav': 'daily',
        'target_date': target_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'is_today': is_today,
        'blocks': blocks,
        'routines': routines,
        'total_blocks': len(blocks),
        'completed_count': completed_count,
        'scheduled_count': scheduled_count,
        'skipped_count': skipped_count,
        'total_work_minutes': total_work_minutes,
        'total_work_str': f"{total_work_minutes // 60}h {total_work_minutes % 60}m",
        'total_free_minutes': total_free_minutes,
        'free_intervals': free_intervals,
        'statuses': ScheduleStatus.choices,
        'block_types': BlockType.choices,
    }
    return render(request, 'timetable/daily.html', context)


@login_required
def schedule_block_create_view(request):
    """
    Manually create a single schedule block on a date.
    """
    target_date_str = request.GET.get('date', '').strip()
    initial = {}
    if target_date_str:
        try:
            initial['block_date'] = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if request.method == 'POST':
        form = ScheduleBlockForm(request.POST, user=request.user)
        if form.is_valid():
            block = form.save()
            messages.success(request, f"Scheduled block '{block.title}' for {block.start_time.strftime('%H:%M')}.")
            return redirect(f"{redirect('productivity:timetable_daily').url}?date={block.block_date.strftime('%Y-%m-%d')}")
    else:
        form = ScheduleBlockForm(user=request.user, initial=initial)

    context = {
        'page_title': 'Add Schedule Block',
        'active_nav': 'timetable',
        'subnav': 'daily',
        'form': form,
    }
    return render(request, 'timetable/block_form.html', context)


@login_required
def schedule_block_update_view(request, pk):
    """
    Edit attributes, timings, or status of a schedule block.
    """
    block = get_object_or_404(ScheduleBlock, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ScheduleBlockForm(request.POST, instance=block, user=request.user)
        if form.is_valid():
            b = form.save()
            messages.success(request, f"Schedule block '{b.title}' updated.")
            return redirect(f"{redirect('productivity:timetable_daily').url}?date={b.block_date.strftime('%Y-%m-%d')}")
    else:
        form = ScheduleBlockForm(instance=block, user=request.user)

    context = {
        'page_title': f"Edit Block — {block.title}",
        'active_nav': 'timetable',
        'subnav': 'daily',
        'form': form,
        'block': block,
    }
    return render(request, 'timetable/block_form.html', context)


@login_required
def schedule_block_delete_view(request, pk):
    """
    Delete a schedule block with confirmation.
    """
    block = get_object_or_404(ScheduleBlock, pk=pk, user=request.user)
    block_date = block.block_date

    if request.method == 'POST':
        title = block.title
        block.delete()
        messages.success(request, f"Block '{title}' removed from timetable.")
        return redirect(f"{redirect('productivity:timetable_daily').url}?date={block_date.strftime('%Y-%m-%d')}")

    context = {
        'page_title': f"Delete Block — {block.title}",
        'active_nav': 'timetable',
        'subnav': 'daily',
        'block': block,
    }
    return render(request, 'timetable/block_confirm_delete.html', context)


@login_required
@require_POST
def schedule_block_status_view(request, pk):
    """
    Quick status action (COMPLETED, SKIPPED, SCHEDULED, IN_PROGRESS) for a block.
    Synchronizes task or study plan completion when completed.
    """
    block = get_object_or_404(ScheduleBlock, pk=pk, user=request.user)
    new_status = request.POST.get('status', '').strip()

    if new_status in ScheduleStatus.values:
        block.status = new_status
        block.save()

        # If completed, synchronize linked Task
        if new_status == ScheduleStatus.COMPLETED:
            if block.related_task and block.related_task.status != TaskStatus.COMPLETED:
                t = block.related_task
                t.status = TaskStatus.COMPLETED
                t.completed_at = timezone.now()
                if not t.actual_minutes:
                    t.actual_minutes = block.duration_minutes
                t.save()
                messages.success(request, f"Marked '{block.title}' and linked task as Completed!")
            elif block.related_study_plan and block.related_study_plan.status != PlanStatus.COMPLETED:
                sp = block.related_study_plan
                sp.status = PlanStatus.COMPLETED
                sp.save()
                messages.success(request, f"Marked '{block.title}' and study plan as Completed!")
            else:
                messages.success(request, f"Block '{block.title}' marked as Completed.")
        elif new_status == ScheduleStatus.SKIPPED:
            mark_block_skipped(request.user, block)
            messages.info(request, f"Block '{block.title}' marked as Skipped.")
        else:
            messages.info(request, f"Block '{block.title}' set to {block.get_status_display()}.")
    else:
        messages.error(request, "Invalid status choice.")

    return redirect(f"{redirect('productivity:timetable_daily').url}?date={block.block_date.strftime('%Y-%m-%d')}")


@login_required
def schedule_block_reschedule_view(request, pk):
    """
    Reschedule an incomplete or skipped block to a new date and time slot.
    """
    block = get_object_or_404(ScheduleBlock, pk=pk, user=request.user)

    if request.method == 'POST':
        form = RescheduleBlockForm(request.POST)
        if form.is_valid():
            new_date = form.cleaned_data['new_date']
            new_start = form.cleaned_data.get('new_start_time')

            success, msg, _ = reschedule_schedule_block(
                user=request.user,
                block=block,
                new_date=new_date,
                new_start_time=new_start
            )
            if success:
                messages.success(request, msg)
                return redirect(f"{redirect('productivity:timetable_daily').url}?date={new_date.strftime('%Y-%m-%d')}")
            else:
                messages.error(request, msg)
    else:
        form = RescheduleBlockForm(initial={
            'new_date': block.block_date + timedelta(days=1),
            'new_start_time': block.start_time,
        })

    context = {
        'page_title': f"Reschedule Block — {block.title}",
        'active_nav': 'timetable',
        'subnav': 'daily',
        'block': block,
        'form': form,
    }
    return render(request, 'timetable/block_reschedule.html', context)


# ==============================================================================
# 6. WEEKLY TIMETABLE VIEW
# ==============================================================================

@login_required
def weekly_timetable_view(request):
    """
    Weekly timetable displaying Monday through Sunday with navigation,
    fixed routines, schedule blocks, and mobile-friendly responsive layout.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()
    date_str = request.GET.get('date', '').strip()

    if date_str:
        try:
            anchor_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            anchor_date = today
    else:
        anchor_date = today

    # Find Monday of anchor_date's week
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    week_end = week_start + timedelta(days=6)
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    # Fetch all blocks for this entire week
    week_blocks = list(
        ScheduleBlock.objects.filter(
            user=user,
            block_date__gte=week_start,
            block_date__lte=week_end
        ).select_related('related_task', 'related_routine', 'related_study_plan')
        .order_by('block_date', 'start_time')
    )

    # Active user routines
    routines = list(Routine.objects.filter(user=user, is_active=True).order_by('start_time'))

    # Build day-by-day structure
    days_data = []
    total_week_work_mins = 0

    for i in range(7):
        current_day = week_start + timedelta(days=i)
        day_blocks = [b for b in week_blocks if b.block_date == current_day]
        day_routines = [r for r in routines if r.applies_on_date(current_day)]
        
        work_mins = sum(
            b.duration_minutes for b in day_blocks
            if b.block_type in [BlockType.FOCUS, BlockType.STUDY]
        )
        total_week_work_mins += work_mins

        days_data.append({
            'date': current_day,
            'day_name': current_day.strftime('%A'),
            'day_short': current_day.strftime('%a'),
            'date_str': current_day.strftime('%b %d'),
            'is_today': (current_day == today),
            'blocks': day_blocks,
            'routines': day_routines,
            'work_mins': work_mins,
            'work_hours': round(work_mins / 60, 1),
            'total_items': len(day_blocks) + len(day_routines),
        })

    # Pending unscheduled tasks summary for sidebar
    pending_tasks = Task.objects.filter(
        user=user,
        status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
    ).order_by('due_date', '-priority')[:8]

    context = {
        'page_title': f"Weekly Timetable — {week_start.strftime('%b %d')} to {week_end.strftime('%b %d, %Y')}",
        'active_nav': 'timetable',
        'subnav': 'weekly',
        'week_start': week_start,
        'week_end': week_end,
        'prev_week': prev_week,
        'next_week': next_week,
        'today': today,
        'days_data': days_data,
        'total_week_work_str': f"{total_week_work_mins // 60}h {total_week_work_mins % 60}m",
        'pending_tasks': pending_tasks,
    }
    return render(request, 'timetable/weekly.html', context)


# ==============================================================================
# 7. ROUTINE MANAGEMENT VIEWS
# ==============================================================================

@login_required
def routine_list_view(request):
    """
    List of user's recurring daily routines with weekday filters and active switches.
    """
    user = request.user
    qs = Routine.objects.filter(user=user)

    day_filter = request.GET.get('day', '').strip().upper()
    if day_filter and day_filter in DayOfWeek.values:
        qs = qs.filter(days_of_week__icontains=day_filter)

    type_filter = request.GET.get('type', '').strip()
    if type_filter and type_filter in RoutineType.values:
        qs = qs.filter(routine_type=type_filter)

    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    routines = qs.order_by('start_time')

    context = {
        'page_title': 'Daily Routines',
        'active_nav': 'routines',
        'subnav': 'routines',
        'routines': routines,
        'day_filter': day_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'days': DayOfWeek.choices,
        'routine_types': RoutineType.choices,
    }
    return render(request, 'timetable/routines.html', context)


@login_required
def routine_create_view(request):
    """
    Define a new recurring routine or fixed commitment.
    """
    if request.method == 'POST':
        form = RoutineForm(request.POST, user=request.user)
        if form.is_valid():
            routine = form.save()
            messages.success(request, f"Routine '{routine.title}' created.")
            return redirect('productivity:routine_list')
    else:
        form = RoutineForm(user=request.user)

    context = {
        'page_title': 'Add Daily Routine',
        'active_nav': 'routines',
        'subnav': 'routines',
        'form': form,
    }
    return render(request, 'timetable/routine_form.html', context)


@login_required
def routine_update_view(request, pk):
    """
    Edit routine attributes, recurrence days, or timings.
    """
    routine = get_object_or_404(Routine, pk=pk, user=request.user)

    if request.method == 'POST':
        form = RoutineForm(request.POST, instance=routine, user=request.user)
        if form.is_valid():
            r = form.save()
            messages.success(request, f"Routine '{r.title}' updated.")
            return redirect('productivity:routine_list')
    else:
        form = RoutineForm(instance=routine, user=request.user)

    context = {
        'page_title': f"Edit Routine — {routine.title}",
        'active_nav': 'routines',
        'subnav': 'routines',
        'form': form,
        'routine': routine,
    }
    return render(request, 'timetable/routine_form.html', context)


@login_required
def routine_delete_view(request, pk):
    """
    Delete routine with confirmation dialog.
    """
    routine = get_object_or_404(Routine, pk=pk, user=request.user)

    if request.method == 'POST':
        title = routine.title
        routine.delete()
        messages.success(request, f"Routine '{title}' deleted.")
        return redirect('productivity:routine_list')

    context = {
        'page_title': f"Delete Routine — {routine.title}",
        'active_nav': 'routines',
        'subnav': 'routines',
        'routine': routine,
    }
    return render(request, 'timetable/routine_confirm_delete.html', context)


@login_required
@require_POST
def routine_toggle_active_view(request, pk):
    """
    Quick toggle to activate or deactivate a routine.
    """
    routine = get_object_or_404(Routine, pk=pk, user=request.user)
    routine.is_active = not routine.is_active
    routine.save()

    status_str = "activated" if routine.is_active else "paused"
    messages.success(request, f"Routine '{routine.title}' {status_str}.")
    return redirect('productivity:routine_list')


# ==============================================================================
# 8. AVAILABILITY MANAGEMENT VIEWS
# ==============================================================================

@login_required
def availability_view(request):
    """
    Weekly availability overview: displays permitted working hours grouped by day
    and provides inline forms to add or remove windows.
    """
    user = request.user
    windows = AvailabilityWindow.objects.filter(user=user).order_by('day_of_week', 'start_time')

    # Group by weekday
    windows_by_day = {code: [] for code, _ in DayOfWeek.choices}
    for w in windows:
        windows_by_day[w.day_of_week].append(w)

    pref = SchedulingPreference.get_for_user(user)

    day_cards = []
    for code, name in DayOfWeek.choices:
        day_windows = windows_by_day[code]
        total_mins = sum(w.duration_minutes for w in day_windows)
        day_cards.append({
            'code': code,
            'name': name,
            'windows': day_windows,
            'has_custom': len(day_windows) > 0,
            'total_mins': total_mins,
            'total_hours': round(total_mins / 60, 1),
        })

    form = AvailabilityWindowForm(user=user)

    context = {
        'page_title': 'Availability Management',
        'active_nav': 'timetable',
        'subnav': 'availability',
        'day_cards': day_cards,
        'pref': pref,
        'form': form,
    }
    return render(request, 'timetable/availability.html', context)


@login_required
@require_POST
def availability_create_view(request):
    """
    Add a new availability window for a day of week.
    """
    form = AvailabilityWindowForm(request.POST, user=request.user)
    if form.is_valid():
        w = form.save()
        messages.success(request, f"Added availability window for {w.get_day_of_week_display()} ({w.start_time.strftime('%H:%M')}-{w.end_time.strftime('%H:%M')}).")
    else:
        error_msg = list(form.errors.values())[0][0] if form.errors else "Invalid availability entry."
        messages.error(request, error_msg)

    return redirect('productivity:availability_list')


@login_required
@require_POST
def availability_delete_view(request, pk):
    """
    Delete an availability window.
    """
    window = get_object_or_404(AvailabilityWindow, pk=pk, user=request.user)
    day_name = window.get_day_of_week_display()
    window.delete()
    messages.success(request, f"Availability window for {day_name} removed.")
    return redirect('productivity:availability_list')


# ==============================================================================
# 9. SCHEDULE GENERATOR VIEWS
# ==============================================================================

@login_required
def schedule_generator_view(request):
    """
    Interactive Timetable Generator interface:
    - Select target date.
    - Inspect fixed commitments, available hours, pending tasks, study plans.
    - Run deterministic rule-based scheduling engine.
    - Preview generated timetable, breaks, and unscheduled items before saving.
    """
    user = request.user
    today = timezone.localtime(timezone.now()).date()
    target_date_str = request.GET.get('date', '').strip()

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = today + timedelta(days=1)
    else:
        target_date = today + timedelta(days=1)

    pref = SchedulingPreference.get_for_user(user)

    # Check existing blocks on target date
    existing_blocks_count = ScheduleBlock.objects.filter(
        user=user,
        block_date=target_date
    ).count()

    # Execute deterministic schedule generation preview
    generator = TimetableGenerator(user, target_date, preferences=pref)
    plan_preview = generator.generate()

    context = {
        'page_title': f"Smart Timetable Generator — {target_date.strftime('%a, %b %d')}",
        'active_nav': 'timetable',
        'subnav': 'generator',
        'target_date': target_date,
        'today': today,
        'pref': pref,
        'preview': plan_preview,
        'existing_blocks_count': existing_blocks_count,
    }
    return render(request, 'timetable/generator.html', context)


@login_required
@require_POST
def schedule_generator_apply_view(request):
    """
    Persist generated preview into active ScheduleBlock database records.
    Optionally replaces non-completed flexible blocks while preserving fixed/completed.
    """
    user = request.user
    target_date_str = request.POST.get('target_date', '').strip()
    replace_existing = bool(request.POST.get('replace_existing') == '1')

    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date.")
        return redirect('productivity:generator')

    generator = TimetableGenerator(user, target_date)
    plan_preview = generator.generate()

    history = generator.apply(plan_preview, replace_existing=replace_existing)

    total_added = plan_preview['statistics']['tasks_scheduled'] + plan_preview['statistics']['study_scheduled']
    messages.success(
        request,
        f"Timetable for {target_date.strftime('%a, %b %d')} generated! "
        f"{total_added} activities scheduled ({plan_preview['statistics']['total_work_minutes']} mins work)."
    )
    return redirect(f"{redirect('productivity:timetable_daily').url}?date={target_date.strftime('%Y-%m-%d')}")


# ==============================================================================
# 10. SCHEDULE HISTORY VIEW
# ==============================================================================

@login_required
def schedule_history_view(request):
    """
    Audit log of previously generated schedules, planned work metrics, and unscheduled items.
    """
    user = request.user
    histories = ScheduleGenerationHistory.objects.filter(user=user).order_by('-generated_at')

    context = {
        'page_title': 'Schedule Generation History',
        'active_nav': 'timetable',
        'subnav': 'history',
        'histories': histories,
    }
    return render(request, 'timetable/history.html', context)


# ==============================================================================
# 11. SCHEDULING PREFERENCES VIEW
# ==============================================================================

@login_required
def scheduling_preferences_view(request):
    """
    User settings governing timetable generation: work hours, breaks, buffers.
    """
    pref = SchedulingPreference.get_for_user(request.user)

    if request.method == 'POST':
        form = SchedulingPreferenceForm(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            messages.success(request, "Scheduling preferences updated.")
            return redirect('productivity:scheduling_preferences')
    else:
        form = SchedulingPreferenceForm(instance=pref)

    context = {
        'page_title': 'Scheduling Preferences',
        'active_nav': 'timetable',
        'subnav': 'preferences',
        'form': form,
    }
    return render(request, 'timetable/preferences.html', context)

