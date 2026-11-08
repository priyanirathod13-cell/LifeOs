from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main Executive Analytics Dashboard
    path('', views.analytics_dashboard_view, name='dashboard'),

    # Dedicated Analytics Pages
    path('productivity/', views.productivity_analytics_view, name='productivity'),
    path('study/', views.study_analytics_view, name='study'),
    path('habits/', views.habit_analytics_view, name='habits'),
    path('time/', views.time_analytics_view, name='time'),
    path('wellbeing/', views.wellbeing_analytics_view, name='wellbeing'),

    # Behavioral Insights Hub & Dismissal API
    path('insights/', views.behavioral_insights_view, name='insights'),
    path('insights/dismiss/', views.dismiss_insight_view, name='dismiss_insight'),
    path('insights/restore/', views.restore_insight_view, name='restore_insight'),

    # Multi-Period Comparison System
    path('compare/', views.comparison_view, name='compare'),
]
