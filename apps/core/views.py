from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render


def health_check(request):
    """
    Health-check endpoint confirming the LifeOS application is operational.

    Returns:
        JsonResponse with service health status and application identifier.
    """
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
    Protected application dashboard view showcasing daily rhythm, priority focus,
    and behavioral insights for the currently authenticated user.
    """
    context = {
        'page_title': 'Dashboard',
        'active_nav': 'dashboard',
    }
    return render(request, 'pages/dashboard.html', context)


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


@login_required
def recommendations_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'AI Recommendations', 'recommendations',
        'Personalized behavioral adjustments and schedule optimization recommendations.'
    )


@login_required
def settings_view(request):
    return generic_module_view(
        request, 'pages/settings.html', 'Settings', 'settings',
        'User profile, system preferences, notification cadences, and security parameters.'
    )
