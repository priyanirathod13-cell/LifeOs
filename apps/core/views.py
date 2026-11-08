from django.http import JsonResponse
from django.shortcuts import render


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


def dashboard(request):
    """
    Main application dashboard view showcasing daily rhythm, priority focus,
    and behavioral insights.
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


# Specific module views ensuring zero broken navigation links
def timetable_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Timetable', 'timetable',
        'Schedule optimization, calendar blocks, and dynamic time allocation.'
    )


def routines_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Routines', 'routines',
        'Morning and evening rituals, recurring behavioral sequences, and habit triggers.'
    )


def tasks_view(request):
    return generic_module_view(
        request, 'pages/tasks.html', 'Tasks & Productivity', 'tasks',
        'Prioritized action items, deep work sessions, and backlog management.'
    )


def habits_view(request):
    return generic_module_view(
        request, 'pages/habits.html', 'Habits & Routines', 'habits',
        'Streak tracking, consistency analysis, and automated behavioral cues.'
    )


def activities_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Activities', 'activities',
        'Ad-hoc time tracking, sports, recovery sessions, and leisure metrics.'
    )


def checkin_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Daily Check-in', 'checkin',
        'Subjective state logs, energy, stress, sleep score, and daily reflections.'
    )


def study_view(request):
    return generic_module_view(
        request, 'pages/study.html', 'Study Management', 'study',
        'Coursework, syllabus mastery, active recall schedules, and learning sessions.'
    )


def goals_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Goals & Milestones', 'goals',
        'High-level vision, quarterly milestones, and actionable objective breakdowns.'
    )


def projects_view(request):
    return generic_module_view(
        request, 'pages/projects.html', 'Projects', 'projects',
        'Multi-stage deliverables, timeline planning, and associated task tracking.'
    )


def journal_view(request):
    return generic_module_view(
        request, 'pages/journal.html', 'Journal Entries', 'journal',
        'Qualitative reflections, cognitive clarity logs, and freeform writing.'
    )


def decisions_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Decisions Log', 'decisions',
        'Strategic decisions, mental models used, expected payoffs, and post-mortems.'
    )


def mistakes_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Mistakes & Learning', 'mistakes',
        'Error analysis, root cause deduction, and anti-pattern mitigation.'
    )


def productivity_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Productivity Analytics', 'productivity_analytics',
        'Time distribution, deep work ratios, task completion velocity, and interruptions.'
    )


def study_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Study Analytics', 'study_analytics',
        'Retention curves, topic coverage, study session consistency, and revision status.'
    )


def behavioral_insights_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Behavioral Insights', 'behavioral_insights',
        'Cross-correlations between sleep, nutrition, mood, and cognitive performance.'
    )


def financial_analytics_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'Financial Analytics', 'financial_analytics',
        'Income, expenses, runway calculations, and behavioral impulse spending audits.'
    )


def recommendations_view(request):
    return generic_module_view(
        request, 'pages/placeholder.html', 'AI Recommendations', 'recommendations',
        'Personalized behavioral adjustments and schedule optimization recommendations.'
    )


def settings_view(request):
    return generic_module_view(
        request, 'pages/settings.html', 'Settings', 'settings',
        'User profile, system preferences, notification cadences, and security parameters.'
    )
