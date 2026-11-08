from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend allowing users to log in using their email address.
    Performs case-insensitive lookup and timing-attack mitigation.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        # Support identifier passed either as 'email' or 'username' parameter
        login_credential = email or username or kwargs.get('email')

        if not login_credential or not password:
            return None

        # Clean credential string
        login_credential = login_credential.strip()

        try:
            # Case-insensitive email lookup
            user = User.objects.get(email__iexact=login_credential)
        except User.DoesNotExist:
            # Fallback check against username field
            try:
                user = User.objects.get(username__iexact=login_credential)
            except User.DoesNotExist:
                # Mitigate timing attack by executing password hashing algorithm
                User().set_password(password)
                return None
        except User.MultipleObjectsReturned:
            # Defensive check
            user = User.objects.filter(email__iexact=login_credential).order_by('id').first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
