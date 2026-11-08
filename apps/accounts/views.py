from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, RegistrationForm, UserProfileForm


def register_view(request):
    """
    Public registration view allowing new users to create an account.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Account created successfully for {user.email}! Please sign in to access your dashboard."
            )
            return redirect('accounts:login')
    else:
        form = RegistrationForm()

    context = {
        'form': form,
        'page_title': 'Create Account',
    }
    return render(request, 'accounts/register.html', context)


def login_view(request):
    """
    Public login view with email, password, and optional Remember Me persistence.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Session persistence management (Remember Me)
            if form.cleaned_data.get('remember_me'):
                # 2 weeks session expiry
                request.session.set_expiry(1209600)
            else:
                # Session expires on browser close
                request.session.set_expiry(0)

            messages.success(request, f"Welcome back, {user.get_display_name()}!")

            # Security: Validate redirect URL to prevent open-redirect attacks
            if redirect_to and url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(redirect_to)

            return redirect('core:dashboard')
    else:
        form = LoginForm(request=request)

    context = {
        'form': form,
        'page_title': 'Sign In',
        'next': redirect_to,
    }
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    """
    Secure logout ending the authenticated session and redirecting to the landing page.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been securely signed out of LifeOS.")
    return redirect('core:landing')


@login_required
def profile_view(request):
    """
    User profile management view allowing users to update their personal details,
    bio, timezone, and securely change their account password.
    """
    user = request.user
    profile_form = UserProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been updated successfully.")
                return redirect('accounts:profile')
            else:
                messages.error(request, "Please correct the errors in the profile form.")

        elif action == 'change_password':
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user_updated = password_form.save()
                # Maintain the user's active session after password change
                update_session_auth_hash(request, user_updated)
                messages.success(request, "Your master password has been successfully updated.")
                return redirect('accounts:profile')
            else:
                messages.error(request, "Please correct the errors in the password form.")

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'page_title': 'Account & Profile Settings',
        'active_nav': 'settings',
    }
    return render(request, 'accounts/profile.html', context)


# ==============================================================================
# PASSWORD RESET WORKFLOW (Customized Django Views)
# ==============================================================================

class LifeOSPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class LifeOSPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class LifeOSPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class LifeOSPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
