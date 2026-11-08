from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class CoreAndLandingTests(TestCase):
    """
    Test suite for LifeOS core endpoints, public landing page, and protected views.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@lifeos.internal',
            email='testuser@lifeos.internal',
            password='TestPassword@2026',
            first_name='Test',
            last_name='User'
        )

    def test_health_check_status_code(self):
        """GET /health/ must return HTTP 200 OK (Step 01 preservation)."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_check_response_payload(self):
        """GET /health/ must return the exact expected JSON structure."""
        response = self.client.get('/health/')
        self.assertEqual(response.json(), {
            "status": "ok",
            "application": "LifeOS"
        })

    def test_public_landing_page_unauthenticated(self):
        """Unauthenticated user accessing '/' sees public Landing Page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/landing.html')
        self.assertContains(response, 'Personal')
        self.assertContains(response, 'Behavioral Intelligence')
        self.assertContains(response, 'Create Account')

    def test_root_redirects_to_dashboard_when_authenticated(self):
        """Authenticated user accessing '/' is redirected to their dashboard."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')
        response = self.client.get('/')
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_dashboard_view_authenticated(self):
        """Authenticated user accessing '/dashboard/' renders dashboard."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/dashboard.html')
        self.assertTemplateUsed(response, 'layouts/app_layout.html')
        self.assertContains(response, 'Behavioral Dashboard')

    def test_ui_system_showcase_accessible(self):
        """Design system demonstration page is accessible at /ui-system/."""
        response = self.client.get(reverse('core:ui_system'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/ui_system.html')
        self.assertContains(response, 'LifeOS Design System')

    def test_all_sidebar_navigation_routes_accessible_when_authenticated(self):
        """Verify that every single sidebar navigation link returns HTTP 200 for authenticated users."""
        self.client.login(email='testuser@lifeos.internal', password='TestPassword@2026')

        nav_routes = [
            'core:dashboard',
            'core:ui_system',
            'core:timetable',
            'core:routines',
            'core:tasks',
            'core:habits',
            'core:activities',
            'core:checkin',
            'core:study',
            'core:goals',
            'core:projects',
            'core:journal',
            'core:decisions',
            'core:mistakes',
            'core:productivity_analytics',
            'core:study_analytics',
            'core:behavioral_insights',
            'core:financial_analytics',
            'core:recommendations',
            'core:settings',
        ]

        for route_name in nav_routes:
            url = reverse(route_name)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"Expected route '{route_name}' ({url}) to return 200 OK, got {response.status_code}"
            )
