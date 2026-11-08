from django.urls import path
from .views import (
    activity_create_view,
    activity_delete_view,
    activity_list_view,
    activity_start_view,
    activity_stop_view,
    category_create_view,
    category_delete_view,
    category_list_view,
    category_update_view,
    habit_create_view,
    habit_delete_view,
    habit_detail_view,
    habit_list_view,
    habit_log_view,
    habit_toggle_active_view,
    habit_update_view,
    task_create_view,
    task_delete_view,
    task_detail_view,
    task_list_view,
    task_toggle_complete_view,
    task_update_view,
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
]
