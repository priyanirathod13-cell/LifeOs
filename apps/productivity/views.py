from datetime import date, datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Case, Count, Q, Sum, When
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ActivityForm, CategoryForm, HabitForm, HabitLogForm, TaskForm
from .models import (
    Activity,
    Category,
    CategoryType,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    Task,
    TaskStatus,
)


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
    else:
        task.status = TaskStatus.COMPLETED
        task.completed_at = timezone.now()
        action = "completed"
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
