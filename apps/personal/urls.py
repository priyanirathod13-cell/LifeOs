from django.urls import path
from apps.finance.views import finance_dashboard_view
from . import views

app_name = 'personal'

urlpatterns = [
    # Personal Dashboard
    path('personal/', views.personal_dashboard_view, name='dashboard'),

    # Journal
    path('personal/journal/', views.journal_list_view, name='journal_list'),
    path('personal/journal/create/', views.journal_create_view, name='journal_create'),
    path('personal/journal/<int:pk>/', views.journal_detail_view, name='journal_detail'),
    path('personal/journal/<int:pk>/edit/', views.journal_edit_view, name='journal_edit'),
    path('personal/journal/<int:pk>/delete/', views.journal_delete_view, name='journal_delete'),

    # Daily Check-in
    path('personal/checkin/', views.daily_checkin_view, name='checkin'),

    # Mood and Energy Tracking
    path('personal/mood-energy/', views.mood_energy_view, name='mood_energy'),

    # Sleep Tracking
    path('personal/sleep/', views.sleep_list_view, name='sleep_list'),
    path('personal/sleep/create/', views.sleep_create_view, name='sleep_create'),
    path('personal/sleep/<int:pk>/edit/', views.sleep_edit_view, name='sleep_edit'),
    path('personal/sleep/<int:pk>/delete/', views.sleep_delete_view, name='sleep_delete'),

    # Decision Journal
    path('personal/decisions/', views.decision_list_view, name='decision_list'),
    path('personal/decisions/create/', views.decision_create_view, name='decision_create'),
    path('personal/decisions/<int:pk>/', views.decision_detail_view, name='decision_detail'),
    path('personal/decisions/<int:pk>/edit/', views.decision_edit_view, name='decision_edit'),
    path('personal/decisions/<int:pk>/delete/', views.decision_delete_view, name='decision_delete'),
    path('personal/decisions/<int:pk>/options/add/', views.decision_option_add_view, name='decision_option_add'),
    path('personal/decisions/<int:pk>/options/<int:option_pk>/edit/', views.decision_option_edit_view, name='decision_option_edit'),
    path('personal/decisions/<int:pk>/options/<int:option_pk>/delete/', views.decision_option_delete_view, name='decision_option_delete'),
    path('personal/decisions/<int:pk>/options/<int:option_pk>/select/', views.decision_select_option_view, name='decision_select_option'),
    path('personal/decisions/<int:pk>/outcome/', views.decision_outcome_view, name='decision_outcome'),

    # Mistake Tracker
    path('personal/mistakes/', views.mistake_list_view, name='mistake_list'),
    path('personal/mistakes/create/', views.mistake_create_view, name='mistake_create'),
    path('personal/mistakes/<int:pk>/', views.mistake_detail_view, name='mistake_detail'),
    path('personal/mistakes/<int:pk>/edit/', views.mistake_edit_view, name='mistake_edit'),
    path('personal/mistakes/<int:pk>/delete/', views.mistake_delete_view, name='mistake_delete'),

    # Finance Integration under Personal
    path('personal/finance/', finance_dashboard_view, name='finance'),
]
