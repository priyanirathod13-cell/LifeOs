from django.urls import path
from .views import (
    health_check,
    dashboard,
    ui_system,
    timetable_view,
    routines_view,
    tasks_view,
    habits_view,
    activities_view,
    checkin_view,
    study_view,
    goals_view,
    projects_view,
    journal_view,
    decisions_view,
    mistakes_view,
    productivity_analytics_view,
    study_analytics_view,
    behavioral_insights_view,
    financial_analytics_view,
    recommendations_view,
    settings_view,
)

app_name = 'core'

urlpatterns = [
    # Health Check (Step 01 foundation)
    path('health/', health_check, name='health_check'),

    # Core Dashboard & UI System Demonstration
    path('', dashboard, name='dashboard'),
    path('ui-system/', ui_system, name='ui_system'),

    # MY DAY
    path('timetable/', timetable_view, name='timetable'),
    path('routines/', routines_view, name='routines'),
    path('tasks/', tasks_view, name='tasks'),
    path('habits/', habits_view, name='habits'),
    path('activities/', activities_view, name='activities'),
    path('checkin/', checkin_view, name='checkin'),

    # MY GROWTH
    path('study/', study_view, name='study'),
    path('goals/', goals_view, name='goals'),
    path('projects/', projects_view, name='projects'),
    path('journal/', journal_view, name='journal'),
    path('decisions/', decisions_view, name='decisions'),
    path('mistakes/', mistakes_view, name='mistakes'),

    # MY INTELLIGENCE
    path('analytics/productivity/', productivity_analytics_view, name='productivity_analytics'),
    path('analytics/study/', study_analytics_view, name='study_analytics'),
    path('analytics/behavioral/', behavioral_insights_view, name='behavioral_insights'),
    path('analytics/financial/', financial_analytics_view, name='financial_analytics'),
    path('recommendations/', recommendations_view, name='recommendations'),

    # SETTINGS
    path('settings/', settings_view, name='settings'),
]
