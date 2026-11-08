from django.urls import path
from .views import (
    goal_create_view,
    goal_delete_view,
    goal_detail_view,
    goal_link_task_view,
    goal_list_view,
    goal_unlink_task_view,
    goal_update_view,
    project_create_view,
    project_delete_view,
    project_detail_view,
    project_list_view,
    project_update_view,
)

app_name = 'planning'

urlpatterns = [
    # Goal Management
    path('goals/', goal_list_view, name='goal_list'),
    path('goals/create/', goal_create_view, name='goal_create'),
    path('goals/<int:pk>/', goal_detail_view, name='goal_detail'),
    path('goals/<int:pk>/edit/', goal_update_view, name='goal_update'),
    path('goals/<int:pk>/delete/', goal_delete_view, name='goal_delete'),
    path('goals/<int:pk>/link-task/', goal_link_task_view, name='goal_link_task'),
    path('goals/<int:pk>/unlink-task/<int:task_id>/', goal_unlink_task_view, name='goal_unlink_task'),

    # Project Management
    path('projects/', project_list_view, name='project_list'),
    path('projects/create/', project_create_view, name='project_create'),
    path('projects/<int:pk>/', project_detail_view, name='project_detail'),
    path('projects/<int:pk>/edit/', project_update_view, name='project_update'),
    path('projects/<int:pk>/delete/', project_delete_view, name='project_delete'),
]
