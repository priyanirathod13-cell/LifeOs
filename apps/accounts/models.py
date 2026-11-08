from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for LifeOS.

    Inherits from AbstractUser to provide standard username, password,
    first_name, last_name, email, is_staff, is_active, and date_joined fields.

    Enhanced for Step 03:
    - Unique email constraint at both database and application levels.
    - Extensible profile attributes (bio, timezone preference).
    - Timestamp tracking.
    """
    # Enforce unique email at the database schema level
    email = models.EmailField(
        unique=True,
        max_length=254,
        verbose_name='email address',
        help_text='Required. Used as primary credential for authentication.'
    )

    # Extensible Profile Fields
    bio = models.TextField(
        blank=True,
        default='',
        max_length=500,
        verbose_name='Bio / Philosophy',
        help_text='Personal behavioral philosophy or life vision summary.'
    )
    timezone_pref = models.CharField(
        max_length=50,
        default='Asia/Kolkata',
        verbose_name='Timezone Preference',
        help_text='Preferred timezone for schedules, timetable and analytics.'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()

    def get_display_name(self):
        """Returns the user's full name or email handle for UI display."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return full_name
        if self.email:
            return self.email.split('@')[0]
        return self.username

    def __str__(self):
        return self.email if self.email else self.username
