from django.urls import path
from apps.analytics.views import (
    analytics_dashboard_view,
    behavioral_insights_view,
    productivity_analytics_view,
    study_analytics_view,
)
from apps.finance.views import finance_dashboard_view
from apps.personal.views import (
    daily_checkin_view,
    decision_list_view,
    journal_list_view,
    mistake_list_view,
    personal_dashboard_view,
)
from apps.planning.views import goal_list_view, project_list_view
from apps.productivity.views import (
    activity_list_view,
    category_list_view,
    daily_timetable_view,
    habit_list_view,
    routine_list_view,
    task_list_view,
)
from apps.study.views import study_dashboard_view
from .views import (
    dashboard,
    data_export_view,
    delete_notification_view,
    dismiss_recommendation_view,
    global_search_view,
    health_check,
    landing_view,
    mark_all_notifications_read_view,
    mark_notification_read_view,
    notification_list_view,
    quick_add_task_view,
    quick_checkin_view,
    recommendations_view,
    reset_dismissed_recommendations_view,
    settings_view,
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
    path('checkin/', daily_checkin_view, name='checkin'),

    # MY PERSONAL & GROWTH (Protected)
    path('personal/', personal_dashboard_view, name='personal'),
    path('study/', study_dashboard_view, name='study'),
    path('goals/', goal_list_view, name='goals'),
    path('projects/', project_list_view, name='projects'),
    path('journal/', journal_list_view, name='journal'),
    path('decisions/', decision_list_view, name='decisions'),
    path('mistakes/', mistake_list_view, name='mistakes'),

    # MY INTELLIGENCE (Protected)
    path('analytics/', analytics_dashboard_view, name='analytics'),
    path('analytics/productivity/', productivity_analytics_view, name='productivity_analytics'),
    path('analytics/study/', study_analytics_view, name='study_analytics'),
    path('analytics/behavioral/', behavioral_insights_view, name='behavioral_insights'),
    path('analytics/financial/', finance_dashboard_view, name='financial_analytics'),
    # NOTIFICATIONS (Protected)
    path('notifications/', notification_list_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', mark_notification_read_view, name='mark_notification_read'),
    path('notifications/read-all/', mark_all_notifications_read_view, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', delete_notification_view, name='delete_notification'),

    # GLOBAL SEARCH (Protected)
    path('search/', global_search_view, name='global_search'),

    # RECOMMENDATIONS (Protected)
    path('recommendations/', recommendations_view, name='recommendations'),
    path('recommendations/dismiss/<str:rec_key>/', dismiss_recommendation_view, name='dismiss_recommendation'),
    path('recommendations/reset/', reset_dismissed_recommendations_view, name='reset_dismissed_recommendations'),

    # SETTINGS & DATA EXPORT (Protected)
    path('settings/', settings_view, name='settings'),
    path('settings/export/', data_export_view, name='data_export'),
]
