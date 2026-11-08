from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AuthenticationSystemTests(TestCase):
    """
    Comprehensive test suite for LifeOS Authentication Architecture (Step 03).
    Covers registration, login, session security, logout, profile management,
    access control, and password reset flows.
    """

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.profile_url = reverse('accounts:profile')
        self.dashboard_url = reverse('core:dashboard')

        # Baseline test user
        self.test_email = 'priyani@lifeos.internal'
        self.test_password = 'ComplexPassword@2026'
        self.user = User.objects.create_user(
            username=self.test_email,
            email=self.test_email,
            password=self.test_password,
            first_name='Priyani',
            last_name='Rathod',
            bio='Architecting behavioral systems.',
            timezone_pref='Asia/Kolkata'
        )

    # =========================================================================
    # 1. REGISTRATION TESTS
    # =========================================================================

    def test_registration_page_loads(self):
        """GET /accounts/register/ should render registration form."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertContains(response, 'Create Your Account')

    def test_successful_user_registration(self):
        """Valid registration creates account in MySQL, hashes password, and redirects to login."""
        payload = {
            'full_name': 'Aarav Patel',
            'email': 'aarav@example.com',
            'password': 'SecureP@ssword2026',
            'confirm_password': 'SecureP@ssword2026',
        }
        response = self.client.post(self.register_url, payload, follow=True)
        self.assertRedirects(response, self.login_url)

        # Verify user was created with normalized email
        created_user = User.objects.filter(email='aarav@example.com').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.first_name, 'Aarav')
        self.assertEqual(created_user.last_name, 'Patel')
        self.assertTrue(created_user.check_password('SecureP@ssword2026'))
        self.assertFalse(created_user.is_staff)

    def test_registration_duplicate_email_prevention(self):
        """Duplicate email registration is blocked case-insensitively."""
        payload = {
            'full_name': 'Duplicate User',
            'email': 'PRIYANI@LIFEOS.INTERNAL',  # Different case of existing email
            'password': 'AnotherPassword123!',
            'confirm_password': 'AnotherPassword123!',
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, 'form', 'email',
            'An account with this email address already exists.'
        )

    def test_registration_password_mismatch(self):
        """Mismatched passwords return clear validation error."""
        payload = {
            'full_name': 'Test User',
            'email': 'newuser@example.com',
            'password': 'SecureP@ssword2026',
            'confirm_password': 'DifferentPassword2026',
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response, 'form', 'confirm_password',
            'Passwords do not match. Please re-enter.'
        )

    def test_registration_weak_password_rejected(self):
        """Weak passwords (e.g. too short or entirely numeric) fail validation."""
        payload = {
            'full_name': 'Short Password User',
            'email': 'shortpass@example.com',
            'password': '123',
            'confirm_password': '123',
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors.get('password'))

    # =========================================================================
    # 2. LOGIN & SESSION TESTS
    # =========================================================================

    def test_login_page_loads(self):
        """GET /accounts/login/ renders the login form."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Welcome Back')

    def test_successful_login(self):
        """User logs in with email and password, redirects to dashboard."""
        payload = {
            'email': 'priyani@lifeos.internal',
            'password': self.test_password,
        }
        response = self.client.post(self.login_url, payload, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_case_insensitive_email_login(self):
        """User can log in with mixed-case email string."""
        payload = {
            'email': 'Priyani@LifeOS.Internal',
            'password': self.test_password,
        }
        response = self.client.post(self.login_url, payload, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_invalid_login_credentials(self):
        """Wrong password displays generic error message without leaking account existence."""
        payload = {
            'email': self.test_email,
            'password': 'WrongPassword123',
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email address or password.')

    def test_nonexistent_email_login(self):
        """Nonexistent email returns identical generic error message."""
        payload = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123',
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email address or password.')

    def test_login_remember_me_controls_session_expiry(self):
        """Remember Me sets 14-day expiry; unchecked sets session to expire on browser close."""
        # 1. Unchecked Remember Me -> expires when browser closes
        self.client.post(self.login_url, {
            'email': self.test_email,
            'password': self.test_password,
            'remember_me': False,
        })
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()

        # 2. Checked Remember Me -> persistent session for 14 days
        self.client.post(self.login_url, {
            'email': self.test_email,
            'password': self.test_password,
            'remember_me': True,
        })
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertEqual(self.client.session.get_expiry_age(), 1209600)

    def test_login_redirect_next_parameter(self):
        """Redirects to ?next= URL upon successful login."""
        target_url = reverse('core:tasks')
        login_with_next = f"{self.login_url}?next={target_url}"
        response = self.client.post(login_with_next, {
            'email': self.test_email,
            'password': self.test_password,
        }, follow=True)
        self.assertRedirects(response, target_url)

    # =========================================================================
    # 3. LOGOUT TESTS
    # =========================================================================

    def test_logout_ends_session(self):
        """Logging out ends session and redirects to landing page."""
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.post(self.logout_url, follow=True)
        self.assertRedirects(response, reverse('core:landing'))
        self.assertFalse(response.context['user'].is_authenticated)

    # =========================================================================
    # 4. ACCESS CONTROL & USER ISOLATION
    # =========================================================================

    def test_unauthenticated_access_redirects_to_login(self):
        """Protected routes require authentication and redirect unauthenticated requests."""
        protected_routes = [
            reverse('core:dashboard'),
            reverse('core:tasks'),
            reverse('core:habits'),
            reverse('core:study'),
            reverse('core:journal'),
            reverse('accounts:profile'),
        ]
        for route in protected_routes:
            response = self.client.get(route)
            expected_redirect = f"{self.login_url}?next={route}"
            self.assertRedirects(response, expected_redirect)

    def test_authenticated_user_accesses_protected_route(self):
        """Authenticated user has full access to their dashboard and modules."""
        self.client.login(email=self.test_email, password=self.test_password)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/dashboard.html')

    # =========================================================================
    # 5. USER PROFILE & SETTINGS TESTS
    # =========================================================================

    def test_user_profile_view_and_update(self):
        """User can view and update their profile details."""
        self.client.login(email=self.test_email, password=self.test_password)

        # GET profile
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Priyani Rathod')
        self.assertContains(response, self.test_email)

        # POST update
        update_payload = {
            'action': 'update_profile',
            'full_name': 'Priyani R. Rathod',
            'bio': 'Updated behavioral intelligence philosophy.',
            'timezone_pref': 'UTC',
        }
        post_response = self.client.post(self.profile_url, update_payload, follow=True)
        self.assertEqual(post_response.status_code, 200)

        # Verify database update
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Priyani')
        self.assertEqual(self.user.last_name, 'R. Rathod')
        self.assertEqual(self.user.bio, 'Updated behavioral intelligence philosophy.')
        self.assertEqual(self.user.timezone_pref, 'UTC')

    def test_user_password_change(self):
        """User can change password from profile view and active session is maintained."""
        self.client.login(email=self.test_email, password=self.test_password)
        new_password = 'NewComplexPassword@2026'

        payload = {
            'action': 'change_password',
            'old_password': self.test_password,
            'new_password1': new_password,
            'new_password2': new_password,
        }
        response = self.client.post(self.profile_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify user can authenticate with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    # =========================================================================
    # 6. PASSWORD RESET WORKFLOW TESTS
    # =========================================================================

    def test_password_reset_flow(self):
        """Password reset request dispatches email with valid token link."""
        reset_url = reverse('accounts:password_reset')
        response = self.client.post(reset_url, {'email': self.test_email}, follow=True)
        self.assertRedirects(response, reverse('accounts:password_reset_done'))

        # Check console email backend delivery
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn(self.test_email, sent_email.to)
        self.assertIn('password-reset-confirm', sent_email.body)
