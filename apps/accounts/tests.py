from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings


class CustomUserModelTests(TestCase):
    """
    Test suite for LifeOS custom User model foundation.
    """

    def test_auth_user_model_setting(self):
        """AUTH_USER_MODEL must point to 'accounts.User'."""
        self.assertEqual(settings.AUTH_USER_MODEL, 'accounts.User')

    def test_create_standard_user(self):
        """Verify creating a standard user with the custom model."""
        User = get_user_model()
        user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertEqual(str(user), 'testuser')

    def test_create_superuser(self):
        """Verify creating a superuser with the custom model."""
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='adminpassword123'
        )
        self.assertEqual(admin_user.username, 'adminuser')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
