from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for LifeOS.

    Inherits from AbstractUser to provide standard username, password,
    first_name, last_name, email, is_staff, is_active, and date_joined fields.

    Extensible foundation for future profile and behavioral tracking attributes
    (e.g., timezone preferences, bio, avatar, notification settings) in later steps.
    """
    # Track model creation and updates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username
