from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, Q, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.productivity.models import Category, Priority, Task, TaskStatus
from .forms import GoalForm, GoalTaskLinkForm, ProjectForm
from .models import Goal, GoalStatus, GoalTask, Project, ProjectStatus


# ==============================================================================
# 1. GOAL MANAGEMENT VIEWS
# ==============================================================================

@login_required
def goal_list_view(request):
    """
    Strategic goals overview with status filtering, deadline countdowns,
    and linked task progress indicators.
    """
    today = timezone.localtime(timezone.now()).date()
    qs = Goal.objects.filter(user=request.user).select_related('category').prefetch_related('goal_tasks__task')

    # Metrics
    total_count = qs.count()
    active_count = qs.filter(status__in=[GoalStatus.NOT_STARTED, GoalStatus.IN_PROGRESS]).count()
    achieved_count = qs.filter(status=GoalStatus.ACHIEVED).count()
    approaching_count = qs.filter(
        status__in=[GoalStatus.NOT_STARTED, GoalStatus.IN_PROGRESS],
        target_date__isnull=False,
        target_date__gte=today,
        target_date__lte=today + timedelta(days=30)
    ).count()
    overdue_count = qs.filter(
        status__in=[GoalStatus.NOT_STARTED, GoalStatus.IN_PROGRESS],
        target_date__isnull=False,
        target_date__lt=today
    ).count()

    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in GoalStatus.values:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '').strip()
    if priority_filter and priority_filter in Priority.values:
        qs = qs.filter(priority=priority_filter)

    goals = list(qs.order_by(
        Case(When(status=GoalStatus.ACHIEVED, then=1), default=0),
        'target_date',
        '-created_at'
    ))

    goals_data = []
    for g in goals:
        total_tasks = g.goal_tasks.count()
        completed_tasks = g.goal_tasks.filter(task__status=TaskStatus.COMPLETED).count()
        progress_pct = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else None
        days_left = (g.target_date - today).days if g.target_date else None
        is_overdue = bool(days_left is not None and days_left < 0 and g.status != GoalStatus.ACHIEVED)

        goals_data.append({
            'goal': g,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress_pct': progress_pct,
            'days_left': days_left,
            'is_overdue': is_overdue,
        })

    context = {
        'page_title': 'Goals & Milestones',
        'active_nav': 'goals',
        'goals_data': goals_data,
        'today': today,

        # Metrics
        'total_count': total_count,
        'active_count': active_count,
        'achieved_count': achieved_count,
        'approaching_count': approaching_count,
        'overdue_count': overdue_count,

        # Filters
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'statuses': GoalStatus.choices,
        'priorities': Priority.choices,
    }
    return render(request, 'planning/goals.html', context)


@login_required
def goal_create_view(request):
    """
    Define a new strategic goal with target milestones.
    """
    if request.method == 'POST':
        form = GoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            if goal.status == GoalStatus.ACHIEVED:
                goal.achieved_at = timezone.now()
            goal.save()
            messages.success(request, f"Goal '{goal.title}' created.")
            return redirect('planning:goal_list')
    else:
        form = GoalForm(user=request.user)

    context = {
        'page_title': 'Set New Goal',
        'active_nav': 'goals',
        'form': form,
    }
    return render(request, 'planning/goal_form.html', context)


@login_required
def goal_detail_view(request, pk):
    """
    Goal detail view listing all associated tasks, target countdowns,
    and task link/unlink actions.
    """
    goal = get_object_or_404(
        Goal.objects.select_related('category').prefetch_related('goal_tasks__task__category'),
        pk=pk,
        user=request.user
    )
    today = timezone.localtime(timezone.now()).date()

    goal_tasks = goal.goal_tasks.all()
    total_tasks = goal_tasks.count()
    completed_tasks = sum(1 for gt in goal_tasks if gt.task.status == TaskStatus.COMPLETED)
    progress_pct = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else None
    days_left = (goal.target_date - today).days if goal.target_date else None
    is_overdue = bool(days_left is not None and days_left < 0 and goal.status != GoalStatus.ACHIEVED)

    link_form = GoalTaskLinkForm(user=request.user, goal=goal)

    context = {
        'page_title': goal.title,
        'active_nav': 'goals',
        'goal': goal,
        'goal_tasks': goal_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress_pct': progress_pct,
        'days_left': days_left,
        'is_overdue': is_overdue,
        'link_form': link_form,
    }
    return render(request, 'planning/goal_detail.html', context)


@login_required
def goal_update_view(request, pk):
    """
    Update goal information and status.
    """
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    prev_status = goal.status

    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            updated_goal = form.save(commit=False)
            if updated_goal.status == GoalStatus.ACHIEVED and prev_status != GoalStatus.ACHIEVED:
                updated_goal.achieved_at = timezone.now()
            elif updated_goal.status != GoalStatus.ACHIEVED:
                updated_goal.achieved_at = None
            updated_goal.save()
            messages.success(request, f"Goal '{updated_goal.title}' updated.")
            return redirect('planning:goal_detail', pk=updated_goal.pk)
    else:
        form = GoalForm(instance=goal, user=request.user)

    context = {
        'page_title': f"Edit Goal — {goal.title}",
        'active_nav': 'goals',
        'form': form,
        'goal': goal,
    }
    return render(request, 'planning/goal_form.html', context)


@login_required
def goal_delete_view(request, pk):
    """
    Delete goal with confirmation. Linked tasks remain intact.
    """
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        title = goal.title
        goal.delete()
        messages.success(request, f"Goal '{title}' deleted. Linked tasks were preserved.")
        return redirect('planning:goal_list')

    context = {
        'page_title': f"Delete Goal — {goal.title}",
        'active_nav': 'goals',
        'goal': goal,
        'linked_tasks_count': goal.goal_tasks.count(),
    }
    return render(request, 'planning/goal_confirm_delete.html', context)


@login_required
@require_POST
def goal_link_task_view(request, pk):
    """
    Associate an existing task with this goal. Strictly validates that
    both goal and task belong to request.user.
    """
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    task_id = request.POST.get('task')
    task = get_object_or_404(Task, id=task_id, user=request.user)

    GoalTask.objects.get_or_create(goal=goal, task=task)
    messages.success(request, f"Linked task '{task.title}' to '{goal.title}'.")
    return redirect('planning:goal_detail', pk=goal.pk)


@login_required
@require_POST
def goal_unlink_task_view(request, pk, task_id):
    """
    Remove task association from goal without deleting the underlying task.
    """
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    task = get_object_or_404(Task, id=task_id, user=request.user)

    GoalTask.objects.filter(goal=goal, task=task).delete()
    messages.success(request, f"Unlinked task '{task.title}' from '{goal.title}'.")
    return redirect('planning:goal_detail', pk=goal.pk)


# ==============================================================================
# 2. PROJECT MANAGEMENT VIEWS
# ==============================================================================

@login_required
def project_list_view(request):
    """
    Project overview displaying status, priority, target dates, and task completion rates.
    """
    today = timezone.localtime(timezone.now()).date()
    qs = Project.objects.filter(user=request.user).select_related('category').prefetch_related('tasks')

    total_count = qs.count()
    active_count = qs.filter(status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS]).count()
    completed_count = qs.filter(status=ProjectStatus.COMPLETED).count()
    approaching_count = qs.filter(
        status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS],
        target_date__isnull=False,
        target_date__gte=today,
        target_date__lte=today + timedelta(days=30)
    ).count()

    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in ProjectStatus.values:
        qs = qs.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '').strip()
    if priority_filter and priority_filter in Priority.values:
        qs = qs.filter(priority=priority_filter)

    projects = list(qs.order_by(
        Case(When(status=ProjectStatus.COMPLETED, then=1), default=0),
        'target_date',
        '-created_at'
    ))

    projects_data = []
    for p in projects:
        tasks = p.tasks.all()
        total_p_tasks = tasks.count()
        completed_p_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        progress_pct = round((completed_p_tasks / total_p_tasks) * 100) if total_p_tasks > 0 else None
        days_left = (p.target_date - today).days if p.target_date else None
        is_overdue = bool(days_left is not None and days_left < 0 and p.status != ProjectStatus.COMPLETED)

        projects_data.append({
            'project': p,
            'total_tasks': total_p_tasks,
            'completed_tasks': completed_p_tasks,
            'progress_pct': progress_pct,
            'days_left': days_left,
            'is_overdue': is_overdue,
        })

    context = {
        'page_title': 'Projects',
        'active_nav': 'projects',
        'projects_data': projects_data,
        'today': today,

        # Metrics
        'total_count': total_count,
        'active_count': active_count,
        'completed_count': completed_count,
        'approaching_count': approaching_count,

        # Filters
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'statuses': ProjectStatus.choices,
        'priorities': Priority.choices,
    }
    return render(request, 'planning/projects.html', context)


@login_required
def project_create_view(request):
    """
    Create a new project.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            if project.status == ProjectStatus.COMPLETED:
                project.completed_at = timezone.now()
            project.save()
            messages.success(request, f"Project '{project.title}' created.")
            return redirect('planning:project_list')
    else:
        form = ProjectForm(user=request.user)

    context = {
        'page_title': 'Create Project',
        'active_nav': 'projects',
        'form': form,
    }
    return render(request, 'planning/project_form.html', context)


@login_required
def project_detail_view(request, pk):
    """
    Project detail view displaying milestone deadlines, associated tasks,
    and progress tracking.
    """
    project = get_object_or_404(
        Project.objects.select_related('category').prefetch_related('tasks__category'),
        pk=pk,
        user=request.user
    )
    today = timezone.localtime(timezone.now()).date()

    tasks = project.tasks.all().order_by(
        Case(When(status=TaskStatus.COMPLETED, then=1), default=0),
        'due_date'
    )
    total_tasks = tasks.count()
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    progress_pct = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else None
    days_left = (project.target_date - today).days if project.target_date else None
    is_overdue = bool(days_left is not None and days_left < 0 and project.status != ProjectStatus.COMPLETED)

    context = {
        'page_title': project.title,
        'active_nav': 'projects',
        'project': project,
        'tasks': tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress_pct': progress_pct,
        'days_left': days_left,
        'is_overdue': is_overdue,
    }
    return render(request, 'planning/project_detail.html', context)


@login_required
def project_update_view(request, pk):
    """
    Update project details and completion status.
    """
    project = get_object_or_404(Project, pk=pk, user=request.user)
    prev_status = project.status

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            updated_p = form.save(commit=False)
            if updated_p.status == ProjectStatus.COMPLETED and prev_status != ProjectStatus.COMPLETED:
                updated_p.completed_at = timezone.now()
            elif updated_p.status != ProjectStatus.COMPLETED:
                updated_p.completed_at = None
            updated_p.save()
            messages.success(request, f"Project '{updated_p.title}' updated.")
            return redirect('planning:project_detail', pk=updated_p.pk)
    else:
        form = ProjectForm(instance=project, user=request.user)

    context = {
        'page_title': f"Edit Project — {project.title}",
        'active_nav': 'projects',
        'form': form,
        'project': project,
    }
    return render(request, 'planning/project_form.html', context)


@login_required
def project_delete_view(request, pk):
    """
    Delete project with confirmation. Associated tasks have project unassigned safely.
    """
    project = get_object_or_404(Project, pk=pk, user=request.user)
    if request.method == 'POST':
        title = project.title
        # on_delete=models.SET_NULL unassigns project on tasks
        project.delete()
        messages.success(request, f"Project '{title}' deleted. Associated tasks were preserved.")
        return redirect('planning:project_list')

    context = {
        'page_title': f"Delete Project — {project.title}",
        'active_nav': 'projects',
        'project': project,
        'tasks_count': project.tasks.count(),
    }
    return render(request, 'planning/project_confirm_delete.html', context)
