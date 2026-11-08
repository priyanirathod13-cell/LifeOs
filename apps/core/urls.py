from django.urls import path
from apps.planning.views import goal_list_view, project_list_view
from apps.productivity.views import (
    activity_list_view,
    category_list_view,
    daily_timetable_view,
    habit_list_view,
    routine_list_view,
    task_list_view,
)
from apps.study.views import study_analytics_view, study_dashboard_view
from .views import (
    behavioral_insights_view,
    checkin_view,
    dashboard,
    decisions_view,
    financial_analytics_view,
    health_check,
    journal_view,
    landing_view,
    mistakes_view,
    productivity_analytics_view,
    quick_add_task_view,
    quick_checkin_view,
    recommendations_view,
    routines_view,
    settings_view,
    timetable_view,
    toggle_habit_view,
    toggle_task_view,
    ui_system,
)

app_name = 'core'

urlpatterns = [
    # Public Root & Landing Page
    path('', landing_view, name='landing'),

    # Public Health Check (Step 01 foundation)
    path('health/', health_check, name='health_check'),

    # Protected Executive Dashboard
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/toggle-task/<int:task_id>/', toggle_task_view, name='toggle_task'),
    path('dashboard/toggle-habit/<int:habit_id>/', toggle_habit_view, name='toggle_habit'),
    path('dashboard/quick-add-task/', quick_add_task_view, name='quick_add_task'),
    path('dashboard/quick-checkin/', quick_checkin_view, name='quick_checkin'),

    # UI System Showcase
    path('ui-system/', ui_system, name='ui_system'),

    # MY DAY (Protected)
    path('timetable/', daily_timetable_view, name='timetable'),
    path('routines/', routine_list_view, name='routines'),
    path('tasks/', task_list_view, name='tasks'),
    path('categories/', category_list_view, name='categories'),
    path('habits/', habit_list_view, name='habits'),
    path('activities/', activity_list_view, name='activities'),
    path('checkin/', checkin_view, name='checkin'),

    # MY GROWTH (Protected)
    path('study/', study_dashboard_view, name='study'),
    path('goals/', goal_list_view, name='goals'),
    path('projects/', project_list_view, name='projects'),
    path('journal/', journal_view, name='journal'),
    path('decisions/', decisions_view, name='decisions'),
    path('mistakes/', mistakes_view, name='mistakes'),

    # MY INTELLIGENCE (Protected)
    path('analytics/productivity/', productivity_analytics_view, name='productivity_analytics'),
    path('analytics/study/', study_analytics_view, name='study_analytics'),
    path('analytics/behavioral/', behavioral_insights_view, name='behavioral_insights'),
    path('analytics/financial/', financial_analytics_view, name='financial_analytics'),
    path('recommendations/', recommendations_view, name='recommendations'),

    # SETTINGS (Protected)
    path('settings/', settings_view, name='settings'),
]
