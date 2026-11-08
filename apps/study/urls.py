from django.urls import path
from .views import (
    exam_create_view,
    exam_delete_view,
    exam_list_view,
    exam_update_view,
    revision_create_view,
    revision_delete_view,
    revision_list_view,
    revision_reschedule_view,
    revision_toggle_complete_view,
    study_analytics_view,
    study_dashboard_view,
    study_plan_create_view,
    study_plan_delete_view,
    study_plan_status_view,
    study_plan_update_view,
    study_planner_view,
    study_session_create_view,
    study_session_delete_view,
    study_session_start_view,
    study_session_stop_view,
    study_session_update_view,
    study_sessions_view,
    subject_create_view,
    subject_delete_view,
    subject_detail_view,
    subject_list_view,
    subject_update_view,
    syllabus_tracker_view,
    topic_create_view,
    topic_delete_view,
    topic_list_view,
    topic_toggle_complete_view,
    topic_update_view,
)

app_name = 'study'

urlpatterns = [
    # 1. Study Dashboard
    path('study/', study_dashboard_view, name='dashboard'),
    path('study/dashboard/', study_dashboard_view, name='dashboard_alias'),

    # 2. Subjects
    path('study/subjects/', subject_list_view, name='subject_list'),
    path('study/subjects/create/', subject_create_view, name='subject_create'),
    path('study/subjects/<int:pk>/', subject_detail_view, name='subject_detail'),
    path('study/subjects/<int:pk>/edit/', subject_update_view, name='subject_update'),
    path('study/subjects/<int:pk>/delete/', subject_delete_view, name='subject_delete'),

    # 3. Topics & Chapters
    path('study/topics/', topic_list_view, name='topic_list'),
    path('study/topics/create/', topic_create_view, name='topic_create'),
    path('study/topics/<int:pk>/edit/', topic_update_view, name='topic_update'),
    path('study/topics/<int:pk>/delete/', topic_delete_view, name='topic_delete'),
    path('study/topics/<int:pk>/toggle/', topic_toggle_complete_view, name='topic_toggle'),

    # 4. Syllabus Tracker
    path('study/syllabus/', syllabus_tracker_view, name='syllabus'),

    # 5. Study Planner
    path('study/planner/', study_planner_view, name='planner'),
    path('study/planner/create/', study_plan_create_view, name='planner_create'),
    path('study/planner/<int:pk>/edit/', study_plan_update_view, name='planner_update'),
    path('study/planner/<int:pk>/delete/', study_plan_delete_view, name='planner_delete'),
    path('study/planner/<int:pk>/status/', study_plan_status_view, name='planner_status'),

    # 6. Study Sessions (Tracking & Timer)
    path('study/sessions/', study_sessions_view, name='sessions'),
    path('study/sessions/start/', study_session_start_view, name='session_start'),
    path('study/sessions/<int:pk>/stop/', study_session_stop_view, name='session_stop'),
    path('study/sessions/create/', study_session_create_view, name='session_create'),
    path('study/sessions/<int:pk>/edit/', study_session_update_view, name='session_update'),
    path('study/sessions/<int:pk>/delete/', study_session_delete_view, name='session_delete'),

    # 7. Revision Planner
    path('study/revisions/', revision_list_view, name='revisions'),
    path('study/revisions/create/', revision_create_view, name='revision_create'),
    path('study/revisions/<int:pk>/toggle/', revision_toggle_complete_view, name='revision_toggle'),
    path('study/revisions/<int:pk>/reschedule/', revision_reschedule_view, name='revision_reschedule'),
    path('study/revisions/<int:pk>/delete/', revision_delete_view, name='revision_delete'),

    # 8. Exams & Assessments
    path('study/exams/', exam_list_view, name='exams'),
    path('study/exams/create/', exam_create_view, name='exam_create'),
    path('study/exams/<int:pk>/edit/', exam_update_view, name='exam_update'),
    path('study/exams/<int:pk>/delete/', exam_delete_view, name='exam_delete'),

    # 9. Study Analytics
    path('study/analytics/', study_analytics_view, name='analytics'),
]
