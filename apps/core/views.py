from datetime import date, datetime, time, timedelta
from decimal import Decimal
import zoneinfo

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Case, Count, Q, Sum, When
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.models import (
    DismissedRecommendation,
    Notification,
    NotificationType,
    UserPreference,
)
from apps.core.services.export_service import ExportService
from apps.core.services.notification_service import NotificationService
from apps.core.services.recommendation_service import RecommendationService
from apps.core.services.search_service import GlobalSearchService
from apps.personal.models import DailyMetric, JournalEntry
from apps.planning.models import Goal, GoalStatus, GoalTask, Priority as GoalPriority, Project
from apps.productivity.models import (
    Activity,
    BlockType,
    Category,
    Habit,
    HabitFrequency,
    HabitLog,
    Priority,
    Routine,
    ScheduleBlock,
    ScheduleStatus,
    Task,
    TaskStatus,
)
from apps.study.models import Exam, StudySession, Subject


def health_check(request):
    """
    Health-check endpoint confirming the LifeOS application is operational.
    Verifies database connectivity before returning HTTP 200.
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({
            "status": "degraded",
            "application": "LifeOS"
        }, status=503)

    return JsonResponse({
        "status": "ok",
        "application": "LifeOS"
    })


def landing_view(request):
    """
    Public landing page introducing LifeOS as 'Your Personal Behavioral Intelligence System'.
    If the user is already authenticated, seamlessly redirect them to their dashboard.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    return render(request, 'pages/landing.html', {
        'page_title': 'LifeOS — Personal Behavioral Intelligence System',
    })


@login_required
def dashboard(request):
    """
    Main authenticated control panel for LifeOS.
    Retrieves and aggregates live, user-scoped data across tasks, habits,
    study sessions, schedules, goals, biometrics, and recent activity streams.
    """
    # 1. Timezone and Local Time Handling
    user_tz_name = getattr(request.user, 'timezone_pref', None) or settings.TIME_ZONE
    try:
        user_tz = zoneinfo.ZoneInfo(user_tz_name)
    except Exception:
        user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

    now = timezone.now().astimezone(user_tz)
    today = now.date()
    current_time = now.time()

    # Time-adaptive greeting
    hour = now.hour
    if hour < 12:
        greeting_time = "Good morning"
    elif hour < 17:
        greeting_time = "Good afternoon"
    else:
        greeting_time = "Good evening"

    user_display_name = request.user.first_name or request.user.username
    formatted_date = today.strftime("%A, %d %B %Y")

    # 2. Today's Overview: Tasks
    user_tasks = Task.objects.filter(user=request.user)
    tasks_due_today = user_tasks.filter(
        Q(due_date=today) |
        Q(due_date__lt=today, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]) |
        Q(completed_at__date=today)
    )
    tasks_total_count = tasks_due_today.count()
    tasks_completed_count = tasks_due_today.filter(status=TaskStatus.COMPLETED).count()
    tasks_pending_count = tasks_total_count - tasks_completed_count
    tasks_completion_pct = round((tasks_completed_count / tasks_total_count) * 100) if tasks_total_count > 0 else 0

    # Ordered list of relevant tasks for today
    todays_tasks_qs = tasks_due_today.select_related('category', 'project').order_by(
        Case(When(status=TaskStatus.COMPLETED, then=1), default=0),
        Case(
            When(priority=Priority.URGENT, then=0),
            When(priority=Priority.HIGH, then=1),
            When(priority=Priority.MEDIUM, then=2),
            default=3
        ),
        'due_date',
        '-created_at'
    )[:8]

    todays_tasks = []
    for t in todays_tasks_qs:
        t.is_overdue = bool(t.due_date and t.due_date < today and t.status != TaskStatus.COMPLETED)
        todays_tasks.append(t)

    # 3. Today's Overview: Habits
    active_habits = Habit.objects.filter(user=request.user, is_active=True).select_related('category')
    habits_total_count = active_habits.count()

    today_completed_habit_ids = set(
        HabitLog.objects.filter(
            user=request.user,
            log_date=today,
            completed=True
        ).values_list('habit_id', flat=True)
    )
    habits_completed_count = len(today_completed_habit_ids)
    habits_remaining_count = max(0, habits_total_count - habits_completed_count)
    habits_completion_pct = round((habits_completed_count / habits_total_count) * 100) if habits_total_count > 0 else 0

    habits_display = []
    for h in active_habits[:8]:
        is_completed = h.id in today_completed_habit_ids
        habits_display.append({
            'habit': h,
            'completed': is_completed,
        })

    # 4. Today's Overview: Study
    today_study_sessions = StudySession.objects.filter(
        user=request.user,
        session_date=today
    ).select_related('subject', 'topic')

    study_sessions_count = today_study_sessions.count()
    total_study_minutes = today_study_sessions.aggregate(total=Sum('duration_minutes'))['total'] or 0

    if total_study_minutes >= 60:
        hrs = total_study_minutes // 60
        mins = total_study_minutes % 60
        study_time_display = f"{hrs}h {mins}m" if mins > 0 else f"{hrs} hrs"
    else:
        study_time_display = f"{total_study_minutes} mins"

    study_subjects_count = today_study_sessions.values('subject_id').distinct().count()

    upcoming_exams_qs = Exam.objects.filter(
        user=request.user,
        exam_date__gte=today
    ).select_related('subject').order_by('exam_date')[:3]

    upcoming_exams = []
    for exam in upcoming_exams_qs:
        exam.days_remaining = (exam.exam_date - today).days
        upcoming_exams.append(exam)

    # 5. Today's Overview: Goals
    active_goals_qs = Goal.objects.filter(
        user=request.user,
        status__in=[GoalStatus.NOT_STARTED, GoalStatus.IN_PROGRESS]
    ).select_related('category').prefetch_related('goal_tasks__task')

    goals_active_count = active_goals_qs.count()
    approaching_window = today + timedelta(days=30)
    goals_approaching_count = active_goals_qs.filter(
        target_date__isnull=False,
        target_date__gte=today,
        target_date__lte=approaching_window
    ).count()

    goals_preview = []
    for g in active_goals_qs.order_by('target_date', '-priority')[:4]:
        total_g_tasks = g.goal_tasks.count()
        completed_g_tasks = g.goal_tasks.filter(task__status=TaskStatus.COMPLETED).count()
        progress_pct = round((completed_g_tasks / total_g_tasks) * 100) if total_g_tasks > 0 else None
        days_left = (g.target_date - today).days if g.target_date else None
        goals_preview.append({
            'goal': g,
            'total_tasks': total_g_tasks,
            'completed_tasks': completed_g_tasks,
            'progress_pct': progress_pct,
            'days_left': days_left,
        })

    # 6. Daily Schedule & Upcoming Activities
    schedule_blocks_qs = ScheduleBlock.objects.filter(
        user=request.user,
        block_date=today
    ).select_related('related_task', 'related_routine').order_by('start_time')

    schedule_blocks = []
    for block in schedule_blocks_qs:
        if block.status == ScheduleStatus.COMPLETED:
            block.time_state = 'completed'
        elif block.end_time <= current_time:
            block.time_state = 'past'
        elif block.start_time <= current_time <= block.end_time:
            block.time_state = 'active'
        else:
            block.time_state = 'upcoming'
        schedule_blocks.append(block)

    today_activities = Activity.objects.filter(
        user=request.user,
        start_time__date=today
    ).select_related('category').order_by('-start_time')[:3]

    # 7. Recent Activity Unified Stream
    recent_stream = []

    # Recently completed tasks
    for rt in Task.objects.filter(
        user=request.user,
        status=TaskStatus.COMPLETED,
        completed_at__isnull=False
    ).order_by('-completed_at')[:3]:
        recent_stream.append({
            'type': 'task',
            'title': f"Completed: {rt.title}",
            'timestamp': rt.completed_at,
            'badge_text': 'Task Completed',
            'badge_class': 'badge-success',
        })

    # Recently logged habits
    for hl in HabitLog.objects.filter(
        user=request.user,
        completed=True
    ).select_related('habit').order_by('-created_at')[:3]:
        recent_stream.append({
            'type': 'habit',
            'title': f"Logged habit: {hl.habit.name}",
            'timestamp': hl.created_at,
            'badge_text': 'Habit Executed',
            'badge_class': 'badge-accent',
        })

    # Recently logged study sessions
    for rs in StudySession.objects.filter(
        user=request.user
    ).select_related('subject').order_by('-created_at')[:3]:
        recent_stream.append({
            'type': 'study',
            'title': f"Studied {rs.subject.name} ({rs.duration_minutes}m)",
            'timestamp': rs.created_at,
            'badge_text': 'Study Session',
            'badge_class': 'badge-secondary',
        })

    # Recently recorded journal reflections
    for rj in JournalEntry.objects.filter(
        user=request.user
    ).order_by('-created_at')[:2]:
        recent_stream.append({
            'type': 'journal',
            'title': f"Journal: {rj.title}",
            'timestamp': rj.created_at,
            'badge_text': 'Reflection',
            'badge_class': 'badge-neutral',
        })

    recent_stream.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_stream[:5]

    # 8. Daily Metric / Productivity Summary
    today_metric = DailyMetric.objects.filter(user=request.user, metric_date=today).first()

    # User categories for quick add task modal
    user_categories = Category.objects.filter(user=request.user).order_by('name')

    context = {
        'page_title': 'Dashboard',
        'active_nav': 'dashboard',

        # Welcome
        'greeting_time': greeting_time,
        'user_display_name': user_display_name,
        'formatted_date': formatted_date,

        # Task Stats
        'tasks_total_count': tasks_total_count,
        'tasks_completed_count': tasks_completed_count,
        'tasks_pending_count': tasks_pending_count,
        'tasks_completion_pct': tasks_completion_pct,
        'todays_tasks': todays_tasks,

        # Habit Stats
        'habits_total_count': habits_total_count,
        'habits_completed_count': habits_completed_count,
        'habits_remaining_count': habits_remaining_count,
        'habits_completion_pct': habits_completion_pct,
        'habits_display': habits_display,

        # Study Stats
        'study_sessions_count': study_sessions_count,
        'total_study_minutes': total_study_minutes,
        'study_time_display': study_time_display,
        'study_subjects_count': study_subjects_count,
        'upcoming_exams': upcoming_exams,

        # Goal Stats
        'goals_active_count': goals_active_count,
        'goals_approaching_count': goals_approaching_count,
        'goals_preview': goals_preview,

        # Schedules & Activities
        'schedule_blocks': schedule_blocks,
        'today_activities': today_activities,

        # Feed & Biometrics
        'recent_activities': recent_activities,
        'today_metric': today_metric,
        'user_categories': user_categories,
        'priority_choices': Priority.choices,
    }

    return render(request, 'pages/dashboard.html', context)


@login_required
@require_POST
def toggle_task_view(request, task_id):
    """
    Secure quick action to toggle task completion state from the dashboard.
    Strictly verifies ownership: task must belong to request.user.
    """
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if task.status == TaskStatus.COMPLETED:
        task.status = TaskStatus.PENDING
        task.completed_at = None
        action_desc = "marked pending"
        # Sync linked schedule blocks
        ScheduleBlock.objects.filter(
            user=request.user,
            related_task=task,
            status=ScheduleStatus.COMPLETED
        ).update(status=ScheduleStatus.SCHEDULED)
    else:
        task.status = TaskStatus.COMPLETED
        task.completed_at = timezone.now()
        action_desc = "marked completed"
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
            'task_id': task.id,
            'is_completed': task.status == TaskStatus.COMPLETED,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'message': f"Task '{task.title}' {action_desc}."
        })

    messages.success(request, f"Task '{task.title}' {action_desc}.")
    return redirect('core:dashboard')


@login_required
@require_POST
def toggle_habit_view(request, habit_id):
    """
    Secure quick action to log or unlog today's execution for a habit.
    Strictly verifies ownership: habit must belong to request.user.
    """
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)

    user_tz_name = getattr(request.user, 'timezone_pref', None) or settings.TIME_ZONE
    try:
        user_tz = zoneinfo.ZoneInfo(user_tz_name)
    except Exception:
        user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

    today = timezone.now().astimezone(user_tz).date()

    hlog, created = HabitLog.objects.get_or_create(
        habit=habit,
        user=request.user,
        log_date=today,
        defaults={'completed': True}
    )

    if not created:
        hlog.completed = not hlog.completed
        hlog.save()

    action_desc = "completed" if hlog.completed else "unmarked"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok',
            'habit_id': habit.id,
            'is_completed': hlog.completed,
            'message': f"Habit '{habit.name}' {action_desc} for today."
        })

    messages.success(request, f"Habit '{habit.name}' {action_desc} for today.")
    return redirect('core:dashboard')


@login_required
@require_POST
def quick_add_task_view(request):
    """
    Quick dashboard action to add a new task without visiting full task creation flow.
    Validates payload and enforces user ownership on category if selected.
    """
    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, "Task title is required.")
        return redirect('core:dashboard')

    priority = request.POST.get('priority', Priority.MEDIUM)
    if priority not in Priority.values:
        priority = Priority.MEDIUM

    due_date_str = request.POST.get('due_date', '').strip()
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            due_date = None

    est_minutes_str = request.POST.get('estimated_minutes', '').strip()
    estimated_minutes = None
    if est_minutes_str and est_minutes_str.isdigit():
        estimated_minutes = max(0, int(est_minutes_str))

    category_id = request.POST.get('category_id', '').strip()
    category = None
    if category_id and category_id.isdigit():
        category = Category.objects.filter(id=int(category_id), user=request.user).first()

    Task.objects.create(
        user=request.user,
        title=title,
        priority=priority,
        due_date=due_date,
        estimated_minutes=estimated_minutes,
        category=category,
        status=TaskStatus.PENDING
    )

    messages.success(request, f"Task '{title}' added to your backlog.")
    return redirect('core:dashboard')


@login_required
@require_POST
def quick_checkin_view(request):
    """
    Quick dashboard action to log biometric/psychometric check-in (mood, energy, sleep).
    Saves or updates DailyMetric for today.
    """
    user_tz_name = getattr(request.user, 'timezone_pref', None) or settings.TIME_ZONE
    try:
        user_tz = zoneinfo.ZoneInfo(user_tz_name)
    except Exception:
        user_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

    today = timezone.now().astimezone(user_tz).date()

    mood_str = request.POST.get('mood_score', '').strip()
    energy_str = request.POST.get('energy_score', '').strip()
    stress_str = request.POST.get('stress_score', '').strip()
    sleep_str = request.POST.get('sleep_hours', '').strip()
    notes = request.POST.get('notes', '').strip()

    def parse_int_range(val, min_v, max_v):
        try:
            v = int(val)
            return max(min_v, min(max_v, v))
        except (ValueError, TypeError):
            return None

    def parse_decimal_range(val, min_v, max_v):
        try:
            d = Decimal(val)
            return max(Decimal(str(min_v)), min(Decimal(str(max_v)), d))
        except Exception:
            return None

    mood_score = parse_int_range(mood_str, 1, 10)
    energy_score = parse_int_range(energy_str, 1, 10)
    stress_score = parse_int_range(stress_str, 1, 10)
    sleep_hours = parse_decimal_range(sleep_str, 0.0, 24.0)

    DailyMetric.objects.update_or_create(
        user=request.user,
        metric_date=today,
        defaults={
            'mood_score': mood_score,
            'energy_score': energy_score,
            'stress_score': stress_score,
            'sleep_hours': sleep_hours,
            'notes': notes,
        }
    )

    messages.success(request, "Daily biometric check-in recorded successfully.")
    return redirect('core:dashboard')


def ui_system(request):
    """
    Comprehensive Design System demonstration page displaying all 16 foundational
    UI components, color tokens, typography scales, and interactive elements.
    """
    context = {
        'page_title': 'UI Design System',
        'active_nav': 'ui_system',
    }
    return render(request, 'pages/ui_system.html', context)


def generic_module_view(request, template_name, title, active_nav, description=""):
    """
    Helper view for rendering modular placeholder pages using the shared layout.
    """
    context = {
        'page_title': title,
        'page_description': description,
        'active_nav': active_nav,
    }
    return render(request, template_name, context)


# Protected module views ensuring strict access control and zero broken navigation links
@login_required
def timetable_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Timetable', 'timetable',
        'Schedule optimization, calendar blocks, and dynamic time allocation.'
    )


@login_required
def routines_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Routines', 'routines',
        'Morning and evening rituals, recurring behavioral sequences, and habit triggers.'
    )


@login_required
def tasks_view(request):
    return generic_module_view(
        request, 'pages/tasks.html', 'Tasks & Productivity', 'tasks',
        'Prioritized action items, deep work sessions, and backlog management.'
    )


@login_required
def habits_view(request):
    return generic_module_view(
        request, 'pages/habits.html', 'Habits & Routines', 'habits',
        'Streak tracking, consistency analysis, and automated behavioral cues.'
    )


@login_required
def activities_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Activities', 'activities',
        'Ad-hoc time tracking, sports, recovery sessions, and leisure metrics.'
    )


@login_required
def checkin_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Check-in', 'checkin',
        'Subjective state logs, energy, stress, sleep score, and daily reflections.'
    )


@login_required
def study_view(request):
    return generic_module_view(
        request, 'pages/study.html', 'Study Management', 'study',
        'Coursework, syllabus mastery, active recall schedules, and learning sessions.'
    )


@login_required
def goals_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Goals & Milestones', 'goals',
        'High-level vision, quarterly milestones, and actionable objective breakdowns.'
    )


@login_required
def projects_view(request):
    return generic_module_view(
        request, 'pages/projects.html', 'Projects', 'projects',
        'Multi-stage deliverables, timeline planning, and associated task tracking.'
    )


@login_required
def journal_view(request):
    return generic_module_view(
        request, 'pages/journal.html', 'Journal Entries', 'journal',
        'Qualitative reflections, cognitive clarity logs, and freeform writing.'
    )


@login_required
def decisions_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Decisions Log', 'decisions',
        'Strategic decisions, mental models used, expected payoffs, and post-mortems.'
    )


@login_required
def mistakes_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Mistakes & Learning', 'mistakes',
        'Error analysis, root cause deduction, and anti-pattern mitigation.'
    )


@login_required
def productivity_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Productivity Analytics', 'productivity_analytics',
        'Time distribution, deep work ratios, task completion velocity, and interruptions.'
    )


@login_required
def study_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Study Analytics', 'study_analytics',
        'Retention curves, topic coverage, study session consistency, and revision status.'
    )


@login_required
def behavioral_insights_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Behavioral Insights', 'behavioral_insights',
        'Cross-correlations between sleep, nutrition, mood, and cognitive performance.'
    )


@login_required
def financial_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Financial Analytics', 'financial_analytics',
        'Income, expenses, runway calculations, and behavioral impulse spending audits.'
    )


# ==============================================================================
# NOTIFICATION VIEWS
# ==============================================================================

@login_required
def notification_list_view(request):
    """
    User notification center with domain filtering, unread status toggles,
    and bulk operations.
    """
    filter_type = request.GET.get('type', 'all').upper()
    status_filter = request.GET.get('status', 'all').lower()

    qs = Notification.objects.filter(user=request.user)

    if status_filter == 'unread':
        qs = qs.filter(is_read=False)
    elif status_filter == 'read':
        qs = qs.filter(is_read=True)

    if filter_type != 'ALL' and filter_type in NotificationType.values:
        qs = qs.filter(notification_type=filter_type)

    total_notifications = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    context = {
        'page_title': 'Notifications',
        'active_nav': 'notifications',
        'notifications': qs,
        'current_filter_type': filter_type,
        'current_status_filter': status_filter,
        'total_count': total_notifications,
        'unread_count': unread_count,
        'notification_types': NotificationType.choices,
    }
    return render(request, 'core/notifications.html', context)


@login_required
def mark_notification_read_view(request, notification_id):
    """
    Marks a specific notification as read.
    """
    notif = get_object_or_404(Notification, id=notification_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'is_read': True})

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('core:notifications')


@login_required
@require_POST
def mark_all_notifications_read_view(request):
    """
    Marks all notifications for the current user as read.
    """
    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, f"Marked {updated} notification{'s' if updated != 1 else ''} as read.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('core:notifications')


@login_required
def delete_notification_view(request, notification_id):
    """
    Deletes a single notification.
    """
    notif = get_object_or_404(Notification, id=notification_id, user=request.user)
    notif.delete()
    messages.success(request, "Notification deleted.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('core:notifications')


# ==============================================================================
# GLOBAL SEARCH VIEW
# ==============================================================================

@login_required
def global_search_view(request):
    """
    Multi-entity global search across tasks, habits, goals, projects,
    study subjects, topics, journal entries, decisions, mistakes, and activities.
    """
    query = request.GET.get('q', '').strip()
    search_data = GlobalSearchService.search(request.user, query)

    context = {
        'page_title': f"Search: {query}" if query else "Global Search",
        'active_nav': 'search',
        'query': query,
        'total_count': search_data['total_count'],
        'results_by_type': search_data['results_by_type'],
        'all_results': search_data['all_results'],
    }
    return render(request, 'core/search_results.html', context)


# ==============================================================================
# RECOMMENDATIONS VIEW
# ==============================================================================

@login_required
def recommendations_view(request):
    """
    Deterministic rule-based recommendations across Productivity, Study,
    Habits, Schedule, and Well-being.
    """
    category_filter = request.GET.get('category', 'all').strip()
    recommendations = RecommendationService.get_recommendations(request.user, category_filter=category_filter)

    categories = [
        ('all', 'All Recommendations'),
        ('productivity', 'Productivity'),
        ('study', 'Study & Learning'),
        ('habits', 'Habits'),
        ('schedule', 'Schedule & Time'),
        ('well-being', 'Well-being'),
    ]

    context = {
        'page_title': 'Personalized Recommendations',
        'active_nav': 'recommendations',
        'recommendations': recommendations,
        'current_category': category_filter.lower(),
        'categories': categories,
        'total_count': len(recommendations),
    }
    return render(request, 'core/recommendations.html', context)


@login_required
@require_POST
def dismiss_recommendation_view(request, rec_key):
    """
    Dismisses a recommendation key so it does not clutter the user's dashboard.
    """
    RecommendationService.dismiss_recommendation(request.user, rec_key)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'dismissed_key': rec_key})

    messages.info(request, "Recommendation dismissed.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return HttpResponseRedirect(referer)
    return redirect('core:recommendations')


@login_required
@require_POST
def reset_dismissed_recommendations_view(request):
    """
    Clears all dismissed recommendations for the user.
    """
    count = RecommendationService.reset_dismissed(request.user)
    messages.success(request, f"Reset {count} previously dismissed recommendation{'s' if count != 1 else ''}.")
    return redirect('core:recommendations')


# ==============================================================================
# DATA EXPORT VIEW
# ==============================================================================

@login_required
def data_export_view(request):
    """
    Self-service export page allowing user to download their complete LifeOS history
    in sanitized JSON or CSV format.
    """
    format_type = request.GET.get('format', '').lower()
    module_choice = request.GET.get('module', 'all').lower()

    if format_type == 'json':
        selected_modules = None if module_choice == 'all' else [module_choice]
        return ExportService.export_json_response(request.user, modules=selected_modules)
    elif format_type == 'csv':
        return ExportService.export_csv_response(request.user, module=module_choice)

    context = {
        'page_title': 'Export Personal Data',
        'active_nav': 'settings',
    }
    return render(request, 'core/export.html', context)


# ==============================================================================
# SETTINGS & USER PREFERENCES VIEW
# ==============================================================================

@login_required
def settings_view(request):
    """
    System & User settings page managing display preferences, notification toggles,
    daily work targets, and privacy/data management.
    """
    prefs = UserPreference.get_for_user(request.user)

    if request.method == 'POST':
        action = request.POST.get('action', 'save_preferences')

        if action == 'save_preferences':
            # Display Preferences
            date_fmt = request.POST.get('date_format', 'YYYY-MM-DD')
            time_fmt = request.POST.get('time_format', '24h')
            week_start = request.POST.get('week_start_day', 'monday')
            work_goal = request.POST.get('daily_work_goal_hours', '8.0')

            # Notification Toggles
            notify_tasks = 'notify_tasks' in request.POST
            notify_study = 'notify_study' in request.POST
            notify_routines = 'notify_routines' in request.POST
            notify_goals = 'notify_goals' in request.POST

            # Timezone
            tz_pref = request.POST.get('timezone_pref', request.user.timezone_pref).strip()
            if tz_pref:
                request.user.timezone_pref = tz_pref
                request.user.save(update_fields=['timezone_pref'])

            try:
                prefs.daily_work_goal_hours = Decimal(work_goal)
            except Exception:
                pass

            prefs.date_format = date_fmt
            prefs.time_format = time_fmt
            prefs.week_start_day = week_start
            prefs.notify_tasks = notify_tasks
            prefs.notify_study = notify_study
            prefs.notify_routines = notify_routines
            prefs.notify_goals = notify_goals
            prefs.save()

            messages.success(request, "Settings and preferences saved successfully.")
            return redirect('core:settings')

    context = {
        'page_title': 'Settings & Preferences',
        'active_nav': 'settings',
        'preferences': prefs,
        'user_tz': getattr(request.user, 'timezone_pref', 'Asia/Kolkata'),
    }
    return render(request, 'pages/settings.html', context)


# ==============================================================================
# PRODUCTION ERROR HANDLERS (HTTP 400, 403, 404, 500)
# ==============================================================================

def page_not_found_view(request, exception=None):
    """
    Custom 404 handler rendered with the LifeOS Minimal Modern Dark design system.
    """
    return render(request, '404.html', {
        'page_title': 'Page Not Found — LifeOS',
        'path': request.path,
    }, status=404)


def server_error_view(request):
    """
    Custom 500 handler rendered with the LifeOS Minimal Modern Dark design system.
    """
    return render(request, '500.html', {
        'page_title': 'Server Error — LifeOS',
    }, status=500)


def permission_denied_view(request, exception=None):
    """
    Custom 403 handler rendered with the LifeOS Minimal Modern Dark design system.
    """
    return render(request, '403.html', {
        'page_title': 'Access Denied — LifeOS',
        'path': request.path,
    }, status=403)


def bad_request_view(request, exception=None):
    """
    Custom 400 handler rendered with the LifeOS Minimal Modern Dark design system.
    """
    return render(request, '400.html', {
        'page_title': 'Bad Request — LifeOS',
    }, status=400)

