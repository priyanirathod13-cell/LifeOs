from django.urls import path
from .views import (
    LifeOSPasswordResetCompleteView,
    LifeOSPasswordResetConfirmView,
    LifeOSPasswordResetDoneView,
    LifeOSPasswordResetView,
    login_view,
    logout_view,
    profile_view,
    register_view,
)

app_name = 'accounts'

urlpatterns = [
    # Registration & Authentication
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # User Profile & Account Settings
    path('profile/', profile_view, name='profile'),

    # Password Reset Flow
    path('password-reset/', LifeOSPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', LifeOSPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', LifeOSPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', LifeOSPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
