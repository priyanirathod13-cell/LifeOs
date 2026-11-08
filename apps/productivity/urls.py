from django.urls import path
from .views import (
    activity_create_view,
    activity_delete_view,
    activity_list_view,
    activity_start_view,
    activity_stop_view,
    availability_create_view,
    availability_delete_view,
    availability_view,
    category_create_view,
    category_delete_view,
    category_list_view,
    category_update_view,
    daily_timetable_view,
    habit_create_view,
    habit_delete_view,
    habit_detail_view,
    habit_list_view,
    habit_log_view,
    habit_toggle_active_view,
    habit_update_view,
    routine_create_view,
    routine_delete_view,
    routine_list_view,
    routine_toggle_active_view,
    routine_update_view,
    schedule_block_create_view,
    schedule_block_delete_view,
    schedule_block_reschedule_view,
    schedule_block_status_view,
    schedule_block_update_view,
    schedule_generator_apply_view,
    schedule_generator_view,
    schedule_history_view,
    scheduling_preferences_view,
    task_create_view,
    task_delete_view,
    task_detail_view,
    task_list_view,
    task_toggle_complete_view,
    task_update_view,
    weekly_timetable_view,
)

app_name = 'productivity'

urlpatterns = [
    # Task Management
    path('tasks/', task_list_view, name='task_list'),
    path('tasks/create/', task_create_view, name='task_create'),
    path('tasks/<int:pk>/', task_detail_view, name='task_detail'),
    path('tasks/<int:pk>/edit/', task_update_view, name='task_update'),
    path('tasks/<int:pk>/delete/', task_delete_view, name='task_delete'),
    path('tasks/<int:pk>/complete/', task_toggle_complete_view, name='task_toggle_complete'),

    # Category Management
    path('categories/', category_list_view, name='category_list'),
    path('categories/create/', category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', category_update_view, name='category_update'),
    path('categories/<int:pk>/delete/', category_delete_view, name='category_delete'),

    # Habit Management
    path('habits/', habit_list_view, name='habit_list'),
    path('habits/create/', habit_create_view, name='habit_create'),
    path('habits/<int:pk>/', habit_detail_view, name='habit_detail'),
    path('habits/<int:pk>/edit/', habit_update_view, name='habit_update'),
    path('habits/<int:pk>/delete/', habit_delete_view, name='habit_delete'),
    path('habits/<int:pk>/log/', habit_log_view, name='habit_log'),
    path('habits/<int:pk>/toggle-active/', habit_toggle_active_view, name='habit_toggle_active'),

    # Activity Tracking
    path('activities/', activity_list_view, name='activity_list'),
    path('activities/create/', activity_create_view, name='activity_create'),
    path('activities/start/', activity_start_view, name='activity_start'),
    path('activities/<int:pk>/stop/', activity_stop_view, name='activity_stop'),
    path('activities/<int:pk>/delete/', activity_delete_view, name='activity_delete'),

    # 1. Daily & Weekly Timetable
    path('timetable/', daily_timetable_view, name='timetable_daily'),
    path('timetable/weekly/', weekly_timetable_view, name='timetable_weekly'),
    path('timetable/blocks/create/', schedule_block_create_view, name='block_create'),
    path('timetable/blocks/<int:pk>/edit/', schedule_block_update_view, name='block_update'),
    path('timetable/blocks/<int:pk>/delete/', schedule_block_delete_view, name='block_delete'),
    path('timetable/blocks/<int:pk>/status/', schedule_block_status_view, name='block_status'),
    path('timetable/blocks/<int:pk>/reschedule/', schedule_block_reschedule_view, name='block_reschedule'),

    # 2. Daily Routines
    path('routines/', routine_list_view, name='routine_list'),
    path('routines/create/', routine_create_view, name='routine_create'),
    path('routines/<int:pk>/edit/', routine_update_view, name='routine_update'),
    path('routines/<int:pk>/delete/', routine_delete_view, name='routine_delete'),
    path('routines/<int:pk>/toggle-active/', routine_toggle_active_view, name='routine_toggle_active'),

    # 3. Availability Management
    path('availability/', availability_view, name='availability_list'),
    path('availability/create/', availability_create_view, name='availability_create'),
    path('availability/<int:pk>/delete/', availability_delete_view, name='availability_delete'),

    # 4. Schedule Generator
    path('timetable/generator/', schedule_generator_view, name='generator'),
    path('timetable/generator/apply/', schedule_generator_apply_view, name='generator_apply'),

    # 5. Schedule History & Preferences
    path('timetable/history/', schedule_history_view, name='schedule_history'),
    path('timetable/preferences/', scheduling_preferences_view, name='scheduling_preferences'),
]
